#!/usr/bin/env bash
# setup_venv.sh - create the project venv (.venv) and install requirements.txt.
# Works on Linux, macOS, and Git Bash on Windows. Lives in scripts/.
# Run from anywhere:
#   bash scripts/setup_venv.sh
set -euo pipefail

WANT="3.14"   # project Python version (docs/decisions/0008)

die() { echo "Error: $*" >&2; exit 1; }

# Work from the repo root (the folder above scripts/), wherever this was called from.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

case "$(uname -s)" in
  Linux*)        OS=linux;   HINT="If your distribution doesn't package Python $WANT, tools like pyenv or uv can install it." ;;
  Darwin*)       OS=macos;   HINT="Install it from python.org, or with Homebrew: brew install python@$WANT" ;;
  MINGW*|MSYS*)  OS=windows; HINT="Install it from python.org; check what is installed with: py --list" ;;
  *) die "unsupported system: $(uname -s)" ;;
esac

# Pick the interpreter. On Windows always go through the py launcher with an
# explicit version, so python3 can't resolve to the Microsoft Store 3.12.
if [[ $OS == windows ]]; then
  command -v py >/dev/null 2>&1 || die "the py launcher was not found. $HINT"
  PY=(py "-$WANT")
  VENV_PY=.venv/Scripts/python.exe
  ACTIVATE=.venv/Scripts/activate
else
  # Linux and macOS. Prefer python3.14 (python.org and Homebrew both install that name).
  # On macOS a bare python3 is often Apple's older copy from the Xcode Command Line Tools.
  if command -v "python$WANT" >/dev/null 2>&1; then
    PY=("python$WANT")
  elif command -v python3 >/dev/null 2>&1; then
    PY=(python3)
  else
    die "Python $WANT was not found. $HINT"
  fi
  VENV_PY=.venv/bin/python
  ACTIVATE=.venv/bin/activate
fi

"${PY[@]}" -c 'import sys' 2>/dev/null || die "'${PY[*]}' did not run. $HINT"
HAVE=$("${PY[@]}" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "Using ${PY[*]} (Python $HAVE)"
[[ $HAVE == "$WANT" ]] || echo "Warning: the project uses Python $WANT; this is $HAVE. $HINT" >&2

[[ -f requirements.txt ]] || die "requirements.txt not found in $(pwd)."

if [[ -x $VENV_PY ]]; then
  echo ".venv already exists; reusing it. Delete .venv to start over."
else
  if ! "${PY[@]}" -m venv .venv; then
    rm -rf .venv   # remove the half-made venv so a rerun starts clean
    [[ $OS == linux ]] && echo "On Debian, install venv support and rerun:  sudo apt install python${HAVE}-venv" >&2
    die "creating .venv failed."
  fi
fi

"$VENV_PY" -m pip install -r requirements.txt

echo
echo "Done. To activate in this terminal:"
echo "  source $ACTIVATE"
