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

It never writes into `data/` or `clf/`. Deploying cannot disturb generated data,
and updating data never needs a code change.

---

## Before you begin

- Linux with cron, `sudo`, and Python **3.11 or later**.
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

## Configure

Configuration is optional. Without any, the pipeline writes into the data
directory `run.sh` exports and sends no mail.

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
sudo FINANCE_DATA_DIR=/var/stock/data FINANCE_MODEL_DIR=/var/stock/clf \
    /var/stock/.venv/bin/finance-charts -c N225 -n 日経平均株価 -y 240 -u
```

Then check the four things that matter:

```bash
ls -l /var/stock/data/stock_N225.csv /var/stock/data/ti_N225.csv \
      /var/stock/data/chart_N225.png
head -1 /var/stock/data/ti_N225.csv
tail -1 /var/stock/data/ti_N225.csv | awk -F, '{print $(NF-1), $NF}'
```

The header must begin `Date,Open,High,Low,Close,Volume,Adj Close`, and the last
two fields of the last row must be the classification and the prediction rather
than empty.

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

18:10 on weekdays, after the Tokyo close and late enough for the day's prices to
have settled at the source. `deploy.sh` installs it.

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

**Every stock fails to fetch** — the provider or the network. Confirm with the
integration checks, which are the only tests that touch it:

```bash
cd /path/to/finance && .venv/bin/pytest -m integration
```

**Charts appear, summaries are empty** — the summaries drop any stock whose
newest indicator row is more than ten days old. After a long outage, run the
chart step with `-u` first and then the summaries, which is what `run.sh` does
in that order anyway.

**Captions render as boxes** — the caption font is missing. Install one and set
`charts.font_path`.

**A model fails to load after an upgrade** — expected and handled. The log says
so and a fresh model is trained in its place.

**The dashboard shows nothing** — check from the dashboard's side that it can
read the directory, then that the files are there. The dashboard caches by
modification time, so a regenerated file appears without a restart.
