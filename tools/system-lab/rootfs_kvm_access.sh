#!/usr/bin/env bash
# GitHub disposable runner only. Reapply scoped user ACL after possible udev changes.
set -euo pipefail
out="$1"
{
    echo "Before:"
    id
    if [[ ! -c /dev/kvm ]]; then
        echo "KVM device absent"
        exit 1
    fi
    stat -c '%A %U:%G %t:%T' /dev/kvm
    getfacl -p /dev/kvm
    sudo setfacl -m "u:$(id -un):rw" /dev/kvm
    echo "After:"
    stat -c '%A %U:%G %t:%T' /dev/kvm
    getfacl -p /dev/kvm
    # Open the actual device as the runner user (not root).
    python3 - <<'PY'
import os
import fcntl
fd = os.open("/dev/kvm", os.O_RDWR | os.O_CLOEXEC)
try:
    version = fcntl.ioctl(fd, 0xAE00, 0)  # KVM_GET_API_VERSION
    if version != 12:
        raise RuntimeError(f"Unexpected KVM API {version}")
    print(f"KVM API {version} available")
finally:
    os.close(fd)
PY
} 2>&1 | tee "$out"
