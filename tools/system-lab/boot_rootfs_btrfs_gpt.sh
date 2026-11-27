#!/usr/bin/env bash
# Single disposable GPT disk: verified systemd-boot, ESP and prepared Btrfs root.
set -euo pipefail
base=$(realpath "$1")
source=$(realpath "$2")
out=$(realpath "$3")
work="$source/gpt"
mkdir "$work"
(cd "$source" && sha256sum -c boot.sha256)
sha256sum "$source/root.raw" > "$out/rootfs-btrfs-gpt-source.sha256"
debugfs -R "dump /usr/lib/systemd/boot/efi/systemd-bootx64.efi $work/bootx64.efi" "$base" 2>/dev/null
expected=$(awk '$2=="usr/lib/systemd/boot/efi/systemd-bootx64.efi" {print $1}' "$out/rootfs-efi.sha256")
[[ "$expected" =~ ^[a-f0-9]{64}$ ]]
printf '%s  %s\n' "$expected" "$work/bootx64.efi" | sha256sum -c

# 512 MiB ESP leaves room for the non-autodetected initramfs.
esp="$work/esp.fat"
disk="$work/gpt.raw"
esp_start=2048
esp_sectors=1048576
root_start=$((esp_start+esp_sectors))
root_bytes=$(stat -c %s "$source/root.raw")
(( root_bytes > 0 && root_bytes % 512 == 0 ))
root_end=$((root_start+root_bytes/512-1))
truncate -s "$((esp_sectors*512))" "$esp"
mkfs.fat -F 32 -n SUPRA_ESP "$esp"
mmd -i "$esp" ::/EFI ::/EFI/BOOT ::/loader ::/loader/entries
mcopy -i "$esp" "$work/bootx64.efi" ::/EFI/BOOT/BOOTX64.EFI
mcopy -i "$esp" "$source/target-kernel" ::/vmlinuz-linux-lts
mcopy -i "$esp" "$source/target-initrd" ::/initramfs-linux-lts.img
printf 'default supra.conf\ntimeout 0\neditor no\n' > "$work/loader.conf"
cat > "$work/supra.conf" <<'CONF'
title SupraLINUX experimental single-disk Btrfs
linux /vmlinuz-linux-lts
initrd /initramfs-linux-lts.img
options root=LABEL=SUPRA_BTRFS_ROOT rootfstype=btrfs rootflags=subvol=deployments/staged rw console=ttyS0 systemd.unit=multi-user.target systemd.mask=serial-getty@ttyS0.service supra_btrfs_root_probe=1 supra_uefi_probe=1 supra_btrfs_gpt_probe=1
CONF
mcopy -i "$esp" "$work/loader.conf" ::/loader/loader.conf
mcopy -i "$esp" "$work/supra.conf" ::/loader/entries/supra.conf
# Reserve aligned partition starts and space for backup GPT. No host mounts.
truncate -s "$(((root_end+1+2048)*512))" "$disk"
sgdisk --clear --new=1:$esp_start:$((root_start-1)) --typecode=1:ef00 --change-name=1:SUPRA_ESP \
    --new=2:$root_start:$root_end --typecode=2:8300 --change-name=2:SUPRA_ROOT "$disk"
# Sparse copying into a fresh zero-filled partition preserves sparse allocation.
dd if="$esp" of="$disk" bs=1M seek=1 conv=notrunc,sparse status=none
dd if="$source/root.raw" of="$disk" bs=1M seek=$((root_start/2048)) conv=notrunc,sparse status=none
sgdisk --verify "$disk" | tee "$out/rootfs-btrfs-gpt-verify.txt"
sgdisk --print "$disk" > "$out/rootfs-btrfs-gpt-layout.txt"
# Independently read the actual partition bytes before QEMU boots.
esp_hash=$(sha256sum "$esp" | cut -d' ' -f1)
root_hash=$(cut -d' ' -f1 "$out/rootfs-btrfs-gpt-source.sha256")
test "$(dd if="$disk" bs=1M skip=1 count=512 status=none | sha256sum | cut -d' ' -f1)" = "$esp_hash"
test "$(dd if="$disk" bs=1M skip=$((root_start/2048)) count=$((root_bytes/1048576)) status=none | sha256sum | cut -d' ' -f1)" = "$root_hash"
sha256sum -c "$out/rootfs-btrfs-gpt-source.sha256"
sha256sum "$disk" > "$out/rootfs-btrfs-gpt-image.sha256"
code=/usr/share/OVMF/OVMF_CODE_4M.fd
vars=/usr/share/OVMF/OVMF_VARS_4M.fd
test -s "$code"
test -s "$vars"
cp "$vars" "$work/uefi-vars.fd"
sha256sum "$code" "$vars" "$work/bootx64.efi" > "$out/rootfs-btrfs-gpt-uefi.sha256"
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-btrfs-gpt-kvm.txt"
status=0
# No -kernel/-initrd, no separate root disk. Snapshot mode preserves base bytes.
timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot \
    -drive "if=pflash,format=raw,readonly=on,file=$code" \
    -drive "if=pflash,format=raw,file=$work/uefi-vars.fd" \
    -drive "if=none,id=target,format=raw,file=$disk,snapshot=on" \
    -device virtio-blk-pci,drive=target,addr=0x5,bootindex=1 \
    2>&1 | tee "$out/rootfs-btrfs-gpt-console.log" || status=$?
sha256sum -c "$out/rootfs-btrfs-gpt-image.sha256"
(( status == 0 ))
python3 tools/system-lab/rootfs_btrfs_gpt_evidence.py "$out"
