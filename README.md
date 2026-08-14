# finance

## Overview

**finance** is a batch pipeline for technical analysis of Japanese and
international market data. Once a day it fetches prices, computes technical
indicators, trains two small models, writes CSV files and PNG charts into one
directory, and mails a summary to the operator.

It has no server, no database and no user interface of its own. The directory it
writes is read by [finance-dashboard](https://github.com/id774/finance-dashboard),
which renders it and generates nothing. The two repositories share no code and
no process; they share a directory of files, and the format of those files is
the whole of the interface between them.

```text
Yahoo Finance
     |
     v
finance  (cron, 18:10 on weekdays)
     |
     v
<data directory>/*.csv  *.txt  *.png
     |
     v
finance-dashboard  (read only)
```

## Features

- **Technical indicators through TA-Lib**, thirty-odd series per stock
- **A trend classifier and a price regression**, refreshed nightly per stock
- **Candlestick charts** at three window lengths, drawn without a display
- **Summary tables** for a portfolio, TOPIX Core30 and an RSI14 screening
- **Incremental price updates** that never rewrite stored history
- **A file contract with finance-dashboard**, pinned by regression tests
- **No network access in the test suite**

## Supported Environments

- Python 3.11 or later
- Linux (Debian, Ubuntu) with cron for production use
- A Japanese TrueType font for the chart captions

Python 3.11 is the minimum because it is the minimum of the scientific stack
this depends on: NumPy 2.4, pandas 3, SciPy 1.17, scikit-learn 1.9 and
matplotlib 3.11 all declare `requires-python >= 3.11`. Python 3.10 reaches end
of life in October 2026, so nothing is gained by holding it back.

## Contents

1. [Installation](#1-installation)
2. [Configuration](#2-configuration)
3. [Data Pipeline](#3-data-pipeline)
4. [CLI Usage](#4-cli-usage)
5. [Generated Files](#5-generated-files)
6. [Relationship with finance-dashboard](#6-relationship-with-finance-dashboard)
7. [Architecture](#7-architecture)
8. [Testing](#8-testing)
9. [Deployment](#9-deployment)
10. [Directory Structure](#10-directory-structure)
11. [Migrating from the previous version](#11-migrating-from-the-previous-version)
12. [Documents](#12-documents)
13. [License](#13-license)

---

## 1. Installation

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

## 2. Configuration

Settings are resolved once, at the entry point, in `finance/config.py`. No
module below it reads the environment. Precedence is **command line option,
then environment variable, then configuration file, then default**.

Nothing is required. With no configuration at all the pipeline writes into
`./data` and `./clf` and sends no mail.

| Environment variable | Configuration key | Default | Description |
|---|---|---|---|
| `FINANCE_CONFIG` | - | `config.yml` | Path of the YAML configuration file |
| `FINANCE_DATA_DIR` | `paths.data_dir` | `./data` | Where the generated files go |
| `FINANCE_HISTORY_DIR` | `paths.history_dir` | `<data_dir>/history` | Dated copies of the summaries |
| `FINANCE_MODEL_DIR` | `paths.model_dir` | `./clf` | Pickled models |
| `FINANCE_STOCK_LIST` | `pipeline.stock_list` | `stocks.txt` | Default stock list, inside the data directory |
| `FINANCE_START_DATE` | `pipeline.start_date` | `2014-10-01` | Earliest date fetched for a new stock |
| `FINANCE_FONT_PATH` | `charts.font_path` | Debian Japanese Gothic | Font for the chart caption |
| `FINANCE_LOG_LEVEL` | `logging.level` | `INFO` | Logging level |
| `FINANCE_MAIL_ENABLED` | `mail.enabled` | `false` | Whether a report may be mailed |
| `FINANCE_MAIL_HOST` | `mail.host` | `localhost` | SMTP host |
| `FINANCE_MAIL_PORT` | `mail.port` | `25` | SMTP port |
| `FINANCE_MAIL_FROM` | `mail.sender` | - | Sender, required when mail is enabled |
| `FINANCE_MAIL_TO` | `mail.recipient` | - | Recipient, required when mail is enabled |
| `FINANCE_MAIL_HOSTNAME_SUFFIX` | `mail.hostname_suffix` | - | Only send from a host whose name ends with this |

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

## 3. Data Pipeline

`run.sh` is the daily job, and its order is a specification rather than a habit:
each group of steps consumes what an earlier group wrote.

| # | Step | Produces | Consumes |
|---|---|---|---|
| 1 | Charts and indicators, `--update` | `stock_CODE.csv`, `ti_CODE.csv`, `chart_CODE.png`, models | prices from the source |
| 2 | Summary, with history | `summary.csv`, `data/history/summary.csv.DATE.csv` | step 1 |
| 3 | Ten day summary | `summary_10.csv` | step 1 |
| 4 | Portfolio | `portfolio.csv` | step 1 |
| 5 | TOPIX Core30 | `topix_core30.csv` | step 1 |
| 6 | RSI14 screening | `screening_rsi14.csv` | step 1 |
| 7 | Mail the summary | - | step 2 |
| 8 | Mail the portfolio | - | step 4 |
| 9 | Long charts | `long_CODE.png` | step 1 |
| 10 | Short charts | `short_CODE.png` | step 1 |

Only step 1 passes `--update`. It is the run that fetches, rewrites and
retrains; steps 9 and 10 draw from what it already stored. The job therefore
makes one pass over the network per stock per day.

A step that fails is reported and the job carries on to the next, because a
broken summary is no reason to skip the charts. The exit status is non-zero if
any step failed, so cron mails the operator rather than the failure passing
unnoticed. Within step 1 the same rule applies per stock: one delisted code does
not cost the other thirty their charts.

The schedule lives in `cron.d/stock` and is unchanged:

```text
10 18  * * 1-5 root test -x /var/stock/run.sh && /var/stock/run.sh
```

18:10 on weekdays, after the Tokyo close and late enough for the day's prices to
have settled at the source. It is cron rather than a systemd timer because a
plain daily batch has no ordering, activation or resource requirement that a
timer would serve, and because it works.

`my_stocks.txt`, the operator's holdings, is not in this repository. It lives in
the data directory on the host and uses the same format as `stocks.txt`. The
portfolio step fails without it and the rest of the job continues.

---

## 4. CLI Usage

Three commands are installed. Each accepts `-h` and `-v`, and each returns `0`
on success, `1` on failure and `2` on a rejected command line.

### finance-charts

Fetch prices, compute indicators, apply the models and draw a chart.

```bash
finance-charts -s stocks.txt -d 2014-10-01 -y 240 -u
finance-charts -c 7203 -n トヨタ -y 60
```

| Option | Meaning |
|---|---|
| `-c, --code CODE` | Analyse one stock. Ignored when `-s` is given |
| `-n, --name NAME` | Display name for the chart caption |
| `-s, --stock FILE` | Analyse every stock in a list, resolved against the data directory |
| `-r, --readfile FILE` | Read stored prices from this CSV instead of `stock_CODE.csv` |
| `-u, --update` | Fetch, rewrite both CSVs and persist the retrained models |
| `-d, --date DATE` | Earliest date to fetch for a stock with no stored history |
| `-y, --days N` | Trailing rows to analyse and chart. `0` means all |
| `-a, --axis N` | `1` price panel only, `2` adds the oscillator panel |
| `-p, --complexity N` | `1` to `3`, how many series each panel carries |

Without `-u` the run draws a chart from stored data and writes nothing else — no
fetch, no CSV, no model. The window given to `-y` also selects the chart file:
over 300 rows writes `long_`, 60 or fewer writes `short_`, anything between
writes `chart_`.

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

### Shared options

`--config PATH`, `--data-dir PATH` and `--log-level NAME` are accepted by all
three.

### Compatibility

`bin/charts.py` and `bin/summary.py` still work and forward to the commands
above with the same options. They hold no logic. They exist so that an
un-updated `run.sh` or crontab on the host keeps working across the upgrade, and
can be deleted once none remain.

---

## 5. Generated Files

Written into the data directory. [`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md)
is the normative description; this is the index.

| File | Format | Content |
|---|---|---|
| `stocks.txt` | `code,name` per line | The stock listing. An input, republished for the dashboard |
| `stock_CODE.csv` | Comma separated, `Date` index | Raw prices, updated incrementally |
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

`ref_index.csv` is linked by the dashboard but is **not produced here**. See
[section 9 of the data contract](doc/DATA_CONTRACT.md#9-ref_indexcsv--documented-not-produced).

---

## 6. Relationship with finance-dashboard

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

## 7. Architecture

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
the filesystem, Yahoo Finance
```

The rules this encodes:

- **The domain layer computes.** It takes frames and returns frames. It opens no
  file, makes no request, reads no environment variable and knows no path.
- **`config.py` is the only module that reads the environment.** Settings are
  resolved at the entry point and passed down.
- **`storage.py` is told where to write.** It decides no path.
- **Third-party types stay in their layer.** A `yfinance`, TA-Lib,
  scikit-learn or matplotlib exception is caught at the boundary of the module
  that owns it and re-raised as a `finance.errors` type.
- **No module calls `sys.exit`** except an entry point; `main()` returns a code.
- **No library module prints.** Everything logs; the CLIs write user-facing
  messages to stderr.

`test/test_package.py` asserts each of these against the source, so they are
enforced rather than merely intended.

The price source sits behind a small protocol with one method, so a test injects
a stub and replacing the provider is one file.

---

## 8. Testing

```bash
.venv/bin/pytest
.venv/bin/ruff check .
```

The suite makes no network request and writes only into temporary directories.
`yfinance` is imported inside the adapter, never at module scope, and the
package imports without it.

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
  `config.py`, no removed or private pandas API, one-way dependency.

Checks that need the real endpoint live in `test/integration/`, are marked
`integration`, and are excluded from the default run and from CI. Run them by
hand when the provider is suspected:

```bash
.venv/bin/pytest -m integration
```

---

## 9. Deployment

```bash
./deploy.sh
```

The script installs the package into a virtual environment under `/var/stock`,
puts `run.sh` and the cron entry in place, and creates the directories the job
writes to. It never writes into `data/` or `clf/`.

| Concern | Location |
|---|---|
| Code | `/var/stock/.venv` |
| Commands | `/var/stock/.venv/bin/finance-charts`, `-summary`, `-notify` |
| Batch script | `/var/stock/run.sh` |
| Data | `/var/stock/data` |
| History | `/var/stock/data/history` |
| Models | `/var/stock/clf` |
| Logs | `/var/log/sysadmin/stock.log` |
| Schedule | `/etc/cron.d/stock` |

`TARGET_DIR`, `PYTHON` and `DATA_GROUP` override the defaults. Code and data are
separated in responsibility: a deployment replaces the virtual environment and
the batch script and touches neither `data/` nor `clf/`, and updating data never
requires a code change.

[`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md) has the full procedure, including the
first install and what to check afterwards.

---

## 10. Directory Structure

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
│   ├── datasources/       # price source protocol and the Yahoo adapter
│   └── cli/               # the three command line entry points
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

## 11. Migrating from the previous version

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

## 12. Documents

| Document | Contents |
|---|---|
| [`doc/REQUIREMENTS.md`](doc/REQUIREMENTS.md) | What the system is for and where its responsibility ends |
| [`doc/BASIC_DESIGN.md`](doc/BASIC_DESIGN.md) | Composition, modules, data flow, error handling |
| [`doc/DATA_CONTRACT.md`](doc/DATA_CONTRACT.md) | Normative format of every generated file |
| [`doc/POLICY.md`](doc/POLICY.md) | Implementation rules a change is judged against |
| [`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md) | Installing, operating and diagnosing the pipeline |
| [`doc/MODERNIZATION_PLAN.md`](doc/MODERNIZATION_PLAN.md) | The survey and plan behind the modernization |
| [`doc/VERSIONS`](doc/VERSIONS) | Release history of the repository |
| [`doc/LICENSE.md`](doc/LICENSE.md) | The license, with the full texts beside it |

Every one of them stands on its own. Nothing here requires reading another
repository to understand what this one does or how it is operated.

Routine operations, the log, and what to check when a step fails are in
[`doc/DEPLOYMENT.md`](doc/DEPLOYMENT.md) rather than here; this README is the
entrance, and the details live under `doc/`.

---

## 13. License

This repository is dual licensed under the
[GPL version 3](https://www.gnu.org/licenses/gpl-3.0.html) or the
[LGPL version 3](https://www.gnu.org/licenses/lgpl-3.0.html), at your option.
For full details, please refer to [`doc/LICENSE.md`](doc/LICENSE.md). See also
[`doc/COPYING`](doc/COPYING) and [`doc/COPYING.LESSER`](doc/COPYING.LESSER) for
the complete license texts.

The same terms apply to the sibling repositories `finance-dashboard` and
`reply-writer`, so the three are consistent. `pyproject.toml` carries the
matching `license` field, and every source module repeats the terms in its
header block.

Third-party components keep their own licenses. This repository bundles none;
its dependencies are installed from PyPI and are listed in `pyproject.toml`.
