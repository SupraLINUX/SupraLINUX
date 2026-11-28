#!/usr/bin/env bash
# PID 1 in disposable guest. No network device is attached.
set -u
mountpoint -q /proc || mount -t proc proc /proc
mountpoint -q /sys || mount -t sysfs sysfs /sys
mountpoint -q /dev || mount -t devtmpfs devtmpfs /dev
mountpoint -q /run || mount -t tmpfs tmpfs /run
ln -sfn /proc/self/fd /dev/fd
ln -sfn /proc/self/fd/0 /dev/stdin
ln -sfn /proc/self/fd/1 /dev/stdout
ln -sfn /proc/self/fd/2 /dev/stderr
exec >/dev/ttyS0 2>&1
echo "SUPRA_BUILD_VM_READY"
status=0
bash /build.sh || status=$?
printf '%s\n' "$status" > /out/rootfs-vm-status.txt
sync
echo "SUPRA_BUILD_VM_EXIT=$status"
poweroff -f
# If the guest poweroff fails, do not allow PID 1 to exit.
while :; do sleep 60; done
