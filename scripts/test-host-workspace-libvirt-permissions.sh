#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="${ROOT}/scripts/supralinux-vm-workspace-broker.sh"

python3 - "${BROKER}" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text()

required = [
    'install -d -m 0700 "${RUN_DIR}"',
    'LIBVIRT_QEMU_GROUP="$(id -gn "${LIBVIRT_QEMU_USER}")"',
    'chgrp "${LIBVIRT_QEMU_GROUP}" "${RUN_DIR}"',
    'chmod 0710 "${RUN_DIR}"',
    'chgrp "${LIBVIRT_QEMU_GROUP}" "${OVERLAY}"',
    'chmod 0660 "${OVERLAY}"',
]
for token in required:
    if token not in text:
        raise SystemExit(f"missing workspace libvirt traversal contract: {token}")

run_pos = text.index('RUN_DIR="${STATE_ROOT}/${RUN_ID}"')
group_pos = text.index('LIBVIRT_QEMU_GROUP="$(id -gn "${LIBVIRT_QEMU_USER}")"', run_pos)
run_chgrp = text.index('chgrp "${LIBVIRT_QEMU_GROUP}" "${RUN_DIR}"', group_pos)
run_mode = text.index('chmod 0710 "${RUN_DIR}"', run_chgrp)
overlay_create = text.index('qemu-img create ', run_mode)
overlay_group = text.index('chgrp "${LIBVIRT_QEMU_GROUP}" "${OVERLAY}"', overlay_create)
overlay_mode = text.index('chmod 0660 "${OVERLAY}"', overlay_group)
virt_install = text.index('virt-install ', overlay_mode)

if not (run_pos < group_pos < run_chgrp < run_mode < overlay_create < overlay_group < overlay_mode < virt_install):
    raise SystemExit("workspace directory/file permissions must be established before virt-install")

if 'chmod 0777 "${RUN_DIR}"' in text or 'chmod -R 0777' in text:
    raise SystemExit("workspace broker must not make VM state world-writable")

print("Workspace libvirt traversal contract: PASS")
PY
