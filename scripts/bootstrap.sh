#!/bin/sh
# LOCATION³ one-line start for macOS and Linux.
#
#   curl -fsSL https://raw.githubusercontent.com/lukexyz/location-location-location/main/scripts/bootstrap.sh | sh -s -- claude
#
# Clones the repository, installs its Python and Node dependencies, reports what
# it found on this machine, and opens the chosen coding agent inside the
# repository with the research skill loaded. It never asks for, reads out, or
# stores a routing key; it only reports whether ORS_API_KEY is set.
#
# Environment overrides (all optional):
#   LOCATION3_AGENT   claude | codex (the first argument wins when given)
#   LOCATION3_DIR     where to clone; default ./location-location-location
#   LOCATION3_REPO    clone source; default the GitHub repository
#   LOCATION3_LAUNCH  set to 0 to stop after installing instead of opening the agent
set -eu

agent="${1:-${LOCATION3_AGENT:-}}"
target="${LOCATION3_DIR:-location-location-location}"
repo="${LOCATION3_REPO:-https://github.com/lukexyz/location-location-location.git}"
launch="${LOCATION3_LAUNCH:-1}"

say() { printf '%s\n' "$*"; }
fail() { say "bootstrap: $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

case "$agent" in
  claude|codex) ;;
  "") fail "name the agent to open: sh -s -- claude   or   sh -s -- codex" ;;
  *) fail "unknown agent '$agent'; use claude or codex" ;;
esac

say "LOCATION3 bootstrap"
say "  agent      $agent"
say "  directory  $target"

# ---- prerequisites --------------------------------------------------------------
missing=""
if have git; then say "  git        found"; else say "  git        MISSING  https://git-scm.com/downloads"; missing="$missing git"; fi
if have uv; then say "  uv         found (installs Python 3.11+ itself)"; else say "  uv         MISSING  curl -LsSf https://astral.sh/uv/install.sh | sh"; missing="$missing uv"; fi
if have node; then
  node_major="$(node --version 2>/dev/null | sed -e 's/^v//' -e 's/\..*$//' || echo 0)"
  node_major="${node_major:-0}"
  if [ "$node_major" -ge 22 ] 2>/dev/null; then say "  node       found (v$node_major)"; else say "  node       TOO OLD (v$node_major; need 22+)  https://nodejs.org"; missing="$missing node"; fi
else say "  node       MISSING  https://nodejs.org (22 or newer)"; missing="$missing node"; fi
if have npm; then say "  npm        found"; else say "  npm        MISSING  ships with Node"; missing="$missing npm"; fi
if have "$agent"; then agent_found=1; printf '  %-10s found\n' "$agent"; else
  agent_found=0
  case "$agent" in
    claude) say "  claude     not on PATH  npm install -g @anthropic-ai/claude-code" ;;
    codex)  say "  codex      not on PATH  npm install -g @openai/codex" ;;
  esac
fi
if [ -n "${ORS_API_KEY:-}" ]; then
  say "  ORS_API_KEY  set (never printed; the run gets a real drive-time boundary)"
else
  say "  ORS_API_KEY  not set  the first run uses a labelled distance boundary; a free key from https://openrouteservice.org upgrades it"
fi
[ -z "$missing" ] || fail "install the missing tools (${missing# }) and paste the line again"

# ---- clone or reuse ---------------------------------------------------------------
if [ -d "$target/.git" ]; then
  say "Using the existing clone at $target (not pulled; run git pull yourself if you want the latest)"
elif [ -e "$target" ]; then
  fail "$target exists and is not a git clone; set LOCATION3_DIR to another folder"
else
  say "Cloning $repo"
  git clone --quiet "$repo" "$target"
fi
cd "$target"

# ---- install ----------------------------------------------------------------------
say "Installing Python dependencies (uv sync)"
uv sync --quiet
say "Installing viewer dependencies (npm install)"
npm install --no-fund --no-audit --loglevel=error

say ""
say "Ready. Everything researched here stays in gitignored folders under $(pwd)."
prompt="Use the location-research skill to help me run my own bounded location search, previewing every outbound call before it happens."
if [ "$launch" = "0" ]; then
  say "Not launching (LOCATION3_LAUNCH=0). To start: cd \"$target\" && $agent \"$prompt\""
  exit 0
fi
if [ "$agent_found" = "0" ]; then
  say "Install $agent, then run:  cd \"$target\" && $agent \"$prompt\""
  exit 0
fi
say "Opening $agent with the research skill loaded"
# When this script arrives through a pipe the agent still needs the terminal.
if [ -t 0 ]; then
  exec "$agent" "$prompt"
elif [ -r /dev/tty ]; then
  exec "$agent" "$prompt" </dev/tty
else
  say "No terminal available to hand over; run:  cd \"$target\" && $agent \"$prompt\""
fi
