#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# bin/summary.py: Compatibility wrapper for finance-summary
#
#  Description:
#  Forward to the finance-summary command, for the same reason as
#  bin/charts.py: run.sh and the operator's crontab name this path, and
#  a deployment should not have to change both at the same moment.
#
#  It holds no logic. Every option is parsed by the command it forwards
#  to.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      python bin/summary.py -o summary.csv -y -r 1 -k Ratio
#
#      Prefer the installed command:
#      finance-summary -o summary.csv -y -r 1 -k Ratio
#
#  Exit Codes:
#  - Whatever finance-summary returns.
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

from finance.cli.summary import main

if __name__ == "__main__":
    sys.exit(main())
