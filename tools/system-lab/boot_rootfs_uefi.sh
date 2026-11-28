#!/usr/bin/env bash
# Firmware boots an experimental separate GPT ESP; no QEMU -kernel/-initrd.
set -euo pipefail
target="$1"
work="$2"
out="$3"
base="$4"
python3 tools/system-lab/rootfs_evidence.py hashes "$out" "$work"
debugfs -R "dump /usr/lib/systemd/boot/efi/systemd-bootx64.efi $work/bootx64.efi" "$base" 2>/dev/null
test -s "$work/bootx64.efi"
expected=$(awk '$2=="usr/lib/systemd/boot/efi/systemd-bootx64.efi" {print $1}' "$out/rootfs-efi.sha256")
[[ "$expected" =~ ^[a-f0-9]{64}$ ]]
printf '%s  %s\n' "$expected" "$work/bootx64.efi" | sha256sum -c
esp="$work/esp.fat"
gpt="$work/esp-gpt.raw"
truncate -s 256M "$esp"
mkfs.fat -F 32 -n SUPRA_ESP "$esp"
mmd -i "$esp" ::/EFI ::/EFI/BOOT ::/loader ::/loader/entries
mcopy -i "$esp" "$work/bootx64.efi" ::/EFI/BOOT/BOOTX64.EFI
mcopy -i "$esp" "$work/target-kernel" ::/vmlinuz-linux-lts
mcopy -i "$esp" "$work/target-initrd" ::/initramfs-linux-lts.img
printf 'default supra.conf\ntimeout 0\neditor no\n' > "$work/loader.conf"
cat > "$work/supra.conf" <<'CONF'
title SupraLINUX experimental UEFI
linux /vmlinuz-linux-lts
initrd /initramfs-linux-lts.img
options root=LABEL=SUPRA_TARGET rootfstype=ext4 rw console=ttyS0 systemd.unit=multi-user.target supra_uefi_probe=1
CONF
mcopy -i "$esp" "$work/loader.conf" ::/loader/loader.conf
mcopy -i "$esp" "$work/supra.conf" ::/loader/entries/supra.conf
truncate -s 260M "$gpt"
sgdisk --clear --new=1:2048:+256M --typecode=1:ef00 --change-name=1:SUPRA_ESP "$gpt"
dd if="$esp" of="$gpt" bs=512 seek=2048 conv=notrunc status=none
sgdisk --verify "$gpt" | tee "$out/rootfs-uefi-gpt.txt"
code=/usr/share/OVMF/OVMF_CODE_4M.fd
vars=/usr/share/OVMF/OVMF_VARS_4M.fd
test -s "$code"
test -s "$vars"
cp "$vars" "$work/uefi-vars.fd"
sha256sum "$code" "$vars" "$work/bootx64.efi" > "$out/rootfs-uefi-inputs.sha256"
bash tools/system-lab/rootfs_kvm_access.sh "$out/rootfs-uefi-kvm.txt"
# Target remains vda; firmware is directed to the separate ESP.
timeout 240 qemu-system-x86_64 -accel kvm -machine q35 -cpu host -m 2048 -smp 2 \
    -display none -monitor none -serial stdio -nic none -no-reboot \
    -drive "if=pflash,format=raw,readonly=on,file=$code" \
    -drive "if=pflash,format=raw,file=$work/uefi-vars.fd" \
    -drive "if=none,id=target,format=qcow2,file=$target" \
    -device virtio-blk-pci,drive=target,addr=0x5 \
    -drive "if=none,id=esp,format=raw,file=$gpt,snapshot=on" \
    -device virtio-blk-pci,drive=esp,addr=0x6,bootindex=1 \
    2>&1 | tee "$out/rootfs-uefi-console.log"
python3 tools/system-lab/rootfs_uefi_evidence.py "$out"
