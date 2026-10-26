#!/usr/bin/env bash
# Explicit Ubuntu 22.04-era toolchain, without replacing the default compiler.
set -euo pipefail
source /etc/os-release
[[ ${ID:-} == ubuntu && (${VERSION_ID:-} == 22.04 || ${VERSION_ID:-} == 24.04) ]]
[[ $(dpkg --print-architecture) == amd64 ]]
export DEBIAN_FRONTEND=noninteractive
apt-get update
# --no-remove refuses a conflicting preinstalled Boost toolchain. Use a fresh
# CPU runtime or review the conflict; do not silently purge installed packages.
apt-get install -y --no-remove --no-install-recommends gcc-11 g++-11 git cmake make pkg-config \
  libbz2-dev libxml2-dev libzip-dev lua5.2 liblua5.2-dev libtbb-dev \
  libboost1.74-dev libboost-date-time1.74-dev libboost-chrono1.74-dev \
  libboost-filesystem1.74-dev libboost-iostreams1.74-dev \
  libboost-program-options1.74-dev libboost-regex1.74-dev libboost-system1.74-dev \
  libboost-thread1.74-dev libboost-test1.74-dev osmium-tool ca-certificates
[[ $(/usr/bin/g++-11 -dumpversion) == 11 ]]
[[ $(/usr/bin/cmake --version | head -n 1) == 'cmake version 3.'* ]]
grep -Eq '^#define BOOST_VERSION 107400$' /usr/include/boost/version.hpp
