#!/usr/bin/env bash
# Disposable OCI filesystem only. No host root, privileged mode or network.
set -euo pipefail
export LC_ALL=C
umask 022
root=$(mktemp -d)
keyring=$(mktemp -d)
trap 'rm -rf "$root" "$keyring"' EXIT
mkdir -p "$root/var/lib/pacman" "$root/var/cache/pacman/pkg" "$root/var/log"
pacman-key --gpgdir "$keyring" --init
pacman-key --gpgdir "$keyring" --populate archlinux
cat > /tmp/supra-offline.conf <<'CONF'
[options]
Architecture = x86_64
SigLevel = Required
LocalFileSigLevel = Required
CONF
files=()
while IFS=$'\t' read -r filename digest; do
    [[ "$filename" =~ ^[A-Za-z0-9+_.@:-]+\.pkg\.tar\.(zst|xz)$ ]]
    [[ "$digest" =~ ^[a-f0-9]{64}$ ]]
    printf '%s  %s\n' "$digest" "/packages/$filename" | sha256sum --check --strict
    [[ -s "/packages/$filename.sig" ]]
    files+=("/packages/$filename")
done < /out/rootfs-input.tsv
(( ${#files[@]} > 0 ))
args=(--config /tmp/supra-offline.conf --root "$root" --dbpath "$root/var/lib/pacman" --cachedir "$root/var/cache/pacman/pkg" --gpgdir "$keyring" --logfile "$root/var/log/pacman.log" --noconfirm)
# Install in a single local transaction, retaining dependency, signature and hook checks.
pacman "${args[@]}" -U "${files[@]}" 2>&1 | tee /out/rootfs-install.log
if grep -Ei '(^|[[:space:]])(error:|ERROR:|failed to execute|failed to run)' /out/rootfs-install.log; then
    echo 'Transaction or hook failure' >&2
    exit 1
fi
pacman "${args[@]}" -Q > /out/installed-packages.txt
test -x "$root/usr/lib/systemd/systemd"
test -s "$root/boot/vmlinuz-linux-lts"
test -s "$root/boot/initramfs-linux-lts.img"
sha256sum "$root/boot/vmlinuz-linux-lts" "$root/boot/initramfs-linux-lts.img" | sed "s|$root/||g" > /out/rootfs-boot-files.sha256
echo "Experimental offline root built; no boot or release claim"
