#!/usr/bin/env bash
# Reuse one powered-off, verified raw image in separate disposable QCOW2 overlays.
# No package or disk image is published; no persistent runner state is required.
set -euo pipefail
command -v qemu-img >/dev/null || { echo 'INFRA_INVALID: qemu-img unavailable' >&2; exit 127; }
base=$(realpath "$1")
work=$(realpath "$2")
out=$(realpath "$3")
test -f "$base"
test -f "$work/target-kernel"
test -f "$work/target-initrd"
chmod a-w "$base"
sha256sum "$base" > "$out/rootfs-checkpoint.sha256"
for probe in uefi btrfs; do
    mkdir "$work/$probe"
    cp "$work/target-kernel" "$work/target-initrd" "$work/$probe/"
    qemu-img create -q -f qcow2 -F raw -b "$base" "$work/$probe/target.qcow2"
    qemu-img info --output=json "$work/$probe/target.qcow2" > "$out/rootfs-$probe-overlay.json"
done
# EFI extraction still requires the original ext4 image, not the overlay container.
# Each probe receives a distinct work directory, console log and writable disk.
run_probe() {
    local probe=$1
    bash "tools/system-lab/boot_rootfs_${probe}.sh" \
        "$work/$probe/target.qcow2" "$work/$probe" "$out" "$base"
}
available=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
mode=sequential
if [[ "$available" =~ ^[0-9]+$ ]] && (( available >= 5242880 && $(nproc) >= 2 )); then
    mode=parallel
fi
start=$(date +%s)
uefi_rc=0
btrfs_rc=0
if [[ "$mode" == parallel ]]; then
    run_probe uefi > "$out/rootfs-uefi-probe.log" 2>&1 &
    uefi_pid=$!
    run_probe btrfs > "$out/rootfs-btrfs-probe.log" 2>&1 &
    btrfs_pid=$!
    wait "$uefi_pid" || uefi_rc=$?
    wait "$btrfs_pid" || btrfs_rc=$?
else
    run_probe uefi > "$out/rootfs-uefi-probe.log" 2>&1 || uefi_rc=$?
    run_probe btrfs > "$out/rootfs-btrfs-probe.log" 2>&1 || btrfs_rc=$?
fi
cat "$out/rootfs-uefi-probe.log" "$out/rootfs-btrfs-probe.log"
# Check the base bytes after both isolated probes even when a probe fails.
sha256sum -c "$out/rootfs-checkpoint.sha256"
printf '{"schema_version":1,"mode":"%s","elapsed_seconds":%s,"uefi_exit":%s,"btrfs_exit":%s,"base_unchanged":true,"cross_run_reuse":false}\n' \
    "$mode" "$(($(date +%s)-start))" "$uefi_rc" "$btrfs_rc" > "$out/rootfs-checkpoint-report.json"
cat "$out/rootfs-checkpoint-report.json"
(( uefi_rc == 0 && btrfs_rc == 0 ))
