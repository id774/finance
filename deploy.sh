#!/bin/sh

########################################################################
# deploy.sh: Install or update the finance pipeline
#
#  Description:
#  Install the package into a virtual environment under the deployment
#  root, put the batch script and the cron entry in place, and create
#  the directories the job writes to.
#
#  This replaces copying bin/ and lib/ into /var/stock. The location has
#  not moved; what has changed is that code now arrives as an installed
#  package rather than as loose files whose imports depended on their
#  position on disk.
#
#  Code and data are separated in what this script touches. It replaces
#  the virtual environment and the batch script, and it creates data/,
#  data/history/ and clf/ if they are absent, but it never writes into
#  them. Updating the pipeline cannot disturb generated data, and
#  generated data cannot require a code change.
#
#  The credential is separated from both. This script creates an empty
#  environment file readable only by root, for the operator to write
#  JQUANTS_API_KEY into by hand, and never writes a key itself: a
#  deployment script that took a secret as an argument would put it in
#  the shell history of every host it ran on. An existing file is left
#  exactly as it is.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - POSIX shell, python3 3.11 or later, sudo
#
#  Usage:
#      ./deploy.sh
#      ./deploy.sh -h | --help
#
#  Options:
#  - -h, --help
#      Display this help and exit.
#
#  Environment Variables:
#  - TARGET_DIR: Deployment root. Defaults to /var/stock.
#  - PYTHON: Interpreter used to build the environment. Defaults to
#      python3 as found on PATH. The previous deployment hardcoded
#      /opt/python/current/bin/python; set PYTHON to that path if the
#      host still keeps its interpreter there.
#  - DATA_GROUP: Group given read access to the generated data, which is
#      how the dashboard reads it. Defaults to www-data. The credential
#      file is not in that group: the dashboard reads generated files
#      and has no business holding the key that produced them.
#
#  Exit Codes:
#  - 0: The deployment finished.
#  - 1: A step failed.
#  - 127: A required command is missing.
#
#  Version History:
#  v1.0 2026-08-14
#       Create the environment file the API key is kept in. Install a package
#       into a virtual environment instead of copying bin/ and lib/.
#
########################################################################

set -u

TARGET_DIR=${TARGET_DIR:-/var/stock}
PYTHON=${PYTHON:-python3}
DATA_GROUP=${DATA_GROUP:-www-data}
VENV_DIR="$TARGET_DIR/.venv"
SOURCE_DIR=$(cd "$(dirname "$0")" && pwd)

# Display this script's header as usage information
usage() {
    awk '
        BEGIN { in_header = 0 }
        /^#+$/ && length($0) >= 10 { if (!in_header) { in_header = 1; next } else exit }
        in_header && /^# ?/ { print substr($0, 3) }
    ' "$0"
    exit 0
}

# Check that the required commands are available
check_commands() {
    for cmd in "$PYTHON" sudo install; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "[ERROR] Command not found: $cmd" >&2
            exit 127
        fi
    done
}

# Refuse an interpreter this package does not support
check_python() {
    if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
        echo "[ERROR] Python 3.11 or later is required." >&2
        "$PYTHON" --version >&2
        echo "[ERROR] Set PYTHON to a newer interpreter and run again." >&2
        exit 1
    fi
}

# Create the directories the job reads and writes
create_directories() {
    echo "[INFO] Creating directories under $TARGET_DIR"
    sudo install -d -m 750 "$TARGET_DIR" || exit 1
    # Data is group readable so that the dashboard can serve it, and
    # group writable so that the job can refresh it.
    sudo install -d -m 770 "$TARGET_DIR/data" || exit 1
    sudo install -d -m 770 "$TARGET_DIR/data/history" || exit 1
    sudo install -d -m 770 "$TARGET_DIR/clf" || exit 1
}

# Create the environment file the API key is kept in, without a key
create_environment_file() {
    if [ -f "$TARGET_DIR/env" ]; then
        echo "[INFO] Keeping the existing $TARGET_DIR/env"
        return 0
    fi
    echo "[INFO] Creating $TARGET_DIR/env"
    printf '%s\n' \
        "# Environment for the finance job, sourced by run.sh." \
        "# Put the J-Quants API key here and nowhere else." \
        "JQUANTS_API_KEY=" \
        | sudo tee "$TARGET_DIR/env" >/dev/null || exit 1
    sudo chown root:root "$TARGET_DIR/env" || exit 1
    sudo chmod 600 "$TARGET_DIR/env" || exit 1
}

# Build or refresh the virtual environment and install the package
install_package() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "[INFO] Creating the virtual environment in $VENV_DIR"
        sudo "$PYTHON" -m venv "$VENV_DIR" || exit 1
    fi

    echo "[INFO] Installing the package from $SOURCE_DIR"
    sudo "$VENV_DIR/bin/pip" install --upgrade --quiet pip || exit 1
    sudo "$VENV_DIR/bin/pip" install --upgrade --quiet "$SOURCE_DIR" || exit 1
}

# Install the batch script and the stock lists that ship with the source
install_scripts() {
    echo "[INFO] Installing run.sh"
    sudo install -m 750 "$SOURCE_DIR/run.sh" "$TARGET_DIR/run.sh" || exit 1

    for name in stocks.txt topix_core30.txt; do
        if [ ! -f "$TARGET_DIR/data/$name" ]; then
            echo "[INFO] Installing the initial $name"
            sudo install -m 660 "$SOURCE_DIR/data/$name" "$TARGET_DIR/data/$name" || exit 1
        fi
    done
}

# Install the cron entry that drives the job
install_cron() {
    echo "[INFO] Installing /etc/cron.d/stock"
    sudo install -m 640 -o root -g root "$SOURCE_DIR/cron.d/stock" /etc/cron.d/stock || exit 1
}

# Give the data directory the ownership the dashboard needs
set_ownership() {
    echo "[INFO] Setting ownership"
    sudo chown -R root:adm "$TARGET_DIR" || exit 1
    sudo chown -R "root:$DATA_GROUP" "$TARGET_DIR/data" || exit 1
    sudo chown -R "root:adm" "$TARGET_DIR/clf" || exit 1
    sudo chmod -R g+r,o-rwx "$TARGET_DIR" || exit 1
    # Restored after the recursive chmod above, which would otherwise
    # have widened the one file that must stay readable by root alone.
    sudo chown root:root "$TARGET_DIR/env" || exit 1
    sudo chmod 600 "$TARGET_DIR/env" || exit 1
}

# Report where the pieces landed
report() {
    echo "[INFO] Deployment finished"
    echo "[INFO] Commands:   $VENV_DIR/bin/finance-charts, finance-summary, finance-notify," \
         "finance-migrate"
    echo "[INFO] Batch:      $TARGET_DIR/run.sh"
    echo "[INFO] Data:       $TARGET_DIR/data"
    echo "[INFO] Models:     $TARGET_DIR/clf"
    echo "[INFO] Schedule:   /etc/cron.d/stock"
    echo "[INFO] Credential: $TARGET_DIR/env"
    if ! sudo grep -q '^JQUANTS_API_KEY=.' "$TARGET_DIR/env" 2>/dev/null; then
        echo "[WARN] $TARGET_DIR/env carries no API key;" \
             "the fetching step will fail until it does."
    fi
    if [ ! -f "$TARGET_DIR/data/my_stocks.txt" ]; then
        echo "[WARN] $TARGET_DIR/data/my_stocks.txt is absent;" \
             "the portfolio summary will fail until it exists."
    fi
}

# Main entry point of the script
main() {
    case "${1:-}" in
        -h|--help) usage ;;
    esac
    check_commands
    check_python
    create_directories
    create_environment_file
    install_package
    install_scripts
    install_cron
    set_ownership
    report
    return 0
}

# Execute main function
main "$@"
