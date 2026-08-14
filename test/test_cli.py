#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_cli.py: The command line entry points
#
#  Description:
#  Assert that the three commands accept the options the batch scripts
#  pass them, that they write where they are told, and that they return
#  the exit status the operator's cron mail depends on.
#
#  The option letters are asserted explicitly rather than implied by a
#  happy path. run.sh has passed the same nine combinations every
#  weekday evening for a decade, and a command that silently stopped
#  recognising one of them would produce an empty summary rather than an
#  error.
#
#  Test Cases:
#  - Every option run.sh passes is accepted, for both commands.
#  - --help and --version exit zero.
#  - An unknown option exits 2.
#  - An invalid choice for -a or -p exits 2.
#  - Neither a code nor a list exits 1 with a message.
#  - A missing stock list exits 1 with a message.
#  - Output lands in the directory given by --data-dir.
#  - A summary with -y also writes a history copy.
#  - A failing stock makes the whole run exit 1.
#  - The notify command declines quietly when mail is unconfigured.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pandas, pytest
#
#  Version History:
#  v2.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import pandas as pd
import pytest

from finance.cli import EXIT_FAILURE, EXIT_SUCCESS, EXIT_USAGE
from finance.cli import charts as charts_cli
from finance.cli import notify as notify_cli
from finance.cli import summary as summary_cli

# --------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------


def test_charts_accepts_every_option_run_sh_passes():
    arguments = charts_cli.parse_arguments(
        ["-a", "2", "-p", "2", "-s", "stocks.txt", "-d", "2014-10-01", "-y", "240", "-u"]
    )

    assert arguments.axis == 2
    assert arguments.complexity == 2
    assert arguments.stocktxt == "stocks.txt"
    assert arguments.startdate == "2014-10-01"
    assert arguments.days == 240
    assert arguments.update is True


def test_charts_accepts_the_single_stock_options():
    arguments = charts_cli.parse_arguments(
        ["-c", "N225", "-n", "日経平均株価", "-r", "stock_N225.csv", "-y", "180"]
    )

    assert arguments.code == "N225"
    assert arguments.name == "日経平均株価"
    assert arguments.csvfile == "stock_N225.csv"
    assert arguments.days == 180
    assert arguments.update is False


def test_charts_defaults_match_the_historical_ones():
    arguments = charts_cli.parse_arguments([])
    assert arguments.days == 240
    assert arguments.axis == 2
    assert arguments.complexity == 3


@pytest.mark.parametrize(
    "argv",
    [
        ["-o", "summary.csv", "-y", "-r", "1", "-k", "Ratio"],
        ["-o", "summary_10.csv", "-r", "10", "-k", "Ratio"],
        ["-s", "my_stocks.txt", "-o", "portfolio.csv", "-r", "1", "-k", "Ratio"],
        ["-s", "topix_core30.txt", "-o", "topix_core30.csv", "-r", "1", "-c", "rsi9",
         "-k", "Ratio"],
        ["-o", "screening_rsi14.csv", "-r", "1", "-c", "rsi14", "-a", "-k", "rsi14"],
    ],
)
def test_summary_accepts_every_invocation_run_sh_makes(argv):
    arguments = summary_cli.parse_arguments(argv)
    assert arguments.output
    assert arguments.span >= 1


def test_summary_option_meanings():
    arguments = summary_cli.parse_arguments(
        ["-o", "screening_rsi14.csv", "-r", "1", "-c", "rsi14", "-a", "-k", "rsi14", "-y"]
    )

    assert arguments.output == "screening_rsi14.csv"
    assert arguments.span == 1
    assert arguments.screening_key == "rsi14"
    assert arguments.ascending is True
    assert arguments.sortkey == "rsi14"
    assert arguments.history is True


def test_notify_takes_the_two_positional_arguments():
    arguments = notify_cli.parse_arguments(
        ["portfolio.csv", "Summary Report of My Portfolio"]
    )
    assert arguments.file == "portfolio.csv"
    assert arguments.subject == "Summary Report of My Portfolio"


def test_notify_defaults_match_the_ruby_script():
    arguments = notify_cli.parse_arguments([])
    assert arguments.file == "summary.csv"
    assert arguments.subject == "Summary Report of Financial Data"


# --------------------------------------------------------------------
# Exit status
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "module", [charts_cli, summary_cli, notify_cli], ids=["charts", "summary", "notify"]
)
@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_help_and_version_exit_zero(module, flag):
    with pytest.raises(SystemExit) as raised:
        module.parse_arguments([flag])
    assert raised.value.code == EXIT_SUCCESS


@pytest.mark.parametrize(
    "module", [charts_cli, summary_cli, notify_cli], ids=["charts", "summary", "notify"]
)
def test_an_unknown_option_exits_two(module):
    with pytest.raises(SystemExit) as raised:
        module.parse_arguments(["--nonsense"])
    assert raised.value.code == EXIT_USAGE


@pytest.mark.parametrize("argv", [["-a", "3"], ["-p", "9"], ["-y", "many"]])
def test_an_invalid_value_exits_two(argv):
    with pytest.raises(SystemExit) as raised:
        charts_cli.parse_arguments(argv)
    assert raised.value.code == EXIT_USAGE


def test_charts_without_a_code_or_a_list_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    status = charts_cli.main(["--data-dir", str(tmp_path)])

    assert status == EXIT_FAILURE
    assert "stock code" in capsys.readouterr().err


def test_charts_with_a_missing_list_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    status = charts_cli.main(["-s", "absent.txt", "--data-dir", str(tmp_path)])

    assert status == EXIT_FAILURE
    assert "does not exist" in capsys.readouterr().err


def test_charts_with_a_malformed_start_date_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    status = charts_cli.main(["-c", "N225", "-d", "not-a-date", "--data-dir", str(tmp_path)])

    assert status == EXIT_FAILURE
    assert "YYYY-MM-DD" in capsys.readouterr().err


def test_summary_with_a_missing_list_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    status = summary_cli.main(
        ["-o", "summary.csv", "-s", "absent.txt", "--data-dir", str(tmp_path)]
    )

    assert status == EXIT_FAILURE
    assert "does not exist" in capsys.readouterr().err


def test_summary_with_an_unknown_sort_key_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "stocks.txt").write_text("7203,トヨタ\n", encoding="utf-8")
    status = summary_cli.main(
        ["-o", "summary.csv", "-k", "nonexistent", "--data-dir", str(tmp_path)]
    )

    assert status == EXIT_FAILURE
    assert "Cannot sort by" in capsys.readouterr().err


# --------------------------------------------------------------------
# Output location
# --------------------------------------------------------------------


def test_summary_writes_where_data_dir_points(tmp_path, monkeypatch, indicator_fixture):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "out"
    data_dir.mkdir()
    (data_dir / "stocks.txt").write_text("7203,トヨタ\n", encoding="utf-8")

    frame = indicator_fixture.copy()
    frame.index = pd.date_range(end=pd.Timestamp.today().normalize(), periods=len(frame), freq="B")
    frame.loc[frame.index[-1], "classified"] = 1
    frame.loc[frame.index[-1], "predicted"] = 2500
    frame.to_csv(data_dir / "ti_7203.csv", index_label="Date")

    status = summary_cli.main(["-o", "summary.csv", "--data-dir", str(data_dir)])

    assert status == EXIT_SUCCESS
    assert (data_dir / "summary.csv").is_file()


def test_summary_history_writes_a_dated_copy(tmp_path, monkeypatch, indicator_fixture):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "out"
    data_dir.mkdir()
    (data_dir / "stocks.txt").write_text("7203,トヨタ\n", encoding="utf-8")

    frame = indicator_fixture.copy()
    frame.index = pd.date_range(end=pd.Timestamp.today().normalize(), periods=len(frame), freq="B")
    frame.loc[frame.index[-1], "classified"] = 1
    frame.loc[frame.index[-1], "predicted"] = 2500
    frame.to_csv(data_dir / "ti_7203.csv", index_label="Date")

    status = summary_cli.main(["-o", "summary.csv", "-y", "--data-dir", str(data_dir)])

    assert status == EXIT_SUCCESS
    copies = list((data_dir / "history").glob("summary.csv.*.csv"))
    assert len(copies) == 1


def test_charts_writes_where_data_dir_points(tmp_path, monkeypatch, raw_prices):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "out"
    data_dir.mkdir()
    (data_dir / "stocks.txt").write_text("N225,日経平均株価\n", encoding="utf-8")
    raw_prices.to_csv(data_dir / "stock_N225.csv", index_label="Date")

    status = charts_cli.main(
        ["-s", "stocks.txt", "-y", "180", "--data-dir", str(data_dir)]
    )

    assert status == EXIT_SUCCESS
    assert (data_dir / "chart_N225.png").is_file()
    # Without -u nothing else is written.
    assert not (data_dir / "ti_N225.csv").exists()


def test_a_failing_stock_makes_the_run_exit_one(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "out"
    data_dir.mkdir()
    (data_dir / "stocks.txt").write_text("9999,存在しない\n", encoding="utf-8")

    def unreachable_source():
        class Source:
            def fetch(self, code, start, end):
                return pd.DataFrame()

        return Source()

    monkeypatch.setattr(charts_cli, "create_source", unreachable_source)
    status = charts_cli.main(["-s", "stocks.txt", "--data-dir", str(data_dir)])

    assert status == EXIT_FAILURE
    assert "9999" in capsys.readouterr().err


# --------------------------------------------------------------------
# notify
# --------------------------------------------------------------------


def test_notify_declines_quietly_when_mail_is_unconfigured(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "out"
    data_dir.mkdir()
    (data_dir / "summary.csv").write_text("Code\tName\n1111\tあ\n", encoding="utf-8")

    assert notify_cli.main(["--data-dir", str(data_dir)]) == EXIT_SUCCESS


def test_notify_dry_run_prints_the_message(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "out"
    data_dir.mkdir()
    (data_dir / "portfolio.csv").write_text("Code\tName\n1111\tあ\n", encoding="utf-8")

    status = notify_cli.main(
        ["portfolio.csv", "My Portfolio", "--dry-run", "--data-dir", str(data_dir)]
    )

    assert status == EXIT_SUCCESS
    printed = capsys.readouterr().out
    assert "My Portfolio" in printed
    assert "Subject:" in printed


def test_notify_reports_a_missing_report(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "out"
    data_dir.mkdir()

    status = notify_cli.main(["--dry-run", "--data-dir", str(data_dir)])

    assert status == EXIT_FAILURE
    assert "does not exist" in capsys.readouterr().err
