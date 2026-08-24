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
  library-specific value from `requests`, TA-Lib, scikit-learn or matplotlib
  travels above the module that owns it.
- **Settings are resolved once.** At the entry point, and passed down.
- **One implementation.** The command line and the batch script drive the same
  functions; nothing is written twice.

## 3. Composition

```text
finance/cli/charts.py  summary.py  notify.py  migrate.py  entry points
        |   parse arguments, resolve settings, return an exit code
        v
analysis.py  reporting.py  notification.py  migration.py  application
        |   the order of the steps, and the paths
        v
indicators.py  features.py  models.py                     domain
aggregation.py charts.py    stocklist.py                  pure computation
        |
        v
storage.py    datasources/                                I/O
        |
        v
the filesystem                the J-Quants API
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
command-line entry points append to the same log file, so the format is
decided once.

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

Parses the comma separated stock lists into `StockEntry` values. Every entry
names a listing on the Tokyo exchange; market indices are not accepted.

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
positional column layouts as constants, the ten day staleness rule, and the
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
start, end)`, returning a frame in canonical shape — plus `create_source()` and
`LazySource`.

`jquants.py` is the only implementation, and everything peculiar to the provider
is inside it: the `x-api-key` header, the base URL, `/equities/bars/daily`, its
`code`, `from` and `to` parameters, the `data` and `pagination_key` members of
the response, the minimum interval between requests, the retry of a throttled or
failed one, the timeout, the HTTP status vocabulary, the abbreviated v2 field
names, and the five character code form. None of it leaves the module.

Normalization is what the module is for. The response rows become a frame
carrying the six canonical columns, on a tz-naive midnight index, sorted,
deduplicated and reindexed to business days. All six columns are taken from the
adjusted series — `AdjO`, `AdjH`, `AdjL`, `AdjC`, `AdjVo` — so that the
candlesticks and the indicators are on one basis; `DATA_CONTRACT.md` section 11
records that decision and the reasoning behind it. A response without the
adjusted fields is refused rather than filled from the unadjusted ones.

Failures are separated by what an operator would do about them:
`AuthenticationError` for a rejected or absent key, `RateLimitError` for a
throttle the retries did not clear, `DataUnavailableError` for a range or a
dataset the plan does not carry, `InvalidStockCodeError` for a code that cannot
name a listing, and `DataSourceError` for the rest.

A source refuses to be built without an API key, before a socket is opened.
`LazySource` defers that construction to the first fetch, which is what lets the
chart-only runs — the long and short passes of `run.sh`, and a workstation
redrawing from a stored CSV — work with no credential at all while a fetching
run still fails before it reaches the network.

`requests` is imported inside the adapter, so the package imports without it.

The adapter does not know what is on disk, does not know which provider wrote
it, and does not know what plan it is on. The dates it may ask for are decided
above it, by `Settings.fetch_window`.

### 4.12 `finance/analysis.py`

The per stock pipeline: load prices, compute indicators, apply both models,
write both CSVs, draw the chart. It owns the order and the paths.

`run_many()` runs a list, catching each stock's failure so that the rest
continue, and returning both the results and the failures.

### 4.13 `finance/reporting.py`

The summary pipeline: read the stock list, load the stored indicator frames,
aggregate, write, and optionally keep a dated copy.

It is where the plan's delay enters the summaries. Staleness is measured against
the newest date the plan publishes, not against today; compared with today, a
source publishing weeks in arrears would drop every stock as stale and write an
empty table every evening.

### 4.14 `finance/notification.py`

Builds and sends the report mail. The transport is a parameter, so a test
asserts the message without opening a connection. Sending is refused unless mail
is enabled and the host name matches the configured suffix.

### 4.14a `finance/migration.py`

Moves the stored per-stock price and indicator files into a dated archive, so
that the next run rebuilds them from the current source. Nothing is deleted, the
stock lists and summaries are left alone, and no daily path calls it.

It exists because the previous provider's series and the current one's do not
mean the same thing, and the update path merges stored rows with fetched ones.
Merging two bases would produce a file whose halves disagree in a way no
indicator would report. Deciding to retire the older half is the operator's
call, and the data source layer is deliberately kept ignorant of it.

### 4.15 `finance/cli/`

The command-line entry points and their shared helpers. Each parses arguments, resolves
settings, calls one function in the application layer and reports what happened.
No analysis is written here.

`charts.py`, `summary.py` and `notify.py` are the daily commands. `migrate.py`
is run once by hand and is not in `run.sh`.

## 5. The flow of one stock

```text
finance-charts -s stocks.txt -y 240 -u
    |
    | read_stock_list()                       stocklist
    v
for each entry:
    |
    | read stock_CODE.csv                     storage
    | fetch from the next business day        datasources/jquants
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
    | load each ti_CODE.csv, skipping stocks
    |   with no file                          analysis + storage
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

`Settings.jquants` holds the endpoint, the credential and the plan's published
properties — how far behind today its newest row is, and how far back it keeps
data. `fetch_window(today)` turns those into the range a fetch may ask for, and
raises a configured start date that predates the plan rather than refusing it.
Their runtime defaults are defined in `finance/config.py`. The README,
`config.yml.sample`, and `doc/DEPLOYMENT.md` expose the same values to
operators, while current provider terms remain the provider's responsibility.

The API key is read from `JQUANTS_API_KEY` and from nothing else. It is refused
if it appears in the configuration file, and its field is excluded from the
dataclass repr so that logging a `Settings` cannot disclose it.

`--data-dir` moves the history directory with it unless the history directory
was configured on its own, so that the option moves the whole output of a run
rather than half of it.

## 8. Error handling

Each layer converts what it catches:

| Layer | Catches | Raises |
|---|---|---|
| `datasources/jquants` | any HTTP client exception, any refused status | the `DataSourceError` hierarchy |
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

Writes are deliberately conservative. An empty frame is never written over an
existing file, and stored price rows are never recalculated.

## 9. Logging

Configured once in `finance/__init__.py`. Library modules take a module logger
and never print; the CLIs write user-facing messages to stderr. Third-party
loggers that report their own HTTP traffic are held at WARNING so that the
nightly log stays a record of the pipeline.

Levels: INFO for what a step did, WARNING for something skipped, ERROR for
something that failed.

## 10. Testing

The test groups are described in the README. The structural rules that matter to
this design are:

- No test in the default run reaches the network. The price source is a protocol
  and tests inject a stub.
- `test/test_package.py` asserts the layering, so the dependency direction is
  enforced rather than merely documented.

The committed fixtures `test/stock_N225.csv` and `test/ti_N225.csv` predate the
rewrite and are load bearing: the contract test regenerates the computed
columns defined by the data contract from the first fixture.
