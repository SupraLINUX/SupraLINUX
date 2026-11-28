#!/usr/bin/env bash
# Read-only root and explicit writable state, not a production security boundary.
set -euo pipefail
export LC_ALL=C
source /usr/local/libexec/supra-immutable-layout
role=$(cat /etc/supra-lab-deployment)
case "$role" in staged|layer) ;; *) exit 1 ;; esac
test "$(findmnt -n -o FSROOT /)" = "/immutable/$role"
test "$(findmnt -n -o FSTYPE /)" = btrfs
test "$(btrfs property get -ts / ro)" = ro=true
findmnt -n -o VFS-OPTIONS / | tr ',' '\n' | grep -Fx ro
test "$(blkid -s LABEL -o value /dev/vda)" = SUPRA_BTRFS_ROOT
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_LAB_STATE
# The root may not merely be a writable snapshot with a temporary overlay.
for path in /usr /etc /var/lib/pacman /boot; do
    if error=$(touch "$path/.supra-ro-probe" 2>&1); then
        echo "Unexpected writable deployment path: $path" >&2
        exit 1
    fi
    grep -Fq 'Read-only file system' <<< "$error"
    test ! -e "$path/.supra-ro-probe"
done
pacman -Q | sha256sum --check /etc/supra-lab-inventory.sha256
if [[ "$role" = staged ]]; then
    test ! -e /usr/bin/tree
    if pacman -Q tree; then exit 1; fi
else
    pacman -Q tree
    /usr/bin/tree --version
fi
test "$(findmnt -n -o FSTYPE --mountpoint /run)" = tmpfs
test "$(findmnt -n -o FSTYPE --mountpoint /tmp)" = tmpfs
test ! -e /run/supra-ephemeral-probe
test ! -e /tmp/supra-ephemeral-probe
touch /run/supra-ephemeral-probe /tmp/supra-ephemeral-probe
phase=
for candidate in first next return; do
    if grep -qw "supra_immutable_phase=$candidate" /proc/cmdline; then
        test -z "$phase"
        phase=$candidate
    fi
done
case "$phase:$role" in first:staged|next:layer|return:staged) ;; *) exit 1 ;; esac
for entry in "${immutable_domains[@]}"; do
    domain="${entry%%:*}"
    path="${entry#*:}"
    test "$(findmnt -n -o FSROOT --mountpoint "$path")" = "/$domain"
    test "$(findmnt -n -o FSTYPE --mountpoint "$path")" = btrfs
    test "$(findmnt -n -o MAJ:MIN --mountpoint "$path")" = "$(lsblk -dn -o MAJ:MIN /dev/vdb)"
    findmnt -n -o VFS-OPTIONS --mountpoint "$path" | tr ',' '\n' | grep -Fx rw
    sentinel="$path/.supra-persistent-probe"
    case "$phase" in
        first) test ! -e "$sentinel"; printf 'first:%s\n' "$domain" > "$sentinel" ;;
        next) test "$(cat "$sentinel")" = "first:$domain"; printf 'next:%s\n' "$domain" > "$sentinel" ;;
        return) test "$(cat "$sentinel")" = "next:$domain" ;;
    esac
done
# No masking system services or ignoring failed units to make a boot green.
systemctl --failed --no-legend --plain > /run/supra-failed-units
cat /run/supra-failed-units
test ! -s /run/supra-failed-units
sync
printf 'SUPRA_IMMUTABLE_%s_READY\n' "${phase^^}" > /dev/ttyS0
