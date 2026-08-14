# finance

## Overview

**finance** is a batch pipeline for technical analysis of Japanese equities,
written for **one person analysing their own investments**. Once a day it
fetches prices from the J-Quants API, computes technical indicators, trains two
small models, writes CSV files and PNG charts into one directory, and mails a
summary to the operator.

It has no server, no database and no user interface of its own. The directory it
writes is read by [finance-dashboard](https://github.com/id774/finance-dashboard),
a private dashboard which renders it and generates nothing. The two repositories
share no code and no process; they share a directory of files, and the format of
those files is the whole of the interface between them.

```text
J-Quants API (Free plan, delayed)
     |
     v
finance  (cron, 18:10 on weekdays)
     |
     v
<data directory>/*.csv  *.txt  *.png
     |
     v
finance-dashboard  (read only, private)
```

**The data is not redistributed.** See [Purpose and Scope](#1-purpose-and-scope)
before deploying this, and [Data Source](#2-data-source) for what the Free plan
does and does not provide.

## Features

- **Prices from the J-Quants API Free plan**, a source an individual may use at
  no cost and read programmatically
- **Technical indicators through TA-Lib**, thirty-odd series per stock
- **A trend classifier and a price regression**, refreshed nightly per stock
- **Candlestick charts** at three window lengths, drawn without a display
- **Summary tables** for a portfolio, TOPIX Core30 and an RSI14 screening
- **Incremental price updates** that never rewrite stored history
- **A file contract with finance-dashboard**, pinned by regression tests
- **No network access, and no API key, in the test suite**

## Supported Environments

- Python 3.11 or later
- Linux (Debian, Ubuntu) with cron for production use
- A Japanese TrueType font for the chart captions

Python 3.11 is the minimum because it is the minimum of the scientific stack
this depends on: NumPy 2.4, pandas 3, SciPy 1.17, scikit-learn 1.9 and
matplotlib 3.11 all declare `requires-python >= 3.11`. Python 3.10 reaches end
of life in October 2026, so nothing is gained by holding it back.

## Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Data Source](#2-data-source)
3. [Installation](#3-installation)
4. [Configuration](#4-configuration)
5. [The API Key](#5-the-api-key)
6. [Data Pipeline](#6-data-pipeline)
7. [CLI Usage](#7-cli-usage)
8. [Generated Files](#8-generated-files)
9. [Relationship with finance-dashboard](#9-relationship-with-finance-dashboard)
10. [Architecture](#10-architecture)
11. [Testing](#11-testing)
12. [Deployment](#12-deployment)
13. [Directory Structure](#13-directory-structure)
14. [Migrating from the previous version](#14-migrating-from-the-previous-version)
15. [Documents](#15-documents)
16. [License](#16-license)

---

## 1. Purpose and Scope

This is software for analysing your own investments. It is written for one
person, and the following are design premises rather than preferences — the
code, the tests and the deployment are arranged around them:

- **Private analysis.** The system exists so that its operator can study a set
  of shares they follow. It is not a market data service and has no users.
- **The market data is not redistributed.** What it fetches is used to produce
  the operator's own analysis and is passed to nobody. No feature exists to hand
  it on, and none may be added.
- **No continuing analysis service for third parties.** Providing an ongoing
  feed of analysis derived from this data to anyone else is out of scope,
  whether or not money changes hands.
- **The consumer is a private dashboard.** `finance-dashboard` is read by the
  same person, behind their own access control. It is not a public web service.
- **The provider's terms and licence are followed.** They are a condition of
  using the data, and they are not the same thing as this repository's licence.
- **The input is free, legitimate and machine-readable.** An individual may use
  it at no cost, it is offered for programmatic access, and its terms permit
  this use.
- **Nothing is scraped.** No page written for a human is parsed for prices, and
  no undocumented endpoint is called. Where a free plan does not carry something,
  the capability is withdrawn rather than obtained by other means.
- **Publishing the code is not publishing the data.** This source is open
  source; the market data put through it is not, and never becomes so by being
  processed here.
- **Nothing sensitive is committed.** No API key, no fetched market data, no
  portfolio. `my_stocks.txt` lives on the host, and every test fixture that
  imitates an API response is invented.

[`doc/POLICY.md`](doc/POLICY.md) states the rules a change is judged against;
[`doc/REQUIREMENTS.md`](doc/REQUIREMENTS.md) states what the system is for.

---

## 2. Data Source

Prices come from the **J-Quants API**, the market data service JPX Market
Innovation & Research operates for individual investors, on its **Free plan**.
The pipeline speaks to the published **v2** interface: a base URL of
`https://api.jquants.com/v2`, an API key sent as the `x-api-key` request header,
and `GET /equities/bars/daily` for daily bars, following `pagination_key` until
the response carries none. The v1 refresh-token exchange was withdrawn on
1 June 2026 and is not implemented.

### What the Free plan gives, and what it does not

| | |
|---|---|
| Cost | Free to an individual |
| Delay | Publishes in arrears — twelve weeks at the time of writing |
| History | About two years behind that point |
| Datasets | Listed issues, daily bars, financial statements, earnings dates |
| Not included | Index values, intraday bars, and the other paid datasets |
| Rate limit | Per plan; requests are paced and a refusal is retried |

**These are the specification, not defects.** The system is built on them:

- It never asks for a date newer than the plan publishes, and reports the last
  trading day it holds so the delay is visible rather than hidden.
- A configured start date older than the plan keeps is raised to what the plan
  has, and the run says so.
- Every indicator is computable inside the window. The longest lookback is a
  200-day moving average against roughly 488 trading days of history, and a test
  asserts the margin.
- A shortfall is **never** made up from another source. No paid plan is assumed
  and no unofficial one is used.

### Market indices are gone

Earlier versions charted N225, GSPC, IXIC and DJI. The Free plan carries no
index values, and no free, licensed, machine-readable alternative has been
adopted, so the capability is withdrawn rather than replaced. Nothing in the
analysis of Japanese equities depends on a reference index: no indicator,
summary, screening or model takes one as an input.

"Not obtainable on acceptable terms, therefore not provided" is a legitimate
outcome, and a better one than an index of uncertain provenance.

---

## 3. Installation

```bash
git clone https://github.com/id774/finance.git
cd finance
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Install without `[dev]` for production, which omits the test and lint tools.

TA-Lib ships binary wheels for Linux, macOS and Windows, so no C library has to
be built by hand. If a wheel is unavailable for your platform, install the
TA-Lib C library first and let pip build the extension against it.

There is no `requirements.txt`. Dependencies are declared in `pyproject.toml`
and are installed by `pip install .`; see
[Migrating from the previous version](#11-migrating-from-the-previous-version).

---

## 4. Configuration

Settings are resolved once, at the entry point, in `finance/config.py`. No
module below it reads the environment. Precedence is **command line option,
then environment variable, then configuration file, then default**.

Nothing but the API key is required. With no other configuration the pipeline
writes into `./data` and `./clf`, fetches the whole window the plan keeps, and
sends no mail.

| Environment variable | Configuration key | Default | Description |
|---|---|---|---|
| `JQUANTS_API_KEY` | **refused in the file** | - | The J-Quants API key. See [The API Key](#5-the-api-key) |
| `FINANCE_CONFIG` | - | `config.yml` | Path of the YAML configuration file |
| `FINANCE_DATA_DIR` | `paths.data_dir` | `./data` | Where the generated files go |
| `FINANCE_HISTORY_DIR` | `paths.history_dir` | `<data_dir>/history` | Dated copies of the summaries |
| `FINANCE_MODEL_DIR` | `paths.model_dir` | `./clf` | Pickled models |
| `FINANCE_STOCK_LIST` | `pipeline.stock_list` | `stocks.txt` | Default stock list, inside the data directory |
| `FINANCE_START_DATE` | `pipeline.start_date` | empty | Earliest date fetched. Empty means the whole plan window |
| `FINANCE_JQUANTS_BASE_URL` | `jquants.base_url` | `https://api.jquants.com/v2` | Base URL of the API |
| `FINANCE_JQUANTS_DELAY_DAYS` | `jquants.delay_days` | `84` | How far behind today the plan's newest row is |
| `FINANCE_JQUANTS_RETENTION_DAYS` | `jquants.retention_days` | `730` | How far back from there the plan keeps data |
| `FINANCE_JQUANTS_REQUEST_INTERVAL` | `jquants.request_interval` | `1.0` | Minimum seconds between two requests |
| `FINANCE_JQUANTS_TIMEOUT` | `jquants.timeout` | `30` | Seconds one request may take |
| `FINANCE_JQUANTS_MAX_RETRIES` | `jquants.max_retries` | `3` | Attempts for a throttled or failed request |
| `FINANCE_FONT_PATH` | `charts.font_path` | Debian Japanese Gothic | Font for the chart caption |
| `FINANCE_LOG_LEVEL` | `logging.level` | `INFO` | Logging level |
| `FINANCE_MAIL_ENABLED` | `mail.enabled` | `false` | Whether a report may be mailed |
| `FINANCE_MAIL_HOST` | `mail.host` | `localhost` | SMTP host |
| `FINANCE_MAIL_PORT` | `mail.port` | `25` | SMTP port |
| `FINANCE_MAIL_FROM` | `mail.sender` | - | Sender, required when mail is enabled |
| `FINANCE_MAIL_TO` | `mail.recipient` | - | Recipient, required when mail is enabled |
| `FINANCE_MAIL_HOSTNAME_SUFFIX` | `mail.hostname_suffix` | - | Only send from a host whose name ends with this |

`delay_days` and `retention_days` describe the **subscription**, not the
program, and this table is the only place either number appears. They are
settings because a plan's published terms can change, and because a paid
subscription sets `delay_days` to `0`. Everything downstream follows from them:
which dates a fetch asks for, whether stored data counts as current, and whether
a summary treats a stock as stale.

Copy the sample to start:

```bash
cp config.yml.sample config.yml
```

A value that is present but unusable — a date that is not `YYYY-MM-DD`, a port
that is not a number, mail enabled without addresses — is refused before any
work begins. This job runs unattended, and a setting rejected at 18:10 is
cheaper than a wrong file written at 18:11.

The chart caption is Japanese and needs a font that can render it. On Debian and
Ubuntu:

```bash
sudo apt-get install fonts-vlgothic
```

Without a usable font the chart is still drawn; only the caption renders as
boxes.

---

## 5. The API Key

Register at the J-Quants site, subscribe to the Free plan, and issue a key from
its dashboard. Then export it:

```bash
export JQUANTS_API_KEY=your-key-here
```

In a deployment it lives in one file, created by `deploy.sh`, owned by root and
readable by nobody else, which `run.sh` sources:

```bash
sudo -e /var/stock/env     # JQUANTS_API_KEY=your-key-here
sudo chmod 600 /var/stock/env
```

**The environment is the only way in.** The name matches the one the official
J-Quants client reads, so a host that already exports it needs nothing added.

| Not accepted | Why |
|---|---|
| `config.yml` | Refused with an error. A file in the working tree is one careless `git add` from being published |
| A command line option | A command line is readable by every user of the host, so no such option exists |
| A committed sample value | Sample configuration carries no key, not even a placeholder that looks like one |

**Where the key never appears:** the log, an exception message, a command's
output, a generated CSV, a chart, the dashboard, an HTTP response, or a test's
output. It is read once in `config.py`, held in a field excluded from the
dataclass repr, and sent only as the `x-api-key` header. `test/test_package.py`
asserts that no module outside `config.py` reads it and that no logging call is
handed it; `test/test_datasources.py` asserts that no error message and no log
record contains it.

A run that would fetch without a key **fails before opening a socket**. A run
that only draws charts from stored files needs no key at all, which is why the
long and short chart passes of `run.sh` work without one.

`finance-dashboard` is never given the key. It does not fetch.

---

## 6. Data Pipeline

`run.sh` is the daily job, and its order is a specification rather than a habit:
each group of steps consumes what an earlier group wrote.

| # | Step | Produces | Consumes |
|---|---|---|---|
| 1 | Charts and indicators, `--update` | `stock_CODE.csv`, `ti_CODE.csv`, `chart_CODE.png`, `data_source.txt`, models | prices from the source |
| 2 | Summary, with history | `summary.csv`, `data/history/summary.csv.DATE.csv` | step 1 |
| 3 | Ten day summary | `summary_10.csv` | step 1 |
| 4 | Portfolio | `portfolio.csv` | step 1 |
| 5 | TOPIX Core30 | `topix_core30.csv` | step 1 |
| 6 | RSI14 screening | `screening_rsi14.csv` | step 1 |
| 7 | Mail the summary | - | step 2 |
| 8 | Mail the portfolio | - | step 4 |
| 9 | Long charts | `long_CODE.png` | step 1 |
| 10 | Short charts | `short_CODE.png` | step 1 |

Only step 1 passes `--update`. It is the run that fetches, rewrites, retrains
and records the provenance; steps 9 and 10 draw from what it already stored. The
job therefore makes one pass over the network per stock per day, and only step 1
needs the API key.

That pass is often empty, and that is correct. The plan publishes weeks in
arrears, so once the stored history reaches the newest published date there is
nothing to add until the window moves. The run says so by name and rewrites
nothing.

A step that fails is reported and the job carries on to the next, because a
broken summary is no reason to skip the charts. The exit status is non-zero if
any step failed, so cron mails the operator rather than the failure passing
unnoticed. Within step 1 the same rule applies per stock: one delisted code does
not cost the other thirty their charts.

The schedule lives in `cron.d/stock` and is unchanged:

```text
10 18  * * 1-5 root test -x /var/stock/run.sh && /var/stock/run.sh
```

18:10 on weekdays, after the Tokyo close. The hour matters less than it did: the
Free plan publishes weeks in arrears, so a run collects what was published long
before it, and a missed evening costs nothing the next run does not pick up. It
is cron rather than a systemd timer because a plain daily batch has no ordering,
activation or resource requirement that a timer would serve, and because it
works.

`my_stocks.txt`, the operator's holdings, is not in this repository. It lives in
the data directory on the host and uses the same format as `stocks.txt`. The
portfolio step fails without it and the rest of the job continues.

---

## 7. CLI Usage

Four commands are installed. Each accepts `-h` and `-v`, and each returns `0`
on success, `1` on failure and `2` on a rejected command line.

### finance-charts

Fetch prices, compute indicators, apply the models and draw a chart.

```bash
finance-charts -s stocks.txt -y 240 -u
finance-charts -c 7203 -n トヨタ -y 60
```

| Option | Meaning |
|---|---|
| `-c, --code CODE` | Analyse one stock. Ignored when `-s` is given |
| `-n, --name NAME` | Display name for the chart caption |
| `-s, --stock FILE` | Analyse every stock in a list, resolved against the data directory |
| `-r, --readfile FILE` | Read stored prices from this CSV instead of `stock_CODE.csv` |
| `-u, --update` | Fetch, rewrite both CSVs and persist the retrained models |
| `-d, --date DATE` | Earliest date to fetch. A date before the plan's window is raised to it |
| `-y, --days N` | Trailing rows to analyse and chart. `0` means all |
| `-a, --axis N` | `1` price panel only, `2` adds the oscillator panel |
| `-p, --complexity N` | `1` to `3`, how many series each panel carries |

Without `-u` the run draws a chart from stored data and writes nothing else — no
fetch, no CSV, no model, and **no API key needed**. The window given to `-y`
also selects the chart file: over 300 rows writes `long_`, 60 or fewer writes
`short_`, anything between writes `chart_`.

A stock code is four characters as it appears in a stock list. The five
character form the API uses exists only inside the data source layer. A code
that cannot name a Tokyo listing — a market index name, for instance — is
refused before a request is made.

### finance-summary

Aggregate the stored `ti_CODE.csv` files into one summary table.

```bash
finance-summary -o summary.csv -y -r 1 -k Ratio
finance-summary -o screening_rsi14.csv -r 1 -c rsi14 -a -k rsi14
```

| Option | Meaning |
|---|---|
| `-s, --stock FILE` | Stock list to aggregate. Defaults to the configured list |
| `-o, --output FILE` | Output name inside the data directory |
| `-r, --range N` | Rows the change spans. `1` compares the last two |
| `-k, --sortkey KEY` | Column to sort by. Defaults to `Ratio` |
| `-a, --ascending` | Sort ascending |
| `-c, --screening_key KEY` | Report this indicator instead of the model outputs |
| `-y, --history` | Also write a dated copy under the history directory |

### finance-notify

Mail a generated report.

```bash
finance-notify portfolio.csv "Summary Report of My Portfolio"
finance-notify --dry-run
```

Exits successfully when mail is not configured or the host is not permitted to
send. `--dry-run` prints the message and sends nothing.

### finance-migrate

Move the stored `stock_CODE.csv` and `ti_CODE.csv` files into a dated archive,
so that the next `--update` run rebuilds them from the current data source.

```bash
finance-migrate --dry-run
finance-migrate
```

**Run once, by hand, when upgrading a deployment whose stored files were
produced before the data source changed.** It is not in `run.sh` and nothing
calls it on a schedule. Nothing is deleted; the stock lists, summaries and
charts are untouched.

It exists because the two providers' price series do not mean the same thing and
the daily job merges stored rows with fetched ones. Rather than let a file's
older and newer halves disagree invisibly, the older half is set aside — and
deciding that about the operator's own archive is the operator's call, not a
cron job's. Expect the rebuilt history to be shorter: the Free plan keeps about
two years.

### Shared options

`--config PATH`, `--data-dir PATH` and `--log-level NAME` are accepted by all
three.

### Compatibility

`bin/charts.py` and `bin/summary.py` still work and forward to the commands
above with the same options. They hold no logic. They exist so that an
un-updated `run.sh` or crontab on the host keeps working across the upgrade, and
can be deleted once none remain.

---

## 8. Generated Files

Written into the data directory. [`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md)
is the normative description; this is the index.

| File | Format | Content |
|---|---|---|
| `stocks.txt` | `code,name` per line | The stock listing. An input, republished for the dashboard |
| `data_source.txt` | Tab separated key and value | Where the data came from, when it was generated, and its last trading day |
| `stock_CODE.csv` | Comma separated, `Date` index | Prices, updated incrementally |
| `ti_CODE.csv` | Comma separated, `Date` index | 42 indicator columns plus the two model outputs |
| `summary.csv` | Tab separated, `Code` header | Full summary, mailed |
| `summary_10.csv` | Tab separated, `Code` header | The same over a ten day change |
| `portfolio.csv` | Tab separated, `Code` header | The operator's holdings |
| `topix_core30.csv` | Tab separated, `Code` header | TOPIX Core30, with RSI9 |
| `screening_rsi14.csv` | Tab separated, `Code` header | Screening, sorted by RSI14 |
| `data/history/NAME.YYYYMMDD.csv` | Tab separated | Dated copy of a summary |
| `chart_CODE.png` | PNG, 1280x1024 | Standard chart, 61 to 300 rows |
| `long_CODE.png` | PNG, 1280x1024 | Long chart, over 300 rows |
| `short_CODE.png` | PNG, 1280x1024 | Short chart, 60 rows or fewer |

Two details are load bearing and easy to lose:

- The summary files are **tab** separated and are read **positionally** by the
  dashboard. A column inserted or reordered does not fail there; it shifts every
  later value into the wrong name.
- In `ti_CODE.csv` the `classified` and `predicted` columns are populated on the
  **last row only**. They are a statement about the next trading day, not a
  series.
- Every column of `stock_CODE.csv` is on **one basis**: the share-split adjusted
  series. Under the previous provider the candlesticks were drawn from
  unadjusted prices while the indicators were computed from an adjusted close,
  so a split put a step in the chart that the indicators under it did not have.
  No formula changed; the two now agree. See
  [section 11 of the data contract](doc/DATA_CONTRACT.md).

`data_source.txt` is why the dashboard can say how old its figures are. It
carries the last trading day the data covers, which is weeks behind the
generation date, and an unknown value is left **empty** rather than filled in
with today.

`ref_index.csv` was linked by earlier versions of the dashboard and was never
produced here. The link is gone; see
[section 10 of the data contract](doc/DATA_CONTRACT.md).

---

## 9. Relationship with finance-dashboard

`finance-dashboard` is not a dependency of this repository, at runtime or in its
tests. Neither imports the other, and this repository is complete on its own:
everything needed to produce correct output is specified here, in
`doc/DATA_CONTRACT.md`.

The integration is the directory. Point both at the same one:

```bash
# on the dashboard host
ln -s /var/stock/data public/data
```

`test/test_contract.py` pins every generated format, parsing the files exactly
as `finance_dashboard/data.py` parses them — splitting on tab, skipping the
`Code` header, zipping against the dashboard's own positional column lists, and
normalizing indicator headers the same way. Those column lists are duplicated
into the test on purpose rather than imported, because the duplication is the
contract and a divergence is what the test is for.

---

## 10. Architecture

Dependency points one way. A layer never imports one above it.

```text
finance/cli/charts.py  summary.py  notify.py     entry points
        |     argparse, exit codes, settings
        v
analysis.py  reporting.py  notification.py       application
        |     the order of the steps, and the paths
        v
indicators  features  models  aggregation        domain
charts      stocklist                             pure computation
        |
        v
storage.py   datasources/                        I/O
        |
        v
the filesystem, the J-Quants API
```

The rules this encodes:

- **The domain layer computes.** It takes frames and returns frames. It opens no
  file, makes no request, reads no environment variable and knows no path.
- **`config.py` is the only module that reads the environment.** Settings are
  resolved at the entry point and passed down.
- **`storage.py` is told where to write.** It decides no path.
- **Third-party types stay in their layer.** A `requests`, TA-Lib,
  scikit-learn or matplotlib exception is caught at the boundary of the module
  that owns it and re-raised as a `finance.errors` type.
- **The data source layer is sealed.** Authentication, the endpoint, query
  parameters, pagination, the request interval, retries, timeouts, HTTP status
  handling, the provider's field names and its five character code form all live
  in `datasources/jquants.py` and leave it in no direction. No module above it
  sees an HTTP response, and it in turn knows nothing about what is on disk,
  which provider wrote it, or what plan it is on.
- **No module calls `sys.exit`** except an entry point; `main()` returns a code.
- **No library module prints.** Everything logs; the CLIs write user-facing
  messages to stderr.

`test/test_package.py` asserts each of these against the source, so they are
enforced rather than merely intended.

The price source sits behind a small protocol with one method, so a test injects
a stub and replacing the provider is one file. It is built lazily: a run that
fetches fails on a missing key before it opens a socket, and a run that only
draws charts never builds it at all.

---

## 11. Testing

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

The suite makes no network request, needs no API key, and writes only into
temporary directories. `requests` is imported inside the adapter, never at
module scope, and the package imports without it.

**No market data from the provider is committed as a fixture.** Every API
response in the tests is invented, in the shape the adapter expects. The one
apparent exception is deliberate and bounded: `test/stock_N225.csv` and
`test/ti_N225.csv` are Nikkei 225 data committed in 2015, under a different
provider, and every regression expectation in the suite derives from them. They
are kept because deleting them would delete the evidence that the arithmetic has
not moved across three library generations. They are not refreshed, and nothing
from the current provider joins them.

The suite is in four groups:

- **Regression** — every indicator, feature and model value asserted against the
  numbers the previous test suite asserted, on the same committed fixture. These
  were produced in 2015 by pandas 0.16, NumPy 1.11, TA-Lib 0.4.9 and
  scikit-learn 0.17, and they still hold on the current stack. That is the
  evidence that the upgrade moved the API and not the arithmetic.
- **Contract** — every generated file, including a test that regenerates all 42
  computed columns of `test/ti_N225.csv` from `test/stock_N225.csv` and compares
  them column by column.
- **CLI** — every option the batch script passes, exit status, and output
  location.
- **Structure** — no `sys.path` mutation, no environment read outside
  `config.py`, no removed or private pandas API, one-way dependency, no module
  naming the withdrawn provider, and no module outside `config.py` reading or
  logging the API key.
- **Plan window** — that a fetch never asks beyond what the plan publishes, that
  a start date before the window is raised, that stored data reaching the newest
  published date is not re-requested, that staleness is measured against that
  date rather than today, and that the longest indicator lookback fits inside
  the retained history.

Checks that need the real endpoint live in `test/integration/`, are marked
`integration`, and are excluded from the default run and from CI. **CI is given
no API key and reaches no API.** Run them by hand when the provider is
suspected:

```bash
JQUANTS_API_KEY=... .venv/bin/pytest -m integration
```

They discard everything they fetch. Saving a response as a fixture is how the
rule against committing market data would get broken.

---

## 12. Deployment

```bash
./deploy.sh
```

The script installs the package into a virtual environment under `/var/stock`,
puts `run.sh` and the cron entry in place, and creates the directories the job
writes to. It never writes into `data/` or `clf/`.

| Concern | Location |
|---|---|
| Code | `/var/stock/.venv` |
| API key | `/var/stock/env`, mode 600, root only |
| Commands | `/var/stock/.venv/bin/finance-charts`, `-summary`, `-notify` |
| Batch script | `/var/stock/run.sh` |
| Data | `/var/stock/data` |
| History | `/var/stock/data/history` |
| Models | `/var/stock/clf` |
| Logs | `/var/log/sysadmin/stock.log` |
| Schedule | `/etc/cron.d/stock` |

`TARGET_DIR`, `PYTHON` and `DATA_GROUP` override the defaults. Code, data and
the credential are separated in responsibility: a deployment replaces the
virtual environment and the batch script, touches neither `data/` nor `clf/`,
and never writes a key into `env`. Updating data needs no code change, and
rotating the credential needs neither.

The dashboard's group reaches `data/` and nothing else — not the virtual
environment, not `config.yml`, and above all not `env`.

[`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md) has the full procedure, including the
first install and what to check afterwards.

---

## 13. Directory Structure

```text
.
├── finance/
│   ├── __init__.py        # version and logging setup
│   ├── config.py          # settings; the only module reading the environment
│   ├── errors.py          # error hierarchy
│   ├── stocklist.py       # stock list parsing
│   ├── indicators.py      # technical indicators
│   ├── features.py        # training set construction
│   ├── models.py          # trend classifier and price regression
│   ├── aggregation.py     # summary table construction
│   ├── charts.py          # chart rendering
│   ├── storage.py         # every file read and write
│   ├── analysis.py        # the per stock pipeline
│   ├── reporting.py       # the summary pipeline
│   ├── notification.py    # report delivery
│   ├── migration.py       # retiring data from a previous source
│   ├── datasources/       # price source protocol and the J-Quants adapter
│   └── cli/               # the four command line entry points
├── bin/                   # compatibility wrappers for the old paths
├── test/                  # pytest suite and the committed fixtures
│   └── integration/       # networked checks, excluded by default
├── data/                  # stock lists; generated files are gitignored
├── clf/                   # pickled models, gitignored
├── doc/                   # requirements, design, contract, deployment, license
├── cron.d/stock           # the schedule
├── run.sh                 # the daily pipeline
├── deploy.sh              # installation
├── config.yml.sample      # sample configuration
└── pyproject.toml         # metadata, dependencies, ruff and pytest settings
```

---

## 14. Migrating from the previous version

### From the version that fetched from Yahoo Finance

This is the change that needs action on both sides.

1. **Get a J-Quants API key** and put it in `/var/stock/env`. Nothing fetches
   without it. See [The API Key](#5-the-api-key).
2. **Retire the stored files.** Run `finance-migrate` once. The previous
   provider's series and this one's do not mean the same thing, and the daily
   job merges stored rows with fetched ones, so the older files are archived and
   rebuilt rather than merged. Nothing is deleted.
3. **Expect a shorter history.** The Free plan keeps about two years, where the
   old configuration fetched from 2014. Every indicator fits inside the window,
   and a test asserts it.
4. **Expect delayed data.** The newest row is weeks old, and
   `data_source.txt` says by how much. This is the plan working as intended, not
   a stalled pipeline.
5. **Drop the market indices from your stock lists.** N225, GSPC, IXIC and DJI
   cannot be fetched on this plan and are refused as codes. The shipped
   `stocks.txt` now holds listed equities.
6. **`START_DATE` in `run.sh` is empty by default**, meaning the whole plan
   window. An explicit older date is raised rather than refused, so an existing
   value does no harm.
7. **Update `finance-dashboard` in the same change.** It gains the delayed-data
   notice and loses the dead `ref_index.csv` link. The generated formats it
   already read are unchanged; `data_source.txt` is additive.

### From the version before the package restructuring

The generated files are unchanged, so `finance-dashboard` needs nothing done to
it. What changes is how this side is installed and driven.

1. **Install rather than copy.** `deploy.sh` no longer copies `bin/` and `lib/`
   into `/var/stock`; it builds `/var/stock/.venv` and installs the package.
   Remove the stale `/var/stock/bin` and `/var/stock/lib` after the first
   successful run.
2. **`requirements.txt` is gone.** Dependencies live in `pyproject.toml`. Where
   a deployment installed them with `pip install -r requirements.txt`, use
   `pip install .` instead.
3. **Ruby is no longer needed.** `bin/email.rb` and the `mail` gem are replaced
   by `finance-notify`. Configure `mail.*` — the old script had its addresses
   hardcoded — and keep `hostname_suffix` set to preserve the guard that stopped
   a copy of the tree from mailing anyone.
4. **The interpreter is not hardcoded.** `/opt/python/current/bin/python` is
   replaced by the virtual environment. If the host keeps its interpreter there,
   pass `PYTHON=/opt/python/current/bin/python` to `deploy.sh`; it must be 3.11
   or later.
5. **Existing pickles in `clf/` will not load.** They were written by
   scikit-learn 0.17. An unreadable model is logged and a fresh one trained in
   its place, which is what already happens for a stock seen for the first time.
   Nothing needs deleting.
6. **`update_charts.sh` is gone.** It was a reduced duplicate of `run.sh` and
   was referenced by nothing, including cron.
7. **`-u` is now honoured.** `bin/charts.py` accepted the flag and then ignored
   it on the stock-list path, so all three of the daily chart runs fetched,
   retrained and rewrote `ti_CODE.csv`. Now only the run that passes `-u` does.
   The visible effect is that `ti_CODE.csv` keeps the 240-row window rather than
   being truncated to 60 rows by the short run minutes later; its name,
   separator, index and columns are unchanged.
8. **cron is unchanged.** The entry and the schedule are the same.

---

## 15. Documents

| Document | Contents |
|---|---|
| [`doc/REQUIREMENTS.md`](doc/REQUIREMENTS.md) | What the system is for and where its responsibility ends |
| [`doc/BASIC_DESIGN.md`](doc/BASIC_DESIGN.md) | Composition, modules, data flow, error handling |
| [`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md) | Normative format of every generated file |
| [`doc/POLICY.md`](doc/POLICY.md) | Implementation rules a change is judged against |
| [`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md) | Installing, operating and diagnosing the pipeline |
| [`doc/MODERNIZATION_PLAN.md`](doc/MODERNIZATION_PLAN.md) | The survey and plan behind the package modernization |
| [`doc/JQUANTS_MIGRATION.md`](doc/JQUANTS_MIGRATION.md) | The survey and decisions behind the move to J-Quants |
| [`doc/VERSIONS`](doc/VERSIONS) | Release history of the repository |
| [`doc/LICENSE.md`](doc/LICENSE.md) | The license, with the full texts beside it |

Every one of them stands on its own. Nothing here requires reading another
repository to understand what this one does or how it is operated.

Routine operations, the log, and what to check when a step fails are in
[`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md) rather than here; this README is the
entrance, and the details live under `doc/`.

---

## 16. License

Two separate questions, and conflating them would be the most consequential
mistake a reader of this file could make.

### The source code

**This repository** is dual licensed under the
[GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html) or the
[LGPL version 3](https://www.gnu.org/licenses/lgpl-3.0.html), at your option.
For full details, please refer to [`doc/LICENSE.md`](doc/LICENSE.md). See also
[`doc/COPYING`](doc/COPYING) and [`doc/COPYING.LESSER`](doc/COPYING.LESSER) for
the complete license texts.

`pyproject.toml` carries the matching `license` field, and every source module
repeats the terms in its header block.

Third-party components keep their own licenses. This repository bundles none;
its dependencies are installed from PyPI and are listed in `pyproject.toml`.

### The market data

**The data this software fetches is not covered by that license, and does not
become freely usable by passing through code that is.** It is obtained from the
J-Quants API and remains governed by that provider's terms of service, which
permit use for personal investment analysis and prohibit redistributing the data
or providing a continuing analysis service to third parties. Read them before
using this, and follow them.

Publishing this source code is not publishing the data. Nothing in the GPL or
the LGPL grants anything over prices, indicators derived from them, or charts
drawn from them, and no wording in this repository should be read as suggesting
otherwise. The generated files are excluded from version control for that
reason, and no market data obtained from the provider is committed as a test
fixture.
