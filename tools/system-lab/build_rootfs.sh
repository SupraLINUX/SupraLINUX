#!/usr/bin/env bash
# Run only inside the disposable, networkless build VM.
set -euo pipefail
export LC_ALL=C
umask 022
root=$(mktemp -d)
keyring=$(mktemp -d)
# A separate blank disk is explicitly attached by the VM launcher.
test -b /dev/vdb
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_TARGET
mount /dev/vdb "$root"
cleanup() {
    for dir in dev sys proc; do
        if mountpoint -q "$root/$dir"; then umount "$root/$dir" || return 1; fi
    done
    umount "$root" || return 1
    rmdir "$root"
    rm -rf "$keyring"
}
trap cleanup EXIT
mkdir -p "$root"/{dev,sys,proc}
mount -t proc proc "$root/proc"
mount -t sysfs sysfs "$root/sys"
mount --bind /dev "$root/dev"
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
(cd "$root" && sha256sum boot/vmlinuz-linux-lts boot/initramfs-linux-lts.img) > /out/rootfs-boot-files.sha256
# Test-only service: prove a fresh systemd boot reached multi-user prerequisites.
# It is never shipped as a release component.
install -D -m 0644 /boot-probe.service "$root/etc/systemd/system/supra-boot-probe.service"
install -D -m 0755 /boot-probe.sh "$root/usr/local/libexec/supra-boot-probe"
mkdir -p "$root/etc/systemd/system/multi-user.target.wants"
ln -s ../supra-boot-probe.service "$root/etc/systemd/system/multi-user.target.wants/supra-boot-probe.service"
sync
echo "Experimental offline root built; no boot or release claim"
