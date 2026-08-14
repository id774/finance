#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/analysis.py: The per stock pipeline
#
#  Description:
#  Run one stock end to end: read what is stored, fetch what is newer,
#  compute the indicators, apply the two models, write stock_CODE.csv
#  and ti_CODE.csv, and draw the chart.
#
#  This is the application layer. It decides the order of the steps and
#  owns the paths, and it is the only place that knows both where files
#  live and what the calculations mean. The modules it calls know one or
#  the other, never both.
#
#  Two behaviours here are load bearing and are preserved from the
#  original rather than tidied away:
#
#  - A run that finds no new rows leaves ti_CODE.csv and the pickled
#    models alone. On a market holiday nothing is rewritten, so the
#    dashboard keeps showing the last real trading day rather than a
#    file restamped with today's date.
#  - Only the last row of ti_CODE.csv carries the classified and
#    predicted columns. They are a statement about tomorrow, not a
#    series, and the dashboard reads them from the last row alone.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - NumPy, pandas
#
#  Version History:
#  v1.0 2026-08-14
#       Separate the pipeline from file paths, the data source and the
#       command line.
#
########################################################################

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from finance import charts, storage
from finance.config import Settings
from finance.datasources import StockDataSource
from finance.errors import DataFormatError, FinanceError
from finance.indicators import build_indicator_frame
from finance.models import PricePredictor, TrendClassifier

DEFAULT_DAYS = 240
DEFAULT_AXIS = 2
DEFAULT_COMPLEXITY = 3

CLASSIFIED_COLUMN = "classified"
PREDICTED_COLUMN = "predicted"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisRequest:
    """ What one stock's run is asked to do. """

    code: str
    name: str = ""
    fullname: str = ""
    days: int = DEFAULT_DAYS
    csvfile: str | None = None
    update: bool = False
    axis: int = DEFAULT_AXIS
    complexity: int = DEFAULT_COMPLEXITY

    @property
    def display_name(self) -> str:
        """ Return the name shown in the chart caption. """
        return self.fullname or self.name or self.code


@dataclass
class AnalysisResult:
    """ What one stock's run produced. """

    code: str
    rows: int
    classified: int
    predicted: int
    chart_path: Path
    indicator_frame: pd.DataFrame
    wrote_indicators: bool


class Analysis:
    """ Run the daily pipeline for one stock. """

    def __init__(
        self,
        settings: Settings,
        source: StockDataSource,
        today: date | None = None,
    ) -> None:
        """
        Args:
            settings: Resolved paths and options.
            source: Where new prices come from.
            today: The date the run is considered to happen on. Injected
                for tests.
        """
        self.settings = settings
        self.source = source
        self.today = today or date.today()
        self.model_store = storage.ModelStore(settings.model_dir)

    def run(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Run one stock and return what it produced.

        Raises:
            FinanceError: Any step failed. A caller running a list
                catches this per stock and continues.
        """
        logger.info("Start analysis: %s", request.code)

        prices, will_update = self._load_prices(request)
        if prices.empty:
            raise DataFormatError("No price data available for {0}".format(request.code))

        window = prices.asfreq("B").dropna()
        if request.days > 0:
            window = window[request.days * -1 :]
        if window.empty:
            raise DataFormatError("No usable rows for {0}".format(request.code))

        indicators = build_indicator_frame(window)
        ret_index = indicators.stock["ret_index"]

        classified = self._classify(request.code, ret_index, will_update)
        predicted = self._predict(request.code, ret_index, indicators, will_update)

        # Assigned to the last row only. The columns exist for every row
        # so that the CSV keeps its shape; every earlier row is empty.
        indicators.stock.loc[indicators.stock.index[-1], CLASSIFIED_COLUMN] = classified
        indicators.stock.loc[indicators.stock.index[-1], PREDICTED_COLUMN] = predicted

        merged = storage.merge_frames(window, indicators.stock)
        if will_update:
            storage.write_price_csv(
                merged, self.settings.data_file(storage.indicator_filename(request.code))
            )

        prefix = charts.chart_prefix(request.days)
        renderer = charts.ChartRenderer(
            request.code, request.display_name, self.settings.font_path
        )
        chart_path = renderer.plot(
            window,
            indicators.stock,
            prefix,
            self.settings.data_dir,
            classified,
            predicted,
            axis=request.axis,
            complexity=request.complexity,
            today=self.today,
        )

        logger.info("Finish analysis: %s (%d rows, chart %s)", request.code, len(window), prefix)
        return AnalysisResult(
            code=request.code,
            rows=len(window),
            classified=classified,
            predicted=predicted,
            chart_path=chart_path,
            indicator_frame=merged,
            wrote_indicators=will_update,
        )

    def _load_prices(self, request: AnalysisRequest) -> tuple[pd.DataFrame, bool]:
        """
        Return the price history and whether this run may write.

        A run asked to update reads what is stored, fetches from the
        business day after the last stored row, and combines the two
        with the stored rows winning. That is what keeps a historical
        adjustment basis from being rewritten under the operator: only
        rows that were not there before come from today's fetch.
        """
        if request.csvfile is None:
            prices = self._fetch(
                request.code, self.settings.start_date_as_date(), self.today
            )
            storage.write_price_csv(
                prices, self.settings.data_file(storage.price_filename(request.code))
            )
            return prices, request.update

        path = Path(request.csvfile)
        if not path.is_absolute():
            path = self.settings.data_file(request.csvfile)

        if not path.is_file():
            logger.info("No stored prices for %s; fetching the full history", request.code)
            prices = self._fetch(
                request.code, self.settings.start_date_as_date(), self.today
            )
            storage.write_price_csv(
                prices, self.settings.data_file(storage.price_filename(request.code))
            )
            return prices, request.update

        stored = storage.read_price_csv(path)
        logger.info("Read %d stored rows for %s", len(stored), request.code)
        if not request.update or stored.empty:
            return stored, False

        next_day = self._next_business_day(stored.index[-1])
        if next_day > self.today:
            logger.info("Stored data for %s is already current", request.code)
            return stored, False

        fetched = self._fetch(request.code, next_day, self.today)
        fresh = fetched.dropna(how="all")
        logger.info("Fetched %d new rows for %s", len(fresh), request.code)
        if fresh.empty:
            # Nothing new: leave the indicator file and the models as
            # they are, so a holiday does not restamp the dashboard.
            return stored, False

        combined = stored.combine_first(fetched)
        storage.write_price_csv(
            combined, self.settings.data_file(storage.price_filename(request.code))
        )
        return combined, True

    def _fetch(self, code: str, start: date, end: date) -> pd.DataFrame:
        """ Fetch prices, letting a DataSourceError propagate to the caller. """
        return self.source.fetch(code, start, end)

    @staticmethod
    def _next_business_day(timestamp: pd.Timestamp) -> date:
        """ Return the business day after the given date. """
        following = pd.date_range(start=timestamp, periods=2, freq="B")
        return following[1].date()

    def _classify(self, code: str, ret_index: pd.Series, remember: bool) -> int:
        """ Train the classifier and return its verdict on the next day. """
        name = "clf_{0}.pickle".format(code)
        classifier = TrendClassifier(estimator=self.model_store.load(name))
        _, train_y = classifier.train(ret_index)
        logger.info("Classifier trained on %d samples for %s", len(train_y), code)
        if remember:
            self.model_store.save(name, classifier.estimator)
        result = classifier.classify(ret_index)
        logger.info("Classified %s as %d", code, result)
        return result

    def _predict(
        self,
        code: str,
        ret_index: pd.Series,
        indicators,
        remember: bool,
    ) -> int:
        """ Train the regression and return the price it predicts. """
        name = "reg_{0}.pickle".format(code)
        predictor = PricePredictor(estimator=self.model_store.load(name))
        _, train_y = predictor.train(ret_index)
        logger.info("Regression trained on %d samples for %s", len(train_y), code)
        if remember:
            self.model_store.save(name, predictor.estimator)
        base = indicators.stock_raw["Adj Close"].iloc[0]
        result = int(predictor.predict(ret_index, base))
        logger.info("Predicted %s as %d", code, result)
        return result


def run_many(
    analysis: Analysis, requests: list[AnalysisRequest]
) -> tuple[list[AnalysisResult], list[tuple[str, Exception]]]:
    """
    Run several stocks, continuing past one that fails.

    A nightly job covering thirty stocks must not lose twenty-nine of
    them because one delisted code cannot be fetched. Each failure is
    logged with its code and returned, so the caller can report a
    partial run through its exit status rather than exiting zero.

    Returns:
        The results that succeeded and the (code, error) pairs that did
        not, both in request order.
    """
    results: list[AnalysisResult] = []
    failures: list[tuple[str, Exception]] = []
    for request in requests:
        try:
            results.append(analysis.run(request))
        except FinanceError as exc:
            logger.error("Analysis failed for %s: %s", request.code, exc)
            failures.append((request.code, exc))
        except (ValueError, KeyError, TypeError) as exc:
            # A malformed stored file can still surface as one of these
            # from deep inside pandas. Treat it as this stock's failure
            # rather than the run's.
            logger.error("Unexpected failure for %s: %s", request.code, exc, exc_info=True)
            failures.append((request.code, exc))
    return results, failures


def load_indicator_frames(
    settings: Settings, entries, skip_indices: bool = True
) -> dict[tuple[str, str], pd.DataFrame]:
    """
    Read the stored indicator frames of a stock list, for aggregation.

    Args:
        settings: Where the files live.
        entries: StockEntry values naming the stocks to load.
        skip_indices: Leave market indices out, which is what the
            summaries have always done.

    Returns:
        Frames keyed by (code, name). A stock without a stored file is
        left out rather than raised on: it has simply not been charted
        yet.
    """
    frames: dict[tuple[str, str], pd.DataFrame] = {}
    for entry in entries:
        if skip_indices and entry.is_index:
            continue
        path = settings.data_file(storage.indicator_filename(entry.code))
        if not path.is_file():
            logger.debug("No indicator file for %s", entry.code)
            continue
        try:
            frames[(entry.code, entry.name)] = storage.read_price_csv(path)
        except FinanceError as exc:
            logger.warning("Skipping %s: %s", entry.code, exc)
    return frames


