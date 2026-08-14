# Moving to the J-Quants API

This document records what was surveyed, what was decided and what was
deliberately not done when this pipeline stopped fetching from Yahoo Finance and
started fetching from the J-Quants API.

It is a companion to [`MODERNIZATION_PLAN.md`](MODERNIZATION_PLAN.md), which
covers the restructuring into a Python package and summarizes the resulting
architecture. This document records the later provider decision in detail.

The normative descriptions live elsewhere: what the system is for is
[`REQUIREMENTS.md`](REQUIREMENTS.md), what it writes is
[`DATA_CONTRACT.md`](DATA_CONTRACT.md), and the rules a change is judged against
are [`POLICY.md`](POLICY.md). This is the reasoning behind them.

---

## 1. Why the provider changed

Not because the old one had stopped working. Because of what using it meant.

The pipeline had, over its history, reached Yahoo in three ways: the Yahoo
reader of `pandas-datareader`, withdrawn in 2017; `pandas.read_html()` against
Yahoo Japan's history pages, which is scraping a page written for a human; and
most recently `yfinance`, an unofficial client for an undocumented endpoint.

All three share the same defect, and it is not a technical one. None of them is
an interface the provider offers for programmatic use. A system built on them is
built on something that may be withdrawn without notice, and that was never
extended in the first place.

The requirement adopted here is that the input be a source an individual may use
**at no cost**, that is **offered for machine access**, and whose **terms permit
this use**. See [`REQUIREMENTS.md`](REQUIREMENTS.md) section 7.2.

Replacing one unofficial Yahoo route with another would not have addressed any
of that. The point was never to modernize the scraper.

---

## 2. What was surveyed before implementing

The J-Quants documentation was read at implementation time rather than recalled.
What it established:

| | |
|---|---|
| Current version | **v2**. v1, with its `/token/auth_user` and `/token/auth_refresh` exchange, was withdrawn on 1 June 2026 |
| Base URL | `https://api.jquants.com/v2` |
| Authentication | An API key issued from the J-Quants dashboard, sent as the `x-api-key` request header |
| Daily bars | `GET /equities/bars/daily`, parameters `code`, `from`, `to`, or `date` |
| Response | A JSON object; rows under `data` |
| Pagination | A `pagination_key` member, echoed as a query parameter until the response carries none |
| Rate limit | Per plan; `429` on exceeding it |
| Free plan datasets | Listed issues, daily bars, financial statements, earnings dates |
| Free plan window | Published in arrears — twelve weeks at the time of writing — with about two years of history behind that point |
| Terms | Personal analysis permitted; redistributing the data and providing a continuing analysis service to third parties prohibited |

The v2 field names for daily bars are abbreviated, which is the change that
mattered most to the adapter:

```text
Date Code O H L C UL LL Vo Va
AdjFactor AdjO AdjH AdjL AdjC AdjVo
M... (morning session)   A... (afternoon session)
```

Anything in this table can change. The two values most likely to — the delay and
the retention — are settings rather than constants for that reason, and this
document is not where an operator should look for the current ones.

---

## 3. Which series to take, and why

This is the decision with the most consequence for what the numbers mean, and
[`DATA_CONTRACT.md`](DATA_CONTRACT.md) section 11 is its normative record.

**What the pipeline used to do.** Candlesticks were drawn from `Open`, `High`,
`Low` and `Close`; every indicator was computed from `Adj Close`. Under Yahoo
Japan the first four were as traded and `Adj Close` was adjusted for splits
only. Under Yahoo Finance `Adj Close` was adjusted for splits *and* dividends.
Either way the file mixed two bases, and a share split put a step in the chart
that the indicators under it did not have.

**What J-Quants offers.** Both series per row: `O`/`H`/`L`/`C`/`Vo` as traded,
and `AdjO`/`AdjH`/`AdjL`/`AdjC`/`AdjVo` restated onto the current share basis
with `AdjFactor`. The adjustment covers splits and reverse splits, not
dividends.

**Decision: take the adjusted series for all six canonical columns.**

- It is the basis the stored history was originally written on, back when the
  source was Yahoo Japan — splits adjusted, dividends not.
- It puts the candles and the indicators on one basis for the first time. That
  removes an inconsistency rather than introducing one.
- The alternative would reproduce the old mixture on purpose, and there is no
  reading under which that is the more correct answer.

**What was not done.** No formula changed. `test/test_contract.py` regenerates
all 42 computed columns of the committed fixture and compares them column by
column, which is the evidence that the calculations are the same ones they were.

---

## 4. Living inside the Free plan

The plan's limits were adopted as the specification. Each one has a concrete
consequence, and each consequence has a test in `test/test_plan_window.py`.

| Limit | Consequence |
|---|---|
| Publishes in arrears | `Settings.fetch_window` ends the range at the newest published date. Nothing asks beyond it |
| | Stored history reaching that date is reported current instead of being re-requested nightly |
| | Summary staleness is measured against that date, not today. Against today, a source weeks in arrears would drop every stock as stale and write an empty table every evening |
| | `data_source.txt` records the last trading day, so a reader is never shown delayed figures as live ones |
| Bounded history | A configured start date older than the plan is raised to what the plan keeps, and the run says so. `STARTDATE=2014-10-01` is gone as a default |
| | Every indicator must fit: the longest lookback is a 200-day average against roughly 488 trading days, asserted by a test |
| | `LONG_DAYS` in `run.sh` is 480 rather than 600, which is inside the window and still above the 300 rows that select the `long_` file name |
| Rate limit | A minimum interval between requests, a retry with backoff on `429` that honours `Retry-After`, and a distinct `RateLimitError` |
| No index data | The reference indices are withdrawn. See section 6 |

What was **not** done about any of them: no other source was consulted to make
up a shortfall, no paid plan is assumed, and nothing is fabricated to fill a
gap.

---

## 5. Where the provider's peculiarities live

Everything specific to J-Quants is in `finance/datasources/jquants.py` and
leaves it in no direction:

- the `x-api-key` header, the base URL, the endpoint and its parameters;
- pagination, including a guard against a repeated key and a page ceiling;
- the request interval, the retry policy, the timeout;
- HTTP status handling, and the mapping from status to an error type an operator
  can act on;
- the abbreviated v2 field names;
- the five character stock code form.

Above it, the analysis layer receives the same six-column frame it always
received and cannot tell which provider filled it. Below it, the adapter knows
nothing about what is on disk, which provider wrote it, or what plan it is on —
the dates it may ask for are decided by the settings and handed to it.

`test/test_package.py` asserts the seal from the other side: no module names the
withdrawn provider, and no module outside `config.py` reads or logs the API key.

**On using the official SDK.** The official `jquants-api-client` was considered.
It is maintained and appropriately licensed, but it resolves configuration from
several implicit locations — a TOML file in the home directory, one in the
current directory, an environment variable — which conflicts directly with this
repository's rule that every setting is resolved in one place. It also returns
DataFrames shaped by its own conventions, which would have to be renormalized
anyway. This pipeline calls one endpoint. A direct REST call over `requests` is
smaller, and the whole adapter is one readable file.

---

## 6. What was withdrawn rather than replaced

**The market indices.** Four market indices were charted from Yahoo. The Free
plan carries no index values, and no free, licensed, machine-readable
alternative was found. Rather than obtain them from somewhere that fails the
conditions in section 1, the capability is withdrawn.

Nothing in the analysis of Japanese equities depended on them: no indicator,
summary, screening or model takes an index as an input. `INDEX_CODES` and the
`is_index` special case are gone with them, and the shipped `stocks.txt` — which
had held nothing *but* the four indices — now holds listed equities.

A boundary remains for a future provider: the source protocol is one method, and
adding a second implementation is one file. What was not added is a stub for a
provider that does not exist. An entry in the source table is a promise that the
name works.

**`ref_index.csv`.** Never produced here, linked by the dashboard, and carrying
fundamentals scraped from a Yahoo Japan quote page that no longer exists. The
link is removed from the dashboard in the same change; nothing dangles.

"Not obtainable on acceptable terms, therefore not provided" is a legitimate
outcome, and a better one than data of uncertain provenance.

---

## 7. The credential

The pipeline gained its first secret, and the rules around it are in
[`REQUIREMENTS.md`](REQUIREMENTS.md) section 18. The reasoning, briefly:

- **Environment only.** `JQUANTS_API_KEY`, matching the name the official client
  reads. The configuration file is *refused* rather than merely undocumented,
  because a credential in a file inside the working tree is one careless
  `git add` from being published. No command line option exists, because a
  command line is readable by every user of the host.
- **Excluded from the repr.** `Settings` is a dataclass that gets logged; the
  key field carries `repr=False` so that it cannot leak that way.
- **Fails before the socket.** The source refuses to be built without a key, so
  a misconfigured run stops once rather than failing per stock.
- **Not required to draw a chart.** `LazySource` defers construction to the
  first fetch, so the long and short chart passes of `run.sh` — which read
  stored files — need no key at all. Without that, a credential would be
  required for work that touches no network.
- **Never given to the dashboard.** That repository does not fetch, and a test
  there asserts it cannot.

---

## 8. Data written under the previous provider

The daily job merges stored rows with fetched ones, keeping the stored value
wherever the two overlap. That is what protects the operator's archive from
being rewritten — and it is exactly what must not happen across a change of
provider, because the two series do not mean the same thing.

**Decision: do not merge, and do not let the data source layer know the problem
exists.**

`finance-migrate` moves the stored per-stock files into a dated archive so that
the next run rebuilds them. It deletes nothing, it is not in `run.sh`, nothing
calls it on a schedule, and `finance/datasources/` contains no reference to it —
a test asserts that last point.

The alternatives were considered and rejected. Merging silently would produce a
file whose halves disagree in a way no indicator would report and no chart would
show. Detecting the provenance heuristically would be guessing about the
operator's data. Having the adapter reconcile it would put a filesystem concern
inside the network layer.

Retiring an archive is the operator's decision. The command makes it easy and
reversible; it does not make it automatic.

---

## 9. What was deliberately not changed

- **No financial formula.** The indicators, features, models, aggregation and
  chart rendering are untouched. The regression suite that pinned them still
  passes on the same committed fixture.
- **No generated format**, beyond adding `data_source.txt`. Names, separators,
  columns, column order, index labels and value meanings are as they were, and
  the contract tests still pass unchanged.
- **No old test deleted for being old.** The 2015 fixtures and the expectations
  derived from them are kept: they are the evidence that the arithmetic has not
  moved across three library generations.
- **No database, no web UI, no Node.js toolchain, no framework.** One HTTP
  endpoint does not justify any of them.
- **No new feature.** Everything here follows from the change of provider or
  from a limit of the plan.
