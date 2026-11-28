#!/usr/bin/env bash
# Lab-only state policy. Each writable domain has one separate subvolume.
immutable_domains=(
    'home:/home'
    'logs:/var/log'
    'cache:/var/cache'
    'systemd:/var/lib/systemd'
    'tmp:/var/tmp'
)
immutable_fstab() {
    local deployment=$1 entry
    case "$deployment" in staged|layer) ;; *) return 1 ;; esac
    printf 'LABEL=SUPRA_BTRFS_ROOT / btrfs ro,subvol=immutable/%s 0 0\n' "$deployment"
    for entry in "${immutable_domains[@]}"; do
        printf 'LABEL=SUPRA_LAB_STATE %s btrfs rw,subvol=%s 0 0\n' "${entry#*:}" "${entry%%:*}"
    done
    printf 'tmpfs /tmp tmpfs rw,nosuid,nodev,mode=1777 0 0\n'
}
