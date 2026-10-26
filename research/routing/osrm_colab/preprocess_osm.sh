#!/usr/bin/env bash
# All three stages use MLD and the pinned source tree's matching car profile.
set -euo pipefail
work=${1:?work directory required}
threads=${2:?bounded thread count required}
[[ $threads =~ ^[12]$ ]]
"$work/build/osrm-extract" --threads "$threads" \
  --profile "$work/source/profiles/car.lua" "$work/data/bangladesh.osm.pbf"
"$work/build/osrm-partition" --threads "$threads" "$work/data/bangladesh.osrm"
"$work/build/osrm-customize" --threads "$threads" "$work/data/bangladesh.osrm"
