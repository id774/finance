#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# bin/charts.py: Compatibility wrapper for finance-charts
#
#  Description:
#  Forward to the finance-charts command. This path is what run.sh and
#  the operator's crontab have invoked for a decade, and it keeps
#  working so that deploying this version does not have to be
#  simultaneous with editing the batch scripts on the host.
#
#  It holds no logic. Every option is parsed by the command it forwards
#  to, so the two cannot drift apart. New work goes to the console
#  script; this file exists only so that an un-updated caller does not
#  break, and it can be deleted once none remain.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      python bin/charts.py -s stocks.txt -d 2014-10-01 -y 240 -u
#
#      Prefer the installed command:
#      finance-charts -s stocks.txt -d 2014-10-01 -y 240 -u
#
#  Exit Codes:
#  - Whatever finance-charts returns.
#
#  Requirements:
#  - Python Version: 3.11 or later
#  - The finance package must be installed.
#
#  Version History:
#  v1.0 2026-08-14
#       Initial release.
#
########################################################################

import sys

from finance.cli.charts import main

if __name__ == "__main__":
    sys.exit(main())
