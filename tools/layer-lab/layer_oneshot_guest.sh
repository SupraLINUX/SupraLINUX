#!/usr/bin/env bash
# Experimental runtime one-shot selection, no ESP mutation or auto-promotion.
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
oneshot=$(read_entry LoaderEntryOneShot)
test -z "$oneshot"
case "$(cat /etc/supra-lab-deployment)" in
    staged)
        if [[ -z "$default" ]]; then
            esp=$(mktemp -d)
            trap 'umount "$esp"; rmdir "$esp"' EXIT
            mount -t vfat -o ro /dev/vda1 "$esp"
            bootctl --esp-path="$esp" set-default supra-staged.conf
            bootctl --esp-path="$esp" set-oneshot supra-layer.conf
            test "$(read_entry LoaderEntryDefault)" = supra-staged.conf
            test "$(read_entry LoaderEntryOneShot)" = supra-layer.conf
            printf '%s\n' SUPRA_ONESHOT_ARMED > /dev/ttyS0
        else
            test "$default" = supra-staged.conf
            printf '%s\n' SUPRA_ONESHOT_RETURNED > /dev/ttyS0
        fi
        ;;
    layer)
        test "$default" = supra-staged.conf
        # Successful trial does NOT promote itself.
        printf '%s\n' SUPRA_ONESHOT_CONSUMED > /dev/ttyS0
        ;;
    *) exit 1 ;;
esac
