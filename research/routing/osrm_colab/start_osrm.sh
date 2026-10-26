#!/usr/bin/env bash
# exec preserves the PID so the notebook can stop only its own server.
set -euo pipefail
work=${1:?work directory required}
port=${2:?dedicated port required}
threads=${3:?bounded thread count required}
[[ $port =~ ^[0-9]+$ && $threads =~ ^[12]$ ]]
exec "$work/build/osrm-routed" --algorithm mld --ip 127.0.0.1 \
  --port "$port" --threads "$threads" --max-table-size 100 \
  "$work/data/bangladesh.osrm"
