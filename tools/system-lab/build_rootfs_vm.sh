#!/usr/bin/env bash
# Assemble the VM disk from the pinned OCI builder; run all hooks in the guest.
set -euo pipefail
work=$(mktemp -d)
cid=
cleanup() {
    if [[ -n "$cid" ]]; then docker rm -f "$cid" >/dev/null 2>&1 || true; fi
    sudo rm -rf -- "$work"
}
trap cleanup EXIT
builder=$(head -n 1 evidence/build-input.txt)
[[ "$builder" =~ ^docker\.io/library/archlinux@sha256:[a-f0-9]{64}$ ]]
stage="$work/stage"
mkdir -p "$stage"
cid=$(docker create --platform linux/amd64 "$builder" /bin/true)
# OCI content is digest-pinned; never execute its scripts on the host.
docker export "$cid" | sudo tar --numeric-owner -xpf - -C "$stage"
docker rm "$cid" >/dev/null
cid=
sudo install -d -m 0755 "$stage/packages" "$stage/out"
sudo cp -a packages/. "$stage/packages/"
sudo install -m 0644 evidence/rootfs-input.tsv "$stage/out/rootfs-input.tsv"
sudo install -m 0755 tools/system-lab/build_rootfs.sh "$stage/build.sh"
sudo install -m 0755 tools/system-lab/rootfs_guest_init.sh "$stage/supra-init"
sudo install -m 0644 tools/system-lab/rootfs_boot_probe.service "$stage/boot-probe.service"
sudo install -m 0755 tools/system-lab/rootfs_boot_probe.sh "$stage/boot-probe.sh"
sudo install -m 0755 tools/system-lab/rootfs_btrfs_guest.sh "$stage/btrfs-probe.sh"
sudo install -m 0755 tools/system-lab/rootfs_btrfs_prepare_guest.sh "$stage/btrfs-prepare.sh"
disk="$work/builder.ext4"
truncate -s 10G "$disk"
sudo mke2fs -q -t ext4 -F -d "$stage" "$disk"
sudo chown "$(id -u):$(id -g)" "$disk"
sudo rm -rf -- "$stage"
target="$work/target.ext4"
truncate -s 6G "$target"
mke2fs -q -F -t ext4 -L SUPRA_TARGET "$target"
# Ubuntu kernel/initramfs is transport for the build VM, not the target kernel.
kernel=$(find /boot -maxdepth 1 -name 'vmlinuz-*-generic' -type f | sort -V | tail -n 1)
test -n "$kernel"
initrd="/boot/initrd.img-${kernel##*/vmlinuz-}"
test -f "$initrd"
sudo install -m 0644 "$kernel" "$work/kernel"
sudo install -m 0644 "$initrd" "$work/initrd"
printf '%s\n' "$kernel" > evidence/rootfs-builder-kernel.txt
bash tools/system-lab/rootfs_kvm_access.sh evidence/rootfs-builder-kvm.txt
status=0
timeout 1200 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 4096 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot \
    -kernel "$work/kernel" -initrd "$work/initrd" \
    -append 'root=/dev/vda rootfstype=ext4 rw console=ttyS0 init=/supra-init' \
    -drive "file=$disk,format=raw,if=virtio,index=0" \
    -drive "file=$target,format=raw,if=virtio,index=1" \
    2>&1 | tee evidence/rootfs-vm-console.log || status=$?
# Extract only named evidence files after the guest exits, never mount the disk on host.
for name in rootfs-vm-status.txt rootfs-install.log installed-packages.txt rootfs-boot-files.sha256 rootfs-efi.sha256; do
    debugfs -R "dump /out/$name evidence/$name" "$disk" 2>/dev/null || true
done
(( status == 0 ))
python3 tools/system-lab/rootfs_evidence.py builder evidence
test -s evidence/installed-packages.txt
test -s evidence/rootfs-boot-files.sha256

# Validate the build closure BEFORE starting a separate target-kernel VM.
python3 tools/system-lab/prepare_rootfs.py distribution/images/experimental-base.json evidence comparison --check-installed
bash tools/system-lab/boot_rootfs.sh "$target" "$work" evidence

# Reuse the verified powered-off root for isolated post-build probes.
bash tools/system-lab/run_rootfs_probes.sh "$target" "$work" evidence

# New experimental root layout, independent of the existing ext4 regressions.
bash tools/system-lab/boot_rootfs_btrfs_root.sh "$target" "$work" evidence
