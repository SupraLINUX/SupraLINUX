#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
test "$(findmnt -n -o FSTYPE /)" = btrfs
device=/dev/vda
if grep -qw supra_layer_uefi=1 /proc/cmdline; then
    device=/dev/vda2
    test -d /sys/firmware/efi
    test "$(cat /sys/firmware/efi/fw_platform_size)" = 64
    test "$(lsblk -dn -o PTTYPE /dev/vda)" = gpt
    test "$(lsblk -dn -o PARTTYPE /dev/vda1)" = c12a7328-f81f-11d2-ba4b-00a0c93ec93b
    grep -qw systemd.gpt_auto=0 /proc/cmdline
    if findmnt -rn -S /dev/vda1; then exit 1; fi
    esp=$(mktemp -d)
    mount -t vfat -o ro /dev/vda1 "$esp"
    cmp "$esp/vmlinuz-linux-lts" /boot/vmlinuz-linux-lts
    cmp "$esp/initramfs-linux-lts.img" /boot/initramfs-linux-lts.img
    # Match the selected Type #1 entry to the actual deployment.
    # EFI variable is four attribute bytes followed by UTF-16LE text.
    selected=$(tail -c +5 /sys/firmware/efi/efivars/LoaderEntrySelected-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f | iconv -f UTF-16LE -t UTF-8 | tr -d '\000')
    test "$selected" = "supra-$(cat /etc/supra-lab-deployment).conf"
    umount "$esp"
    rmdir "$esp"
    printf '%s\n' SUPRA_LAYER_UEFI_READY > /dev/ttyS0
fi
test "$(findmnt -n -o SOURCE / | cut -d '[' -f1)" = "$device"
test "$(blkid -s LABEL -o value "$device")" = SUPRA_BTRFS_ROOT
test "$(btrfs property get -ts / ro)" = ro=false
case "$(cat /etc/supra-lab-deployment)" in
    staged)
        test "$(findmnt -n -o FSROOT /)" = /deployments/staged
        test ! -e /usr/bin/tree
        if pacman -Q tree; then exit 1; fi
        pacman -Q | sha256sum --check /etc/supra-lab-inventory.sha256
        printf '%s\n' SUPRA_LAYER_PREVIOUS_READY > /dev/ttyS0
        ;;
    layer)
        test "$(findmnt -n -o FSROOT /)" = /deployments/layer
        pacman -Q | sha256sum --check /etc/supra-lab-inventory.sha256
        pacman -Q tree
        /usr/bin/tree --version
        printf '%s\n' SUPRA_LAYER_NEW_READY > /dev/ttyS0
        ;;
    *) exit 1 ;;
esac

if grep -qw supra_layer_oneshot=1 /proc/cmdline; then
    /usr/local/libexec/supra-layer-oneshot
fi

if grep -qw supra_layer_promotion=1 /proc/cmdline; then
    /usr/local/libexec/supra-layer-promotion
fi
