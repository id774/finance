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
6. **The ordinary test suite reaches no network.**
7. **No other repository is a runtime dependency.**

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

- Exactly one module talks to the provider.
- Every difference between what the provider returns and what the pipeline
  expects is corrected there: columns, order, timezone, calendar, duplicates.
  A difference that reaches the analysis layer is a defect in the adapter.
- A difference that cannot be corrected — an adjustment basis, for instance — is
  documented in `DATA_CONTRACT.md` rather than absorbed silently.
- Prices are requested explicitly rather than by default. A response missing a
  column the pipeline needs is refused, never substituted from a column that
  happens to be present.
- The client library is imported inside the adapter, so the package imports
  without it.

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
- Prefer `str.format()` over an f-string. This is a house convention shared with
  the sibling repositories; ruff's `UP030` and `UP032` are disabled for it.

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
- Some dependencies are refused by what this system is rather than by their
  quality: a database driver or object mapper, a web framework, a task queue, a
  Node.js toolchain, an error-reporting agent. Each would be the first half of
  something the requirements rule out.
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
  the mail transport is a parameter.
- Tests that need a real endpoint live in `test/integration/`, carry the
  `integration` marker, and are excluded from the default run and from CI.
- The committed fixtures are load bearing and are not regenerated. An expected
  value carried over from an older suite is not adjusted to match new output
  without establishing why the output moved.
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

### 2.7 Documentation

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
- Module versions use a two-level `major.minor` scheme. Do not bump for a
  comment, formatting or documentation-only change; do bump for anything that
  changes behaviour.
- Documents named `.md` are Markdown and may assume a renderer. Prose is wrapped
  near the width the document already uses; a URL, a table row or a code block
  may run long.
- Comments, docstrings and documents are in English. Japanese appears only where
  it is data: a company name, a chart caption, a stock list.

### 2.8 License

This repository is dual licensed: GPL version 3 or LGPL version 3, at the
recipient's option. The texts are [`COPYING`](COPYING) and
[`COPYING.LESSER`](COPYING.LESSER), and [`LICENSE.md`](LICENSE.md) states the
choice. This settles what earlier revisions of this document and of
[`MODERNIZATION_PLAN.md`](MODERNIZATION_PLAN.md) recorded as an open item for the
copyright holder; the decision came from the copyright holder, not from an
inference drawn across the sibling repositories.

- Every source module carries the line
  `License: The GPL version 3, or LGPL version 3 (Dual License).` in its header
  block, between `Source Code` and `Contact`.
- `pyproject.toml` carries the matching
  `license = { text = "GPL-3.0-or-later OR LGPL-3.0-or-later" }`.
- The README, `LICENSE.md` and the module headers state one thing. A change to
  the license is a change to all four places in the same commit.
- Do not vendor third-party code into this repository. Dependencies are declared
  in `pyproject.toml` and installed from PyPI, which keeps their licenses theirs
  and this file short.
