#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
test "$(findmnt -n -o FSTYPE /)" = btrfs
test "$(findmnt -n -o SOURCE / | cut -d '[' -f1)" = /dev/vda
test "$(blkid -s LABEL -o value /dev/vda)" = SUPRA_BTRFS_ROOT
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
