#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="${1:-}"
[[ -n "${NODE}" ]] || { printf 'Usage: %s NODE\n' "$0" >&2; exit 64; }

WORK="${ROOT}/.work/fast-package-preflight/${NODE}"
EVIDENCE="${ROOT}/evidence/fast-package-preflight/${NODE}"
rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}" "${EVIDENCE}"

for command_name in autopkgtest curl dpkg-source gpg gpgv python3 sha256sum; do
    command -v "${command_name}" >/dev/null
done

python3 "${ROOT}/scripts/validate_plasma_package_build.py"
python3 "${ROOT}/scripts/test-reviewed-package-contract.py"     > "${EVIDENCE}/reviewed-package-contract.log"

mapfile -t RECORD < <(python3 - "${ROOT}" "${NODE}" <<'PY'
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
node = sys.argv[2]
manifest = json.loads((root / "manifests/kde-plasma-package-build.json").read_text())
record = manifest["nodes"][node]
print(record["version"])
print(record["upstream_url"])
print(record["upstream_sha256"])
print(record["signature_sha256"])
print(record["packaging_path"])
print(record.get("signing_key_path", ""))
print(record.get("signing_fingerprint", ""))
PY
)
[[ ${#RECORD[@]} == 7 ]]
VERSION="${RECORD[0]}"
SOURCE_URL="${RECORD[1]}"
SOURCE_SHA256="${RECORD[2]}"
SIGNATURE_SHA256="${RECORD[3]}"
PACKAGING_PATH="${RECORD[4]}"
SIGNING_KEY_PATH="${RECORD[5]}"
SIGNING_FINGERPRINT="${RECORD[6]}"

TARBALL="${WORK}/upstream.tar.xz"
curl --fail --location --retry 3 --connect-timeout 20 --max-time 180     --output "${TARBALL}" "${SOURCE_URL}"
curl --fail --location --retry 3 --connect-timeout 20 --max-time 180     --output "${TARBALL}.sig" "${SOURCE_URL}.sig"
printf '%s  %s\n%s  %s\n'     "${SOURCE_SHA256}" "${TARBALL}"     "${SIGNATURE_SHA256}" "${TARBALL}.sig"     | sha256sum --check --strict     > "${EVIDENCE}/source-digests.log"

if [[ -n "${SIGNING_KEY_PATH}" ]]; then
    KEY="${ROOT}/${PACKAGING_PATH}/${SIGNING_KEY_PATH}"
    [[ -f "${KEY}" ]]
else
    python3 "${ROOT}/scripts/run-kde-plasma-level0-materialization.py" --check-signing-key
    KEY="${ROOT}/keys/kde-plasma-release.asc"
fi
gpg --batch --yes --dearmor --output "${WORK}/release-keyring.gpg" "${KEY}"
gpgv --status-fd 1 --keyring "${WORK}/release-keyring.gpg"     "${TARBALL}.sig" "${TARBALL}"     > "${EVIDENCE}/signature.log" 2>&1

if [[ -n "${SIGNING_FINGERPRINT}" ]]; then
    grep -F "VALIDSIG ${SIGNING_FINGERPRINT}" "${EVIDENCE}/signature.log" >/dev/null
fi

mkdir -p "${WORK}/source"
python3 "${ROOT}/scripts/prepare-plasma-package.py" "${NODE}"     --upstream "${TARBALL}" --output "${WORK}/source"     > "${EVIDENCE}/source-package.log" 2>&1

mapfile -t DSCS < <(find "${WORK}/source" -maxdepth 1 -name '*.dsc' -type f | sort)
[[ ${#DSCS[@]} == 1 ]]

SOURCE_TREE="$(find "${WORK}/source" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
[[ -n "${SOURCE_TREE}" ]]
dpkg-source --before-build "${SOURCE_TREE}"     > "${EVIDENCE}/dpkg-source-before-build.log" 2>&1
dpkg-source --after-build "${SOURCE_TREE}"     >> "${EVIDENCE}/dpkg-source-before-build.log" 2>&1

autopkgtest --validate "${DSCS[0]}"     > "${EVIDENCE}/autopkgtest-validate.log" 2>&1

python3 "${ROOT}/scripts/scan-upstream-test-network.py" "${SOURCE_TREE}"     --output "${EVIDENCE}/upstream-test-network.json"

python3 - "${EVIDENCE}" "${NODE}" "${VERSION}" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
payload = {
    "schema": 1,
    "state": "PASS",
    "kind": "fast-package-preflight",
    "node": sys.argv[2],
    "version": sys.argv[3],
    "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip(),
    "package_attempt_consumed": False,
    "sbuild_invoked": False,
    "kvm_created": False,
    "checks": [
        "repository-package-contract",
        "upstream-source-sha256",
        "upstream-signature",
        "source-package-materialization",
        "dpkg-source-hooks",
        "autopkgtest-control-validation",
        "upstream-test-network-static-review",
    ],
    "files_sha256": {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    },
}
(root / "result.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY

echo "SUPRALINUX_FAST_PACKAGE_PREFLIGHT=PASS node=${NODE}"
