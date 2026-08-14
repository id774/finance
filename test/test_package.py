#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_package.py: Structural rules of the package
#
#  Description:
#  Assert the properties that the modernization was for, so that they
#  cannot quietly come undone. These are not tests of behaviour; they
#  are tests of the shape the code has to keep.
#
#  Each one guards against a specific thing this repository actually
#  suffered from: import paths patched at runtime, environment variables
#  read from the middle of a calculation, a print statement left in a
#  library module, and a private pandas API relied on until it was
#  deleted.
#
#  Two of them guard a decision rather than a shape. The provider this
#  repository fetches from is a licensing decision, and the API key is a
#  secret; a test that no module names the withdrawn provider, and a
#  test that no module outside config.py reads or logs the key, are what
#  keep either from being undone by a convenient import or a debug line.
#
#  Test Cases:
#  - The package imports without touching sys.path.
#  - No module mutates sys.path or calls sys.exit outside an entry point.
#  - Only config.py reads the environment.
#  - No library module prints.
#  - No module uses a removed or private pandas or NumPy API.
#  - No wildcard imports.
#  - The domain layer does not import the I/O or CLI layers.
#  - The package imports without an HTTP client installed.
#  - No module names the withdrawn data source.
#  - No module outside config.py reads the API key, and none logs it.
#  - Console scripts resolve.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - pytest
#
#  Version History:
#  v1.0 2026-08-14
#       Guard the data source decision and the API key.
#       Initial release.
#
########################################################################

from __future__ import annotations

import ast
import importlib
import sys
import tokenize
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parent.parent / "finance"

# Modules that are entry points and may therefore end the process.
ENTRY_POINTS = {"charts.py", "summary.py", "notify.py", "migrate.py"}

# The domain layer: calculation only. It may not reach for a file, the
# network, the environment or the command line.
DOMAIN_MODULES = (
    "finance.indicators",
    "finance.features",
    "finance.models",
    "finance.aggregation",
)

FORBIDDEN_IMPORTS = {
    "finance.storage",
    "finance.datasources",
    "finance.config",
    "finance.cli",
    "finance.analysis",
    "finance.reporting",
    "finance.notification",
}

# APIs that were removed from pandas or NumPy, or were never public.
# Each of these was load bearing in the implementation this replaced.
BANNED_PATTERNS = (
    "pandas.stats",
    "pandas.core.datetools",
    "pandas.tools.plotting",
    "pandas.plotting._core",
    "pandas.tseries.plotting",
    "matplotlib.finance",
    "pd.rolling_",
    "pd.ewma",
    ".ix[",
    "np.float(",
    "np.int(",
    "np.bool(",
    "np.object(",
)


def python_files() -> list[Path]:
    """ Return every module of the package. """
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def parse(path: Path) -> ast.Module:
    """ Parse a module into a syntax tree. """
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def code_only(path: Path) -> str:
    """
    Return the module with its comments and string literals removed.

    Several modules name a removed API in a comment, to record what the
    current call replaced and why. Scanning the raw text for those names
    would flag the explanation along with the thing it warns about.
    """
    kept: list[str] = []
    with tokenize.open(path) as handle:
        for token in tokenize.generate_tokens(handle.readline):
            if token.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            kept.append(token.string)
    return " ".join(kept)


def test_the_package_has_modules():
    assert len(python_files()) >= 12


def test_the_package_imports_cleanly():
    before = list(sys.path)
    importlib.import_module("finance")
    importlib.import_module("finance.analysis")
    importlib.import_module("finance.reporting")
    assert sys.path == before, "importing the package changed sys.path"


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_no_module_mutates_sys_path(path: Path):
    source = code_only(path)
    assert "sys.path.append" not in source
    assert "sys.path.insert" not in source


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_only_entry_points_exit_the_process(path: Path):
    source = code_only(path)
    if path.name in ENTRY_POINTS:
        return
    assert "sys.exit(" not in source, "{0} ends the process".format(path)


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_only_config_reads_the_environment(path: Path):
    source = code_only(path)
    if path.name == "config.py":
        return
    assert "os.environ" not in source, "{0} reads the environment".format(path)
    assert "os.getenv" not in source, "{0} reads the environment".format(path)


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_no_library_module_prints(path: Path):
    if path.parts[-2] == "cli":
        return
    tree = parse(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "print", "{0} prints; use logging".format(path)


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_no_removed_or_private_apis(path: Path):
    source = code_only(path)
    for pattern in BANNED_PATTERNS:
        assert pattern not in source, "{0} uses {1}".format(path, pattern)


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_no_wildcard_imports(path: Path):
    tree = parse(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                assert alias.name != "*", "{0} imports with a wildcard".format(path)


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_every_module_carries_a_header(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#!/usr/bin/env python"
    assert lines[1] == "# -*- coding: utf-8 -*-"
    assert "#  Description:" in lines[:12], "{0} has no Description block".format(path)


@pytest.mark.parametrize("module_name", DOMAIN_MODULES)
def test_the_domain_layer_does_not_reach_upward(module_name: str):
    """ A calculation module imports no I/O, settings or entry point. """
    path = PACKAGE_ROOT / (module_name.split(".")[-1] + ".py")
    tree = parse(path)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    # finance.errors and finance.features are the two the domain may use.
    allowed = {"finance.errors", "finance.features"}
    for name in imported:
        if name in allowed:
            continue
        assert name not in FORBIDDEN_IMPORTS, "{0} imports {1}".format(module_name, name)


def test_the_domain_layer_does_no_file_access():
    for module_name in DOMAIN_MODULES:
        path = PACKAGE_ROOT / (module_name.split(".")[-1] + ".py")
        source = code_only(path)
        assert "open(" not in source, "{0} opens a file".format(module_name)
        assert "to_csv" not in source, "{0} writes a file".format(module_name)
        assert "read_csv" not in source, "{0} reads a file".format(module_name)


def test_the_http_client_is_not_imported_at_module_scope():
    """
    The package must import without an HTTP client installed.

    A workstation reading stored CSVs and drawing a chart makes no
    request, and a test must never be able to reach one by accident.
    """
    for path in python_files():
        tree = parse(path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if not any(name.startswith("requests") for name in names):
                continue
            assert node.col_offset > 0, "{0} imports requests at module scope".format(path)


# Names of the provider this repository no longer fetches from, in every
# spelling a reintroduction would arrive under. A market data source is
# a licensing decision as much as a technical one, and this is what
# keeps the decision from being undone by a convenient import.
WITHDRAWN_SOURCES = ("yfinance", "yahoo", "pandas_datareader", "pandas-datareader", "read_html")


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_no_module_reaches_for_a_withdrawn_source(path: Path):
    source = code_only(path).lower()
    for name in WITHDRAWN_SOURCES:
        assert name not in source, "{0} names {1}".format(path, name)


@pytest.mark.parametrize("path", python_files(), ids=lambda p: p.name)
def test_no_module_reads_the_api_key_outside_config(path: Path):
    """
    The credential is resolved once, in config.py, like every setting.

    A module reading it for itself would also be a module able to log
    it, and there would be no single place left to assert that none of
    them do.
    """
    if path.name == "config.py":
        return
    source = code_only(path)
    assert "JQUANTS_API_KEY" not in source, "{0} reads the API key".format(path)


def test_no_module_logs_the_api_key():
    """ No log or message call is handed the key field. """
    for path in python_files():
        source = code_only(path)
        for call in ("logger.debug", "logger.info", "logger.warning", "logger.error"):
            for fragment in source.split(call)[1:]:
                head = fragment[:200]
                assert "api_key" not in head, "{0} may log the API key".format(path)


def test_console_scripts_resolve():
    from finance.cli.charts import run as charts_run
    from finance.cli.migrate import run as migrate_run
    from finance.cli.notify import run as notify_run
    from finance.cli.summary import run as summary_run

    for entry in (charts_run, summary_run, notify_run, migrate_run):
        assert callable(entry)


def test_the_version_is_exposed():
    import finance

    assert finance.__version__
    assert finance.__version__.count(".") == 2
