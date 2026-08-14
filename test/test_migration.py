#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_migration.py: Retiring data written before the source changed
#
#  Description:
#  Assert that the one-off migration moves the stored per-stock series
#  out of the way without deleting anything, leaves the operator's own
#  inputs alone, and is reachable only by being run on purpose.
#
#  The last of those is the point of the whole exercise. The daily job
#  must not decide by itself to move a decade of the operator's stored
#  history, and the data source must not know that stored history from
#  a previous provider exists at all. Both are asserted here rather than
#  left to the reading of run.sh.
#
#  Test Cases:
#  - Price and indicator files are moved into a dated archive.
#  - The files still exist afterwards, in the archive.
#  - Stock lists, summaries and charts are left where they are.
#  - A dry run reports what would move and moves nothing.
#  - An empty data directory is not an error.
#  - The command exits zero in both cases.
#  - The daily batch script does not call the migration.
#  - No module under datasources refers to the migration.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pytest
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

from datetime import date
from pathlib import Path

from finance.cli import EXIT_SUCCESS
from finance.cli import migrate as migrate_cli
from finance.migration import archive_legacy_data, legacy_files

RUN_DATE = date(2026, 8, 14)

GENERATED = ("stock_7203.csv", "stock_6758.csv", "ti_7203.csv", "ti_6758.csv")
KEPT = ("stocks.txt", "topix_core30.txt", "summary.csv", "chart_7203.png")


def populate(data_dir: Path) -> None:
    """ Fill a data directory with one of everything the pipeline writes. """
    for name in GENERATED + KEPT:
        (data_dir / name).write_text("placeholder\n", encoding="utf-8")


def test_the_per_stock_series_are_the_files_that_migrate(data_dir):
    populate(data_dir)
    names = sorted(path.name for path in legacy_files(data_dir))
    assert names == sorted(GENERATED)


def test_the_files_are_moved_into_a_dated_archive(data_dir):
    populate(data_dir)
    result = archive_legacy_data(data_dir, on=RUN_DATE)

    assert result.archive_dir == data_dir / "legacy.20260814"
    assert result.count == len(GENERATED)
    for name in GENERATED:
        assert not (data_dir / name).exists()
        assert (result.archive_dir / name).is_file()


def test_nothing_is_deleted(data_dir):
    populate(data_dir)
    result = archive_legacy_data(data_dir, on=RUN_DATE)
    moved = sorted(path.name for path in result.archive_dir.iterdir())
    assert moved == sorted(GENERATED)


def test_inputs_summaries_and_charts_are_left_alone(data_dir):
    populate(data_dir)
    archive_legacy_data(data_dir, on=RUN_DATE)
    for name in KEPT:
        assert (data_dir / name).is_file()


def test_a_dry_run_moves_nothing(data_dir):
    populate(data_dir)
    result = archive_legacy_data(data_dir, on=RUN_DATE, dry_run=True)

    assert result.dry_run is True
    assert sorted(result.moved) == sorted(GENERATED)
    assert not result.archive_dir.exists()
    for name in GENERATED:
        assert (data_dir / name).is_file()


def test_an_empty_directory_is_not_an_error(data_dir):
    result = archive_legacy_data(data_dir, on=RUN_DATE)
    assert result.count == 0
    assert not result.archive_dir.exists()


def test_the_command_reports_and_exits_zero(tmp_path, monkeypatch, capsys, data_dir):
    monkeypatch.chdir(tmp_path)
    populate(data_dir)

    status = migrate_cli.main(["--data-dir", str(data_dir)])
    assert status == EXIT_SUCCESS
    assert "Moved 4" in capsys.readouterr().err
    assert not (data_dir / "stock_7203.csv").exists()


def test_the_command_exits_zero_with_nothing_to_do(tmp_path, monkeypatch, capsys, data_dir):
    monkeypatch.chdir(tmp_path)
    status = migrate_cli.main(["--data-dir", str(data_dir)])

    assert status == EXIT_SUCCESS
    assert "Nothing to migrate" in capsys.readouterr().err


def test_the_daily_batch_does_not_run_the_migration():
    """ Moving stored history is never something a cron job decides. """
    script = (Path(__file__).parent.parent / "run.sh").read_text(encoding="utf-8")
    assert "finance-migrate" not in script


def test_the_data_source_layer_knows_nothing_about_it():
    """ Where data came from is not the fetcher's problem. """
    package = Path(__file__).parent.parent / "finance" / "datasources"
    for path in package.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "migration" not in source, "{0} refers to the migration".format(path)
