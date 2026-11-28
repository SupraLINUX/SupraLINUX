#!/usr/bin/env bash
# Disposable guest fault checkpoint, intentionally BEFORE inventory readiness.
set -euo pipefail
test "$(findmnt -n -o FSROOT /)" = /deployments/layer
test "$(cat /etc/supra-lab-deployment)" = layer
dir=/sys/firmware/efi/efivars
guid=4a67b082-0a4c-41cf-b6c7-440b29bb8c4f
test ! -e "$dir/LoaderEntryOneShot-$guid"
test "$(tail -c +5 "$dir/LoaderEntryDefault-$guid" | iconv -f UTF-16LE -t UTF-8 | tr -d '\000')" = supra-staged.conf
printf '%s\n' SUPRA_TRIAL_INTERRUPT_POINT > /dev/ttyS0
# Host kills QEMU here; a timeout without injection is a failed experiment.
sleep 180
exit 1
