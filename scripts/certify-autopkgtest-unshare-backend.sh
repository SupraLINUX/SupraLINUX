#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${ROOT}/.work/autopkgtest-unshare-certification"
EVIDENCE="${ROOT}/evidence/runner-contract/autopkgtest-unshare-certification"
FIXTURE="${WORK}/fixture"
PKGROOT="${WORK}/pkgroot"
DEB="${WORK}/supralinux-autopkgtest-backend-fixture_1.0_all.deb"
ROOTFS="${WORK}/resolute-amd64.tar"
QEMU_IMAGE="${AUTOPKGTEST_QEMU_IMAGE:-/var/lib/supralinux/autopkgtest/resolute-amd64.img}"
MIRROR="${SBUILD_MIRROR:-https://archive.ubuntu.com/ubuntu}"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${FIXTURE}/debian/tests" "${PKGROOT}/DEBIAN"     "${PKGROOT}/usr/share/supralinux-autopkgtest-backend-fixture" "${EVIDENCE}"

for command_name in autopkgtest autopkgtest-virt-unshare dpkg-deb python3 unshare; do
    command -v "${command_name}" >/dev/null
done
unshare --user --map-auto true
test -f "${QEMU_IMAGE}"
test "$(systemd-detect-virt --vm)" = "kvm"

python3 "${ROOT}/scripts/prepare-milestone-sbuild-rootfs.py" drkonqi     --output "${ROOTFS}"     --evidence "${EVIDENCE}/rootfs-admission.json"     --mirror "${MIRROR}"     --tls-ca-bundle /etc/ssl/certs/ca-certificates.crt

cat > "${FIXTURE}/debian/control" <<'EOF'
Source: supralinux-autopkgtest-backend-fixture
Section: misc
Priority: optional
Maintainer: SupraLINUX <noreply@invalid>
Standards-Version: 4.7.2
Rules-Requires-Root: no

Package: supralinux-autopkgtest-backend-fixture
Architecture: all
Description: SupraLINUX autopkgtest backend certification fixture
 Synthetic package used only to compare authoritative autopkgtest backends.
EOF

cat > "${FIXTURE}/debian/changelog" <<'EOF'
supralinux-autopkgtest-backend-fixture (1.0) resolute; urgency=medium

  * Infrastructure certification fixture.

 -- SupraLINUX <noreply@invalid>  Mon, 27 Oct 2026 00:00:00 +0000
EOF

cat > "${FIXTURE}/debian/tests/control" <<'EOF'
Tests: installed-payload
Depends: @, python3

Tests: needs-root
Depends: @, python3, apt
Restrictions: needs-root
EOF

cat > "${FIXTURE}/debian/tests/installed-payload" <<'EOF'
#!/bin/sh
set -eu
test "$(dpkg-query -W -f='${Status}' supralinux-autopkgtest-backend-fixture)" = "install ok installed"
test "$(cat /usr/share/supralinux-autopkgtest-backend-fixture/marker)" = "SUPRALINUX_AUTOPKGTEST_BACKEND_FIXTURE"
test -n "${AUTOPKGTEST_TMP:-}"
python3 - <<'PY'
import platform
assert platform.machine() == "x86_64"
print("fixture_python=PASS")
PY
EOF

cat > "${FIXTURE}/debian/tests/needs-root" <<'EOF'
#!/bin/sh
set -eu
test "$(id -u)" = "0"
test -d /root
touch /root/supralinux-autopkgtest-needs-root
apt-cache policy python3 >/dev/null
echo "fixture_needs_root=PASS"
EOF
chmod 0755 "${FIXTURE}/debian/tests/installed-payload" "${FIXTURE}/debian/tests/needs-root"

cat > "${PKGROOT}/DEBIAN/control" <<'EOF'
Package: supralinux-autopkgtest-backend-fixture
Source: supralinux-autopkgtest-backend-fixture
Version: 1.0
Architecture: all
Maintainer: SupraLINUX <noreply@invalid>
Description: SupraLINUX autopkgtest backend certification fixture
EOF
printf '%s\n' 'SUPRALINUX_AUTOPKGTEST_BACKEND_FIXTURE'     > "${PKGROOT}/usr/share/supralinux-autopkgtest-backend-fixture/marker"
dpkg-deb --build --root-owner-group "${PKGROOT}" "${DEB}"     > "${EVIDENCE}/fixture-build.log"

python3 "${ROOT}/scripts/autopkgtest-backend-policy.py"     "${FIXTURE}/debian/tests/control"     > "${EVIDENCE}/fixture-backend-policy.json"

run_backend() {
    local backend="$1"
    local output="${EVIDENCE}/${backend}"
    local start end rc
    mkdir -p "${output}"
    start="$(date +%s)"
    set +e
    if [[ "${backend}" == "qemu" ]]; then
        autopkgtest "${FIXTURE}/" "${DEB}"             --output-dir="${output}" --             qemu --qemu-command="${ROOT}/scripts/qemu-kvm-required.sh"             --qemu-architecture=x86_64 --cpus=2 --ram-size=2048 "${QEMU_IMAGE}"             > "${EVIDENCE}/qemu.log" 2>&1
        rc=$?
    else
        autopkgtest "${FIXTURE}/" "${DEB}"             --output-dir="${output}" --             unshare --arch amd64 --tarball "${ROOTFS}"             > "${EVIDENCE}/unshare.log" 2>&1
        rc=$?
    fi
    set -e
    end="$(date +%s)"
    printf 'exit_code=%s\nduration_seconds=%s\n' "${rc}" "$((end-start))"         > "${EVIDENCE}/${backend}-result.txt"
    return "${rc}"
}

run_backend qemu
run_backend unshare

python3 - "${EVIDENCE}" "${ROOTFS}" "${QEMU_IMAGE}" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

evidence = Path(sys.argv[1])
rootfs = Path(sys.argv[2])
qemu_image = Path(sys.argv[3])
expected = {"installed-payload", "needs-root"}

def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def parse_summary(path):
    rows = {}
    for raw in path.read_text().splitlines():
        fields = raw.split()
        if len(fields) < 2:
            continue
        name, status = fields[0], fields[1]
        if status in {"PASS", "FAIL", "SKIP", "FLAKY"}:
            if name in rows:
                raise SystemExit(f"duplicate autopkgtest result: {name}")
            rows[name] = status
    if set(rows) != expected:
        raise SystemExit(f"unexpected autopkgtest set in {path}: {rows}")
    if set(rows.values()) != {"PASS"}:
        raise SystemExit(f"non-PASS autopkgtest result in {path}: {rows}")
    return rows

def read_kv(path):
    return dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if "=" in line
    )

qemu = parse_summary(evidence / "qemu" / "summary")
unshare = parse_summary(evidence / "unshare" / "summary")
if qemu != unshare:
    raise SystemExit(f"backend result mismatch: qemu={qemu} unshare={unshare}")

qemu_meta = read_kv(evidence / "qemu-result.txt")
unshare_meta = read_kv(evidence / "unshare-result.txt")
qemu_seconds = int(qemu_meta["duration_seconds"])
unshare_seconds = int(unshare_meta["duration_seconds"])
speedup = None
if unshare_seconds > 0:
    speedup = qemu_seconds / unshare_seconds

result = {
    "schema": 1,
    "state": "PASS",
    "scope": "autopkgtest-backend-mechanism-certification",
    "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip(),
    "outer_environment": {
        "os": "Ubuntu 26.04",
        "virtualization": "kvm",
        "architecture": os.uname().machine,
    },
    "fixture": {
        "package": "supralinux-autopkgtest-backend-fixture",
        "version": "1.0",
        "tests": sorted(expected),
        "restrictions": ["needs-root"],
    },
    "qemu": {
        "state": "PASS",
        "results": qemu,
        "duration_seconds": qemu_seconds,
        "image_sha256": sha256(qemu_image),
    },
    "unshare": {
        "state": "PASS",
        "results": unshare,
        "duration_seconds": unshare_seconds,
        "rootfs_sha256": sha256(rootfs),
    },
    "normalized_results_equal": True,
    "speedup_qemu_over_unshare": speedup,
    "package_attempt_consumed": False,
    "sbuild_invoked": False,
    "production_backend_changed": False,
    "next_step": "one-real-package-canary-before-default-rollout",
}
(evidence / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
PY

echo "SUPRALINUX_AUTOPKGTEST_UNSHARE_CERTIFICATION=PASS"
