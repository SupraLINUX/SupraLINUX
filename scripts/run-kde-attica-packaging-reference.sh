#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${ROOT}/evidence/kde-attica-packaging-reference"
WORK="${ROOT}/.work/kde-attica-packaging-reference"

rm -rf "${EVIDENCE}" "${WORK}"
mkdir -p "${EVIDENCE}" "${WORK}"
exec > >(tee "${EVIDENCE}/capture.log") 2>&1

. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    echo "Expected Ubuntu 26.04; got ${PRETTY_NAME}" >&2
    exit 1
fi

capture_reference() {
    local name="$1"
    local version="$2"
    local url="$3"
    local expected_sha="$4"
    local archive="${WORK}/${name}.debian.tar.xz"
    local out="${EVIDENCE}/${name}"

    mkdir -p "${out}"
    curl --fail --location --retry 3 --retry-delay 2 --output "${archive}" "${url}"
    printf '%s  %s\n' "${expected_sha}" "${archive}" | sha256sum --check --strict
    sha256sum "${archive}" > "${out}/debian-tarball.sha256"

    tar -xJf "${archive}" -C "${out}"
    test -d "${out}/debian"

    for required in \
        control \
        rules \
        copyright \
        libkf6attica6.install \
        libkf6attica-dev.install \
        libkf6attica-doc.install \
        libkf6attica6.symbols; do
        if [[ ! -f "${out}/debian/${required}" ]]; then
            echo "${name} ${version}: required packaging reference file missing: debian/${required}" >&2
            exit 1
        fi
    done

    chmod -R u=rwX,go=rX "${out}/debian"
    find "${out}/debian" -type f -print0 | sort -z | xargs -0 sha256sum > "${out}/debian-files.sha256"
    printf '%s\n' "${version}" > "${out}/version.txt"
    printf '%s\n' "${url}" > "${out}/url.txt"
}

capture_reference \
    ubuntu-resolute \
    6.24.0-0ubuntu1 \
    https://archive.ubuntu.com/ubuntu/pool/universe/k/kf6-attica/kf6-attica_6.24.0-0ubuntu1.debian.tar.xz \
    a3bdf81f4d7c624fd2003b4446e0a038cd2d47db45970fd0153027a76a422b9e

capture_reference \
    debian-sid \
    6.28.0-1 \
    https://deb.debian.org/debian/pool/main/k/kf6-attica/kf6-attica_6.28.0-1.debian.tar.xz \
    17f7367dce612b888be9dd5e1b249a48e21a0e86a99afa3f304c0051bb7d1c4f

python3 - "${EVIDENCE}" <<'PY'
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
refs = {}
for name in ("ubuntu-resolute", "debian-sid"):
    base = root / name
    selected = {}
    for filename in (
        "control",
        "rules",
        "copyright",
        "libkf6attica6.install",
        "libkf6attica-dev.install",
        "libkf6attica-doc.install",
        "libkf6attica6.symbols",
    ):
        path = base / "debian" / filename
        data = path.read_bytes()
        selected[filename] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    refs[name] = {
        "version": (base / "version.txt").read_text(encoding="utf-8").strip(),
        "url": (base / "url.txt").read_text(encoding="utf-8").strip(),
        "selected_files": selected,
    }

out = {
    "schema": 1,
    "node": "attica",
    "selected_kde": "6.30.0",
    "authority": False,
    "role": "packaging-reference-tree-only",
    "references": refs,
    "framework_package_build_certification": "pending",
}
(root / "summary.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
PY

sha256sum "${EVIDENCE}/summary.json" > "${EVIDENCE}/summary.sha256"
cat > "${EVIDENCE}/result.env" <<'EOF'
status=PASS
node=attica
authority=false
role=packaging-reference-tree-only
selected_kde=6.30.0
framework_package_build_certification=pending
EOF

echo "Attica packaging reference trees: PASS"
