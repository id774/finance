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

One person follows a set of Japanese shares and four market indices. They want
to open a page in the evening and see, for each of them, a chart with the usual
technical overlays, the current values of the usual oscillators, and a table
ranking the set by how it moved today.

Producing that is this repository's job. Displaying it is not.

The system exists to turn daily price data into a fixed set of files, on a fixed
schedule, without anybody present.

## 4. What it is not

- Not a trading system. It places no orders and connects to no broker.
- Not advice. The classifier and the regression are a decoration on a chart, and
  the requirements deliberately keep them at that size.
- Not a web application. It serves nothing and listens on nothing.
- Not a database. Its state is files in a directory.
- Not a market data service. It fetches what it needs for itself.

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

- `stocks.txt` — the full set, in the repository.
- `topix_core30.txt` — the TOPIX Core30 constituents, in the repository.
- `my_stocks.txt` — the operator's holdings. **Not** in the repository: it is a
  private file that lives in the data directory on the host.

### 7.2 Prices

Daily open, high, low, close, volume and adjusted close, from an external
provider, for each code in the list.

### 7.3 Stored history

What previous runs already fetched. A run reads it, asks the provider only for
what is newer, and combines the two.

## 8. What it produces

For each stock: a raw price file, a technical indicator file, and three chart
images at different window lengths. For each list: a summary table. Once a day:
a dated copy of the main summary, and two mails.

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
  a provider exists.
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

There are none. The provider needs no credential, and the mail path uses a local
relay. If that ever changes, a credential gets no command line option: a command
line is readable by every user of the host.

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
