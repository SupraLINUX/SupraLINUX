#!/usr/bin/env bash
# Disposable networkless VM only: vda ext4 active overlay, vdb Btrfs,
# vdc authenticated input read-only, vdd evidence output.
set -Eeuo pipefail
export LC_ALL=C
trap 'printf "LAYER_ERROR line=%s command=%s\n" "$LINENO" "$BASH_COMMAND" >&2' ERR
test "$(findmnt -n -o SOURCE /)" = /dev/vda
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_BTRFS_ROOT
test "$(blkid -s LABEL -o value /dev/vdc)" = SUPRA_LAYER_IN
test "$(blockdev --getro /dev/vdc)" = 1
test "$(blkid -s LABEL -o value /dev/vdd)" = SUPRA_LAB_OUTPUT
work=$(mktemp -d)
mkdir "$work"/{top,in,out,root}
top="$work/top"
input="$work/in"
out="$work/out"
root="$work/root"
keyring="$work/keyring"
cleanup() {
    local rc=0
    for path in "$root/dev" "$root/sys" "$root/proc" "$root" "$out" "$input" "$top"; do
        if mountpoint -q "$path"; then umount "$path" || rc=1; fi
    done
    return "$rc"
}
trap cleanup EXIT
mount -t btrfs -o subvolid=5 /dev/vdb "$top"
mount -t ext4 -o ro,noload /dev/vdc "$input"
mount -t ext4 /dev/vdd "$out"
base="$top/deployments/base"
previous="$top/deployments/staged"
test "$(btrfs property get -ts "$base" ro)" = ro=true
test ! -e "$top/deployments/layer"
test ! -e "$base/usr/bin/tree"
test ! -e "$previous/usr/bin/tree"
# The active ext4 root is never the transaction target.
pacman -Q > "$out/active-before.txt"
chroot "$base" pacman -Q > "$out/base-before.txt"
chroot "$previous" pacman -Q > "$out/previous-before.txt"
cmp "$out/active-before.txt" "$out/base-before.txt"
cmp "$out/base-before.txt" "$out/previous-before.txt"
btrfs subvolume show "$base" > "$out/base-before-subvolume.txt"
# Snapshot creation legitimately updates source root metadata. Compare the
# stable identity and logical filesystem contents, excluding atime/ctime.
source /usr/local/libexec/supra-layer-digest
layer_digest "$base" > "$out/base-before-content.sha256"
layer_digest "$previous" > "$out/previous-before-content.sha256"
btrfs subvolume snapshot "$base" "$top/deployments/layer"
mount -t btrfs -o subvol=deployments/layer /dev/vdb "$root"
test "$(findmnt -n -o FSROOT --mountpoint "$root")" = /deployments/layer
test "$(btrfs property get -ts "$root" ro)" = ro=false
IFS=$'\t' read -r name version filename digest < "$input/layer.tsv"
test "$name" = tree
[[ "$filename" =~ ^tree-[A-Za-z0-9+_.@:-]+\.pkg\.tar\.(zst|xz)$ ]]
[[ "$digest" =~ ^[a-f0-9]{64}$ ]]
printf '%s  %s\n' "$digest" "$input/$filename" | sha256sum --check --strict
test -s "$input/$filename.sig"
mkdir -m 700 "$keyring"
pacman-key --gpgdir "$keyring" --init
pacman-key --gpgdir "$keyring" --populate archlinux
source /usr/local/libexec/supra-layer-pacman-config
write_layer_pacman_config "$root" "$work/pacman.conf"
# Resolve the actual configuration with the installed pacman version.
hookdir=$(pacman-conf --config "$work/pacman.conf" --rootdir "$root" HookDir)
printf 'Layer HookDir: %s\n' "$hookdir"
test "$hookdir" = "$root/etc/pacman.d/hooks" || test "$hookdir" = "$root/etc/pacman.d/hooks/"
interrupt=0
mount -t proc proc "$root/proc"
mount -t sysfs sysfs "$root/sys"
mount --bind /dev "$root/dev"
if grep -qw supra_install_interrupt=1 /proc/cmdline; then
    interrupt=1
    # Test-only hook inside the unapproved target, never in the old root.
    mkdir -p "$root/etc/pacman.d/hooks"
    cat > "$root/etc/pacman.d/hooks/zz-supra-interrupt.hook" <<'HOOK'
[Trigger]
Operation = Install
Type = Package
Target = tree
[Action]
Description = SupraLINUX lab interruption before publication
When = PostTransaction
Exec = /usr/local/libexec/supra-install-interrupt-hook
HOOK
    install -m 0755 /usr/local/libexec/supra-install-interrupt-hook "$root/usr/local/libexec/supra-install-interrupt-hook"
    test -s "$hookdir/zz-supra-interrupt.hook"
    test -x "$root/usr/local/libexec/supra-install-interrupt-hook"
    test -c "$root/dev/ttyS0"
    printf '%s\n' 'Layer interruption hook configured'
else
    test ! -e "$hookdir/zz-supra-interrupt.hook"
    printf '%s\n' 'Layer normal transaction'
fi
# Use libalpm for actual dependency/conflict, signature and hook enforcement.
timeout --kill-after=5 120 pacman --config "$work/pacman.conf" --root "$root" \
    --dbpath "$root/var/lib/pacman" --cachedir "$root/var/cache/pacman/pkg" \
    --gpgdir "$keyring" --logfile "$root/var/log/pacman.log" --noconfirm \
    -U "$input/$filename" 2>&1 | tee "$out/install.log"
# Returning from a transaction in interruption mode is a failed fixture,
# even if libalpm reports success after a failed post-transaction hook.
if (( interrupt )); then
    echo 'Interruption hook returned without VM termination; refusing publication' >&2
    exit 1
fi
if grep -Ei '(^|[[:space:]])(error:|failed to execute|failed to run)' "$out/install.log"; then exit 1; fi
chroot "$root" pacman -Q > "$out/layer-installed.txt"
cmp "$input/expected.txt" "$out/layer-installed.txt"
test "$(chroot "$root" pacman -Q tree)" = "tree $version"
chroot "$root" /usr/bin/tree --version | tee "$out/tree-version.txt"
for asset in vmlinuz-linux-lts initramfs-linux-lts.img; do cmp "$base/boot/$asset" "$root/boot/$asset"; done
printf 'layer\n' > "$root/etc/supra-lab-deployment"
printf 'LABEL=SUPRA_BTRFS_ROOT / btrfs rw,subvol=deployments/layer 0 0\n' > "$root/etc/fstab"
sha256sum "$out/layer-installed.txt" | awk '{print $1 "  -"}' > "$root/etc/supra-lab-inventory.sha256"
for path in "$root/dev" "$root/sys" "$root/proc"; do umount "$path"; done
sync
btrfs filesystem sync "$top"
test "$(btrfs property get -ts "$base" ro)" = ro=true
test ! -e "$base/usr/bin/tree"
test ! -e "$previous/usr/bin/tree"
chroot "$base" pacman -Q > "$out/base-after.txt"
chroot "$previous" pacman -Q > "$out/previous-after.txt"
pacman -Q > "$out/active-after.txt"
cmp "$out/base-before.txt" "$out/base-after.txt"
cmp "$out/previous-before.txt" "$out/previous-after.txt"
cmp "$out/active-before.txt" "$out/active-after.txt"
btrfs subvolume show "$base" > "$out/base-after-subvolume.txt"
for field in UUID "Gen at creation" "Subvolume ID" Flags; do
    cmp <(grep -E "^[[:space:]]*$field:" "$out/base-before-subvolume.txt") \
        <(grep -E "^[[:space:]]*$field:" "$out/base-after-subvolume.txt")
done
layer_digest "$base" > "$out/base-after-content.sha256"
layer_digest "$previous" > "$out/previous-after-content.sha256"
for role in base previous; do
    cmp "$out/$role-before-content.sha256" "$out/$role-after-content.sha256"
done
cleanup
trap - EXIT
printf '%s\n' SUPRA_LAYER_PREPARED > /dev/ttyS0
