#!/usr/bin/env bash
# Run only inside the Colab Linux runtime. Build the four native MLD tools.
set -euo pipefail
work=${1:?work directory required}
threads=${2:?bounded thread count required}
commit=4f3ee609ec1af40eb1f445c6706cfa5beb04c990
[[ $threads =~ ^[12]$ ]]
bash "$(dirname "$0")/install_dependencies.sh"
if [[ ! -d "$work/source/.git" ]]; then
  git clone --no-checkout https://github.com/Project-OSRM/osrm-backend.git "$work/source"
fi
git -C "$work/source" checkout --detach "$commit"
[[ $(git -C "$work/source" rev-parse HEAD) == "$commit" ]]
cmake -S "$work/source" -B "$work/build" -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_NODE_BINDINGS=OFF -DENABLE_LTO=OFF -DENABLE_GOLD_LINKER=OFF
cmake --build "$work/build" --parallel "$threads" \
  --target osrm-extract osrm-partition osrm-customize osrm-routed
"$work/build/osrm-routed" --version
dpkg-query -W > "$work/system-packages.txt"
