#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_storage_and_config.py: File access and settings
#
#  Description:
#  Assert the two modules that stand between the calculations and the
#  world: the one that names and writes files, and the one that decides
#  where they go.
#
#  The settings tests exist mostly to pin the precedence rule. A value
#  can arrive from four places, and a pipeline that runs unattended at
#  18:10 is not the place to discover that they were consulted in a
#  different order than documented.
#
#  Test Cases:
#  - File names follow the contract.
#  - A round trip through the CSV writers preserves values and index.
#  - An empty frame is not written over a good file.
#  - A missing or malformed file is reported as the right error.
#  - Models round trip, and a corrupt one reads as absent.
#  - Defaults, environment, file and precedence between them.
#  - A malformed date, port or configuration file is refused.
#  - The mail host guard.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, pytest
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from finance import storage
from finance.config import MailSettings, load_settings
from finance.errors import ConfigurationError, DataFormatError, StorageError
from finance.stocklist import read_stock_list

# --------------------------------------------------------------------
# storage
# --------------------------------------------------------------------


def test_file_names():
    assert storage.price_filename("N225") == "stock_N225.csv"
    assert storage.indicator_filename("7203") == "ti_7203.csv"
    assert storage.history_filename("summary.csv", date(2026, 8, 14)) == (
        "summary.csv.20260814.csv"
    )


def test_price_csv_round_trip(settings, raw_prices):
    path = settings.data_file("stock_TEST.csv")
    storage.write_price_csv(raw_prices, path)
    reloaded = storage.read_price_csv(path)

    assert list(reloaded.columns) == list(raw_prices.columns)
    assert len(reloaded) == len(raw_prices)
    assert float(reloaded.loc["2015-03-20", "Adj Close"]) == 19560.22


def test_summary_csv_round_trip(settings):
    frame = pd.DataFrame(
        {"Open": [100, 200], "Name": ["あ", "い"]}, index=["1111", "2222"]
    )
    path = settings.data_file("summary.csv")
    storage.write_summary_csv(frame, path)
    reloaded = storage.read_summary_csv(path)

    assert list(reloaded.index) == [1111, 2222]
    assert list(reloaded["Name"]) == ["あ", "い"]


def test_an_empty_frame_is_not_written(settings):
    path = settings.data_file("stock_TEST.csv")
    path.write_text("Date,Open\n2015-01-01,1\n", encoding="utf-8")
    storage.write_price_csv(pd.DataFrame(), path)

    # The good file survives rather than being truncated by a bad run.
    assert "2015-01-01" in path.read_text(encoding="utf-8")


def test_a_missing_file_is_reported(settings):
    with pytest.raises(StorageError, match="does not exist"):
        storage.read_price_csv(settings.data_file("absent.csv"))


def test_a_file_without_dates_is_reported(settings):
    path = settings.data_file("bad.csv")
    path.write_text("Name,Value\nalpha,1\nbeta,2\n", encoding="utf-8")
    with pytest.raises(DataFormatError, match="not indexed by date"):
        storage.read_price_csv(path)


def test_writing_creates_the_directory(settings, raw_prices):
    path = settings.history_dir / "nested" / "stock.csv"
    storage.write_price_csv(raw_prices, path)
    assert path.is_file()


def test_read_text_reports_a_missing_report(settings):
    with pytest.raises(StorageError, match="does not exist"):
        storage.read_text(settings.data_file("summary.csv"))


def test_model_round_trip(settings):
    store = storage.ModelStore(settings.model_dir)
    assert store.load("absent.pickle") is None

    store.save("model.pickle", {"weights": [1, 2, 3]})
    assert store.load("model.pickle") == {"weights": [1, 2, 3]}


def test_a_corrupt_model_reads_as_absent(settings):
    store = storage.ModelStore(settings.model_dir)
    storage.ensure_directory(settings.model_dir)
    (settings.model_dir / "broken.pickle").write_bytes(b"\x00 not a pickle")

    assert store.load("broken.pickle") is None


def test_merge_frames_joins_on_the_index(raw_prices):
    left = raw_prices.iloc[:10]
    right = pd.DataFrame({"extra": range(10)}, index=left.index)
    merged = storage.merge_frames(left, right)

    assert "extra" in merged.columns
    assert len(merged) == 10


# --------------------------------------------------------------------
# stocklist
# --------------------------------------------------------------------


def test_stock_list_reads_optional_columns(tmp_path):
    path = tmp_path / "stocks.txt"
    path.write_text(
        "6758,ソニー\n7203,トヨタ,トヨタ自動車(株),自動車,CORE30\n\n",
        encoding="utf-8",
    )
    entries = read_stock_list(path)

    assert len(entries) == 2
    assert entries[0].fullname == ""
    assert entries[0].display_name == "ソニー"
    assert entries[1].fullname == "トヨタ自動車(株)"
    assert entries[1].display_name == "トヨタ自動車(株)"


def test_a_missing_stock_list_is_reported(tmp_path):
    with pytest.raises(StorageError, match="does not exist"):
        read_stock_list(tmp_path / "absent.txt")


def test_a_one_column_line_is_refused(tmp_path):
    path = tmp_path / "stocks.txt"
    path.write_text("N225\n", encoding="utf-8")
    with pytest.raises(DataFormatError, match="at least a code and a name"):
        read_stock_list(path)


def test_an_empty_stock_list_is_refused(tmp_path):
    path = tmp_path / "stocks.txt"
    path.write_text("\n\n", encoding="utf-8")
    with pytest.raises(DataFormatError, match="empty"):
        read_stock_list(path)


# --------------------------------------------------------------------
# config
# --------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """ Remove every application variable so a test starts from defaults. """
    for name in list(__import__("os").environ):
        if name.startswith("FINANCE_") or name == "JQUANTS_API_KEY":
            monkeypatch.delenv(name, raising=False)


def test_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = load_settings()

    assert settings.data_dir == (tmp_path / "data").resolve()
    assert settings.history_dir == (tmp_path / "data" / "history").resolve()
    assert settings.model_dir == (tmp_path / "clf").resolve()
    assert settings.stock_list == "stocks.txt"
    assert settings.start_date == ""
    assert settings.log_level == "INFO"
    assert settings.mail.enabled is False
    assert settings.jquants.base_url == "https://api.jquants.com/v2"
    assert settings.jquants.has_api_key() is False


def test_environment_overrides_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path / "elsewhere"))
    monkeypatch.setenv("FINANCE_START_DATE", "2020-01-06")
    monkeypatch.setenv("FINANCE_LOG_LEVEL", "DEBUG")

    settings = load_settings()
    assert settings.data_dir == (tmp_path / "elsewhere").resolve()
    assert settings.start_date == "2020-01-06"
    assert settings.log_level == "DEBUG"


def test_a_configuration_file_is_read(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config.yml"
    config.write_text(
        "paths:\n"
        "  data_dir: {0}/from-file\n"
        "pipeline:\n"
        "  start_date: '2019-04-01'\n"
        "  stock_list: my_stocks.txt\n".format(tmp_path),
        encoding="utf-8",
    )

    settings = load_settings(config)
    assert settings.data_dir == (tmp_path / "from-file").resolve()
    assert settings.start_date == "2019-04-01"
    assert settings.stock_list == "my_stocks.txt"


def test_environment_beats_the_configuration_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config.yml"
    config.write_text("pipeline:\n  start_date: '2019-04-01'\n", encoding="utf-8")
    monkeypatch.setenv("FINANCE_START_DATE", "2021-01-04")

    assert load_settings(config).start_date == "2021-01-04"


def test_a_blank_variable_reads_as_unset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINANCE_START_DATE", "   ")
    assert load_settings().start_date == ""


def test_a_malformed_date_is_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINANCE_START_DATE", "01/04/2020")
    with pytest.raises(ConfigurationError, match="YYYY-MM-DD"):
        load_settings()


def test_a_malformed_port_is_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINANCE_MAIL_PORT", "not-a-port")
    with pytest.raises(ConfigurationError, match="integer"):
        load_settings()


def test_mail_without_addresses_is_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINANCE_MAIL_ENABLED", "true")
    with pytest.raises(ConfigurationError, match="sender or the recipient"):
        load_settings()


def test_a_named_configuration_file_must_exist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_settings(tmp_path / "absent.yml")


def test_a_configuration_file_that_is_not_a_mapping_is_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config.yml"
    config.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not a mapping"):
        load_settings(config)


def test_start_date_is_parsed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINANCE_START_DATE", "2014-10-01")
    assert load_settings().start_date_as_date() == date(2014, 10, 1)


def test_an_unset_start_date_reads_as_no_start_date(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_settings().start_date_as_date() is None


def test_the_mail_host_guard():
    disabled = MailSettings(enabled=False, hostname_suffix="id774.net")
    assert disabled.permits("host.id774.net") is False

    guarded = MailSettings(enabled=True, hostname_suffix="id774.net")
    assert guarded.permits("host.id774.net") is True
    assert guarded.permits("laptop.local") is False

    open_host = MailSettings(enabled=True, hostname_suffix="")
    assert open_host.permits("anything") is True
