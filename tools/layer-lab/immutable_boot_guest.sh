#!/usr/bin/env bash
# Read-only root and explicit writable state, not a production security boundary.
set -Eeuo pipefail
export LC_ALL=C
check_phase=initial
trap 'rc=$?; printf "SUPRA_IMMUTABLE_ERROR phase=%s line=%s exit=%s command=%s\n" "$check_phase" "$LINENO" "$rc" "$BASH_COMMAND" >&2' ERR
step() { check_phase=$1; printf 'SUPRA_IMMUTABLE_CHECK=%s\n' "$check_phase"; }
source /usr/local/libexec/supra-immutable-layout
step root
findmnt -n -o TARGET,SOURCE,FSTYPE,FSROOT,VFS-OPTIONS,MAJ:MIN --mountpoint /
role=$(cat /etc/supra-lab-deployment)
case "$role" in staged|layer) ;; *) exit 1 ;; esac
test "$(findmnt -n -o FSROOT /)" = "/immutable/$role"
test "$(findmnt -n -o FSTYPE /)" = btrfs
test "$(btrfs property get -ts / ro)" = ro=true
findmnt -n -o VFS-OPTIONS / | tr ',' '\n' | grep -Fx ro
root_device=/dev/vda
if grep -qw supra_immutable_uefi=1 /proc/cmdline; then
    step firmware
    root_device=/dev/vda2
    test -d /sys/firmware/efi
    test "$(cat /sys/firmware/efi/fw_platform_size)" = 64
    test "$(lsblk -dn -o PTTYPE /dev/vda)" = gpt
    test "$(lsblk -dn -o PARTTYPE /dev/vda1)" = c12a7328-f81f-11d2-ba4b-00a0c93ec93b
    test "$(blkid -s LABEL -o value /dev/vda1)" = SUPRA_ESP
    grep -qw systemd.gpt_auto=0 /proc/cmdline
    if findmnt -rn -S /dev/vda1; then exit 1; fi
    esp=$(mktemp -d /run/supra-esp.XXXXXX)
    mount -t vfat -o ro /dev/vda1 "$esp"
    cmp "$esp/vmlinuz-linux-lts" /boot/vmlinuz-linux-lts
    cmp "$esp/initramfs-linux-lts.img" /boot/initramfs-linux-lts.img
    selected=$(tail -c +5 /sys/firmware/efi/efivars/LoaderEntrySelected-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f | iconv -f UTF-16LE -t UTF-8 | tr -d '\000')
    printf 'SUPRA_IMMUTABLE_ENTRY=%s\n' "$selected"
    if grep -qw supra_immutable_bless=1 /proc/cmdline || grep -qw supra_immutable_auto_bless=1 /proc/cmdline; then
        test "$role" = layer
        test "$selected" = supra-immutable-layer.conf
        count_var=/sys/firmware/efi/efivars/LoaderBootCountPath-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f
        if [[ -e "$count_var" ]]; then
            count_path=$(tail -c +5 "$count_var" | iconv -f UTF-16LE -t UTF-8 | tr -d '\000' | tr '\\' '/')
            expected_count=/loader/entries/supra-immutable-layer+1-1.conf
            if grep -qw supra_immutable_reject=1 /proc/cmdline; then
                expected_count=/loader/entries/supra-immutable-layer+0-1.conf
            fi
            test "$count_path" = "$expected_count"
            test -f "$esp$count_path"
            test ! -e "$esp/loader/entries/supra-immutable-layer.conf"
            printf '%s\n' SUPRA_BLESS_COUNTED > /dev/ttyS0
        else
            test -f "$esp/loader/entries/supra-immutable-layer.conf"
            test ! -e "$esp/loader/entries/supra-immutable-layer+1-1.conf"
            printf '%s\n' SUPRA_BLESS_ALREADY_GOOD > /dev/ttyS0
        fi
    elif grep -qw supra_immutable_bootcount=1 /proc/cmdline && [[ "$role" = layer ]]; then
        # Counted entry ID is normalized by some systemd-boot versions.
        count_path=$(tail -c +5 /sys/firmware/efi/efivars/LoaderBootCountPath-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f | iconv -f UTF-16LE -t UTF-8 | tr -d '\000' | tr '\\' '/')
        case "$count_path" in
            /loader/entries/supra-immutable-layer+1-1.conf|/loader/entries/supra-immutable-layer+0-2.conf) ;;
            *) exit 1 ;;
        esac
        case "$selected" in
            supra-immutable-layer.conf|supra-immutable-layer+2.conf|supra-immutable-layer+1-1.conf|supra-immutable-layer+0-2.conf) ;;
            *) exit 1 ;;
        esac
        printf 'SUPRA_BOOTCOUNT_PATH=%s\n' "$count_path" > /dev/ttyS0
    else
        test "$selected" = "supra-immutable-$role.conf"
    fi
    umount "$esp"
    rmdir "$esp"
    printf '%s\n' SUPRA_IMMUTABLE_UEFI_READY > /dev/ttyS0
fi
test "$(findmnt -n --nofsroot -o SOURCE --mountpoint /)" = "$root_device"
test "$(blkid -s LABEL -o value "$root_device")" = SUPRA_BTRFS_ROOT
test "$(blkid -s LABEL -o value /dev/vdb)" = SUPRA_LAB_STATE
step readonly-paths
# The root may not merely be a writable snapshot with a temporary overlay.
for path in /usr /etc /var/lib/pacman /boot; do
    if error=$(touch "$path/.supra-ro-probe" 2>&1); then
        echo "Unexpected writable deployment path: $path" >&2
        exit 1
    fi
    grep -Fq 'Read-only file system' <<< "$error"
    test ! -e "$path/.supra-ro-probe"
done
step inventory
pacman -Q | sha256sum --check /etc/supra-lab-inventory.sha256
if [[ "$role" = staged ]]; then
    test ! -e /usr/bin/tree
    if pacman -Q tree; then exit 1; fi
else
    pacman -Q tree
    /usr/bin/tree --version
fi
step ephemeral
findmnt -n -o TARGET,SOURCE,FSTYPE,VFS-OPTIONS --mountpoint /run
findmnt -n -o TARGET,SOURCE,FSTYPE,VFS-OPTIONS --mountpoint /tmp
test "$(findmnt -n -o FSTYPE --mountpoint /run)" = tmpfs
test "$(findmnt -n -o FSTYPE --mountpoint /tmp)" = tmpfs
test ! -e /run/supra-ephemeral-probe
test ! -e /tmp/supra-ephemeral-probe
touch /run/supra-ephemeral-probe /tmp/supra-ephemeral-probe
step phase-argument
phase=
for candidate in first next return count-trial count-return bless auto-bless; do
    if grep -qw "supra_immutable_phase=$candidate" /proc/cmdline; then
        test -z "$phase"
        phase=$candidate
    fi
done
case "$phase:$role" in first:staged|next:layer|return:staged|count-trial:layer|count-return:staged|bless:layer|auto-bless:layer) ;; *) exit 1 ;; esac
if [[ "$phase" = count-* ]]; then
    grep -qw supra_immutable_bootcount=1 /proc/cmdline
    grep -qw supra_immutable_uefi=1 /proc/cmdline
fi
for entry in "${immutable_domains[@]}"; do
    domain="${entry%%:*}"
    path="${entry#*:}"
    step "mount-$domain"
    findmnt -n -o TARGET,SOURCE,FSTYPE,FSROOT,VFS-OPTIONS,MAJ:MIN --mountpoint "$path"
    test "$(findmnt -n -o FSROOT --mountpoint "$path")" = "/$domain"
    test "$(findmnt -n -o FSTYPE --mountpoint "$path")" = btrfs
    # Btrfs subvolume mountinfo may expose an anonymous device number.
    # Verify the actual source block device and its filesystem UUID instead.
    source_device=$(findmnt -n --nofsroot -o SOURCE --mountpoint "$path")
    test -b "$source_device"
    test "$(readlink -f "$source_device")" = "$(readlink -f /dev/vdb)"
    test "$(blkid -s UUID -o value "$source_device")" = "$(blkid -s UUID -o value /dev/vdb)"
    findmnt -n -o VFS-OPTIONS --mountpoint "$path" | tr ',' '\n' | grep -Fx rw
    step "sentinel-$domain"
    sentinel="$path/.supra-persistent-probe"
    case "$phase" in
        first) test ! -e "$sentinel"; printf 'first:%s\n' "$domain" > "$sentinel" ;;
        next) test "$(cat "$sentinel")" = "first:$domain"; printf 'next:%s\n' "$domain" > "$sentinel" ;;
        return|count-trial|count-return|bless|auto-bless) test "$(cat "$sentinel")" = "next:$domain" ;;
    esac
done
# No masking system services or ignoring failed units to make a boot green.
step systemd
systemctl list-units --state=failed --no-legend --plain --no-pager > /run/supra-failed-units
cat /run/supra-failed-units
test "$(systemctl show --property=NFailedUnits --value)" = 0
sync
if [[ "$phase" = auto-bless ]]; then
    step automatic-health
    grep -qw supra_immutable_auto_bless=1 /proc/cmdline
    grep -qw supra_immutable_uefi=1 /proc/cmdline
    test "$(systemctl show --property=LoadState --value systemd-bless-boot.service)" = loaded
    mkdir /run/supra-auto-esp
    mount -t vfat -o rw,nosuid,nodev,noexec /dev/vda1 /run/supra-auto-esp
    test "$(findmnt -n -o SOURCE --mountpoint /run/supra-auto-esp)" = /dev/vda1
    export SYSTEMD_ESP_PATH=/run/supra-auto-esp
    # v262.2 status returns dirty when the firmware decremented the
    # counter to zero on this boot, even before any explicit decision.
    status=$(/usr/lib/systemd/systemd-bless-boot status)
    printf 'SUPRA_AUTO_HEALTH_STATUS=%s\n' "$status" > /dev/ttyS0
    if grep -qw supra_immutable_reject=1 /proc/cmdline; then
        test -e "$count_var"
        test "$status" = dirty
    elif [[ -e "$count_var" ]]; then
        test "$status" = indeterminate
    else
        test "$status" = clean
    fi
    printf '%s\n' SUPRA_AUTO_HEALTH_CHECKS_PASSED > /dev/ttyS0
    if grep -qw supra_immutable_reject=1 /proc/cmdline; then
        printf '%s\n' SUPRA_AUTO_HEALTH_REJECTED > /dev/ttyS0
        exit 23
    fi
    printf '%s\n' SUPRA_AUTO_HEALTH_ACCEPTED > /dev/ttyS0
    exit 0
fi
if [[ "$phase" = bless ]]; then
    step health-gated-bless
    grep -qw supra_immutable_bless=1 /proc/cmdline
    grep -qw supra_immutable_uefi=1 /proc/cmdline
    # Explicit lab policy: mask automatic service only in this test, and
    # call its native executable AFTER all existing health checks succeed.
    test "$(systemctl show --property=LoadState --value systemd-bless-boot.service)" = masked
    esp=$(mktemp -d /run/supra-bless.XXXXXX)
    mount -t vfat -o rw,nosuid,nodev,noexec /dev/vda1 "$esp"
    test "$(findmnt -n -o SOURCE --mountpoint "$esp")" = /dev/vda1
    export SYSTEMD_ESP_PATH="$esp"
    bless=/usr/lib/systemd/systemd-bless-boot
    test -x "$bless"
    printf '%s\n' SUPRA_BLESS_HEALTH_READY > /dev/ttyS0
    if [[ -e "$count_var" ]]; then
        test "$("$bless" status)" = indeterminate
        "$bless" good
        test "$("$bless" status)" = good
        printf '%s\n' SUPRA_BLESS_MARKED_GOOD > /dev/ttyS0
    else
        test "$("$bless" status)" = clean
        printf '%s\n' SUPRA_BLESS_CLEAN_BOOT > /dev/ttyS0
    fi
    test -f "$esp/loader/entries/supra-immutable-layer.conf"
    test ! -e "$esp/loader/entries/supra-immutable-layer+1-1.conf"
    sync
    umount "$esp"
    rmdir "$esp"
    printf '%s\n' SUPRA_BLESS_READY > /dev/ttyS0
    exit 0
fi
if [[ "$phase" = count-trial ]]; then
    # Lab-only fault injection: never bless a candidate intended to fail.
    # The host kills this QEMU child only after the durable firmware decrement.
    grep -qw systemd.mask=systemd-bless-boot.service /proc/cmdline
    test "$(systemctl show --property=LoadState --value systemd-bless-boot.service)" = masked
    printf '%s\n' SUPRA_BOOTCOUNT_INTERRUPT_POINT > /dev/ttyS0
    sleep 180
    exit 1
fi
if [[ "$phase" = count-return ]]; then
    printf '%s\n' SUPRA_BOOTCOUNT_FALLBACK_READY > /dev/ttyS0
    exit 0
fi
printf 'SUPRA_IMMUTABLE_%s_READY\n' "${phase^^}" > /dev/ttyS0
