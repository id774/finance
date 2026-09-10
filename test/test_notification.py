#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# test_notification.py: Report delivery
#
#  Description:
#  Assert what a report mail contains and when it is refused. No test
#  here opens a connection: the transport is a function the test
#  supplies, and the default SMTP transport is never constructed.
#
#  Test Cases:
#  - The subject keeps the cron and host prefix the operator filters on.
#  - The body is the CSV as written, unaltered.
#  - Japanese in a report survives the encoding.
#  - Sending is refused when mail is disabled, and when the host does
#    not match the configured suffix.
#  - A permitted host sends exactly one message.
#  - A transport failure becomes NotificationError.
#  - A missing report is reported before any transport is used.
#
#  Author: id774 (More info: https://id774.net)
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
#       Initial release.
#
########################################################################

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from finance.config import MailSettings
from finance.errors import NotificationError, StorageError
from finance.notification import build_subject, send_report

REPORT = "Code\tName\tRatio\n7203\tトヨタ\t2.5\n"
RUN_DATE = date(2026, 8, 14)


@pytest.fixture()
def mail_settings(settings):
    """ Return settings with mail enabled for a permitted host. """
    return replace(
        settings,
        mail=MailSettings(
            enabled=True,
            host="localhost",
            port=25,
            sender="finance@host.id774.net",
            recipient="finance@id774.net",
            hostname_suffix="id774.net",
        ),
    )


@pytest.fixture()
def report(settings):
    """ Write a report where the notifier will look for it. """
    path = settings.data_file("summary.csv")
    path.write_text(REPORT, encoding="utf-8")
    return path


class Recorder:
    """ A transport that records instead of sending. """

    def __init__(self, error=None):
        self.messages = []
        self.error = error

    def __call__(self, message):
        if self.error is not None:
            raise self.error
        self.messages.append(message)


def test_subject_keeps_the_historical_prefix():
    subject = build_subject("Summary Report of My Portfolio", "host.id774.net", RUN_DATE)
    assert subject == (
        "[cron][host.id774.net] Summary Report of My Portfolio on Fri 14 Aug 2026"
    )


def test_a_permitted_host_sends_one_message(mail_settings, report):
    transport = Recorder()
    sent = send_report(
        mail_settings,
        "summary.csv",
        "Summary Report of Financial Data",
        hostname="host.id774.net",
        transport=transport,
        today=RUN_DATE,
    )

    assert sent is True
    assert len(transport.messages) == 1

    message = transport.messages[0]
    assert message["From"] == "finance@host.id774.net"
    assert message["To"] == "finance@id774.net"
    assert "Summary Report of Financial Data" in message["Subject"]
    assert message.get_content().rstrip("\n") == REPORT.rstrip("\n")


def test_japanese_survives_the_encoding(mail_settings, report):
    transport = Recorder()
    send_report(
        mail_settings, hostname="host.id774.net", transport=transport, today=RUN_DATE
    )
    assert "トヨタ" in transport.messages[0].get_content()


def test_an_unpermitted_host_does_not_send(mail_settings, report):
    transport = Recorder()
    sent = send_report(
        mail_settings, hostname="laptop.local", transport=transport, today=RUN_DATE
    )

    assert sent is False
    assert transport.messages == []


def test_disabled_mail_does_not_send(settings, report):
    transport = Recorder()
    sent = send_report(
        settings, hostname="host.id774.net", transport=transport, today=RUN_DATE
    )

    assert sent is False
    assert transport.messages == []


def test_a_transport_failure_is_reported(mail_settings, report):
    transport = Recorder(error=OSError("connection refused"))
    with pytest.raises(NotificationError, match="could not be sent"):
        send_report(
            mail_settings, hostname="host.id774.net", transport=transport, today=RUN_DATE
        )


def test_a_missing_report_is_reported_before_sending(mail_settings):
    transport = Recorder()
    with pytest.raises(StorageError, match="does not exist"):
        send_report(
            mail_settings,
            "absent.csv",
            hostname="host.id774.net",
            transport=transport,
            today=RUN_DATE,
        )
    assert transport.messages == []
