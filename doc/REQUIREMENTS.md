# Requirements: a technical analysis batch pipeline

## 1. Purpose of this document

This document states what the system is for, what it accepts, what it produces
and where its responsibility ends. It does not describe how any of it is built;
that belongs to [`BASIC_DESIGN.md`](BASIC_DESIGN.md), and how a change is
carried out belongs to [`POLICY.md`](POLICY.md).

It stands on its own. Nothing in it is completed by a document in another
repository.

## 2. Name

`finance`. The name is the subject, not the technique: the repository is about
market data, and the indicators, models and charts are how it is examined.

## 3. Purpose

One person follows a set of Japanese shares. They want to open a page in the
evening and see, for each of them, a chart with the usual technical overlays,
the current values of the usual oscillators, and a table ranking the set by how
it moved.

Producing that is this repository's job. Displaying it is not.

The system exists to turn daily price data into a fixed set of files, on a fixed
schedule, without anybody present.

**It is software for one person's private analysis of their own investments.**
That is a design premise rather than a description of current usage, and the
following four statements are binding on every change:

- The market data it obtains is not redistributed to anyone.
- No continuing analysis service built on that data is provided to anyone.
- The consumer of its output, `finance-dashboard`, is a private dashboard read
  by the same person, not a public web service.
- The terms and licence of the external market data are followed, and are a
  separate question from the licence of this source code.

Section 4 says what follows from that, section 7.2 says where the data comes
from and under what conditions, and [`POLICY.md`](POLICY.md) section 1.1 states
the rules a change is judged against.

## 4. What it is not

- Not a trading system. It places no orders and connects to no broker.
- Not advice. The classifier and the regression are a decoration on a chart, and
  the requirements deliberately keep them at that size.
- Not a web application. It serves nothing and listens on nothing.
- Not a database. Its state is files in a directory.
- Not a market data service. It fetches what it needs for itself, for one
  person, and republishes none of it. It does not serve data to a third party,
  does not offer the fetched CSVs as a distribution channel, and does not
  become one by being open source.
- Not a scraper. It does not read a web page written for a human and take the
  numbers out of it. Its input is an API offered for programmatic use, on terms
  that permit this use.

## 5. Who uses it

One operator, who is also the maintainer. There are no accounts, no roles and no
multi-user concerns. The audience for the output is one person and the dashboard
they read it in.

## 6. Where it runs

A single Linux host, under cron, at 18:10 on weekdays. It runs unattended. It
must be assumed that nobody is watching when it fails.

## 7. Input

### 7.1 The stock lists

Comma separated files naming the stocks a run covers: the code, a short name,
and optionally a longer name for a chart caption.

- `stocks.txt` — the full set, in the repository. It seeds a new deployment and
  is meant to be replaced by the operator's own watchlist; the version shipped
  here is the TOPIX Core30 constituents. Every entry names a listing on the
  Tokyo exchange.
- `topix_core30.txt` — the TOPIX Core30 constituents, in the repository.
- `my_stocks.txt` — the operator's holdings. **Not** in the repository: it is a
  private file that lives in the data directory on the host. A portfolio is
  personal information and is not published with the source code.

### 7.2 Prices

Daily open, high, low, close, volume and adjusted close, for each code in the
list, from the **J-Quants API Free plan**.

The provider is chosen on three conditions, in this order:

1. **Free to an individual**, so that the system's premise of personal,
   no-cost operation holds without a subscription.
2. **Offered for machine access**, so that reading it is the intended use of the
   interface rather than a tolerated one.
3. **Terms that permit this use.** Personal analysis is permitted;
   redistribution and providing a continuing analysis service to third parties
   are not, and the system does neither.

A provider that fails any of the three is not adopted, and a shortfall in the
data is never made up from one that does. In particular, no page written for a
human is scraped, and no undocumented endpoint is called.

The plan's limits are requirements, not defects:

- **A publication delay.** The newest available row is weeks behind today. The
  system fetches no further forward than the plan publishes, and states the last
  trading day it holds so that the delay is visible to the reader.
- **A bounded history.** The plan keeps a fixed span behind that point. A
  request for anything older is raised to the oldest date kept, and every
  analysis must be computable inside the span.
- **A rate limit.** Requests are paced and a refusal is retried rather than
  worked around.

The interfaces the Free plan does not carry are not obtained elsewhere. Market
index values are the case that matters here; see section 7.4.

### 7.3 Stored history

What previous runs already fetched. A run reads it, asks the provider only for
what is newer, and combines the two.

Rows stored under a *different* provider are not combined with these. Where the
meaning of a series cannot be shown to be the same, mixing it is worse than
starting again, and retiring the older files is an explicit operation the
operator performs rather than something a nightly job decides.

### 7.4 Market indices

None. The system previously charted N225, GSPC, IXIC and DJI, fetched from a
provider it no longer uses. The J-Quants Free plan carries no index values, and
no free, licensed, machine-readable source for them has been adopted.

The requirement is therefore withdrawn rather than met by other means. The
analysis of Japanese shares stands without a reference index: no indicator,
summary, screening or model takes one as an input. "Not obtainable on acceptable
terms, therefore not provided" is an acceptable outcome, and a better one than
an index of uncertain provenance.

## 8. What it produces

For each stock: a price file, a technical indicator file, and three chart
images at different window lengths. For each list: a summary table. Once a day:
a record of where the data came from and how old it is, a dated copy of the main
summary, and two mails.

None of it is published. The files are written into one directory on the
operator's host for the operator's dashboard to read, and this repository
offers no route by which they reach anybody else. They are excluded from version
control for the same reason.

The exact format of every one of them is
[`DATA_CONTRACT.md`](DATA_CONTRACT.md), which is normative.

## 9. The data contract

**This is the central requirement, and the one that constrains everything
else.**

The output is read by a separate application, `finance-dashboard`, which
generates nothing and holds no copy of this code. The two are joined by a
directory of files.

- The names, separators, columns, column order, index and value meanings of the
  generated files are a published interface.
- They may not be changed to suit an implementation here.
- A change to them is a change to an interface: the reason and the effect are
  established first, a compatible route is preferred, and the reading side is
  considered before the writing side.
- The summary files are read positionally, so a column inserted or reordered
  corrupts the display silently rather than failing loudly. That property is why
  the contract has tests rather than only a document.

`finance-dashboard` is never a runtime dependency. Neither repository imports
the other.

## 10. Indicators

The set is fixed and is listed in the data contract: moving averages both simple
and exponential, Bollinger bands, parabolic SAR, a return index, rolling
volatility, RSI, MFI, rates of change, CCI, the ultimate oscillator, both
stochastics, MACD, Williams %R, momentum, true range, ATR and NATR, and two
volume ratios.

- The formulas are what they have always been. Adding an indicator is a feature;
  changing an existing one restates history.
- Values are stored unscaled. The display shifts several of them onto a shared
  axis, and that shifting belongs to the chart, not to the file.

## 11. The models

Two, per stock, both trained on the return index:

- A classifier answering whether the next value rises.
- A ridge regression estimating the next value, reported as a price.

They are refreshed nightly. A model seen for the first time is fitted over the
whole available history; a stored one is refreshed on the most recent window
only. A stored model that cannot be loaded is replaced by a fresh one rather
than ending the run.

Their output reaches the last row of the indicator file and the chart caption,
and nothing else.

## 12. Charts

Three per stock, distinguished by window length and by file name prefix. Each
carries a candlestick price panel with trend overlays and, optionally, an
oscillator panel below it. Two switches control how much is drawn.

The images are for a person to look at. Their content is specified; their pixels
are not, and no requirement here asks for reproducible rendering.

## 13. Scheduling and order

The daily job runs the steps in a fixed order because they depend on each other:
indicators before the summaries that read them, summaries before the mails that
report them. Charts that nothing consumes come last.

Exactly one step fetches prices. The others work from what it stored.

## 14. Failure

The job runs unattended, so how it fails is part of what it is.

- **One stock must not cost the others their run.** A code that cannot be
  fetched is logged and skipped; the remaining stocks are analysed.
- **A failure must be visible.** A run with any failure ends non-zero, so that
  cron reports it. Silence must mean success.
- **A bad configuration fails before work starts**, not halfway through a
  directory of files.
- **A failed run must not destroy good data.** A file is not replaced by an
  empty one, and stored history is not truncated by a run that fetched nothing.
- **Errors are distinguishable.** A source that could not be reached, a stored
  file that is malformed, an indicator that could not be computed and a file
  that could not be written are different problems and are reported as such.

## 15. Networking

- Exactly one component talks to the provider. Nothing else in the system knows
  a provider exists, and nothing else sees an HTTP response, a provider field
  name or a credential.
- Changing provider must not change what the analysis sees. Differences in
  columns, timezone, calendar or adjustment are corrected at the boundary, and a
  difference that cannot be corrected is documented rather than absorbed
  silently.
- The ordinary test suite reaches no network. Tests that do are separated and
  are not a condition of a commit.

## 16. Stored history

Once a price row is stored it is not recalculated. An update adds dates the
store does not have and keeps the stored value wherever the two overlap.

This is what lets the provider change without the operator's archive changing
under them: a figure reported last year still reconciles with the file it came
from.

## 17. Configuration

Operational values — where files go, which list is used, how far back to fetch,
where mail goes — are settings, not constants in code. They are resolved in one
place and passed down; no module reaches for the environment on its own.

Values that are not operational stay in code. Not every constant needs to become
a setting.

## 18. Secrets

One: the J-Quants API key.

- It is supplied through the environment, and through nothing else. It gets no
  command line option, because a command line is readable by every user of the
  host, and it is not accepted from the configuration file, because a file in
  the working tree is one careless commit away from being published.
- It is never committed to this repository, in any form, including as a sample
  value.
- It is resolved once, with every other setting, and no module below the entry
  point reads it.
- It never appears in a log line, an exception message, a command's output, a
  generated file, a chart, the dashboard, or a test's output.
- A run that would fetch without it fails before opening a socket. A run that
  only draws charts from stored files does not require it at all.
- It is not given to `finance-dashboard`. That repository does not fetch.

The mail path continues to use a local relay and needs no credential.

## 19. Independence

The repository is complete on its own.

- Its documents specify its behaviour without reference to another repository.
- Its tests run without another repository present.
- Its output is defined here, not by reading the consumer's source.

The consumer's source was read to establish the contract. That reading is
recorded in [`DATA_CONTRACT.md`](DATA_CONTRACT.md) so that nobody has to repeat
it.

## 20. Simplicity

The system is one person's daily batch job. It should stay the size of that.

Not wanted: a database, a web interface, a queue, a scheduler beyond cron, a
plugin system, a second data provider maintained in parallel, or a configuration
language. Each would be more machinery than the job justifies, and the job has
survived a decade without any of them.
