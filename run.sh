#!/bin/sh

########################################################################
# run.sh: Daily data pipeline
#
#  Description:
#  Run the whole nightly job in the order the steps depend on each
#  other: charts and indicators first, then the summaries that read the
#  indicator files, then the mail that reads the summaries, and last the
#  long and short charts, which nothing else consumes.
#
#  That order is a specification, not a habit. Steps 2 to 6 read the
#  ti_CODE.csv files step 1 writes, and steps 7 and 8 read the summaries
#  steps 2 and 4 write.
#
#  Only step 1 passes --update. It is the run that fetches prices,
#  rewrites stock_CODE.csv and ti_CODE.csv, retrains the models and
#  records where the data came from. The long and short runs draw their
#  charts from what step 1 already stored, so the job makes one pass
#  over the network per stock per day rather than three, and needs no
#  API key of their own.
#
#  A step that fails is reported and the job continues to the next one,
#  because a broken summary is no reason to skip the charts. The exit
#  status is non-zero if any step failed, so cron mails the operator
#  instead of the failure passing unnoticed.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - POSIX shell
#  - The finance package installed in VENV_DIR
#
#  Usage:
#      ./run.sh
#      ./run.sh -h | --help
#
#  Environment Variables:
#  - JQUANTS_API_KEY: The J-Quants API key. Required by step 1, which is
#      the only step that fetches. It is not set here: put it in an
#      environment file the deployment owns, readable only by the user
#      the job runs as, and never in this script or in the repository.
#  - WORK_DIR: Deployment root. Defaults to /var/stock.
#  - ENV_FILE: A file of KEY=value lines sourced before the job, holding
#      JQUANTS_API_KEY. Defaults to $WORK_DIR/env, and is skipped when
#      absent so that a run with the key already exported still works.
#  - VENV_DIR: Virtual environment holding the commands. Defaults to
#      $WORK_DIR/.venv.
#  - FINANCE_DATA_DIR: Where generated files go. Defaults to
#      $WORK_DIR/data.
#  - JOBLOG: Log file. Defaults to /var/log/sysadmin/stock.log.
#  - STOCK_LIST / PORTFOLIO_LIST / CORE30_LIST: Stock list file names,
#      resolved against the data directory.
#  - START_DATE: Earliest date fetched. Empty, the default, means the
#      whole window the subscribed plan keeps.
#  - DAYS / LONG_DAYS / SHORT_DAYS: Chart windows. The values decide
#      which of chart_, long_ and short_ each run writes.
#
#  Exit Codes:
#  - 0: Every step succeeded.
#  - 1: At least one step failed.
#
#  Version History:
#  v1.0 2026-08-14
#       Read the API key from an environment file and check that step 1
#       has one before the job starts.
#       Rewrite for POSIX sh, report failures, and drop the Ruby mailer.
#
########################################################################

set -u

WORK_DIR=${WORK_DIR:-/var/stock}
VENV_DIR=${VENV_DIR:-$WORK_DIR/.venv}
JOBLOG=${JOBLOG:-/var/log/sysadmin/stock.log}
ENV_FILE=${ENV_FILE:-$WORK_DIR/env}

FINANCE_DATA_DIR=${FINANCE_DATA_DIR:-$WORK_DIR/data}
FINANCE_MODEL_DIR=${FINANCE_MODEL_DIR:-$WORK_DIR/clf}
export FINANCE_DATA_DIR
export FINANCE_MODEL_DIR

STOCK_LIST=${STOCK_LIST:-stocks.txt}
PORTFOLIO_LIST=${PORTFOLIO_LIST:-my_stocks.txt}
CORE30_LIST=${CORE30_LIST:-topix_core30.txt}

# Empty means the whole window the subscribed plan keeps, which is what
# a run wants unless the operator is deliberately shortening it.
START_DATE=${START_DATE:-}

# The chart windows. LONG_DAYS is above the 300 rows that select the
# long_ file name; a larger value would draw the same chart under the
# same name.
DAYS=${DAYS:-240}
LONG_DAYS=${LONG_DAYS:-480}
SHORT_DAYS=${SHORT_DAYS:-60}

CHARTS="$VENV_DIR/bin/finance-charts"
SUMMARY="$VENV_DIR/bin/finance-summary"
NOTIFY="$VENV_DIR/bin/finance-notify"

failures=0

# Display this script's header as usage information
usage() {
    awk '
        BEGIN { in_header = 0 }
        /^#+$/ && length($0) >= 10 { if (!in_header) { in_header = 1; next } else exit }
        in_header && /^# ?/ { print substr($0, 3) }
    ' "$0"
    exit 0
}

# Load the environment file holding the API key, when there is one
load_environment() {
    [ -f "$ENV_FILE" ] || return 0
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    export JQUANTS_API_KEY
}

# Write a line to the job log
log() {
    echo "$@" >>"$JOBLOG" 2>&1
}

# Check that the commands this job drives are installed
check_commands() {
    for cmd in "$CHARTS" "$SUMMARY" "$NOTIFY"; do
        if [ ! -x "$cmd" ]; then
            echo "[ERROR] Command not found: $cmd" >&2
            echo "[ERROR] Install the package with: $VENV_DIR/bin/pip install ." >&2
            exit 1
        fi
    done
    if ! command -v date >/dev/null 2>&1; then
        echo "[ERROR] Command not found: date" >&2
        exit 127
    fi
}

# Check that the fetching step has the credential it needs
check_credential() {
    if [ -z "${JQUANTS_API_KEY:-}" ]; then
        echo "[ERROR] JQUANTS_API_KEY is not set." >&2
        echo "[ERROR] Put it in $ENV_FILE, or export it before running." >&2
        exit 1
    fi
}

# Check that the data directory exists and can be written
check_environment() {
    if [ ! -d "$FINANCE_DATA_DIR" ]; then
        echo "[ERROR] Data directory does not exist: $FINANCE_DATA_DIR" >&2
        exit 1
    fi
    if [ ! -w "$FINANCE_DATA_DIR" ]; then
        echo "[ERROR] Data directory is not writable: $FINANCE_DATA_DIR" >&2
        exit 1
    fi
}

# Run one step, recording a failure without ending the job
step() {
    description=$1
    shift
    log "*** $description"
    if "$@" >>"$JOBLOG" 2>&1; then
        return 0
    fi
    log "*** FAILED: $description"
    echo "[ERROR] Step failed: $description" >&2
    failures=$((failures + 1))
    return 1
}

# Generate the standard charts, the indicator files and the models.
# This is the only step that fetches, and the only one that needs the
# API key. -d is passed only when a start date was configured, so that
# an unset one means the whole window the plan offers.
update_charts() {
    if [ -n "$START_DATE" ]; then
        step "Charts and indicators" \
            "$CHARTS" -a 2 -p 2 -s "$STOCK_LIST" -d "$START_DATE" -y "$DAYS" -u
    else
        step "Charts and indicators" \
            "$CHARTS" -a 2 -p 2 -s "$STOCK_LIST" -y "$DAYS" -u
    fi
}

# Aggregate the indicator files into the summaries the dashboard reads
build_summaries() {
    step "Summary" \
        "$SUMMARY" -o summary.csv -y -r 1 -k Ratio
    step "Summary over ten days" \
        "$SUMMARY" -o summary_10.csv -r 10 -k Ratio
    step "Portfolio" \
        "$SUMMARY" -s "$PORTFOLIO_LIST" -o portfolio.csv -r 1 -k Ratio
    step "TOPIX Core30" \
        "$SUMMARY" -s "$CORE30_LIST" -o topix_core30.csv -r 1 -c rsi9 -k Ratio
    step "RSI14 screening" \
        "$SUMMARY" -o screening_rsi14.csv -r 1 -c rsi14 -a -k rsi14
}

# Mail the two reports the operator reads
send_reports() {
    step "Mail the summary" \
        "$NOTIFY" summary.csv "Summary Report of Financial Data"
    step "Mail the portfolio" \
        "$NOTIFY" portfolio.csv "Summary Report of My Portfolio"
}

# Draw the long and short charts from the stored data. Neither fetches,
# so neither is given a start date or needs the API key.
draw_extra_charts() {
    step "Long charts" \
        "$CHARTS" -a 2 -p 1 -s "$STOCK_LIST" -y "$LONG_DAYS"
    step "Short charts" \
        "$CHARTS" -a 2 -p 3 -s "$STOCK_LIST" -y "$SHORT_DAYS"
}

# Main entry point of the script
main() {
    case "${1:-}" in
        -h|--help) usage ;;
    esac
    load_environment
    check_commands
    check_credential
    check_environment

    log "*** $0: Job started on $(hostname) at $(date '+%Y/%m/%d %T')"

    update_charts
    build_summaries
    send_reports
    draw_extra_charts

    log "*** $0: Job ended on $(hostname) at $(date '+%Y/%m/%d %T')"
    log ""

    if [ "$failures" -gt 0 ]; then
        echo "[ERROR] $failures step(s) failed; see $JOBLOG" >&2
        return 1
    fi
    return 0
}

# Execute main function
main "$@"
