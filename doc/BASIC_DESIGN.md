# Basic design: a technical analysis batch pipeline

## 1. Purpose

This document describes how the system is composed: the layers, what each module
is for, how data moves through them, and how failure is handled.

What the system is for belongs to [`REQUIREMENTS.md`](REQUIREMENTS.md). The
format of what it writes belongs to [`DATA_CONTRACT.md`](DATA_CONTRACT.md). How
a change is carried out belongs to [`POLICY.md`](POLICY.md). This document does
not restate them.

## 2. Design policy

- **The contract decides.** Where a cleaner internal structure would change a
  generated file, the file wins.
- **Dependency points one way.** A layer never imports one above it.
- **Computation is separable from the world.** A module that computes does not
  open a file, make a request or read the environment, so that it can be tested
  by passing it values.
- **A foreign type stops at its boundary.** No exception, client object or
  library-specific value from `yfinance`, TA-Lib, scikit-learn or matplotlib
  travels above the module that owns it.
- **Settings are resolved once.** At the entry point, and passed down.
- **One implementation.** The command line and the batch script drive the same
  functions; nothing is written twice.

## 3. Composition

```text
finance/cli/charts.py   summary.py   notify.py            entry points
        |   parse arguments, resolve settings, return an exit code
        v
analysis.py   reporting.py   notification.py              application
        |   the order of the steps, and the paths
        v
indicators.py  features.py  models.py                     domain
aggregation.py charts.py    stocklist.py                  pure computation
        |
        v
storage.py    datasources/                                I/O
        |
        v
the filesystem                Yahoo Finance
```

`config.py` and `errors.py` sit beside all of it: every layer may use them, and
neither depends on anything in the package.

`test/test_package.py` asserts this shape against the source — that no module
mutates `sys.path`, that only `config.py` reads the environment, that no domain
module opens a file or imports an I/O module, and that no library module prints.

## 4. What each module is for

### 4.1 `finance/__init__.py`

The package version and the one place logging is configured. Imports nothing
beyond the standard library, so every other module can import it freely. The
three commands append to the same log file, so the format is decided once.

### 4.2 `finance/config.py`

Resolves every operational value: paths, the default stock list, the start date,
the caption font, the log level and the mail settings. Precedence is command
line, environment, YAML file, default.

**The only module in the package that reads the environment.** A value that is
present but unusable is refused here, before any work begins.

### 4.3 `finance/errors.py`

The error hierarchy. Its purpose is that a caller can distinguish a source that
could not be reached from a stored file that is malformed, and decide to
continue or stop on that difference.

`FinanceError` is the base. Below it: `ConfigurationError`, `DataSourceError`,
`DataFormatError`, `IndicatorError`, `ModelError` (and `ModelNotTrainedError`),
`StorageError`, `NotificationError`.

### 4.4 `finance/stocklist.py`

Parses the comma separated stock lists into `StockEntry` values, and knows which
codes name a market index rather than a company.

### 4.5 `finance/indicators.py`

`TechnicalIndicators` computes each indicator onto a frame indexed by the
business days of the input. Each `calc_*` method appends its columns and returns
the whole frame.

`build_indicator_frame()` is the single definition of the call sequence, and
that sequence is the column order of `ti_CODE.csv`. A caller that wants the
contract calls it rather than replaying the methods.

TA-Lib exceptions are caught here and re-raised as `IndicatorError`.

### 4.6 `finance/features.py`

Builds the training sets: sliding windows of fourteen consecutive return index
values, labelled either by whether the next value rises or by the next value
itself. Windows are expressed as negative offsets from the end of the series, so
that training stays anchored to the most recent data, and the reach back is
capped so that a long history does not lengthen the nightly run.

### 4.7 `finance/models.py`

`TrendClassifier` and `PricePredictor`. Both fit, both predict, neither
persists: loading and saving are `storage.ModelStore`, so that a model can be
exercised without a filesystem.

A model built fresh trains over the whole history; one restored from disk is
refreshed on the recent window only.

### 4.8 `finance/aggregation.py`

`Aggregator` reduces many indicator frames to one summary table. It holds the
two positional column layouts as constants, the ten day staleness rule, and the
historical ratio formula. It is handed frames; it reads nothing.

### 4.9 `finance/charts.py`

`ChartRenderer` draws the two panels and writes the PNG, and `chart_prefix()`
maps a window length to a file name prefix.

This is the one module that could not be ported by changing API calls. The
previous implementation registered a subclass of a private pandas plotting class
into three private pandas registries and drew candles with
`matplotlib.finance.candlestick_ochl`; the registries are gone from pandas and
the module was deleted from matplotlib in 3.0. Candles are now drawn with
matplotlib primitives against row positions, with the ticks labelled by date, so
that consecutive business days sit side by side as they did before.

Display scalings are applied to a copy. The frame the caller passes in is the
one that was written to `ti_CODE.csv`.

### 4.10 `finance/storage.py`

Every read and write of a generated file, and the file naming rules. Holds the
separators and index labels of the contract in one place. Decides no path: it is
told where to write.

`ModelStore` loads and saves pickles. A model that cannot be unpickled is
reported as absent rather than raised, because estimators pickled by an older
scikit-learn do not load on a newer one and refusing to run for that reason
would stop the whole job the first time the library is upgraded.

### 4.11 `finance/datasources/`

`__init__.py` declares the `StockDataSource` protocol — one method, `fetch(code,
start, end)`, returning a frame in canonical shape — and `create_source()`.

`yahoo.py` is the only implementation. It maps a code to a Yahoo symbol and
normalizes the response: unadjusted prices requested explicitly, the timezone
localized away and the index normalized to midnight, action columns dropped, the
six canonical columns put in order, duplicates resolved, and the frame reindexed
to business days. A response without `Adj Close` is refused rather than filled
from `Close`.

`yfinance` is imported inside the adapter, so the package imports without it.

### 4.12 `finance/analysis.py`

The per stock pipeline: load prices, compute indicators, apply both models,
write both CSVs, draw the chart. It owns the order and the paths.

`run_many()` runs a list, catching each stock's failure so that the rest
continue, and returning both the results and the failures.

### 4.13 `finance/reporting.py`

The summary pipeline: read the stock list, load the stored indicator frames,
aggregate, write, and optionally keep a dated copy.

### 4.14 `finance/notification.py`

Builds and sends the report mail. The transport is a parameter, so a test
asserts the message without opening a connection. Sending is refused unless mail
is enabled and the host name matches the configured suffix.

### 4.15 `finance/cli/`

Three entry points and their shared helpers. Each parses arguments, resolves
settings, calls one function in the application layer and reports what happened.
No analysis is written here.

## 5. The flow of one stock

```text
finance-charts -s stocks.txt -y 240 -u
    |
    | read_stock_list()                       stocklist
    v
for each entry:
    |
    | read stock_CODE.csv                     storage
    | fetch from the next business day        datasources/yahoo
    | combine, stored rows winning            analysis
    | write stock_CODE.csv                    storage
    v
    | reindex to business days, drop gaps,
    | take the trailing window                analysis
    v
    | build_indicator_frame()                 indicators
    v
    | load models, train, classify, predict   storage + models
    | write the two values to the last row    analysis
    v
    | merge and write ti_CODE.csv             storage
    | draw and write CODE.png                 charts
```

If the fetch returns nothing new, the run stops short of writing: no indicator
file, no model saved. On a market holiday nothing is restamped and the dashboard
keeps showing the last real trading day.

## 6. The flow of a summary

```text
finance-summary -o portfolio.csv -s my_stocks.txt -r 1 -k Ratio
    |
    | read_stock_list()                       stocklist
    | load each ti_CODE.csv, skipping indices
    |   and stocks with no file               analysis + storage
    v
    | reduce each to one row, dropping the
    |   stale and the too-short               aggregation
    | sort                                    aggregation
    v
    | write the tab separated table           storage
    | optionally write the dated copy         storage
```

## 7. Settings

Resolved into a frozen `Settings` dataclass at the entry point and passed down.
A command line override is applied with `dataclasses.replace`, so a module below
never sees a mutable object it could change.

`--data-dir` moves the history directory with it unless the history directory
was configured on its own, so that the option moves the whole output of a run
rather than half of it.

## 8. Error handling

Each layer converts what it catches:

| Layer | Catches | Raises |
|---|---|---|
| `datasources/yahoo` | any client exception | `DataSourceError` |
| `indicators` | any TA-Lib exception | `IndicatorError` |
| `models` | any scikit-learn exception | `ModelError` |
| `storage` | `OSError`, parser errors | `StorageError`, `DataFormatError` |
| `config` | bad values | `ConfigurationError` |
| `notification` | `OSError`, `SMTPException` | `NotificationError` |

Above them:

- `run_many()` catches per stock, logs with the code, and continues.
- The CLI wrapper turns a `FinanceError` into a message on stderr and exit
  status 1. Anything else is left to propagate: an unexpected exception is a
  defect and its traceback is wanted.
- A list run with any failure exits 1, so cron reports a partial run.

Two writes are deliberately conservative. An empty frame is never written over
an existing file, and stored price rows are never recalculated.

## 9. Logging

Configured once in `finance/__init__.py`. Library modules take a module logger
and never print; the CLIs write user-facing messages to stderr. Third-party
loggers that report their own HTTP traffic are held at WARNING so that the
nightly log stays a record of the pipeline.

Levels: INFO for what a step did, WARNING for something skipped, ERROR for
something that failed.

## 10. Testing

Four groups, described in the README. Two structural rules matter to this
design:

- No test in the default run reaches the network. The price source is a protocol
  and tests inject a stub.
- `test/test_package.py` asserts the layering, so the dependency direction is
  enforced rather than merely documented.

The committed fixtures `test/stock_N225.csv` and `test/ti_N225.csv` predate the
rewrite and are load bearing: the contract test regenerates all 42 computed
columns of the second from the first.
