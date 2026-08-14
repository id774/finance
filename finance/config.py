#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/config.py: Settings loader of finance
#
#  Description:
#  Resolve every operational value the pipeline needs: where data is
#  read and written, where models are kept, which stock list is used,
#  how charts are drawn and how a report is delivered.
#
#  This is the only module in the package that reads the environment.
#  Everything below the entry points receives a Settings instance, so
#  that a calculation never depends on how the process was started and
#  a test never has to set a variable to exercise one.
#
#  Precedence is command line, then environment, then configuration
#  file, then default. A value that cannot be used is refused here,
#  before any work begins, because this pipeline runs unattended and a
#  setting rejected at 18:10 is cheaper than a wrong file written at
#  18:11.
#
#  The J-Quants API key is the one setting that is read from the
#  environment only. It is deliberately not accepted from the YAML file:
#  a credential in a file next to the code is a credential that is one
#  careless `git add` away from being published, and there is no reason
#  to offer that route when the environment already works. It is held in
#  a field excluded from the dataclass repr, so that logging a Settings
#  cannot disclose it.
#
#  The plan window -- how far back the subscribed J-Quants plan keeps
#  data and how far behind today its newest row is -- is a setting
#  rather than a constant scattered through the code. It is a published
#  property of the plan that can change, and the pipeline needs exactly
#  one place to change it in.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Environment Variables:
#  - JQUANTS_API_KEY: The J-Quants API key, issued from the J-Quants
#      dashboard. Required for any run that fetches. Read from the
#      environment only, never from the configuration file. The name
#      matches the one the official J-Quants client reads, so a host
#      that already exports it needs nothing added.
#  - FINANCE_CONFIG: Path of the YAML configuration file. Optional.
#      Defaults to ./config.yml when that file exists.
#  - FINANCE_DATA_DIR: Directory holding generated files. Defaults to
#      ./data.
#  - FINANCE_HISTORY_DIR: Directory holding dated summary copies.
#      Defaults to <data_dir>/history.
#  - FINANCE_MODEL_DIR: Directory holding pickled models. Defaults to
#      ./clf.
#  - FINANCE_STOCK_LIST: Default stock list file name, resolved against
#      the data directory. Defaults to stocks.txt.
#  - FINANCE_START_DATE: Earliest date fetched for a stock, as
#      YYYY-MM-DD. Empty by default, which means the earliest date the
#      plan window offers. A date before that is raised to it.
#  - FINANCE_JQUANTS_BASE_URL: Base URL of the API. Defaults to the
#      published v2 endpoint.
#  - FINANCE_JQUANTS_TIMEOUT: Seconds one HTTP request may take.
#  - FINANCE_JQUANTS_MAX_RETRIES: Retries of a throttled or failed
#      request.
#  - FINANCE_JQUANTS_REQUEST_INTERVAL: Minimum seconds between two
#      requests.
#  - FINANCE_JQUANTS_DELAY_DAYS: How many days behind today the newest
#      row of the plan is.
#  - FINANCE_JQUANTS_RETENTION_DAYS: How far back from that newest row
#      the plan keeps data.
#  - FINANCE_FONT_PATH: TrueType font used for the Japanese chart
#      caption. Defaults to the Debian Japanese Gothic path.
#  - FINANCE_LOG_LEVEL: Logging level name. Defaults to INFO.
#  - FINANCE_MAIL_ENABLED: Whether a report may be mailed. Defaults to
#      false.
#  - FINANCE_MAIL_HOST / FINANCE_MAIL_PORT: SMTP endpoint. Default
#      localhost and 25.
#  - FINANCE_MAIL_FROM / FINANCE_MAIL_TO: Sender and recipient. Both
#      required when mail is enabled.
#  - FINANCE_MAIL_HOSTNAME_SUFFIX: Only send when the host name ends
#      with this suffix. Empty disables the check.
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - PyYAML
#
#  Version History:
#  v1.0 2026-08-14
#       Add the J-Quants settings and the plan window, and make the
#       start date default to what the plan offers.
#       Initial release.
#
########################################################################

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from finance.errors import ConfigurationError

ENV_PREFIX = "FINANCE_"

# Read without the prefix above, because this is the name the official
# J-Quants client uses and a host that already exports it should not
# have to export it twice.
API_KEY_ENV = "JQUANTS_API_KEY"

DEFAULT_STOCK_LIST = "stocks.txt"
DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"

# The published v2 endpoint. v1, with its refresh token exchange, was
# withdrawn on 1 June 2026 and is not supported here.
DEFAULT_BASE_URL = "https://api.jquants.com/v2"

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_REQUEST_INTERVAL = 1.0

# The Free plan publishes data up to twelve weeks behind today, and
# keeps two years of it behind that point. Both are defaults rather than
# constants: a plan change moves them, and a paid subscription sets
# delay_days to 0. Nothing else in the package spells either number.
DEFAULT_DELAY_DAYS = 84
DEFAULT_RETENTION_DAYS = 730

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MailSettings:
    """ Where a generated report is delivered, and whether it may be. """

    enabled: bool = False
    host: str = "localhost"
    port: int = 25
    sender: str = ""
    recipient: str = ""
    hostname_suffix: str = ""

    def permits(self, hostname: str) -> bool:
        """
        Report whether a report may be sent from this host.

        The suffix check preserves the guard of the Ruby script this
        replaced, which refused to send from anywhere but the operator's
        own domain so that a copy of the tree on a laptop could not mail
        anyone.
        """
        if not self.enabled:
            return False
        if not self.hostname_suffix:
            return True
        return hostname.endswith(self.hostname_suffix)


@dataclass(frozen=True)
class JQuantsSettings:
    """
    How the J-Quants API is reached, and what its plan publishes.

    api_key is excluded from the repr so that logging or reporting a
    Settings cannot disclose it. Nothing in this package prints the
    field, and has_api_key() is what the rest of the code asks instead.
    """

    api_key: str = field(default="", repr=False)
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    request_interval: float = DEFAULT_REQUEST_INTERVAL
    delay_days: int = DEFAULT_DELAY_DAYS
    retention_days: int = DEFAULT_RETENTION_DAYS

    def has_api_key(self) -> bool:
        """ Report whether a key is configured, without revealing it. """
        return bool(self.api_key)

    def latest_available(self, today: date) -> date:
        """
        Return the newest date the plan publishes as of the given day.

        On the Free plan this is twelve weeks back. Asking for anything
        newer is answered with nothing, so the pipeline stops at this
        date rather than requesting a window it cannot be given.
        """
        return today - timedelta(days=self.delay_days)

    def earliest_available(self, today: date) -> date:
        """ Return the oldest date the plan still keeps as of that day. """
        return self.latest_available(today) - timedelta(days=self.retention_days)


@dataclass(frozen=True)
class Settings:
    """ Every operational value the pipeline needs, resolved once. """

    data_dir: Path
    history_dir: Path
    model_dir: Path
    stock_list: str = DEFAULT_STOCK_LIST
    start_date: str = ""
    font_path: str = DEFAULT_FONT_PATH
    log_level: str = "INFO"
    mail: MailSettings = field(default_factory=MailSettings)
    jquants: JQuantsSettings = field(default_factory=JQuantsSettings)

    def data_file(self, name: str) -> Path:
        """ Return the path of a generated file inside the data directory. """
        return self.data_dir / name

    def history_file(self, name: str) -> Path:
        """ Return the path of a dated copy inside the history directory. """
        return self.history_dir / name

    def model_file(self, name: str) -> Path:
        """ Return the path of a pickled model inside the model directory. """
        return self.model_dir / name

    def start_date_as_date(self) -> date | None:
        """
        Return the configured start date, or None when none was given.

        Raises:
            ConfigurationError: A start date was given but is not a
                YYYY-MM-DD date.
        """
        if not self.start_date:
            return None
        return _parse_date(self.start_date, "start_date")

    def fetch_window(self, today: date) -> tuple[date, date]:
        """
        Return the date range a fetch on the given day may ask for.

        The end is the newest date the plan publishes. The start is the
        configured start date, raised to the oldest date the plan still
        keeps: a request for 2014 against a plan holding two years is
        not an error, it is simply answered from where the data begins,
        and clamping says so in the log instead of implying otherwise.
        """
        end = self.jquants.latest_available(today)
        earliest = self.jquants.earliest_available(today)
        configured = self.start_date_as_date()
        if configured is None:
            return earliest, end
        if configured < earliest:
            logger.info(
                "Start date %s is older than the plan window; using %s",
                configured,
                earliest,
            )
            return earliest, end
        return configured, end


def _env(name: str) -> str | None:
    """ Read an application environment variable, treating blank as unset. """
    value = os.environ.get(ENV_PREFIX + name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _load_file(path: Path) -> dict[str, Any]:
    """ Load a YAML configuration file, returning an empty mapping when absent. """
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - PyYAML is a declared dependency
        raise ConfigurationError("PyYAML is required to read {0}".format(path)) from exc
    try:
        with open(path, encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except (OSError, ValueError) as exc:
        raise ConfigurationError("Configuration file could not be read: {0}".format(path)) from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigurationError("Configuration file is not a mapping: {0}".format(path))
    return loaded


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    """ Return a mapping section of the configuration. """
    section = config.get(name)
    return section if isinstance(section, dict) else {}


def _first(*values: Any) -> Any:
    """ Return the first value that is neither None nor an empty string. """
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _as_bool(value: Any) -> bool:
    """ Interpret a configuration value as a boolean. """
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, name: str) -> int:
    """ Interpret a configuration value as an integer, or refuse it. """
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("{0} must be an integer, got {1!r}".format(name, value)) from exc


def _as_float(value: Any, name: str) -> float:
    """ Interpret a configuration value as a number, or refuse it. """
    try:
        return float(str(value))
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("{0} must be a number, got {1!r}".format(name, value)) from exc


def _as_positive_int(value: Any, name: str) -> int:
    """ Interpret a configuration value as an integer above zero. """
    number = _as_int(value, name)
    if number <= 0:
        raise ConfigurationError("{0} must be greater than zero, got {1}".format(name, number))
    return number


def _as_positive_float(value: Any, name: str) -> float:
    """ Interpret a configuration value as a number above zero. """
    number = _as_float(value, name)
    if number <= 0:
        raise ConfigurationError("{0} must be greater than zero, got {1}".format(name, number))
    return number


def _as_non_negative(value: Any, name: str) -> float:
    """ Interpret a configuration value as a number of zero or more. """
    number = _as_float(value, name)
    if number < 0:
        raise ConfigurationError("{0} must not be negative, got {1}".format(name, number))
    return number


def _as_non_negative_int(value: Any, name: str) -> int:
    """ Interpret a configuration value as an integer of zero or more. """
    number = _as_int(value, name)
    if number < 0:
        raise ConfigurationError("{0} must not be negative, got {1}".format(name, number))
    return number


def _parse_date(value: str, name: str) -> date:
    """ Parse a YYYY-MM-DD setting, or refuse it. """
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ConfigurationError(
            "{0} must be formatted as YYYY-MM-DD, got {1!r}".format(name, value)
        ) from exc


def _resolve(value: Any) -> Path:
    """ Expand a path setting to an absolute path. """
    return Path(os.path.expanduser(str(value))).resolve()


def load_settings(config_file: str | os.PathLike[str] | None = None) -> Settings:
    """
    Resolve settings from the environment and the configuration file.

    Args:
        config_file: Explicit path of a YAML file. When omitted,
            FINANCE_CONFIG is used, and failing that ./config.yml when
            it exists.

    Returns:
        A validated Settings instance.

    Raises:
        ConfigurationError: A value is present but cannot be used.
    """
    path = Path(config_file) if config_file else Path(_env("CONFIG") or "config.yml")
    if config_file and not Path(config_file).is_file():
        raise ConfigurationError("Configuration file does not exist: {0}".format(config_file))
    config = _load_file(path)

    paths = _section(config, "paths")
    pipeline = _section(config, "pipeline")
    charts = _section(config, "charts")
    logging_section = _section(config, "logging")
    mail_section = _section(config, "mail")
    jquants_section = _section(config, "jquants")

    data_dir = _resolve(_first(_env("DATA_DIR"), paths.get("data_dir"), "data"))
    history_dir = _resolve(
        _first(_env("HISTORY_DIR"), paths.get("history_dir"), data_dir / "history")
    )
    model_dir = _resolve(_first(_env("MODEL_DIR"), paths.get("model_dir"), "clf"))

    start_date = str(_first(_env("START_DATE"), pipeline.get("start_date"), "") or "")
    if start_date:
        _parse_date(start_date, "start_date")

    settings = Settings(
        data_dir=data_dir,
        history_dir=history_dir,
        model_dir=model_dir,
        stock_list=str(
            _first(_env("STOCK_LIST"), pipeline.get("stock_list"), DEFAULT_STOCK_LIST)
        ),
        start_date=start_date,
        font_path=str(_first(_env("FONT_PATH"), charts.get("font_path"), DEFAULT_FONT_PATH)),
        log_level=str(_first(_env("LOG_LEVEL"), logging_section.get("level"), "INFO")),
        mail=_load_mail(mail_section),
        jquants=_load_jquants(jquants_section),
    )
    logger.debug("Resolved settings from %s", path if path.is_file() else "defaults")
    return settings


def _load_jquants(section: dict[str, Any]) -> JQuantsSettings:
    """
    Resolve the J-Quants settings.

    The key comes from the environment alone. A key found under the
    jquants section of the configuration file is refused rather than
    used, because accepting it would make writing a credential into a
    file in the working tree the documented way to configure this.
    """
    if "api_key" in section:
        raise ConfigurationError(
            "The J-Quants API key must not be written into the configuration file. "
            "Export {0} instead.".format(API_KEY_ENV)
        )

    return JQuantsSettings(
        api_key=(os.environ.get(API_KEY_ENV) or "").strip(),
        base_url=str(
            _first(_env("JQUANTS_BASE_URL"), section.get("base_url"), DEFAULT_BASE_URL)
        ).rstrip("/"),
        timeout=_as_positive_float(
            _first(_env("JQUANTS_TIMEOUT"), section.get("timeout"), DEFAULT_TIMEOUT),
            "jquants timeout",
        ),
        max_retries=_as_positive_int(
            _first(_env("JQUANTS_MAX_RETRIES"), section.get("max_retries"), DEFAULT_MAX_RETRIES),
            "jquants max_retries",
        ),
        request_interval=_as_non_negative(
            _first(
                _env("JQUANTS_REQUEST_INTERVAL"),
                section.get("request_interval"),
                DEFAULT_REQUEST_INTERVAL,
            ),
            "jquants request_interval",
        ),
        delay_days=_as_non_negative_int(
            _first(_env("JQUANTS_DELAY_DAYS"), section.get("delay_days"), DEFAULT_DELAY_DAYS),
            "jquants delay_days",
        ),
        retention_days=_as_positive_int(
            _first(
                _env("JQUANTS_RETENTION_DAYS"),
                section.get("retention_days"),
                DEFAULT_RETENTION_DAYS,
            ),
            "jquants retention_days",
        ),
    )


def _load_mail(section: dict[str, Any]) -> MailSettings:
    """ Resolve the notification settings and refuse an unusable combination. """
    enabled = _as_bool(_first(_env("MAIL_ENABLED"), section.get("enabled"), False))
    sender = str(_first(_env("MAIL_FROM"), section.get("sender"), "") or "")
    recipient = str(_first(_env("MAIL_TO"), section.get("recipient"), "") or "")
    if enabled and not (sender and recipient):
        raise ConfigurationError(
            "mail is enabled but the sender or the recipient is not configured"
        )
    return MailSettings(
        enabled=enabled,
        host=str(_first(_env("MAIL_HOST"), section.get("host"), "localhost")),
        port=_as_int(_first(_env("MAIL_PORT"), section.get("port"), 25), "mail port"),
        sender=sender,
        recipient=recipient,
        hostname_suffix=str(
            _first(_env("MAIL_HOSTNAME_SUFFIX"), section.get("hostname_suffix"), "") or ""
        ),
    )
