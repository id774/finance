#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance/notification.py: Report delivery
#
#  Description:
#  Mail a generated summary to the operator. This replaces bin/email.rb,
#  which did the same thing through the Ruby mail gem and was the only
#  reason a Ruby runtime had to be installed alongside the Python one.
#
#  Two things about the original are kept because they were deliberate.
#  The message body is the CSV itself, unformatted, because the operator
#  reads it as a table in a terminal mail client. And the send is
#  refused unless the host name matches a configured suffix, so that a
#  copy of the tree on a laptop or in a test cannot mail anyone.
#
#  Sending is separated from every calculation: nothing in this module
#  computes anything, and nothing that computes anything sends mail. A
#  test asserts the message that would be sent by supplying its own
#  transport, and never opens a connection.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - Standard library only
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

from __future__ import annotations

import logging
import smtplib
import socket
from collections.abc import Callable
from datetime import date
from email.message import EmailMessage

from finance import storage
from finance.config import Settings
from finance.errors import NotificationError

DEFAULT_REPORT = "summary.csv"
DEFAULT_SUBJECT = "Summary Report of Financial Data"

Transport = Callable[[EmailMessage], None]

logger = logging.getLogger(__name__)


def build_subject(report_name: str, hostname: str, today: date | None = None) -> str:
    """
    Build the subject line.

    The bracketed cron and host prefix is kept from the original so that
    the operator's existing mail filters keep matching.
    """
    stamp = (today or date.today()).strftime("%a %d %b %Y")
    return "[cron][{0}] {1} on {2}".format(hostname, report_name, stamp)


def build_message(
    settings: Settings, filename: str, report_name: str, hostname: str, today: date | None = None
) -> EmailMessage:
    """
    Build the message carrying one report.

    Raises:
        StorageError: The report does not exist or cannot be read.
    """
    body = storage.read_text(settings.data_file(filename))
    message = EmailMessage()
    message["From"] = settings.mail.sender
    message["To"] = settings.mail.recipient
    message["Subject"] = build_subject(report_name, hostname, today)
    message.set_content(body, subtype="plain", charset="utf-8")
    return message


def _smtp_transport(settings: Settings) -> Transport:
    """ Return a transport that delivers over SMTP. """

    def send(message: EmailMessage) -> None:
        with smtplib.SMTP(settings.mail.host, settings.mail.port, timeout=30) as client:
            client.send_message(message)

    return send


def send_report(
    settings: Settings,
    filename: str = DEFAULT_REPORT,
    report_name: str = DEFAULT_SUBJECT,
    hostname: str | None = None,
    transport: Transport | None = None,
    today: date | None = None,
) -> bool:
    """
    Mail one report, if this host is permitted to send it.

    Args:
        settings: Mail configuration and the data directory.
        filename: The generated file to send, relative to the data
            directory.
        report_name: Human readable name placed in the subject.
        hostname: The host the guard is checked against. Defaults to the
            real host name.
        transport: How the message is delivered. Injected by tests; the
            default opens an SMTP connection.
        today: The date in the subject. Injected for tests.

    Returns:
        True when a message was handed to the transport, False when the
        configuration or the host guard declined the send. Declining is
        a normal outcome and not an error.

    Raises:
        NotificationError: Delivery was attempted and failed.
        StorageError: The report could not be read.
    """
    host = hostname if hostname is not None else socket.gethostname()
    if not settings.mail.permits(host):
        logger.info("Not sending %s: mail is disabled or %s is not permitted", filename, host)
        return False

    message = build_message(settings, filename, report_name, host, today)
    deliver = transport or _smtp_transport(settings)
    try:
        deliver(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise NotificationError("Report {0} could not be sent: {1}".format(filename, exc)) from exc
    logger.info("Sent %s to %s", filename, settings.mail.recipient)
    return True
