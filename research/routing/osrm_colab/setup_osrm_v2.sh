#!/usr/bin/env bash
# A new private attempt directory is mandatory. No resets, cleans or source edits.
set -euo pipefail
set -E
trap 'printf "ERROR: native setup failed at line %s: %s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR
attempt=${1:?new attempt directory required}
[[ ! -e "$attempt" ]]
mkdir -p "$attempt"
commit=4f3ee609ec1af40eb1f445c6706cfa5beb04c990
export LC_ALL=C
echo '=== Original runtime toolchain (before dependency selection) ==='
uname -a
cat /etc/os-release
command -v g++ >/dev/null && g++ --version || true
command -v cmake >/dev/null && cmake --version || true
dpkg-query -W > "$attempt/packages-before.txt"
bash "$(dirname "$0")/install_dependencies_v2.sh"
echo '=== Selected toolchain ==='
/usr/bin/gcc-11 --version
/usr/bin/g++-11 --version
/usr/bin/cmake --version
pkg-config --modversion lua5.2 libxml-2.0
dpkg-query -W > "$attempt/system-packages.txt"
git init "$attempt/source"
git -C "$attempt/source" remote add origin https://github.com/Project-OSRM/osrm-backend.git
git -C "$attempt/source" fetch --depth 1 origin refs/tags/v5.27.1
[[ $(git -C "$attempt/source" rev-parse 'FETCH_HEAD^{commit}') == "$commit" ]]
git -C "$attempt/source" checkout --detach "$commit"
git -C "$attempt/source" submodule update --init --recursive --depth 1
git -C "$attempt/source" fsck --no-dangling
[[ $(git -C "$attempt/source" rev-parse HEAD) == "$commit" ]]
[[ -z $(git -C "$attempt/source" status --porcelain --untracked-files=all) ]]
git -C "$attempt/source" submodule status --recursive
sha256sum "$attempt/source/include/util/coordinate.hpp" "$attempt/source/include/util/alias.hpp"
# This independent probe does not add includes or patches to OSRM source.
/usr/bin/g++-11 -std=c++17 -fdiagnostics-color=never -I "$attempt/source/include" \
  -fsyntax-only -x c++ "$(dirname "$0")/coordinate_probe.cpp"
/usr/bin/cmake -S "$attempt/source" -B "$attempt/build" \
  -DCMAKE_C_COMPILER=/usr/bin/gcc-11 -DCMAKE_CXX_COMPILER=/usr/bin/g++-11 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_VERBOSE_MAKEFILE=ON \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_CXX_FLAGS=-fdiagnostics-color=never \
  -DBoost_NO_BOOST_CMAKE=ON -DBOOST_ROOT=/usr -DBOOST_INCLUDEDIR=/usr/include \
  -DBoost_ADDITIONAL_VERSIONS=1.74.0 -DENABLE_CCACHE=OFF \
  -DENABLE_NODE_BINDINGS=OFF -DENABLE_LTO=OFF -DENABLE_GOLD_LINKER=OFF
# Serial, verbose build: diagnostics preserve the earliest failure in order.
/usr/bin/cmake --build "$attempt/build" --verbose --parallel 1 \
  --target osrm-extract osrm-partition osrm-customize osrm-routed
for name in extract partition customize routed; do
  "$attempt/build/osrm-$name" --version
  "$attempt/build/osrm-$name" --help > "$attempt/$name-help.txt"
  ldd "$attempt/build/osrm-$name"
done
[[ -z $(git -C "$attempt/source" status --porcelain --untracked-files=all) ]]
