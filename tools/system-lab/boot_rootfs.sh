#!/usr/bin/env bash
# Direct kernel boot probe, not UEFI or a deployable disk image.
set -euo pipefail
target="$1"
work="$2"
out="$3"
debugfs -R "dump /boot/vmlinuz-linux-lts $work/target-kernel" "$target" 2>/dev/null
debugfs -R "dump /boot/initramfs-linux-lts.img $work/target-initrd" "$target" 2>/dev/null
test -s "$work/target-kernel"
test -s "$work/target-initrd"
python3 tools/system-lab/rootfs_evidence.py hashes "$out" "$work"
run_target() {
    local accel="$1" cpu="$2" budget="$3" logfile="$4"
    timeout "$budget" qemu-system-x86_64 -accel "$accel" -machine q35 -cpu "$cpu" -m 2048 -smp 2 \
        -display none -monitor none -serial stdio -nic none -no-reboot -snapshot \
        -kernel "$work/target-kernel" -initrd "$work/target-initrd" \
        -append 'root=LABEL=SUPRA_TARGET rootfstype=ext4 rw console=ttyS0 systemd.unit=multi-user.target' \
        -drive "file=$target,format=raw,if=virtio" \
        2>&1 | tee "$logfile"
}
accel=kvm
status=0
if bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-target-kvm.txt"; then
    run_target kvm host 180 "$out/rootfs-target-kvm-console.log" || status=$?
    if (( status != 0 )); then
        # Retry in TCG only for a known pre-boot accelerator initialization error.
        if grep -Eq 'failed to initialize kvm: (Permission denied|Operation not permitted)' "$out/rootfs-target-kvm-console.log"; then
            accel=tcg
        else
            exit "$status"
        fi
    fi
else
    accel=tcg
fi
if [[ "$accel" == tcg ]]; then
    echo "KVM target unavailable: trying explicit TCG functional boot"
    run_target tcg max 420 "$out/rootfs-target-console.log"
else
    cp "$out/rootfs-target-kvm-console.log" "$out/rootfs-target-console.log"
fi
python3 tools/system-lab/rootfs_evidence.py target "$out" --accel "$accel"
