#!/usr/bin/env bash
# [C5-REAL] TERMINAL BUFFER OPTIMIZER
# Action: Execute within alternative screen buffer (smcup/rmcup) to bypass DOM rendering bottlenecks.

set -euo pipefail

cleanup() {
  tput rmcup
  tput cnorm
}
trap cleanup EXIT INT TERM

if [ "$#" -eq 0 ]; then
  echo "Usage: $0 <command> [args...]"
  exit 1
fi

tput smcup
tput cinvis
clear

"$@"
