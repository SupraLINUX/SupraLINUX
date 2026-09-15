#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_MANIFEST="${ROOT}/manifests/kde-frameworks-tier1.json"
REFERENCE_MANIFEST="${ROOT}/manifests/kde-frameworks-tier1-packaging-reference.json"
WORK_DIR="${ROOT}/.work/kde-tier1-packaging-tree-reference"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-packaging-tree-reference"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
UBUNTU_LISTS="${WORK_DIR}/apt-lists-ubuntu"
DEBIAN_LISTS="${WORK_DIR}/apt-lists-debian"
UBUNTU_SOURCES="${WORK_DIR}/ubuntu.sources.list"
DEBIAN_SOURCES="${WORK_DIR}/debian.sources.list"
SELECTED_KDE="6.30.0"
STATE="FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p \
    "${WORK_DIR}/archives" \
    "${EVIDENCE_DIR}/source-records/ubuntu" \
    "${EVIDENCE_DIR}/source-records/debian" \
    "${EVIDENCE_DIR}/trees/ubuntu" \
    "${EVIDENCE_DIR}/trees/debian"

write_result() {
    local rc="$?"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT_JSON}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json
import sys
from pathlib import Path

path, state, rc, stage, started, finished = sys.argv[1:]
Path(path).write_text(json.dumps({
    "node": "kde-frameworks-tier1-packaging-tree-reference",
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": False,
    "claim": "packaging-reference-trees-only",
    "framework_package_build_certification": "unchanged",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "KDE Frameworks Tier 1 packaging-tree reference snapshot"
echo "Ubuntu/Debian packaging is technical reference only; KDE upstream remains authoritative."

STAGE="host-validation"
. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    echo "Expected Ubuntu 26.04; got ${PRETTY_NAME}" >&2
    exit 1
fi

python3 - "${SOURCE_MANIFEST}" "${REFERENCE_MANIFEST}" <<'PY'
import json
import sys
from pathlib import Path

source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
reference = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
ids = [node["id"] for node in source["nodes"]]
expected = {node_id: f"kf6-{node_id}" for node_id in ids}
actual = {node_id: item["source_package"] for node_id, item in reference["nodes"].items()}
if source.get("frameworks_series") != "6.30.0" or len(ids) != 29:
    raise SystemExit("Tier 1 source manifest is not the selected 29-node Frameworks 6.30.0 set")
if reference.get("authority") is not False or reference.get("role") != "packaging-reference-only":
    raise SystemExit("Packaging-reference manifest must remain explicitly non-authoritative")
if reference.get("selected_kde") != "6.30.0":
    raise SystemExit("Packaging-reference manifest does not follow selected KDE 6.30.0")
if actual != expected:
    raise SystemExit("Packaging-reference source-package mapping does not match the selected Tier 1 set")
PY

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    debian-archive-keyring \
    dpkg-dev \
    ubuntu-keyring

STAGE="source-index-setup"
cat > "${UBUNTU_SOURCES}" <<'EOF_UBUNTU'
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu resolute main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu resolute-updates main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://security.ubuntu.com/ubuntu resolute-security main universe
EOF_UBUNTU

cat > "${DEBIAN_SOURCES}" <<'EOF_DEBIAN'
deb-src [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian sid main
EOF_DEBIAN

sudo mkdir -p "${UBUNTU_LISTS}" "${DEBIAN_LISTS}"
sudo chown _apt:root "${UBUNTU_LISTS}" "${DEBIAN_LISTS}"
sudo chmod 0755 "${UBUNTU_LISTS}" "${DEBIAN_LISTS}"

ubuntu_apt=(
    -o "Dir::Etc::sourcelist=${UBUNTU_SOURCES}"
    -o "Dir::Etc::sourceparts=-"
    -o "Dir::State::lists=${UBUNTU_LISTS}"
    -o "APT::Get::List-Cleanup=0"
)
debian_apt=(
    -o "Dir::Etc::sourcelist=${DEBIAN_SOURCES}"
    -o "Dir::Etc::sourceparts=-"
    -o "Dir::State::lists=${DEBIAN_LISTS}"
    -o "APT::Get::List-Cleanup=0"
)

sudo apt-get "${ubuntu_apt[@]}" update |& tee "${EVIDENCE_DIR}/ubuntu-apt-update.log"
sudo apt-get "${debian_apt[@]}" update |& tee "${EVIDENCE_DIR}/debian-apt-update.log"

cp "${UBUNTU_SOURCES}" "${EVIDENCE_DIR}/ubuntu.sources.list"
cp "${DEBIAN_SOURCES}" "${EVIDENCE_DIR}/debian.sources.list"
sha256sum "${SOURCE_MANIFEST}" "${REFERENCE_MANIFEST}" > "${EVIDENCE_DIR}/input-manifests.sha256"
sha256sum "${EVIDENCE_DIR}/ubuntu.sources.list" "${EVIDENCE_DIR}/debian.sources.list" > "${EVIDENCE_DIR}/source-lists.sha256"

STAGE="source-record-capture"
mapfile -t package_rows < <(python3 - "${REFERENCE_MANIFEST}" <<'PY'
import json
import sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for node_id in sorted(manifest["nodes"]):
    print(f"{node_id}\t{manifest['nodes'][node_id]['source_package']}")
PY
)

for row in "${package_rows[@]}"; do
    IFS=$'\t' read -r node_id source_package <<<"${row}"
    echo "Capturing signed source records for ${node_id}: ${source_package}"
    apt-cache "${ubuntu_apt[@]}" showsrc "${source_package}" > "${EVIDENCE_DIR}/source-records/ubuntu/${node_id}.txt"
    apt-cache "${debian_apt[@]}" showsrc "${source_package}" > "${EVIDENCE_DIR}/source-records/debian/${node_id}.txt"
    if [[ ! -s "${EVIDENCE_DIR}/source-records/ubuntu/${node_id}.txt" || ! -s "${EVIDENCE_DIR}/source-records/debian/${node_id}.txt" ]]; then
        echo "Empty source record for ${source_package}" >&2
        exit 1
    fi
done

STAGE="download-plan"
python3 - "${REFERENCE_MANIFEST}" "${EVIDENCE_DIR}" "${SELECTED_KDE}" <<'PY'
from __future__ import annotations

import functools
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2])
selected_kde = sys.argv[3]

BASE_URLS = {
    "ubuntu": "https://archive.ubuntu.com/ubuntu",
    "debian": "https://deb.debian.org/debian",
}


def parse_paragraphs(text: str) -> list[dict[str, str]]:
    paragraphs: list[dict[str, str]] = []
    current: dict[str, str] = {}
    key: str | None = None
    for line in text.splitlines():
        if not line.strip():
            if current:
                paragraphs.append(current)
                current = {}
                key = None
            continue
        if line[0].isspace() and key is not None:
            current[key] += "\n" + line.strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key] = value.lstrip()
    if current:
        paragraphs.append(current)
    return paragraphs


def version_cmp(left: str, right: str) -> int:
    if subprocess.run(["dpkg", "--compare-versions", left, "gt", right], check=False).returncode == 0:
        return 1
    if subprocess.run(["dpkg", "--compare-versions", left, "lt", right], check=False).returncode == 0:
        return -1
    return 0


def upstream_version(version: str) -> str:
    no_epoch = version.split(":", 1)[-1]
    return no_epoch.rsplit("-", 1)[0] if "-" in no_epoch else no_epoch


def checksums(record: dict[str, str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in record.get("Checksums-Sha256", "").splitlines():
        parts = line.split()
        if len(parts) == 3:
            rows.append({"sha256": parts[0], "size": int(parts[1]), "file": parts[2]})
    return rows


def select_record(path: Path, source_package: str, distribution: str) -> dict[str, object]:
    records = [r for r in parse_paragraphs(path.read_text(encoding="utf-8")) if r.get("Package") == source_package]
    if not records:
        raise SystemExit(f"No exact source record for {source_package} in {path}")
    record = sorted(records, key=functools.cmp_to_key(lambda a, b: version_cmp(a["Version"], b["Version"])))[-1]
    upstream = upstream_version(record["Version"])
    if subprocess.run(["dpkg", "--compare-versions", upstream, "gt", selected_kde], check=False).returncode == 0:
        raise SystemExit(f"Reference {source_package} {record['Version']} is newer than selected KDE {selected_kde}; review required")
    directory = record.get("Directory", "").strip()
    if not directory:
        raise SystemExit(f"Source record lacks Directory for {source_package} {record['Version']}")
    debian_archives = [item for item in checksums(record) if ".debian.tar." in str(item["file"])]
    if len(debian_archives) != 1:
        raise SystemExit(f"Expected exactly one .debian.tar.* for {source_package} {record['Version']}; got {len(debian_archives)}")
    archive = debian_archives[0]
    archive["url"] = f"{BASE_URLS[distribution].rstrip('/')}/{directory}/{archive['file']}"
    return {
        "source_package": source_package,
        "version": record["Version"],
        "upstream_version": upstream,
        "directory": directory,
        "debian_tarball": archive,
    }

snapshot = {
    "schema": 1,
    "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "authority": False,
    "role": "packaging-reference-trees-only",
    "selected_kde": selected_kde,
    "framework_package_build_certification": "unchanged",
    "references": {
        "ubuntu": {"distribution": "ubuntu", "series": "resolute", "source_index_signature": "APT-verified"},
        "debian": {"distribution": "debian", "series": "sid", "source_index_signature": "APT-verified"},
    },
    "nodes": {},
}
versions = ["node\tsource-package\tubuntu-version\tubuntu-upstream\tdebian-version\tdebian-upstream"]
plan = ["distribution\tnode\tsource-package\tversion\turl\tsha256\tsize\tfilename"]

for node_id in sorted(manifest["nodes"]):
    source_package = manifest["nodes"][node_id]["source_package"]
    ubuntu = select_record(out / "source-records" / "ubuntu" / f"{node_id}.txt", source_package, "ubuntu")
    debian = select_record(out / "source-records" / "debian" / f"{node_id}.txt", source_package, "debian")
    snapshot["nodes"][node_id] = {"ubuntu": ubuntu, "debian": debian}
    versions.append("\t".join([node_id, source_package, str(ubuntu["version"]), str(ubuntu["upstream_version"]), str(debian["version"]), str(debian["upstream_version"])]))
    for distribution, record in (("ubuntu", ubuntu), ("debian", debian)):
        archive = record["debian_tarball"]
        plan.append("\t".join([
            distribution,
            node_id,
            source_package,
            str(record["version"]),
            str(archive["url"]),
            str(archive["sha256"]),
            str(archive["size"]),
            str(archive["file"]),
        ]))

if len(snapshot["nodes"]) != 29:
    raise SystemExit(f"Expected 29 Tier 1 nodes, got {len(snapshot['nodes'])}")
if len(plan) != 59:
    raise SystemExit(f"Expected 58 packaging-tree downloads, got {len(plan) - 1}")

(out / "snapshot.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(out / "versions.tsv").write_text("\n".join(versions) + "\n", encoding="utf-8")
(out / "download-plan.tsv").write_text("\n".join(plan) + "\n", encoding="utf-8")
PY

STAGE="packaging-tree-capture"
printf 'distribution\tnode\tsource-package\tversion\tdebian-tarball-sha256\ttree-files-manifest-sha256\n' > "${EVIDENCE_DIR}/tree-hashes.tsv"

tail -n +2 "${EVIDENCE_DIR}/download-plan.tsv" | while IFS=$'\t' read -r distribution node_id source_package version url expected_sha expected_size filename; do
    echo "Downloading ${distribution}/${node_id} ${version}: ${filename}"
    archive="${WORK_DIR}/archives/${distribution}-${node_id}-${filename}"
    tree_root="${EVIDENCE_DIR}/trees/${distribution}/${node_id}"
    mkdir -p "${tree_root}"

    curl --fail --location --retry 3 --retry-delay 2 --output "${archive}" "${url}"
    printf '%s  %s\n' "${expected_sha}" "${archive}" | sha256sum --check --strict
    actual_size="$(stat -c '%s' "${archive}")"
    if [[ "${actual_size}" != "${expected_size}" ]]; then
        echo "Size mismatch for ${distribution}/${node_id}: expected ${expected_size}, got ${actual_size}" >&2
        exit 1
    fi

    tar -xf "${archive}" -C "${tree_root}"
    if [[ ! -d "${tree_root}/debian" ]]; then
        echo "Extracted reference lacks debian/ tree: ${distribution}/${node_id}" >&2
        exit 1
    fi

    (
        cd "${tree_root}"
        find debian -type f -print0 | sort -z | xargs -0 sha256sum > tree-files.sha256
    )
    tree_manifest_sha="$(sha256sum "${tree_root}/tree-files.sha256" | awk '{print $1}')"
    printf '%s\n' "${source_package}" > "${tree_root}/source-package.txt"
    printf '%s\n' "${version}" > "${tree_root}/version.txt"
    printf '%s\n' "${url}" > "${tree_root}/url.txt"
    printf '%s  %s\n' "${expected_sha}" "${filename}" > "${tree_root}/debian-tarball.sha256"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "${distribution}" "${node_id}" "${source_package}" "${version}" "${expected_sha}" "${tree_manifest_sha}" \
        >> "${EVIDENCE_DIR}/tree-hashes.tsv"
done

tree_count="$(tail -n +2 "${EVIDENCE_DIR}/tree-hashes.tsv" | wc -l | tr -d ' ')"
if [[ "${tree_count}" != "58" ]]; then
    echo "Expected 58 extracted packaging trees; got ${tree_count}" >&2
    exit 1
fi

sha256sum \
    "${EVIDENCE_DIR}/snapshot.json" \
    "${EVIDENCE_DIR}/versions.tsv" \
    "${EVIDENCE_DIR}/download-plan.tsv" \
    "${EVIDENCE_DIR}/tree-hashes.tsv" \
    > "${EVIDENCE_DIR}/snapshot.sha256"

STAGE="summary"
ubuntu_versions="$(cut -f4 "${EVIDENCE_DIR}/versions.tsv" | tail -n +2 | sort -u | paste -sd, -)"
debian_versions="$(cut -f6 "${EVIDENCE_DIR}/versions.tsv" | tail -n +2 | sort -u | paste -sd, -)"
{
    echo "status=PASS"
    echo "authority=false"
    echo "role=packaging-reference-trees-only"
    echo "selected_kde=${SELECTED_KDE}"
    echo "ubuntu_series=resolute"
    echo "ubuntu_reference_upstream_versions=${ubuntu_versions}"
    echo "debian_series=sid"
    echo "debian_reference_upstream_versions=${debian_versions}"
    echo "nodes=29"
    echo "packaging_trees=58"
    echo "source_index_signature=APT-verified"
    echo "framework_package_build_certification=unchanged"
} > "${EVIDENCE_DIR}/summary.env"

STATE="PASS"
STAGE="complete"
echo "KDE Frameworks Tier 1 packaging-tree reference snapshot: PASS"
echo "Captured and hash-verified 58 debian/ trees for 29 nodes from signed source indices."
echo "No Framework package or DAG state was promoted."
