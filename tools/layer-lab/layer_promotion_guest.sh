#!/usr/bin/env bash
# Lab-only explicit promotion policy. Never install as a production service.
set -euo pipefail
export LC_ALL=C
grep -qw supra_layer_uefi=1 /proc/cmdline
guid=4a67b082-0a4c-41cf-b6c7-440b29bb8c4f
dir=/sys/firmware/efi/efivars
read_entry() {
    local file="$dir/$1-$guid"
    if [[ -e "$file" ]]; then tail -c +5 "$file" | iconv -f UTF-16LE -t UTF-8 | tr -d '\000'; fi
}
default=$(read_entry LoaderEntryDefault)
test -z "$(read_entry LoaderEntryOneShot)"
esp=$(mktemp -d)
trap 'umount "$esp"; rmdir "$esp"' EXIT
mount -t vfat -o ro /dev/vda1 "$esp"
# Explicit fixture policy token comes from the lab boot entry, not a production
# authorization mechanism. All health checks in layer_boot_guest already passed.
case "$(cat /etc/supra-lab-deployment):$default" in
    staged:)
        bootctl --esp-path="$esp" set-default supra-staged.conf
        bootctl --esp-path="$esp" set-oneshot supra-layer.conf
        test "$(read_entry LoaderEntryDefault)" = supra-staged.conf
        test "$(read_entry LoaderEntryOneShot)" = supra-layer.conf
        printf '%s\n' SUPRA_PROMOTION_ARMED > /dev/ttyS0
        ;;
    layer:supra-staged.conf)
        bootctl --esp-path="$esp" set-default supra-layer.conf
        test "$(read_entry LoaderEntryDefault)" = supra-layer.conf
        printf '%s\n' SUPRA_PROMOTION_COMMITTED > /dev/ttyS0
        ;;
    layer:supra-layer.conf)
        # Persistent boot proven before deliberate reversal.
        printf '%s\n' SUPRA_PROMOTION_PERSISTENT > /dev/ttyS0
        bootctl --esp-path="$esp" set-default supra-staged.conf
        test "$(read_entry LoaderEntryDefault)" = supra-staged.conf
        printf '%s\n' SUPRA_PROMOTION_REVERSED > /dev/ttyS0
        ;;
    staged:supra-staged.conf)
        printf '%s\n' SUPRA_PROMOTION_PREVIOUS_READY > /dev/ttyS0
        ;;
    *) exit 1 ;;
esac
