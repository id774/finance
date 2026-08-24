# Deployment

How to install and operate the pipeline on the host that runs it nightly.

The deployment root is `/var/stock`, unchanged from the previous version. What
changed is that code arrives as a package installed into a virtual environment
rather than as `bin/` and `lib/` copied into place.

---

## What this touches, and what it does not

`deploy.sh` replaces:

- `/var/stock/.venv` — the virtual environment and the installed package
- `/var/stock/run.sh` — the batch script
- `/etc/cron.d/stock` — the schedule

It creates, if absent, and otherwise leaves alone:

- `/var/stock/data`, `/var/stock/data/history`, `/var/stock/clf`
- `/var/stock/data/stocks.txt` and `topix_core30.txt`, only when missing
- `/var/stock/env`, empty, mode 600, root only — the file the API key goes in

It never writes into `data/` or `clf/`, and it never writes a key into `env`.
Deploying cannot disturb generated data, updating data never needs a code
change, and rotating the credential never needs either.

These concerns are kept apart on purpose, and it is worth naming them because
they used to be one directory of copied files:

| Concern | Where |
|---|---|
| Application code | `/var/stock/.venv`, an installed package |
| Batch script | `/var/stock/run.sh` |
| Configuration | `/var/stock/config.yml`, optional |
| Credential | `/var/stock/env`, root only |
| Generated data and charts | `/var/stock/data`, readable by the dashboard's group |
| Models | `/var/stock/clf` |
| Logs | `/var/log/sysadmin/stock.log` |
| Schedule | `/etc/cron.d/stock` |

The dashboard's group reaches exactly one of those.

---

## Before you begin

- Linux with cron, `sudo`, and Python **3.11 or later**.
- **A J-Quants API key.** Obtain a key for the J-Quants subscription used by
  this deployment. The pipeline cannot fetch without one, and there is no
  other way to give it prices.
- A Japanese TrueType font for the chart captions:
  `sudo apt-get install fonts-vlgothic`.
- A local mail relay on port 25 if reports are to be sent.
- The log directory `/var/log/sysadmin/` must exist and be writable by root.

Check the interpreter first. This is the one prerequisite that will not announce
itself politely:

```bash
python3 --version
```

If the host keeps its interpreter at `/opt/python/current/bin/python`, as the
previous deployment assumed, pass it explicitly and make sure it is new enough:

```bash
/opt/python/current/bin/python --version
```

---

## Install

```bash
git clone https://github.com/id774/finance.git
cd finance
./deploy.sh
```

Override the defaults through the environment:

```bash
TARGET_DIR=/var/stock \
PYTHON=/opt/python/current/bin/python \
DATA_GROUP=www-data \
./deploy.sh
```

| Variable | Default | What it decides |
|---|---|---|
| `TARGET_DIR` | `/var/stock` | Deployment root |
| `PYTHON` | `python3` on `PATH` | Interpreter the virtual environment is built from |
| `DATA_GROUP` | `www-data` | Group given read access to the generated data |

`DATA_GROUP` is how the dashboard reads the files. It must match the user the
dashboard runs as.

---

## The API key

The key is the one secret this system has, and it is kept in one file.
`deploy.sh` creates it empty, owned by root and readable by nobody else. Fill it
in by hand:

```bash
sudo -e /var/stock/env
```

```text
# Environment for the finance job, sourced by run.sh.
# Put the J-Quants API key here and nowhere else.
JQUANTS_API_KEY=your-key-here
```

```bash
sudo chown root:root /var/stock/env
sudo chmod 600 /var/stock/env
```

`run.sh` sources it and refuses to start if the key is empty, so a missing
credential is a message at 18:10 rather than thirty failed fetches.

Four things not to do with it:

- **Do not put it in `config.yml`.** The settings loader refuses a key found
  there. A file in the working tree is one careless `git add` from being
  published.
- **Do not pass it on a command line.** A command line is readable by every user
  of the host, and there is no option that accepts one.
- **Do not give it to `finance-dashboard`.** That side does not fetch and has no
  use for it.
- **Do not commit it**, in any form, including as a sample value.

The key is never written to the log, an error message, a generated file, a chart
or the dashboard. If you ever see one in any of those, it is a bug worth
reporting.

The dashboard host, if it is a different machine, needs read access to the
generated directory and nothing else.

---

## Configure

Configuration is optional. Without any, the pipeline writes into the data
directory `run.sh` exports, fetches the whole configured plan window, and
sends no mail.

The settings worth knowing about are under `jquants`, which describe the plan
rather than the program:

| Key | Default | What it is |
|---|---|---|
| `delay_days` | 84 | How far behind today the configured plan's newest row is |
| `retention_days` | 730 | How far back from that point the plan keeps data |
| `request_interval` | 1.0 | Minimum seconds between two requests |
| `timeout` | 30 | Seconds one request may take |
| `max_retries` | 3 | Attempts for a throttled or failed request |

The runtime defaults are defined in `finance/config.py`; this table exposes
them to the operator as configuration defaults. They are not assertions about
current provider terms. Consult the official J-Quants service information when
aligning them with the subscription in use. Everything downstream — the dates
a fetch asks for, whether stored data counts as current, whether a summary
treats a stock as stale — follows from the configured values.

`pipeline.start_date` is empty by default, which means the whole window the plan
keeps. A date older than that is raised to it, and the run says so in the log.

To configure mail, or to move a directory:

```bash
sudo cp config.yml.sample /var/stock/config.yml
sudo chmod 640 /var/stock/config.yml
sudo chown root:adm /var/stock/config.yml
sudo -e /var/stock/config.yml
```

and point the job at it by exporting `FINANCE_CONFIG=/var/stock/config.yml` in
the cron entry, or by passing `--config` in `run.sh`.

Mail is off until `mail.enabled` is true and both addresses are set. Keep
`mail.hostname_suffix` set: it is what stops a copy of the tree on a workstation
from mailing the operator.

---

## The private stock list

`my_stocks.txt` is the operator's holdings and is deliberately not in the
repository. Create it in the data directory, in the same format as
`stocks.txt`:

```bash
sudo -u root tee /var/stock/data/my_stocks.txt >/dev/null <<'EOF'
7203,トヨタ,トヨタ自動車(株)
9432,ＮＴＴ,日本電信電話(株)
EOF
sudo chown root:www-data /var/stock/data/my_stocks.txt
sudo chmod 660 /var/stock/data/my_stocks.txt
```

Without it the portfolio step fails and the rest of the job continues.

---

## Verify

Run one stock by hand before trusting the schedule. It writes into the real data
directory, so use a code that is already in the list:

```bash
sudo -i
. /var/stock/env && export JQUANTS_API_KEY
FINANCE_DATA_DIR=/var/stock/data FINANCE_MODEL_DIR=/var/stock/clf \
    /var/stock/.venv/bin/finance-charts -c 7203 -n トヨタ -y 240 -u
```

Then check the five things that matter:

```bash
ls -l /var/stock/data/stock_7203.csv /var/stock/data/ti_7203.csv \
      /var/stock/data/chart_7203.png
head -1 /var/stock/data/ti_7203.csv
tail -1 /var/stock/data/ti_7203.csv | awk -F, '{print $(NF-1), $NF}'
cat /var/stock/data/data_source.txt
```

The header must begin `Date,Open,High,Low,Close,Volume,Adj Close`, and the last
two fields of the last row must be the classification and the prediction rather
than empty.

`data_source.txt` must name the source and carry a `last_trading_day`. It may
be earlier than today by the configured publication delay, and that is correct
rather than a fault; it is the figure the dashboard shows so that nobody reads
these pages as live market data. If it is empty, the run analysed nothing.

If the command fails with a message about `JQUANTS_API_KEY`, the environment
file is empty or was not sourced. If it fails with an authentication error, the
key is wrong or the subscription does not currently permit the request.

Then run the whole job once:

```bash
sudo /var/stock/run.sh
echo "exit=$?"
tail -40 /var/log/sysadmin/stock.log
```

A zero exit means every step succeeded. A non-zero exit names the failed steps
on stderr, which is what cron will mail.

---

## The schedule

```text
10 18  * * 1-5 root test -x /var/stock/run.sh && /var/stock/run.sh
```

18:10 on weekdays, after the Tokyo close. `deploy.sh` installs it.

The schedule is kept for operational consistency. The configured publication
window, not the wall-clock hour, determines which dates a fetch may request.
An occasional missed evening is recovered by the next updating run, which asks
for data newer than the last stored row. The operator relies on the schedule;
the data source does not require this particular hour.

It is cron rather than a systemd timer because a plain daily batch has no
ordering, activation or resource requirement that a timer would serve. Changing
it is not forbidden, but nothing about the modernization calls for it.

Confirm cron accepted the file:

```bash
systemctl status cron
grep stock /var/log/syslog | tail
```

---

## Connecting the dashboard

The integration is the directory, not a package. On the dashboard host:

```bash
ln -s /var/stock/data /var/www/finance-dashboard/public/data
```

or point it there directly with `FINANCE_DASHBOARD_DATA_DIR=/var/stock/data`.

The dashboard's user must be able to read `/var/stock/data`, which is what
`DATA_GROUP` arranges. It needs no write access: it generates nothing.

It gets nothing else. Not the virtual environment, not `config.yml`, and above
all not `/var/stock/env`: the dashboard does not fetch market data and must not
hold the credential that does. It also does not import the `finance` package —
the two sides share a directory of files and nothing else.

The data in that directory came from the J-Quants API under terms permitting
personal analysis and prohibiting redistribution. Whatever the dashboard is
published behind, that is the constraint it inherits; see its README.

---

## Updating

```bash
cd /path/to/finance
git pull
./deploy.sh
```

The virtual environment and `run.sh` are replaced; `data/` and `clf/` are not
touched. Re-run one stock by hand as above before the next scheduled run.

---

## Routine operations

**Add a stock.** Append it to `/var/stock/data/stocks.txt`. The next run fetches
its full history from the configured start date, writes its files and trains its
models. Nothing else is needed.

**Remove a stock.** Delete its line. Its existing files stay where they are; the
dashboard stops linking it from the index. Remove
`/var/stock/data/{stock,ti}_CODE.csv`, the three PNGs and
`/var/stock/clf/{clf,reg}_CODE.pickle` if the space is wanted.

**Retrain a stock from scratch.** Delete its two pickles. The next updating run
fits fresh models over the whole history.

**Refetch a stock's history.** Delete its `stock_CODE.csv`. The next updating
run fetches from the configured start date. Note that rows refetched now come
from the current adjustment basis; see section 10 of
[`DATA_CONTRACT.md`](DATA_CONTRACT.md).

**Prune the archive.** `/var/stock/data/history/` grows by one file per weekday
and nothing reads it back. Delete by age when it matters.

---

## What the log holds

`/var/log/sysadmin/stock.log`, appended to by every run. Each step is bracketed
by a `***` line, and a failed step is marked `*** FAILED:`.

```bash
grep FAILED /var/log/sysadmin/stock.log | tail
```

Raise the detail for one run with `FINANCE_LOG_LEVEL=DEBUG`. The job holds the
HTTP client's own loggers at WARNING, so DEBUG stays readable.

---

## When something fails

**`Command not found: .../finance-charts`** — the package is not installed in
the virtual environment. Re-run `./deploy.sh`, or
`/var/stock/.venv/bin/pip install /path/to/finance`.

**`Python 3.11 or later is required`** — `deploy.sh` refused the interpreter.
Set `PYTHON` to a newer one.

**One stock fails, the rest succeed** — expected behaviour. The log names the
code and the reason. A delisted or renamed code needs removing from the list; a
transient fetch failure resolves itself the next evening.

**Every stock fails with `JQUANTS_API_KEY is not set`** — `/var/stock/env` is
empty or unreadable. `run.sh` checks before it starts, so nothing was fetched.

**Every stock fails to authenticate** — the key is wrong, was revoked, or the
subscription lapsed. Re-registering and issuing a new key is the fix.

**Every stock fails with a rate limit** — the job is asking too quickly.
Raise `jquants.request_interval`.

**Every stock fails to fetch** — the provider or the network. Confirm with the
integration checks, which are the only tests that touch it:

```bash
cd /path/to/finance && JQUANTS_API_KEY=... .venv/bin/pytest -m integration
```

**A fetch succeeds but returns nothing new, every evening** — expected. The plan
publishes in arrears; once the stored history reaches the newest published date,
there is nothing to add until the window moves. The log says so by name.

**Charts appear, summaries are empty** — the summaries drop any stock whose
newest indicator row is more than ten days older than the newest date the plan
publishes. After a long outage, run the chart step with `-u` first and then the
summaries, which is what `run.sh` does in that order anyway. If `jquants.
delay_days` is wrong for the subscription, this is the symptom: the reference
date moves and everything looks stale.

**The dashboard says the data is twelve weeks old** — it is, and it is meant to
say so. That is the Free plan's publication delay, not a stalled pipeline.
Compare `last_trading_day` in `/var/stock/data/data_source.txt` with what the
plan currently publishes.

**Captions render as boxes** — the caption font is missing. Install one and set
`charts.font_path`.

**A model fails to load after an upgrade** — expected and handled. The log says
so and a fresh model is trained in its place.

**The dashboard shows nothing** — check from the dashboard's side that it can
read the directory, then that the files are there. The dashboard caches by
modification time, so a regenerated file appears without a restart.

---

## Migrating data written by a previous provider

Run this once, when upgrading a deployment whose stored files were produced
before the data source changed, and never again.

```bash
sudo -i
/var/stock/.venv/bin/finance-migrate --data-dir /var/stock/data --dry-run
/var/stock/.venv/bin/finance-migrate --data-dir /var/stock/data
```

It moves every `stock_CODE.csv` and `ti_CODE.csv` into
`/var/stock/data/legacy.YYYYMMDD/` and deletes nothing. The stock lists, the
summaries and the charts are left where they are; the next run with `-u`
rebuilds the per-stock files from the current source.

Why it is a separate command rather than part of the upgrade: the previous
provider's prices and the current one's are not the same series, and the daily
job merges stored rows with fetched ones. Merged, the older and newer halves of
a file would mean different things — a difference no indicator would report and
no chart would show. Since the meaning cannot be reconciled, the honest move is
to set the old files aside, and deciding to do that with the operator's own
archive is the operator's call rather than a cron job's.

Expect the rebuilt history to be **shorter**. The Free plan keeps about two
years, and files that went back to 2014 will not. That is the plan's constraint
working as intended; every indicator the pipeline computes fits inside the
window, and a test asserts it.

Keep or delete `legacy.YYYYMMDD/` as you see fit. Nothing reads it.
