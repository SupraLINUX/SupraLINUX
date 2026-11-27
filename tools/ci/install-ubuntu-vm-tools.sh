#!/usr/bin/env bash
# Hosted Ubuntu runner tooling only; not a SupraLINUX package manager.
set -euo pipefail
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_ID" = 24.04
test -s /etc/apt/sources.list.d/ubuntu.sources
(( $# > 0 ))
# A vendor index unrelated to QEMU must not block the Ubuntu VM tooling.
# Keep the runner's configured Ubuntu mirrors and normal signature checks.
apt_options=(-o Dir::Etc::sourcelist=/etc/apt/sources.list.d/ubuntu.sources
             -o Dir::Etc::sourceparts=-
             -o APT::Get::List-Cleanup=0)
sudo apt-get "${apt_options[@]}" -o APT::Update::Error-Mode=any update -qq
sudo apt-get "${apt_options[@]}" install -y --no-install-recommends "$@"
