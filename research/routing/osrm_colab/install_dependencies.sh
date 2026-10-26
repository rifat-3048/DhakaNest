#!/usr/bin/env bash
# On a fresh runtime restore system libraries, even when reusing Drive binaries.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends build-essential git cmake pkg-config \
  libbz2-dev libxml2-dev libzip-dev libboost-all-dev lua5.2 liblua5.2-dev \
  libtbb-dev osmium-tool ca-certificates
