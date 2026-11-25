#!/usr/bin/env bash
# Executed INSIDE a disposable Arch OCI builder; no host package installation.
set -euo pipefail
export LC_ALL=C
date_path="$1"
shift
[[ "$date_path" =~ ^[0-9]{4}/[0-9]{2}/[0-9]{2}$ ]]
[[ "$#" -gt 0 ]]
mkdir -p /tmp/supra-root/var/lib/pacman /tmp/supra-cache
cat > /tmp/supra-pacman.conf <<EOF
[options]
Architecture = x86_64
SigLevel = Required DatabaseOptional
ParallelDownloads = 4
[core]
Server = https://archive.archlinux.org/repos/$date_path/\$repo/os/\$arch
[extra]
Server = https://archive.archlinux.org/repos/$date_path/\$repo/os/\$arch
EOF
args=(--config /tmp/supra-pacman.conf --root /tmp/supra-root --dbpath /tmp/supra-root/var/lib/pacman --cachedir /tmp/supra-cache --gpgdir /etc/pacman.d/gnupg --noconfirm)
pacman --version > /out/pacman-version.txt
pacman "${args[@]}" -Sy
pacman "${args[@]}" -Sp --print-format '%r|%n|%v|%a|%h|%f|%l' "$@" > /out/transaction.txt
for repo in core extra; do
    cp "/tmp/supra-root/var/lib/pacman/sync/$repo.db" "/out/$repo.db"
done
# No downloads or installation: metadata discovery does not establish authenticity.
