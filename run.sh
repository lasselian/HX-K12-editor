#!/usr/bin/env bash
#
# One step way to start the HX-K12 editor.
#
# It sets up a private Python environment the first time, installs the editor
# into it, makes sure the keyboard is allowed to be reprogrammed, and then opens
# the graphical editor. It is safe to run this again any time; after the first
# run it just starts the app.
#
# Usage:
#   ./run.sh          open the graphical editor (default)
#   ./run.sh cli ...  run a command line command, e.g. ./run.sh cli info
#
set -euo pipefail

# Always work from the folder this script lives in, so it can be started from
# anywhere (including a double click in the file manager).
cd "$(dirname "$0")"

VENV=".venv"
PY="${PYTHON:-python3}"

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Python 3 was not found. Please install Python 3.9 or newer and try again."
  exit 1
fi

# 1. Private environment and dependencies.
if [ ! -d "$VENV" ]; then
  echo "First run: creating a private Python environment in $VENV ..."
  "$PY" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Linux talks to the keyboard directly and only needs the GUI toolkit.
# Windows and macOS also need the hidapi backend.
EXTRAS="gui"
if [ "$(uname)" != "Linux" ]; then
  EXTRAS="gui,hid"
fi

echo "Checking the editor is installed and up to date ..."
pip install --quiet --upgrade pip
pip install --quiet -e ".[$EXTRAS]"

# 2. One time permission so the keyboard can be reprogrammed (Linux only).
RULE=/etc/udev/rules.d/99-hx-k12.rules
if [ "$(uname)" = "Linux" ] && [ ! -f "$RULE" ]; then
  echo
  echo "The keyboard needs a one time permission rule."
  echo "This is the only step that asks for your password."
  if sudo install -m644 udev/99-hx-k12.rules "$RULE"; then
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "Permission set. If the editor cannot see the pad, unplug it and plug it back in."
  else
    echo "Skipped. You can do this later, see the README under Troubleshooting."
  fi
fi

# 3. Start.
if [ "${1:-}" = "cli" ]; then
  shift
  exec python -m hxk12 "$@"
fi

echo "Starting the HX-K12 editor ..."
exec python -m hxk12 gui
