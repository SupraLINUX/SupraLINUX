#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${ROOT}/evidence/runner-contract/autopkgtest-unshare-real-canary"
WORK="${ROOT}/.work/autopkgtest-unshare-real-canary"
ROOTFS="${ROOT}/.work/autopkgtest-unshare-certification/resolute-amd64.tar"
QEMU_IMAGE="${AUTOPKGTEST_QEMU_IMAGE:-/var/lib/supralinux/autopkgtest/resolute-amd64.img}"
NODE="ocean-sound-theme"
VERSION="6.7.5-0supralinux1"
ARTIFACT_ID="11317894456"
ARTIFACT_SHA256="9243fe8efcf9a24b659ed3ec76954cca4263a08dd71e7613f12f20b57cddc2f2"
ARTIFACT_SOURCE_COMMIT="d999e3f9cdf28bc52a50587b3fc157f4f8aa2ac9"
API_VERSION="2022-11-28"

: "${GITHUB_TOKEN:?GITHUB_TOKEN is required for retained artifact read access}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}/artifact" "${EVIDENCE}"

for command_name in autopkgtest curl python3 sha256sum; do
    command -v "${command_name}" >/dev/null
done
test -f "${ROOTFS}"
test -f "${QEMU_IMAGE}"
test "$(systemd-detect-virt --vm)" = "kvm"

ZIP="${WORK}/artifact.zip"
DOWNLOAD_HEADERS="${WORK}/artifact-download.headers"
curl --fail --silent --show-error \
    --dump-header "${DOWNLOAD_HEADERS}" \
    --output /dev/null \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: ${API_VERSION}" \
    "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/artifacts/${ARTIFACT_ID}/zip"
SIGNED_URL="$(python3 - "${DOWNLOAD_HEADERS}" <<'PY'
import sys
from pathlib import Path
from urllib.parse import urlsplit

location = None
for raw in Path(sys.argv[1]).read_text(errors="replace").splitlines():
    if raw.lower().startswith("location:"):
        location = raw.split(":", 1)[1].strip()
if not location:
    raise SystemExit("GitHub artifact API did not return a signed Location header")
parsed = urlsplit(location)
if parsed.scheme != "https" or not parsed.hostname:
    raise SystemExit("GitHub artifact redirect is not an HTTPS URL")
if parsed.hostname == "api.github.com":
    raise SystemExit("GitHub artifact redirect unexpectedly targets the API host")
print(location)
PY
)"
curl --fail --location --silent --show-error \
    --output "${ZIP}" "${SIGNED_URL}"
unset SIGNED_URL
printf '%s  %s\n' "${ARTIFACT_SHA256}" "${ZIP}" | sha256sum --check --strict \
    > "${EVIDENCE}/artifact-sha256.log"

python3 - "${ZIP}" "${WORK}/artifact" <<'PY'
import sys
import zipfile
from pathlib import Path, PurePosixPath

archive = Path(sys.argv[1])
output = Path(sys.argv[2]).resolve()
with zipfile.ZipFile(archive) as handle:
    for info in handle.infolist():
        relative = PurePosixPath(info.filename)
        if relative.is_absolute() or ".." in relative.parts:
            raise SystemExit(f"unsafe artifact member: {info.filename}")
        target = (output / Path(*relative.parts)).resolve()
        if not target.is_relative_to(output):
            raise SystemExit(f"artifact member escapes output: {info.filename}")
    handle.extractall(output)
PY

python3 - "${ROOT}" "${WORK}/artifact" "${NODE}" "${VERSION}" "${ARTIFACT_SOURCE_COMMIT}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
artifact = Path(sys.argv[2])
node, version, source_commit = sys.argv[3:]

result = json.loads((artifact / "result.json").read_text())
if not (
    result["state"] == "PASS"
    and result["node"] == node
    and result["version"] == version
    and result["source_commit"] == source_commit
    and result["package_attempt_consumed"] is True
    and result["sbuild_result"] == "PASS"
    and result["autopkgtest_result"] == "PASS"
):
    raise SystemExit(f"retained PASS identity mismatch: {result}")

contract = json.loads((artifact / "build-contract.json").read_text())
record = contract["nodes"][node]
if record["version"] != version:
    raise SystemExit("retained build-contract version mismatch")

packaging = root / record["packaging_path"]
for relative, expected in record["packaging_sha256"].items():
    path = packaging / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"current reviewed packaging file missing: {relative}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"current reviewed packaging drift: {relative}")
PY

PKG_DIR="${WORK}/artifact/packages"
DSC="${PKG_DIR}/ocean-sound-theme_6.7.5-0supralinux1.dsc"
DEB="${PKG_DIR}/ocean-sound-theme_6.7.5-0supralinux1_all.deb"
test -f "${DSC}"
test -f "${DEB}"

for source_file in \
    "${PKG_DIR}/ocean-sound-theme_6.7.5.orig.tar.xz" \
    "${PKG_DIR}/ocean-sound-theme_6.7.5-0supralinux1.debian.tar.xz"; do
    test -f "${source_file}"
done

SETUP="$(python3 "${ROOT}/scripts/plasma-package-testing.py" setup "${NODE}" --https-transport)"

run_backend() {
    local backend="$1"
    local output="${EVIDENCE}/${backend}"
    local start end rc
    mkdir -p "${output}"
    start="$(date +%s)"
    set +e
    if [[ "${backend}" == "qemu" ]]; then
        autopkgtest "${DSC}" "${DEB}" \
            --setup-commands="${SETUP}" \
            --output-dir="${output}" -- \
            qemu --qemu-command="${ROOT}/scripts/qemu-kvm-required.sh" \
            --qemu-architecture=x86_64 --cpus=2 --ram-size=2048 "${QEMU_IMAGE}" \
            > "${EVIDENCE}/qemu.log" 2>&1
        rc=$?
    else
        autopkgtest "${DSC}" "${DEB}" \
            --setup-commands="${SETUP}" \
            --output-dir="${output}" -- \
            unshare --arch amd64 --tarball "${ROOTFS}" \
            > "${EVIDENCE}/unshare.log" 2>&1
        rc=$?
    fi
    set -e
    end="$(date +%s)"
    printf 'exit_code=%s\nduration_seconds=%s\n' "${rc}" "$((end-start))" \
        > "${EVIDENCE}/${backend}-result.txt"
    return "${rc}"
}

QEMU_RC=0
UNSHARE_RC=0
run_backend qemu || QEMU_RC=$?
run_backend unshare || UNSHARE_RC=$?
printf 'qemu_exit_code=%s\nunshare_exit_code=%s\n' "${QEMU_RC}" "${UNSHARE_RC}" \
    > "${EVIDENCE}/backend-exit-codes.txt"
if (( QEMU_RC != 0 || UNSHARE_RC != 0 )); then
    printf 'real-package backend canary failed: qemu=%s unshare=%s\n' \
        "${QEMU_RC}" "${UNSHARE_RC}" >&2
    exit 20
fi

python3 - "${EVIDENCE}" "${ARTIFACT_ID}" "${ARTIFACT_SHA256}" "${NODE}" "${VERSION}" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

evidence = Path(sys.argv[1])
artifact_id, artifact_sha256, node, version = sys.argv[2:]
expected = {"sound-resources", "ubuntu-upgrade"}

def parse_summary(path):
    rows = {}
    for raw in path.read_text().splitlines():
        fields = raw.split()
        if len(fields) < 2:
            continue
        if fields[1] in {"PASS", "FAIL", "SKIP", "FLAKY"}:
            rows[fields[0]] = fields[1]
    if set(rows) != expected or set(rows.values()) != {"PASS"}:
        raise SystemExit(f"unexpected real canary results in {path}: {rows}")
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
    raise SystemExit(f"real canary backend result mismatch: {qemu} != {unshare}")

qemu_seconds = int(read_kv(evidence / "qemu-result.txt")["duration_seconds"])
unshare_seconds = int(read_kv(evidence / "unshare-result.txt")["duration_seconds"])
payload = {
    "schema": 1,
    "state": "PASS",
    "scope": "historical-pass-real-package-autopkgtest-backend-canary",
    "node": node,
    "version": version,
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "retained_artifact_id": int(artifact_id),
    "retained_artifact_sha256": artifact_sha256,
    "qemu": {"state": "PASS", "results": qemu, "duration_seconds": qemu_seconds},
    "unshare": {"state": "PASS", "results": unshare, "duration_seconds": unshare_seconds},
    "normalized_results_equal": True,
    "speedup_qemu_over_unshare": (
        qemu_seconds / unshare_seconds if unshare_seconds else None
    ),
    "package_attempt_consumed": False,
    "sbuild_invoked": False,
    "candidate_rebuilt": False,
    "canonical_package_state_effect": "none",
    "next_step": "backend-default-rollout-review",
}
(evidence / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(json.dumps(payload, indent=2, sort_keys=True))
PY

echo "SUPRALINUX_AUTOPKGTEST_UNSHARE_REAL_CANARY=PASS"
