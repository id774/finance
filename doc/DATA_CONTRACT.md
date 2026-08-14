# Data Contract

This is the normative description of every file this repository writes. It is
the interface between `finance` and `finance-dashboard`, and it is the reason
most of the modernization was constrained rather than free.

The two repositories share no code and no process. They share a directory. That
makes this document the whole of the interface specification, and
`test/test_contract.py` its executable form: every rule stated here is asserted
there, in the terms the consumer reads the files in.

Nothing here may be changed to suit an implementation. A change to this document
is a change to a published interface and needs the consumer considered first.

---

## 1. The boundary

```text
J-Quants API (Free plan, delayed)
     |
     v
finance  (batch, cron, 18:10 on weekdays)
     |
     v
<data directory>/*.csv  *.txt  *.png
     |
     v
finance-dashboard  (FastAPI, read only)
```

The data directory defaults to `./data` and is `/var/stock/data` in the
deployment. `finance-dashboard` is pointed at the same directory, usually
through a symlink at `public/data`.

Neither side imports the other. `finance-dashboard` never writes; `finance`
never reads anything the dashboard produces, because the dashboard produces
nothing. The provider appears at the top of that diagram and nowhere below it:
the dashboard never calls the J-Quants API and is never given its API key.

The files in that directory are market data obtained for personal analysis.
Neither repository publishes them, and neither offers a route by which a third
party obtains them.

---

## 2. How the consumer parses each file

Two parsing styles are in use on the other side, and the difference decides what
is safe to change.

| Style | Files | Safe to reorder? | Safe to rename? |
|---|---|---|---|
| **Positional**: skip the header line, split on tab, `zip` against a fixed name list | `portfolio.csv`, `topix_core30.csv`, `screening_rsi14.csv` | **No** | Yes, headers are ignored |
| **By header name**: `csv.DictReader`, each header lowercased with non-alphanumerics collapsed to `_` | `ti_CODE.csv` | Yes | **No** |
| **Line split**: split on comma, take the first two fields | `stocks.txt` | No | n/a |
| **Key and value**: split each line on tab, take the known keys | `data_source.txt` | Yes | **No** |
| **Not parsed**: served as a download or an image | `stock_CODE.csv`, `*.png` | n/a | n/a |

A positional file is the dangerous one. An extra column inserted in the middle
of `portfolio.csv` does not raise on the other side; it shifts every later value
one name to the left and renders a company name where a ratio belongs.

---

## 3. `stocks.txt`

The list of stocks the pipeline covers, and the index page's company listing.

- Encoding UTF-8, one record per line, comma separated, **no header**.
- Field 1 is the code, field 2 the short name. Both are required.
- Further fields are optional. `finance` uses field 3 as the long name in a
  chart caption; the dashboard ignores everything past field 2.
- A code is the four character form of a Tokyo listing code. The data source
  appends the trailing zero required by the J-Quants API; market index codes are
  not accepted.

```text
7203,トヨタ,トヨタ自動車(株),自動車,CORE30
```

`topix_core30.txt` and the operator's private `my_stocks.txt` use the same
format. They are inputs to `finance` only; the dashboard does not read them.

---

## 4. `stock_CODE.csv`

The price history of one stock, and the file the pipeline updates
incrementally.

- Comma separated, index label `Date`, dates as `YYYY-MM-DD`.
- Columns, in this order: `Open`, `High`, `Low`, `Close`, `Volume`, `Adj Close`.
- One row per trading day. Rows are never removed and, once written, never
  recalculated: an update fetches only dates after the last stored row and
  combines them with the stored rows winning any overlap.
- Every column is on **one basis**: the share-split adjusted series. `Adj Close`
  and `Close` are both the adjusted close, and `Open`, `High`, `Low` and
  `Volume` are the adjusted open, high, low and volume. Indicators are computed
  from `Adj Close` and candlesticks are drawn from `Open`, `High`, `Low` and
  `Close`, as they always were; what changed is that the two now agree. See
  section 10.

The dashboard links this file for download from each stock page. It does not
parse it.

```text
Date,Open,High,Low,Close,Volume,Adj Close
2026-04-22,2891.0,2913.5,2874.0,2902.0,9812400,2902.0
```

---

## 5. `ti_CODE.csv`

The technical indicators of one stock. This is the file the dashboard's chart
and time series pages are built from.

- Comma separated, index label `Date`, dates as `YYYY-MM-DD`.
- One row per trading day of the analysed window. Holidays are absent, not
  blank.
- Written **only** by a run given `--update`. A run that finds no new prices
  leaves the previous file in place.

### 5.1 Columns, in order

The order is the order the indicators are computed in, and it is fixed by
`finance.indicators.build_indicator_frame()`.

| Position | Columns |
|---|---|
| 1-6 | `Open`, `High`, `Low`, `Close`, `Volume`, `Adj Close` |
| 7-11 | `sma5`, `sma25`, `sma50`, `sma75`, `sma200` |
| 12-16 | `ewma5`, `ewma25`, `ewma50`, `ewma75`, `ewma200` |
| 17-19 | `upperband`, `middleband`, `lowerband` |
| 20 | `sar` |
| 21-22 | `ret_index`, `vol` |
| 23-24 | `rsi9`, `rsi14` |
| 25 | `mfi14` |
| 26-30 | `roc10`, `roc25`, `roc50`, `roc75`, `roc150` |
| 31 | `cci14` |
| 32 | `ultosc` |
| 33-34 | `slowk`, `slowd` |
| 35-36 | `fastk`, `fastd` |
| 37-39 | `macd`, `macdsignal`, `macdhist` |
| 40 | `willr14` |
| 41-42 | `mom10`, `mom25` |
| 43-44 | `tr`, `vl` |
| 45-46 | `atr`, `natr` |
| 47-48 | `v_rate`, `v_rate_p` |
| 49-50 | `classified`, `predicted` |

### 5.2 What the values mean

- Moving averages, oscillators and ranges are TA-Lib outputs on `Adj Close`,
  except those that need the full bar. Since the whole row is on the adjusted
  basis, "the full bar" and "the adjusted close" no longer disagree; see
  section 11. `ewma*` are pandas exponentially weighted
  means with `adjust=True` and `min_periods=0`.
- `upperband`, `middleband`, `lowerband` are Bollinger bands smoothed with
  `MA_Type.T3`, not the TA-Lib default.
- `ret_index` is the cumulative return index, based at exactly 1 on the first
  row of the window. Both models are trained on it.
- `vol` is the rolling 250-day standard deviation of `ret_index`, annualized by
  the square root of 250, with a 50-row minimum.
- `vl` is the true range as a percentage of the typical price.
- `v_rate` is volume relative to the window maximum, scaled to 0-50 for the
  oscillator panel. `v_rate_p` is the same ratio projected onto the price scale.
- **Values are unscaled.** The chart shifts several of them for display — the
  rates of change by 50, Williams %R by 100, `vl` by a factor of five — and none
  of that reaches this file.
- A leading run of empty cells is normal and is how long each indicator takes to
  warm up. The dashboard renders those as blank.

### 5.3 `classified` and `predicted`

**Only the last row carries them. Every other row is empty.**

- `classified` is `1` when the classifier expects the next value of `ret_index`
  to rise and `0` otherwise. The dashboard shows it as a direction.
- `predicted` is the ridge regression's estimate of the next value, multiplied
  back into currency by the first adjusted close of the window, truncated to an
  integer.

Both are a statement about the next trading day, not a series, which is why they
are not carried down the column.

### 5.4 Header spelling

The dashboard lowercases each header and collapses non-alphanumerics to
underscores, so `Adj Close` becomes `adj_close`. Renaming any column breaks the
lookup silently, leaving an empty cell rather than an error.

---

## 6. The summary files

All four share one shape and differ only in which columns they carry.

- Tab separated, **not** comma separated.
- One header line beginning `Code`. The dashboard skips it by that literal.
- One row per stock, indexed by code.
- Every price and model value is **truncated** with `int()`, not rounded.
- `Name` is always the last field.

### 6.1 The ten column layout

`portfolio.csv`, `summary.csv`, `summary_10.csv`:

```text
Code	Open	High	Low	Close	Change	Ratio	Trend	Pred	Name
```

Read by the dashboard as `code, open, high, low, close, diff, ratio, trend,
predict, name`.

### 6.2 The nine column layout

`topix_core30.csv` (`rsi9`) and `screening_rsi14.csv` (`rsi14`):

```text
Code	Open	High	Low	Close	Change	Ratio	rsi14	Name
```

Read by the dashboard as `code, open, high, low, close, diff, ratio, rsi, name`.
The screening column replaces `Trend` and `Pred`; its header carries the
indicator name, which the dashboard ignores in favour of its position.

### 6.3 What the values mean

- `Open`, `High`, `Low`, `Close` are the last row of the stock's `ti_CODE.csv`.
  `Close` is the adjusted close.
- `Change` is the adjusted close now minus the adjusted close `--range` rows
  back. `--range 1` compares the last two rows.
- `Ratio` is `round((1 + Change) / Close * 100, 2)`.

  This is not the textbook percentage change: the numerator is one plus the
  change, not the change. It is preserved deliberately. Every figure in
  `data/history/` and every mailed report since the repository was written uses
  it, and the dashboard labels it as the ratio. Correcting it would restate the
  archive.
- `Trend` and `Pred` are the `classified` and `predicted` of that stock's last
  indicator row.
- A stock whose newest indicator row is more than **10 days** old is left out
  entirely. The window absorbs a run of market holidays while still dropping a
  stock that has stopped updating.
- Market index codes are never included in a summary.

### 6.4 Which file each invocation produces

| File | Invocation | Layout | Read by the dashboard |
|---|---|---|---|
| `summary.csv` | `-o summary.csv -y -r 1 -k Ratio` | ten column | no, mailed |
| `summary_10.csv` | `-o summary_10.csv -r 10 -k Ratio` | ten column | no |
| `portfolio.csv` | `-s my_stocks.txt -o portfolio.csv -r 1 -k Ratio` | ten column | yes |
| `topix_core30.csv` | `-s topix_core30.txt -o topix_core30.csv -r 1 -c rsi9 -k Ratio` | nine column | yes |
| `screening_rsi14.csv` | `-o screening_rsi14.csv -r 1 -c rsi14 -a -k rsi14` | nine column | yes |

---

## 7. `data/history/`

Dated copies of a summary, written when `--history` is given. Only `summary.csv`
gets one in the daily job.

- Name: `<output name>.<YYYYMMDD>.csv`, for example `summary.csv.20260814.csv`.
  The double extension is original and is what the operator's archive is sorted
  and globbed on.
- Byte-for-byte the summary as written that day, in the same tab separated
  format.
- Nothing reads it back. It exists so that a figure reported months ago can be
  checked against what was reported at the time.

---

## 8. Chart images

Three PNGs per stock, one per window length. The dashboard builds an `<img>`
source from the view and the code and never looks inside the file.

| File | Window | Written by |
|---|---|---|
| `chart_CODE.png` | 61 to 300 rows | the 240-row run |
| `long_CODE.png` | over 300 rows | the 600-row run |
| `short_CODE.png` | 60 rows or fewer | the 60-row run |

The prefix is chosen by the window length, not by an option:
`finance.charts.chart_prefix()`.

Each image is 1280 by 1024 pixels. The upper panel carries candlesticks, red for
a day that closed at or above its open and blue for one that closed below, with
exponential moving averages, Bollinger bands and the parabolic SAR over them.
The lower panel carries the oscillators on a 0-100 scale. The caption under the
chart reports the close, the change, the ratio, the volume, the window high and
low, the classifier's direction and the regression's price.

The caption needs a Japanese TrueType font. Without one the chart is still
drawn and the caption renders as boxes.

---

## 9. `data_source.txt`

Where the generated data came from and how old it is. It exists because the
source publishes in arrears: the newest figure in this directory is weeks
behind the run that produced it, and a dashboard showing it without saying so
would read as live market information.

- Tab separated, one key and value per line, no header, UTF-8.
- Three keys, in this order: `source`, `generated`, `last_trading_day`.
- Written by `finance-charts --update`, which is the run that fetches. The
  chart-only runs later in the job do not rewrite it; restamping it from them
  would age the notice by the length of the job rather than by the data.

| Key | Meaning |
|---|---|
| `source` | The provider and plan, as one line of text |
| `generated` | The date of the run, `YYYY-MM-DD` |
| `last_trading_day` | The newest trading day the run analysed, `YYYY-MM-DD` |

```text
source	J-Quants API (Free plan, delayed)
generated	2026-07-21
last_trading_day	2026-04-24
```

`last_trading_day` is **empty when it is not known** — when a run analysed
nothing — and is never filled in with today's date. The dashboard shows an empty
value as unknown. Substituting `generated` for it would present the age of the
run as the age of the data, which is the exact misreading this file exists to
prevent.

---

## 10. `ref_index.csv` — withdrawn

Earlier versions of `finance-dashboard` linked this file from the index page.
**`finance` never wrote it.**

It was produced by `bin/reference.rb`, a Ruby script using the `jpstock` gem,
deleted in commit `e6fef22`. It carried fundamentals — PER, PBR, EPS, BPS,
dividend yield, market capitalisation — scraped from a Yahoo Japan quote page
that no longer exists.

Nothing replaces it. Restoring it would mean choosing a new source for
fundamentals; the J-Quants Free plan does not carry them in this form, and no
other source that is free, licensed for this use and offered for machine access
has been adopted. Scraping one is not an option here. The link has been removed
from the dashboard so that nothing dangles, and neither repository refers to the
file.

The four market indices the pipeline used to chart — N225, GSPC, IXIC, DJI —
are withdrawn on the same grounds and by the same reasoning. See
[`REQUIREMENTS.md`](REQUIREMENTS.md) section 7.4.

---

## 11. What changed in the meaning of the numbers

The provider changed, and the two sources do not mean the same thing by the same
column name. This is what was decided and why.

**Then.** Japanese share prices came from Yahoo Japan's history pages, whose
`Open`, `High`, `Low` and `Close` were as traded and whose adjusted close was
adjusted for **splits only**. The last version fetched from Yahoo Finance, whose
adjusted close is adjusted for **splits and dividends**. Under both, the file
mixed two bases: candles were drawn from unadjusted prices while every indicator
was computed from an adjusted close, so a share split put a step in the chart
that the indicators under it did not have.

**Now.** J-Quants publishes both series per row: `O`, `H`, `L`, `C`, `Vo` as
traded, and `AdjO`, `AdjH`, `AdjL`, `AdjC`, `AdjVo` restated onto the current
share basis using `AdjFactor`. The adjustment is for share splits and reverse
splits, and **not** for dividends.

**The decision.** All six canonical columns are taken from the adjusted series.

- It is the basis the stored history was originally written on, when the source
  was Yahoo Japan: splits adjusted, dividends not.
- It puts the candlesticks and the indicators on one basis for the first time,
  removing the step at a split rather than adding one.
- The alternative — unadjusted OHLC beside an adjusted close — would reproduce
  the old inconsistency deliberately, and there is no reading of the data under
  which that is the more correct answer.

No formula changed. `test/test_contract.py` regenerates all 42 computed columns
of the committed fixture and compares them column by column, which is the
evidence that the calculations are the same ones.

**Other differences of meaning, and how each is handled:**

| Aspect | How the adapter handles it |
|---|---|
| Adjustment factor | Applied by the provider; `AdjFactor` itself is not carried into the frame |
| Turnover value (`Va`) | Not carried. No indicator, summary or chart uses it |
| Volume | The adjusted volume, so that it is on the same basis as the prices |
| Trading day | The provider returns trading days only; the frame is reindexed to business days, and a non-trading weekday is an empty row the pipeline drops |
| Missing values | A field present and null becomes a gap, never a zero |
| Split, reverse split | Absorbed by the adjusted series |
| Delisting | The provider stops returning rows; the summary drops the stock as stale |
| Stock code | Four characters in the stock lists and in every generated file name; five, with a trailing zero, only inside the adapter |
| Dates | `YYYY-MM-DD`, parsed to a tz-naive midnight index. No timezone is involved: these are trading dates, not timestamps |
| Delay | The plan publishes in arrears. Recorded in `data_source.txt`, never hidden |

**Legacy rows.** Data stored under the previous provider is not merged with
this. Where the meaning of a series cannot be shown to be the same, mixing it is
worse than starting again, so `finance-migrate` moves the older per-stock files
into a dated archive and the next run rebuilds them. That is an explicit
operation the operator runs once; it is not in `run.sh`, and the data source
knows nothing about it.

---

## 12. Changing this contract

1. Read `finance_dashboard/data.py` and `finance_dashboard/indicators.py` first.
   They, not this document, are what will actually run.
2. Decide whether the change is positional or by-name, using section 2.
3. Update `test/test_contract.py` in the same change. A contract change with no
   test change has not been made.
4. For anything a consumer would notice, land the reading side first.
