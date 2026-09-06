# Implementation Policies

This document decides how this repository is implemented: the coding rules, the
responsibilities of the layers and the direction of dependency between them, the
handling of settings, the approach to tests and documentation, and the criteria
a change is judged by.

It stands on its own. No rule here is completed by a document kept in another
repository, and a subject it does not cover is a gap in this document, to be
filled here rather than looked up elsewhere.

The Invariants below decide over the rest of it.

---

## 1. General Policy

### 1.1 Purpose and Scope

- **This system is for one person's private analysis of their own investments.**
  It is not a market data service, not a publication, and not a way of giving
  anyone else access to what it fetches. That premise decides several rules
  below that would otherwise look arbitrary.
- **The data it fetches is licensed; this source code is not the data.** Market
  data is obtained from the J-Quants API under terms permitting personal
  analysis and prohibiting redistribution and the provision of a continuing
  analysis service to third parties. This repository is published under the GPL
  or the LGPL, which covers the source code and grants nothing whatever over the
  data put through it. Never write anything implying the second follows from the
  first.
- **Binding consequences.** No market data is committed to this repository, in
  any form, including as a test fixture. No API key is committed, and none
  appears in a sample configuration. No feature exists whose purpose is to hand
  the fetched data to a third party. The consumer, `finance-dashboard`, is a
  private dashboard and is documented as one.
- **The input must be free, legitimate and machine-readable.** A source is
  adopted only if an individual may use it at no cost, it is offered for
  programmatic access, and its terms permit this use. No web page written for a
  human is scraped, no undocumented endpoint is called, and a gap in what a free
  plan offers is never filled from a source that fails those conditions. A
  capability that cannot be obtained on acceptable terms is withdrawn instead;
  see `REQUIREMENTS.md` section 7.4.
- This document applies to everything committed here: the package, the batch and
  deployment scripts, the cron entry, the tests and the documents.
- What the system is for belongs to [`REQUIREMENTS.md`](REQUIREMENTS.md); how it
  is composed belongs to [`BASIC_DESIGN.md`](BASIC_DESIGN.md); what it writes
  belongs to [`DATA_CONTRACT.md`](DATA_CONTRACT.md). This document does not
  restate them; it decides how they are carried out.

### 1.2 Invariants

These come before every other rule here. Some of what they forbid is what a
general policy would otherwise ask for.

1. **The generated files are an interface, and this repository is not free to
   change them.** Names, separators, columns, column order, index labels and
   value meanings are fixed by `DATA_CONTRACT.md`. An internal improvement that
   would change one of them is not made.
2. **A financial formula is not changed by a refactor.** Migrating an API and
   changing arithmetic are different work and are never done in one change. If a
   library moves a result, the move is measured, written down, and decided on
   deliberately.
3. **The stored price history is not recalculated.** An update adds dates that
   are missing and keeps the stored value wherever the two overlap.
4. **One stock's failure does not end the run.** A batch over a list logs the
   failure, continues, and reports a non-zero status at the end.
5. **A failure is never silent.** No bare `except` that returns an empty value,
   and no run that exits zero after something went wrong.
6. **The ordinary test suite reaches no network.** No API key is needed to run
   it, and none is configured in CI.
7. **No other repository is a runtime dependency.**
8. **The API key is never disclosed.** Not to a log, an exception message, a
   command's output, a generated file, a chart, the dashboard, or a test's
   output. It is read in one place and passed as a field excluded from the
   dataclass repr.
9. **The plan's limits are the specification.** A publication delay, a bounded
   history and a rate limit are what the system is built on, not defects to be
   routed around. Nothing is fetched from elsewhere to make up the difference,
   and no paid plan is assumed.

### 1.3 Design Philosophy

- The system is one person's daily batch job, and should stay the size of that.
- Prefer the smallest change that solves the problem. A pipeline that has run
  for a decade has earned the benefit of the doubt.
- Understand why something exists before replacing it. A constant that looks
  arbitrary usually encodes an operational fact.
- Where a decision looks odd, the comment gives the reason, so that a later
  change does not quietly undo it.

### 1.4 The Layers and the Direction of Dependency

The layers of the basic design are the layers of the code, and dependency points
one way:

```text
finance/cli/*
      |
      v
analysis.py  reporting.py  notification.py
      |
      v
indicators  features  models  aggregation  charts  stocklist
      |
      v
storage.py  datasources/
      |
      v
the filesystem, the price provider
```

- **The domain layer computes and nothing else.** It takes values and returns
  values. It opens no file, makes no request, reads no environment variable,
  knows no path and has no opinion about the command line. That is what lets one
  set of expected numbers be asserted without a filesystem.
- **`storage.py` is told where to write.** It names files, it does not place
  them.
- **The data source layer keeps whatever is peculiar to a provider inside it.**
  An exception, a client object or a column convention belonging to the provider
  does not appear above it; what leaves it is this application's own frame and
  this application's own errors.
- **Settings are read at the entry point and passed down.** A module below never
  reaches for the environment.
- A new responsibility goes to the layer that owns it. Where it appears to
  belong to two, the boundary is wrong and is corrected, rather than the code
  being written across it.

### 1.5 The Data Source

- Exactly one module talks to the provider. Authentication, the endpoint, query
  parameters, pagination, the request interval, retries, timeouts, HTTP status
  handling, the provider's field names and its stock code form all live in it
  and leave it in no direction.
- Every difference between what the provider returns and what the pipeline
  expects is corrected there: columns, order, timezone, calendar, duplicates.
  A difference that reaches the analysis layer is a defect in the adapter.
- A difference that cannot be corrected — an adjustment basis, for instance — is
  documented in `DATA_CONTRACT.md` rather than absorbed silently.
- Prices are requested explicitly rather than by default. A response missing a
  column the pipeline needs is refused, never substituted from a column that
  happens to be present. The adjusted series is never filled in from the
  unadjusted one.
- The adapter knows nothing about what is on disk, and nothing about data a
  previous provider wrote. Retiring that is a separate, explicit command.
- The dates a fetch may ask for are decided above the adapter, by the settings
  that describe the plan. The adapter answers the range it is given.
- Errors are distinguished by what the operator would do about them:
  authentication, rate limit, a dataset outside the plan, an invalid stock
  code, and everything else.
- The HTTP client is imported inside the adapter, so the package imports without
  it and a run that only draws charts needs neither the client nor a key.
- A third-party SDK is judged on whether it earns its place. The official
  J-Quants client was considered and not adopted: it reads configuration from
  several implicit locations, which conflicts with resolving every setting in
  one place, and this pipeline uses one endpoint. A direct REST call over
  `requests` is smaller, and the whole adapter is one readable file.

### 1.6 Configuration

- Every setting lives in `config.py`, in the `Settings` dataclass. Precedence is
  command line, environment, YAML file, default.
- `Settings` is frozen. An override is applied with `dataclasses.replace`.
- Validation happens at load. A malformed value is refused before any work
  starts, because this job runs unattended.
- An empty or whitespace-only environment variable reads as unset, so that a
  bare `NAME=` behaves exactly like the absent line.
- Not every constant becomes a setting. A value the operator would plausibly
  change on a host is a setting; a value that is part of what the program means
  stays in code.

### 1.7 Logging and Output

- A library module never prints. It takes a module logger and logs.
- A command line entry point writes user-facing messages to stderr, prefixed
  `[ERROR]` or `[WARN]`, and its ordinary output to stdout.
- INFO says what a step did, WARNING says what was skipped, ERROR says what
  failed. A nightly log is read as a record of the run, so third-party loggers
  that report their own transport are held at WARNING.
- Log with `%s` placeholders, not with an already-formatted string.

### 1.8 Error Handling and Exit Codes

- Every failure the system expects has a class in `errors.py`.
- A third-party exception is caught at the boundary of the module that owns the
  library and re-raised as one of them, with the original attached by `from`.
- A broad `except Exception` is permitted only at such a boundary, only where
  the library raises unrelated builtin types, and always with a comment saying
  which library and why.
- An unexpected exception is left to propagate. It is a defect, and its
  traceback is wanted.
- Exit codes: `0` the command did its work, `1` it failed or a stock in a list
  run failed, `2` argparse rejected the command line.

### 1.9 Judging a Change

A change is judged by:

- Does it keep the data contract, and does a test say so?
- Does it separate an API migration from a change of behaviour?
- Does it respect the direction of dependency?
- Is a formula change deliberate, measured and documented?
- Does it leave the repository understandable on its own?
- Is it the smallest change that does the job?

---

## 2. Python Policy

### 2.1 Structure

- Python 3.11 or later. Every module states `Python Version: 3.11 or later`
  under `Requirements`.
- The shebang is `#!/usr/bin/env python`. Do not write `python3`.
- The encoding header `# -*- coding: utf-8 -*-` follows the shebang.
- Every module starts with the header block described under
  [Documentation](#27-documentation).
- Comments are in English, in the imperative, and short. A comment says why, not
  what.
- Type hints are used on the public functions of a module, where they aid the
  reader. They are not pursued into shapes that need a paragraph to read.
- Every public function, class and method carries a docstring saying what the
  call returns or does. A one-line docstring stays on one line with a space
  inside each pair of quotes. A longer one opens on the line after the quotes
  and describes the non-obvious parameters under `Args:`, the result under
  `Returns:` and the failures under `Raises:`.
- Prefer `str.format()` over an f-string. This is the repository's convention;
  ruff's `UP030` and `UP032` are disabled for it.

### 2.2 Program Structure

- An executable defines `main() -> int` and terminates with `sys.exit(main())`.
- `sys.exit()` is never called from a library module.
- `sys.path` is never modified at runtime. The package is installed.
- No wildcard imports.
- Imports are grouped standard library, third party, then local. A third-party
  package is imported inside the function that needs it only when it is
  optional, and the error names the package to install.
- Avoid mutable global state. Where a module-level constant is a collection, it
  is a tuple or a frozenset.

### 2.3 Dependencies

- Runtime dependencies are declared in `pyproject.toml` and bounded at both
  ends: a floor that is a version actually supported, and a ceiling at the next
  major, so that a future release cannot break a running job overnight.
- Never pin a decade-old version, and never leave a dependency unbounded.
- Add a dependency only when it earns its place. Prefer the standard library.
  A large framework is not introduced to call one HTTP endpoint; before adopting
  a provider SDK, establish that it is needed, maintained, appropriately
  licensed, current with the API, and more maintainable than a direct call.
- Some dependencies are refused by what this system is rather than by their
  quality: a database driver or object mapper, a web framework, a task queue, a
  Node.js toolchain, an error-reporting agent. Each would be the first half of
  something the requirements rule out.
- A client for a market data provider whose terms this system does not meet is
  refused on those grounds alone, whatever its quality. That includes any
  library that reads Yahoo Finance.
- Always pass `encoding="utf-8"` for a text file operation.

### 2.4 pandas and NumPy

This repository was left behind by exactly the practices this section forbids.

- **No private or removed API.** Nothing under `pandas.core`, `pandas.stats`,
  `pandas.tools`, `pandas.plotting._core` or `pandas.tseries.plotting`, and
  nothing from `matplotlib.finance`.
- **Positional access is explicit.** `.iloc` for position, `.loc` for label.
  Never rely on `Series.__getitem__` falling back to position.
- **No deprecated top-level functions.** `Series.rolling(...)`, not
  `pd.rolling_*`. `Series.ewm(...)`, not `pd.ewma`.
- **State the parameters that matter.** Where a default has moved between
  versions — `adjust` and `min_periods` on `ewm`, for instance — pass it
  explicitly rather than inheriting it.
- **A `FutureWarning` fails the test suite.** It is how the next removal
  announces itself, and this repository has already paid for ignoring one.
- `test/test_package.py` scans the source for the banned patterns.

### 2.5 Testing and Operation

- `pytest` and `ruff check .` must both pass.
- A test never reaches the network, never writes outside a temporary directory,
  and never sends mail. The price source is a protocol and tests inject a stub;
  the mail transport is a parameter. The default suite needs no API key, and CI
  is given none.
- Tests that need a real endpoint live in `test/integration/`, carry the
  `integration` marker, and are excluded from the default run and from CI. They
  discard what they fetch.
- **No market data obtained from the provider is committed as a fixture.** An
  API response is reproduced with invented values in the shape the adapter
  expects. A test that saved a real response would be how the rule against
  redistributing the data got broken.
- The committed fixtures are load bearing and are not regenerated. An expected
  value carried over from an older suite is not adjusted to match new output
  without establishing why the output moved. `test/stock_N225.csv` and
  `test/ti_N225.csv` are the exception that proves the rule: they are Nikkei 225
  index data committed in 2015, when the source was a different provider, and
  every regression expectation in the suite derives from them. They are kept
  because deleting them would delete the evidence that the arithmetic has not
  moved across three library generations, they are not refreshed, and nothing
  from the current provider joins them.
- A test that exists because of a rule states the rule. The structural suite
  asserts that no module names the withdrawn provider and that none outside
  `config.py` reads or logs the API key, because a decision nobody can undo by
  accident is worth more than a decision written down.
- A test asserts behaviour that is specified. Where a behaviour is a quirk kept
  on purpose — the ratio formula, the truncation, the ten day window — the test
  says so in a comment, so that a later reader does not "fix" it.
- Every test module carries a `Test Cases` block in its header. Test cases
  belong in the test code, never in an application module.

### 2.6 Shell Scripts

- POSIX `/bin/sh`. No bashisms.
- `command -v`, never `which`.
- Quote every variable expansion.
- Use `$(...)`, not backticks.
- A script reports failure. Never end one with an unconditional `exit 0`, and
  never let a failing step pass unnoticed.
- Define `usage()`, `main()`, and call `main "$@"` at the end.
- An interpreter path is a default that can be overridden, not a constant
  compiled into the script.

### 2.7 Documentation and Versioning

Every module carries a header block in this order: `Description`, the standard
`Author`, `Source Code`, `License`, `Contact` block, `Usage` and `Options`
(executables only), `Exit Codes` (where more than one status is possible),
`Environment Variables` (`config.py` only), `Requirements`, `Version History`.
Test modules carry `Test Cases` after `Description`.

The `Description` is what makes the file readable on its own. It states why the
module exists, which responsibility of the pipeline it holds, what it consumes
and what it produces, and which modules or external systems it touches. It is
not a list of the functions below it, which the code already carries.

- Documentation is updated in the same change as the behaviour it describes.
- A change to a generated file updates `DATA_CONTRACT.md` and
  `test/test_contract.py` in the same change. A contract change with no test
  change has not been made.
- Documents named `.md` are Markdown and may assume a renderer. Prose is wrapped
  near the width the document already uses; a URL, a table row or a code block
  may run long.
- Comments, docstrings and documents are in English. Japanese appears only where
  it is data: a company name, a chart caption, a stock list.

#### 2.7.1 When to Bump a Module Version

- These rules apply to the `Version History` in each module header. Repository
  release versions and Git tags follow the separate rules below.
- Do not bump the version mechanically every time a file is touched. Decide
  based on the nature of the change:
  - Documentation-only, comment-only and formatting-only changes (help text,
    README/POLICY/VERSIONS wording, whitespace and layout, with no effect on
    behaviour) do not bump the version.
  - Any change that affects code behaviour (bug fixes, new options, and
    refactors that change observable behaviour) bumps the version.
  - Multiple updates on the same date are consolidated into a single version
    entry; do not increment the version multiple times on the same date.
  - Finalizing only the release date of an entry that already exists, such as
    changing `TBD` to the actual date, is not by itself a new change. Classify
    that entry as version-only or as containing real changes based on what it
    actually contains, not on the date edit.
- A `Version History` entry is written as `vX.Y YYYY-MM-DD`, newest first, and
  the date is the date of the change.
- Each entry's description is at most two lines, and a single line at or
  under 80 columns is preferred whenever practical.
- The first entry, at the lowest version the file's own history reaches,
  reads only `Initial release.` and nothing else.

#### 2.7.2 Module Version Numbering

- Versions use a two-level `major.minor` scheme.
- When incrementing `minor` would reach `10`, roll over instead: increment
  `major` by 1 and reset `minor` to `0` (for example `v0.9` -> `v1.0`,
  `v1.9` -> `v2.0`, `v2.9` -> `v3.0`).
- Do not continue `minor` past `9` as in standard semantic versioning
  (do not use `v1.10`, `v1.11`, ...).
- Raising `major` for a reason other than the rollover is a decision the
  maintainer makes, not one this document derives from the change.
- Removing or renaming an option, changing what an existing argument means,
  changing a default so that an unchanged invocation does something else, and
  changing how a path or a configuration value is resolved are all incompatible
  changes. Say so in the `Version History` entry, so that the number the change
  is released under can be chosen knowing that.

#### 2.7.3 Repository Versioning

- Repository release versions are independent of individual module versions.
- Record repository release versions in [`VERSIONS`](VERSIONS) and use the same
  versions for Git tags.
- Repository release versions may use a three-level `major.minor.patch` scheme.
- Work that is not released yet takes no version of its own: it belongs to the
  entry already standing at the top of `doc/VERSIONS`.
- An unreleased entry carries `(Release Date: TBD)`, and its version number
  stays provisional until it ships. An entry opened as
  `v1.0.1 (Release Date: TBD)` may be released under a different number once
  what accumulated in it is known; which number it takes is decided then.
- Replacing `TBD` with the actual release date is the release itself, not a
  change to record in the entry.
- A repository that has not yet made its first release is in its initial
  construction stage, and that stage takes no entry here. Typically this is the
  state while `v1.0` is the first release and the repository still stands below
  it, or `v1.0` itself is unreleased. The changes made while building up to that
  release are not accumulated in `doc/VERSIONS` one by one: the file is the
  record of released versions, not of the construction that precedes the first
  of them, and its first entry is written when that release is made.
- A documentation-only change takes no `doc/VERSIONS` entry, unless its scale
  makes it worth one line saying so.
- The version declared in `pyproject.toml`, the one exposed as
  `finance.__version__`, and the one the `finance-*` commands print for
  `--version` are the repository release version. They are one number and are
  changed together.
- File level `Version History` and the repository level `doc/VERSIONS` are kept
  apart. A release entry does not raise a module version, and a module version
  does not become a release entry unless the change is observable from outside.

#### 2.7.4 doc/VERSIONS Structure

- `doc/VERSIONS` must read as a version-level summary of overall changes, not a
  raw commit log. It tells a reader what a release changed. It is not the place
  to transcribe how that work happened to be committed.
- Each entry opens with a heading of the form `vX.Y.Z (YYYY-MM-DD)`, or
  `vX.Y.Z (Release Date: TBD)` while it is unreleased, underlined with `-`
  characters, followed by one `-` bullet per change.
- Use UTF-8.

##### 2.7.4.1 One Change per Line

- One coherent change is one bullet. A bullet is at most two physical lines,
  and a single line at or under 80 columns is preferred whenever practical.
  This is an explicit limit, not a prompt to reread: a bullet that runs past
  two lines, or a single line that runs past 80 columns without necessity,
  must be shortened. The entry is a list meant to be scanned, and a bullet
  that grows past this limit costs it that: the eye no longer finds the
  changes by counting lines, and a diff no longer shows a small, bounded
  edit.
- A bullet that has to carry file names, command names, function names,
  option names or configuration names may pass 80 columns on its one or two
  lines when those names cannot be shortened without losing meaning. The
  two-line ceiling still applies.
- Bullets written before this rule are left as they stand. The rule applies
  to what is written from now on.
- `doc/VERSIONS` carries these guidelines again at its foot, and an entry
  written into it follows the limit recorded there.
- Where the record reaches back to a genuine first version, that entry
  reads only `Initial release.` and nothing else. `v1.0` here is a
  modernization release, not that first version, and keeps its own record.
- The case standing outside the rule is a version history that has already
  settled on a width and a layout of its own, predating this limit. There a
  new bullet is wrapped to that width and balanced against the lines already
  standing, so that the version history stays of a piece. Wrapping to hold an
  established form does not overturn the two-line, 80-column limit above;
  where a file has settled on no such form, that limit applies in full.

##### 2.7.4.2 Shortening a Long Entry

- When a bullet runs long, the first move is to abstract it, not to reach for
  the second line the two-line limit allows. Drop the implementation detail,
  the examples, the reason and the secondary effects, and state what the
  change is. Wrap onto the second line only when the abstracted bullet still
  exceeds 80 columns.
- Keep what a reader of the release cannot reconstruct without it: what was
  changed, what is now observably different from outside, what it does to
  compatibility, what it does to safety, and the identifiers someone would
  search for.
- A bullet that is long because it names what it must name stays long. Do not
  cut a file name, an option name or a configuration key to reach a column
  count.

##### 2.7.4.3 Grouping and Order

- When multiple changes to the same file within one version are really one
  coherent change, merge them into a single bullet instead of listing them
  separately. Changes that serve one purpose are described together even when
  they touch several files.
- Changes to one file that carry independent meaning are not forced together.
  Coherence decides, not the file name.
- When changes are independent, still place entries that touch the same file or
  the same feature near each other, so that each version's entry reads as a
  coherent, reviewable whole rather than an unordered sequence of unrelated
  lines.
- An independent change that belongs with nothing already listed is appended to
  the end of the current version's entry.
- Order within a version serves the reader, not the commit history. Do not
  preserve commit order at the cost of the entry reading as a whole.

### 2.8 License

This repository is dual licensed: GPL version 3 or LGPL version 3, at the
recipient's option. The texts are [`COPYING`](COPYING) and
[`COPYING.LESSER`](COPYING.LESSER), and [`LICENSE.md`](LICENSE.md) states the
choice. This settles what earlier revisions of this document and of
[`MODERNIZATION_PLAN.md`](MODERNIZATION_PLAN.md) recorded as an open item for the
copyright holder; the decision came from the copyright holder.

- Every source module carries the line
  `License: The GPL version 3, or LGPL version 3 (Dual License).` in its header
  block, between `Source Code` and `Contact`.
- `pyproject.toml` carries the matching
  `license = { text = "GPL-3.0-or-later OR LGPL-3.0-or-later" }`.
- The README, `LICENSE.md`, `pyproject.toml`, and the module headers must state
  the same licence. A licence change updates each of those locations in the same
  commit.
- Do not vendor third-party code into this repository. Dependencies are declared
  in `pyproject.toml` and installed from PyPI, which keeps their licenses theirs
  and this file short.
