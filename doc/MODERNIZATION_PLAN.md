# Modernization Plan

This document records the survey that preceded the modernization of this
repository and the plan derived from it. It is kept after the work as the
account of what was found, what was decided and why, so that a later reader can
tell an API migration from a change of behaviour without reading the old code.

The rule the whole plan is built around: **the files this repository writes are
a contract with `finance-dashboard`, and the modernization does not renegotiate
it.**

---

## 1. The system as it was found

`finance` is a batch pipeline. It has no server, no database and no user
interface. Once a day, driven by cron, it fetches prices, computes technical
indicators, trains two small models, writes CSV files and PNG charts into one
directory, and mails two of the CSV files to the operator.

`finance-dashboard` is a separate FastAPI application that reads that same
directory and renders it. It generates nothing. The two repositories share no
code and no process; they share a directory of files.

```text
Yahoo Finance
     |
     v
finance (cron, daily)
     |
     v
/var/stock/data/*.csv, *.txt, *.png
     |
     v
finance-dashboard (FastAPI)
```

### 1.1 Layout as found

| Path | Contents |
|---|---|
| `bin/charts.py` | `optparse` CLI: fetch, compute indicators, train, draw a chart |
| `bin/summary.py` | `optparse` CLI: aggregate `ti_*.csv` into a summary table |
| `bin/demo.py` | ipython demonstration helper |
| `bin/email.rb` | Ruby script mailing a CSV to the operator |
| `lib/*.py` | Nine modules imported by mutating `sys.path` |
| `test/*.py` | Eight `nose` test modules plus two CSV fixtures |
| `data/` | `stocks.txt`, `topix_core30.txt`; generated files are gitignored |
| `clf/` | Pickled models, one pair per stock code |
| `cron.d/stock` | `10 18 * * 1-5 root /var/stock/run.sh` |
| `run.sh` | The daily pipeline |
| `update_charts.sh` | A reduced pipeline, no longer referenced by cron |
| `deploy.sh` | `cp -av bin lib` into `/var/stock` |
| `requirements.txt` | Seven dependencies, all pinned to 2015-2016 releases |

### 1.2 Data flow as found

`run.sh` is the specification of the daily job. Its order matters, because
each step consumes what an earlier step wrote:

1. `charts.py -a 2 -p 2 -s stocks.txt -d 2014-10-01 -y 240 -u`
   For every code: read `stock_CODE.csv`, fetch anything newer, write
   `stock_CODE.csv`, compute indicators, train and persist both models, write
   `ti_CODE.csv`, draw `chart_CODE.png`.
2. `summary.py -o summary.csv -y -r 1 -k Ratio` — full summary, plus a dated
   copy under `data/history/`.
3. `summary.py -o summary_10.csv -r 10 -k Ratio` — the same over a 10-day change.
4. `summary.py -s my_stocks.txt -o portfolio.csv -r 1 -k Ratio` — the operator's
   holdings. `my_stocks.txt` is not in the repository; it is a private file on
   the host.
5. `summary.py -s topix_core30.txt -o topix_core30.csv -r 1 -c rsi9 -k Ratio`
6. `summary.py -o screening_rsi14.csv -r 1 -c rsi14 -a -k rsi14`
7. `email.rb` — mails `summary.csv`.
8. `email.rb portfolio.csv ...` — mails `portfolio.csv`.
9. `charts.py ... -y 600` — long charts.
10. `charts.py ... -y 60` — short charts.

Steps 2-6 read the `ti_CODE.csv` files written by step 1, which is why the
summaries come after the charts and before the long and short runs.

### 1.3 What decides the chart file name

`Analysis` picks the prefix from the requested window, not from an option:

| Window (`-y`) | Prefix | File |
|---|---|---|
| `> 300` | `long` | `long_CODE.png` |
| `61`-`300` | `chart` | `chart_CODE.png` |
| `<= 60` | `short` | `short_CODE.png` |

`run.sh` uses 240, 600 and 60, producing all three.

---

## 2. The contract with finance-dashboard

This was established by reading `finance_dashboard/data.py`,
`finance_dashboard/indicators.py`, the Jinja2 templates and `test/conftest.py`
in that repository, not by reading its README alone. It is restated in full in
[`DATA_CONTRACT.md`](DATA_CONTRACT.md), which is the normative document; what
follows is the summary that drove the plan.

| File | Read by the dashboard as | Verdict |
|---|---|---|
| `stocks.txt` | `code,name` per line, comma separated | unchanged |
| `ti_CODE.csv` | Comma separated, header row, `csv.DictReader`, header cells normalized to lower snake case | unchanged |
| `stock_CODE.csv` | Served as a file download, not parsed | unchanged |
| `portfolio.csv` | Tab separated, 10 positional fields, `Code` header skipped | unchanged |
| `topix_core30.csv` | Tab separated, 9 positional fields | unchanged |
| `screening_rsi14.csv` | Tab separated, 9 positional fields | unchanged |
| `chart_CODE.png`, `long_CODE.png`, `short_CODE.png` | `<img>` sources | unchanged |
| `summary.csv`, `summary_10.csv` | **not read** — mail only | unchanged |
| `data/history/*.csv` | **not read** — operator's archive | unchanged |
| `ref_index.csv` | Linked from the index page | **no longer produced** (see 2.2) |

The decisive detail is that the summary files are read **positionally**. The
dashboard skips the header line and then does `dict(zip(columns, fields))`. A
column inserted, removed or reordered in a summary file silently shifts every
value after it into the wrong name. `ti_CODE.csv` is read by header name
instead, so it tolerates reordering but not renaming.

### 2.1 Column order of `ti_CODE.csv`

The order is not decorative: it is the order in which `Analysis` calls the
indicator methods, and `test/ti_N225.csv` records it. It is now pinned by a
contract test rather than left to the call order of a procedure.

### 2.2 `ref_index.csv` is an orphan

`finance-dashboard` links `ref_index.csv` from its index page and documents it
as a file it reads. Nothing in `finance` writes it. It was produced by
`bin/reference.rb`, a Ruby script using the `jpstock` gem, deleted in commit
`e6fef22` ("307 Remove reference.rb"). The gem scraped a Yahoo Japan quote page
that no longer exists.

This is a pre-existing gap, not one this work introduces. Restoring it would
mean choosing a new source for fundamentals — PER, PBR, EPS, BPS, dividend
yield, market capitalisation — which is a feature decision, not a
modernization. It is therefore recorded as a known limitation and left alone.
The dashboard degrades gracefully: the link 404s.

---

## 3. Legacy inventory

### 3.1 Dependencies as found

| Package | Pinned | Released | State |
|---|---|---|---|
| `matplotlib` | 1.4.3 | 2015 | `matplotlib.finance` deleted in 3.0 |
| `numpy` | 1.11.0 | 2016 | pre-dates NumPy 2 |
| `pandas` | 0.16.2 | 2015 | `.ix`, `pandas.stats`, `pandas.core.datetools`, `DataFrame.sort` all deleted |
| `pandas-datareader` | 0.2.1 | 2015 | its Yahoo reader stopped working in 2017 |
| `scikit-learn` | 0.17.1 | 2016 | pickles from it will not load on any modern release |
| `scipy` | 0.17.1 | 2016 | pulled in only by scikit-learn |
| `TA-Lib` | 0.4.9 | 2016 | required a hand-built C library |

### 3.2 Removed APIs relied upon

| Use | Where | Replacement |
|---|---|---|
| `pandas.stats.moments.ewma` | `ti.py` | `Series.ewm(span=..., adjust=True, min_periods=0).mean()` |
| `pandas.core.datetools.to_datetime` | `jpstock.py` | `pandas.to_datetime` |
| `pandas.tools.plotting` / `pandas.plotting._core` internals | `draw.py`, `ohlc_plot.py` | drawn with matplotlib primitives |
| `pandas.tseries.plotting._decorate_axes`, `format_dateaxis` | `ohlc_plot.py` | matplotlib date axis |
| `matplotlib.finance.candlestick_ochl` | `ohlc_plot.py` | a local candlestick renderer |
| `pd.rolling_std`, `pd.rolling_corr` | `ti.py` | `Series.rolling(...).std()` / `.corr()` |
| `DataFrame.ix` | six modules | `.loc` / `.iloc` by intent |
| `DataFrame.sort` | `aggregate.py` | `sort_values` |
| `Timestamp.to_datetime` | `aggregate.py` | `Timestamp.date()` |
| `Series.resample(freq, how=...)` | `ohlc_plot.py` | dead code, removed |
| `optparse` | both CLIs | `argparse` |
| `sys.path.append` | every module | a real package |
| `try: import cPickle` | two modules | `pickle` |
| `sys.version_info > (3, 0)` guards | five modules | `requires-python` |
| `nose.tools.eq_` | every test | plain `assert` under pytest |
| `http://` data URLs | `jpstock.py` | HTTPS, via the source library |

### 3.3 Operational legacy

| Item | Finding |
|---|---|
| `/opt/python/current/bin/python` hardcoded | A pyenv-style symlink on the host. Replaced by a virtual environment interpreter, still overridable. |
| `/opt/ruby/current/bin/ruby` hardcoded | Needed only by `email.rb`. Removed with it. |
| `/var/stock` hardcoded in library code | `summary.py` and the model modules computed paths from `__file__`. Moved into settings. |
| `deploy.sh` copying `bin/` and `lib/` | Replaced by an installed package in a virtual environment. |
| `run.sh` `#!/bin/bash`, unquoted variables, backticks, `exit 0` at the end | Rewritten as POSIX `sh` that reports failure. |
| `cron.d/stock` at 18:10 on weekdays | **Kept exactly.** It is an operational contract, and nothing about it is broken. |
| `update_charts.sh` | Referenced by nothing. A reduced duplicate of `run.sh`. Removed. |
| `bin/demo.py` | An ipython aid that duplicates the pipeline. Removed; the CLI does the same thing. |

---

## 4. What must not change

- The name, separator, index label, column set and column order of every
  generated file.
- The formula of every indicator, including the quirks:
  `ratio = round((1 + change) / close * 100, 2)` is arithmetically odd but it is
  what both the summaries and the chart caption have always reported, and both
  the dashboard and the operator read it as such.
- The truncation of summary values with `int()` rather than rounding.
- The rule that only the last row of `ti_CODE.csv` carries `classified` and
  `predicted`.
- The 10-day staleness filter that drops a stock whose latest row is older than
  ten days from a summary.
- The mapping from window length to chart file prefix.
- The `-c/-n/-s/-r/-u/-d/-y/-a/-p` options of `charts.py` and the
  `-s/-o/-r/-k/-a/-c/-y` options of `summary.py`.
- The cron schedule.

---

## 5. Verified: the calculations survive the library jump

Before writing any new code, the whole computational core was re-executed on
NumPy 2.4, pandas 3.0, SciPy 1.17, scikit-learn 1.9 and TA-Lib 0.7 and compared
against the values the old tests assert and against the committed
`test/ti_N225.csv`.

- Every one of the 31 indicator values asserted by `test_ti.py` reproduces
  **exactly** at the asserted precision.
- Regenerating all 42 indicator columns of `test/ti_N225.csv` from
  `test/stock_N225.csv` reproduces the committed fixture with a maximum
  relative difference of `9.1e-15` and an identical NaN pattern in every
  column.
- `Features.binary_class` and `proportion_class` reproduce every expected label
  and window.
- The decision tree reproduces its expected class, and Ridge reproduces
  `19177.97` to the asserted two decimal places.

The conclusion that shapes the rest of the plan: **for indicators, features and
models this is an API migration, not a numerical one.** No formula is touched,
and no "the library changed the answer" allowance is needed. The one place
where output genuinely cannot be byte-identical is chart rendering, because the
drawing function it used no longer exists.

The `ewma` equivalence is worth stating explicitly, because it is the only
non-obvious mapping. `pandas.stats.moments.ewma(x, span=n)` defaulted to
`adjust=True`, `ignore_na=False`, `min_periods=0`; `Series.ewm` defaults
differently on `min_periods` in some call forms, so the three parameters are
passed explicitly rather than left to defaults.

---

## 6. The data source

### 6.1 What was there

Two paths, chosen by whether the code is an index:

- `N225`, `GSPC`, `IXIC`, `DJI` went to `pandas_datareader.data.DataReader('^CODE', 'yahoo', ...)`.
- Everything else went to `JpStock`, which paged through
  `http://info.finance.yahoo.co.jp/history/?code=NNNN.T&...` with
  `pandas.read_html` and renamed the Japanese columns.

Both are dead. The Yahoo endpoint `pandas-datareader` used was withdrawn in
2017, and the Yahoo Japan history page it scraped no longer exists. Neither is
deprecated-but-working; both fail outright. There is no option to keep them.

### 6.2 What replaces them

One adapter over `yfinance`, mapping a code to a Yahoo symbol: the four indices
keep their `^` prefix, and any other code becomes `CODE.T`. This is the
narrowest possible move, because it is the same upstream data provider the
repository has always used — only the access route changes.

### 6.3 The differences it introduces, and how they are contained

This is the one place where the meaning of the data can shift, so it is handled
in the adapter and not allowed to reach the analysis code.

| Aspect | Legacy | yfinance | Handling |
|---|---|---|---|
| Column set | `Open, High, Low, Close, Volume, Adj Close` | adds `Dividends`, `Stock Splits`, sometimes `Capital Gains` | extra columns dropped, the six reordered to the legacy order |
| Adjusted close | present when `auto_adjust=False` | **absent** under the modern default `auto_adjust=True` | `auto_adjust=False` passed explicitly; a response without `Adj Close` is an error, never silently filled from `Close` |
| Index | tz-naive dates | tz-aware in the exchange timezone | localized away and normalized to midnight, so a date never shifts by a day |
| Calendar | trading days | trading days | reindexed to business days, matching what `JpStock` returned |
| Volume | integer | integer, occasionally `NaN` | left as fetched; the downstream `dropna()` already handles it |
| Split handling | Yahoo Japan adjusted `Adj Close` for splits only | Yahoo adjusts for splits **and** dividends | **a genuine difference — see below** |

The dividend adjustment is the only difference that changes numbers rather than
shape, and only for Japanese stocks, whose old `Adj Close` was split-adjusted
only. The effect is confined to `Adj Close`, and therefore to every indicator
computed from it, on stocks that pay dividends.

It cannot be avoided while using Yahoo, and reconstructing a split-only series
would mean inventing an adjustment the source does not publish. It is therefore
accepted, documented, and bounded by the fact that it applies to newly fetched
history only: the existing `stock_CODE.csv` files are never rewritten
retroactively, because the incremental update combines new rows onto the stored
ones with the stored rows winning. A stock's history does not change under the
operator's feet; only rows fetched from now on come from the new adjustment
basis. The indices — which is what the committed fixtures cover — are
unaffected, since they pay no dividends.

### 6.4 Testability

`yfinance` is imported inside the adapter, never at module scope elsewhere, and
the analysis layer depends on a small protocol with a `fetch(code, start, end)`
method. Tests inject a stub. No test in the ordinary suite performs a network
request, and the package imports without `yfinance` installed.

---

## 7. The new structure

```text
finance/
  __init__.py        version, logging setup
  config.py          Settings; the only module that reads the environment
  errors.py          the error hierarchy
  stocklist.py       parsing stocks.txt and its variants
  indicators.py      TechnicalIndicators — pure computation
  features.py        Features — pure computation
  models.py          TrendClassifier, PricePredictor — pure fit/predict
  aggregation.py     Aggregator — pure computation over loaded frames
  charts.py          ChartRenderer — matplotlib, writes a PNG
  storage.py         every CSV and pickle read and write
  datasources/
    __init__.py      StockDataSource protocol, create_source()
    yahoo.py         the yfinance adapter
  analysis.py        the per-stock pipeline
  reporting.py       the summary pipeline
  notification.py    mailing a report
  cli/
    charts.py  summary.py  notify.py
```

Dependency direction, one way:

```text
finance/cli/*            entry points: argparse, exit codes, settings
      |
      v
analysis.py, reporting.py, notification.py    application
      |
      v
indicators, features, models, aggregation, charts, stocklist     domain
      |
      v
storage.py, datasources/                      I/O
```

The rules this encodes:

- The domain modules take frames and return frames. They open no file, make no
  request, read no environment variable and know no path.
- `storage.py` is told where to write; it does not decide.
- `config.py` is the only module that reads `os.environ`. Settings are resolved
  at the entry point and passed down.
- `yfinance`, `talib`, `sklearn` and `matplotlib` types and exceptions do not
  cross upward out of the layer that owns them; failures become
  `finance.errors` exceptions.
- No module calls `sys.exit`; `main()` returns an exit code.

`bin/charts.py` and `bin/summary.py` remain as compatibility wrappers so that an
un-updated `run.sh` or crontab keeps working. They contain argument forwarding
and nothing else.

---

## 8. CLI

Preserved option by option. `argparse` replaces `optparse`, and each CLI gains
`-h` and `-v`.

| Console script | Wrapper | Options |
|---|---|---|
| `finance-charts` | `bin/charts.py` | `-c -n -s -r -u -d -y -a -p` |
| `finance-summary` | `bin/summary.py` | `-s -o -r -k -a -c -y` |
| `finance-notify` | replaces `bin/email.rb` | `[file] [subject]` |

Exit codes: `0` success, `1` a run failed, `2` the command line was rejected.

Two deliberate corrections, both of which the old code contradicted itself on:

1. `charts.py` accepted `-u` and then, on the stock-list path, hardcoded
   `update=True`, ignoring it. `run.sh` passes `-u` only on the first of its
   three chart runs, and commit `7dd9e05` ("288 Not write ti.csv when update is
   false") shows the intent plainly. Honouring the flag means the long and
   short runs no longer refetch, no longer rewrite `stock_CODE.csv`, no longer
   retrain and re-pickle both models, and no longer overwrite `ti_CODE.csv`.
   The visible effect on the contract is that `ti_CODE.csv` keeps the 240-day
   window written by the `-u` run instead of being truncated to 60 rows by the
   short run minutes later. The file's name, separator, index and columns are
   unchanged; it simply holds the window the operator asked to keep. This is
   recorded here rather than done silently.
2. `summary.py` declared `-s` as "read stock names from text file" but the
   value was used only in the constructor, while `aggregate()` took a second,
   always-defaulted `filename` parameter of the same name. The dead parameter
   is gone.

---

## 9. Test strategy

`nose` has not run on a supported Python for years, so the suite moves to
pytest. No test is dropped for being old: every assertion in the eight existing
modules was read and carried over, and the two CSV fixtures are kept untouched
and are now load-bearing.

Four groups:

1. **Regression** — the indicator, feature and model values verified in section
   5, asserted against the same expected numbers the old suite used.
2. **Contract** — the shape of every generated file, including a test that
   regenerates all 42 indicator columns from `stock_N225.csv` and compares them
   against `ti_N225.csv` column by column, and tests that parse the summary
   files the way `finance-dashboard` parses them: split on tab, skip the `Code`
   header, `zip` against the dashboard's own positional column lists.
3. **CLI** — success, bad arguments, missing input, exit status, output
   location.
4. **Data source** — the adapter's normalization, driven by stub frames shaped
   like `yfinance` responses. Networked checks live in `test/integration/`,
   deselected by default and excluded from CI.

Old assertions that could not be carried across, and why:

- `test_analysis.py` asserted `os.path.exists('chart_N225.png')` relative to the
  working directory. The output directory is now explicit, so the assertion
  moves to a temporary directory.
- `test_draw.py` asserted only that a PNG appeared. That is kept; pixel
  comparison was never done and is not introduced.
- `test_aggregate.py` asserted `result.empty` against a directory with no
  matching `ti_*.csv`. Kept, and joined by tests that assert a populated result.

### The classifier's untested edge

`Classifier.classify` was reachable before `train`, in which case `self.clf`
does not exist and it raises `AttributeError`. `Analysis` always trains first,
so the path never ran in production. The new `TrendClassifier` raises a
`ModelNotTrainedError` instead, and that is tested.

---

## 10. Deployment

The shape of the deployment changes; its location does not.

| Concern | Was | Becomes |
|---|---|---|
| Code | `cp -av bin lib /var/stock` | `pip install .` into `/var/stock/.venv` |
| Interpreter | `/opt/python/current/bin/python` | `/var/stock/.venv/bin/python`, overridable |
| Ruby | `/opt/ruby/current/bin/ruby` + the `mail` gem | removed |
| Data | `/var/stock/data` | `/var/stock/data`, unchanged, now a setting |
| History | `/var/stock/data/history` | unchanged |
| Models | `/var/stock/clf` | unchanged, now a setting |
| Logs | `/var/log/sysadmin/stock.log` | unchanged |
| Schedule | `cron.d/stock`, 18:10 weekdays | unchanged |

Code and data stay in the same tree but are separated in responsibility: a
deployment replaces `.venv` and the checkout and never touches `data/` or
`clf/`, and updating data never requires touching code.

cron is kept. It works, the operator knows it, and the job is a plain daily
batch with no dependency ordering, socket activation or resource control that a
systemd timer would give it. Replacing it would be change for its own sake.

---

## 11. Configuration

Resolved once, at the entry point, in `config.py`; nothing below it reads the
environment.

| Setting | Environment variable | Default |
|---|---|---|
| Data directory | `FINANCE_DATA_DIR` | `./data` |
| History directory | `FINANCE_HISTORY_DIR` | `<data>/history` |
| Model directory | `FINANCE_MODEL_DIR` | `./clf` |
| Stock list | `FINANCE_STOCK_LIST` | `stocks.txt` |
| Start date | `FINANCE_START_DATE` | `2014-10-01` |
| Chart font | `FINANCE_FONT_PATH` | the Debian Japanese Gothic path |
| Log level | `FINANCE_LOG_LEVEL` | `INFO` |
| Mail settings | `FINANCE_MAIL_*` | unset; notification is skipped |

A YAML file may supply the same keys, matching how `finance-dashboard` is
configured on the same host. Precedence is CLI option, then environment, then
file, then default. A malformed value is refused at startup rather than
producing a wrong file at 18:10.

---

## 12. Error handling

The old pipeline swallowed nearly everything: `FileIO` caught bare `Exception`
and returned an empty frame, and `Analysis` caught `ValueError` and `KeyError`
and returned `None`. A failed fetch and a genuinely empty result were
indistinguishable, and the exit status did not reflect either.

The replacement keeps the operational intent — **one bad stock must not stop the
nightly run for the other thirty** — while making it visible:

- Errors are typed: `DataSourceError`, `DataFormatError`, `IndicatorError`,
  `ModelError`, `StorageError`, `ConfigurationError`.
- In a stock-list run each failure is logged with its code and the run
  continues. The count is reported at the end and the exit status is non-zero
  if any stock failed, so cron mail shows a partial failure instead of hiding
  it.
- A single-stock run fails immediately with a non-zero status.
- A configuration error fails before any work starts.
- No library module prints; all of them log. The CLIs write user-facing
  messages to stderr.

---

## 13. Order of work

Contracts first, because they are the hardest to walk back:

1. Fixtures and contract tests against the current output format.
2. `pyproject.toml` and the package skeleton.
3. Domain modules ported with the formulas untouched, under the regression
   tests.
4. `storage.py`, then `datasources/`.
5. `analysis.py` and `reporting.py`.
6. The CLIs and the compatibility wrappers.
7. `run.sh`, `cron.d`, `deploy.sh`.
8. README and `doc/`.

---

## 14. Risks

| Risk | Mitigation |
|---|---|
| Dividend-adjusted `Adj Close` shifts Japanese stock indicators | Documented in 6.3; stored history is never rewritten; indices unaffected |
| Charts cannot be pixel-identical | Series, colours, labels, caption, figure size and file names preserved; the caption is asserted by test |
| Existing pickles in `clf/` were written by scikit-learn 0.17 and cannot be loaded | An unreadable model file is logged and a fresh model trained in its place, which is what the first run of any new stock already does |
| A summary column shifting would corrupt the dashboard silently | Contract tests parse the files exactly as the dashboard does |
| `yfinance` is an unofficial client and may break | Confined to one adapter behind a protocol; a replacement touches one file |
| pandas 3 changed `Series.__getitem__` and copy semantics | Positional access is now explicit `.iloc` everywhere; the fixture comparison would catch a regression |

---

## 15. License

**Unresolved, and deliberately not decided here.**

The repository has never contained a `LICENSE`, `COPYING` or any license header,
in any commit reachable in its history. `README.md` states none, and
`pyproject.toml` did not exist. The sibling repositories `finance-dashboard` and
`reply-writer` are both dual licensed GPL-3.0-or-later or LGPL-3.0-or-later and
carry the texts under `doc/`, which suggests the same intent here — but that is
an inference about the author's wishes, not a fact recorded in this repository.

Choosing a license is the copyright holder's decision and is out of scope for a
modernization. `pyproject.toml` therefore carries **no** `license` field, and no
license file has been added. This is reported as an open item for the
maintainer to settle.
