#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_MANIFEST="${ROOT}/manifests/kde-frameworks-tier1.json"
REFERENCE_MANIFEST="${ROOT}/manifests/kde-frameworks-tier1-packaging-reference.json"
WORK_DIR="${ROOT}/.work/kde-tier1-packaging-reference"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-packaging-reference"
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
mkdir -p "${WORK_DIR}" "${EVIDENCE_DIR}/source-records/ubuntu" "${EVIDENCE_DIR}/source-records/debian"

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
    "node": "kde-frameworks-tier1-packaging-reference",
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": False,
    "claim": "packaging-reference-snapshot-only",
    "framework_package_build_certification": "pending",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "KDE Frameworks Tier 1 packaging-reference snapshot"
echo "Debian/Ubuntu packaging is technical reference only; KDE upstream remains authoritative."

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
ref = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
ids = [n["id"] for n in source["nodes"]]
expected = {node_id: f"kf6-{node_id}" for node_id in ids}
actual = {node_id: node["source_package"] for node_id, node in ref["nodes"].items()}
if source.get("frameworks_series") != "6.30.0" or len(ids) != 29:
    raise SystemExit("Tier 1 source manifest is not the selected 29-node Frameworks 6.30.0 set")
if ref.get("authority") is not False or ref.get("role") != "packaging-reference-only":
    raise SystemExit("Packaging reference manifest must remain explicitly non-authoritative")
if actual != expected:
    raise SystemExit("Packaging reference source-package mapping does not match the selected Tier 1 set")
PY

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates \
    debian-archive-keyring \
    dpkg-dev \
    ubuntu-keyring

STAGE="source-index-setup"
cat > "${UBUNTU_SOURCES}" <<'EOF_UBUNTU'
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute-updates main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://security.ubuntu.com/ubuntu resolute-security main universe
EOF_UBUNTU

cat > "${DEBIAN_SOURCES}" <<'EOF_DEBIAN'
deb-src [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian sid main
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
m = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for node_id in sorted(m["nodes"]):
    print(f"{node_id}\t{m['nodes'][node_id]['source_package']}")
PY
)

for row in "${package_rows[@]}"; do
    IFS=$'\t' read -r node_id source_package <<<"${row}"
    echo "Capturing ${node_id}: ${source_package}"
    if ! apt-cache "${ubuntu_apt[@]}" showsrc "${source_package}" > "${EVIDENCE_DIR}/source-records/ubuntu/${node_id}.txt"; then
        echo "Ubuntu Resolute source record unavailable: ${source_package}" >&2
        exit 1
    fi
    if ! apt-cache "${debian_apt[@]}" showsrc "${source_package}" > "${EVIDENCE_DIR}/source-records/debian/${node_id}.txt"; then
        echo "Debian sid source record unavailable: ${source_package}" >&2
        exit 1
    fi
    if [[ ! -s "${EVIDENCE_DIR}/source-records/ubuntu/${node_id}.txt" || ! -s "${EVIDENCE_DIR}/source-records/debian/${node_id}.txt" ]]; then
        echo "Empty source record for ${source_package}" >&2
        exit 1
    fi
done

STAGE="snapshot-normalization"
python3 - "${REFERENCE_MANIFEST}" "${EVIDENCE_DIR}" "${SELECTED_KDE}" <<'PY'
import functools
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2])
selected_kde = sys.argv[3]


def parse_paragraphs(text: str):
    paragraphs = []
    current = {}
    key = None
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


def normalized_field(record, name):
    value = record.get(name)
    if value is None:
        return None
    return " ".join(value.split())


def checksums(record):
    rows = []
    raw = record.get("Checksums-Sha256", "")
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) == 3:
            rows.append({"sha256": parts[0], "size": int(parts[1]), "file": parts[2]})
    return rows


def select_record(path: Path, source_package: str):
    records = [r for r in parse_paragraphs(path.read_text(encoding="utf-8")) if r.get("Package") == source_package]
    if not records:
        raise SystemExit(f"No exact source record for {source_package} in {path}")
    record = sorted(records, key=functools.cmp_to_key(lambda a, b: version_cmp(a["Version"], b["Version"])))[-1]
    upstream = upstream_version(record["Version"])
    if subprocess.run(["dpkg", "--compare-versions", upstream, "gt", selected_kde], check=False).returncode == 0:
        raise SystemExit(f"Reference {source_package} {record['Version']} is newer than selected KDE {selected_kde}; review required")
    return {
        "source_package": source_package,
        "version": record["Version"],
        "upstream_version": upstream,
        "binary_packages": [p.strip() for p in record.get("Binary", "").split(",") if p.strip()],
        "architecture": normalized_field(record, "Architecture"),
        "build_depends": normalized_field(record, "Build-Depends"),
        "build_depends_indep": normalized_field(record, "Build-Depends-Indep"),
        "build_conflicts": normalized_field(record, "Build-Conflicts"),
        "build_conflicts_indep": normalized_field(record, "Build-Conflicts-Indep"),
        "standards_version": normalized_field(record, "Standards-Version"),
        "homepage": normalized_field(record, "Homepage"),
        "vcs_git": normalized_field(record, "Vcs-Git"),
        "vcs_browser": normalized_field(record, "Vcs-Browser"),
        "directory": normalized_field(record, "Directory"),
        "checksums_sha256": checksums(record),
    }

snapshot = {
    "schema": 1,
    "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "authority": False,
    "role": "packaging-reference-only",
    "selected_kde": selected_kde,
    "framework_package_build_certification": "pending",
    "references": {
        "ubuntu": {"distribution": "ubuntu", "series": "resolute"},
        "debian": {"distribution": "debian", "series": "sid"},
    },
    "nodes": {},
}

version_lines = ["node\tsource-package\tubuntu-version\tubuntu-upstream\tdebian-version\tdebian-upstream"]
for node_id in sorted(manifest["nodes"]):
    source_package = manifest["nodes"][node_id]["source_package"]
    ubuntu = select_record(out / "source-records" / "ubuntu" / f"{node_id}.txt", source_package)
    debian = select_record(out / "source-records" / "debian" / f"{node_id}.txt", source_package)
    snapshot["nodes"][node_id] = {"ubuntu": ubuntu, "debian": debian}
    version_lines.append("\t".join([node_id, source_package, ubuntu["version"], ubuntu["upstream_version"], debian["version"], debian["upstream_version"]]))

if len(snapshot["nodes"]) != 29:
    raise SystemExit(f"Expected 29 Tier 1 reference nodes, got {len(snapshot['nodes'])}")

(out / "snapshot.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(out / "versions.tsv").write_text("\n".join(version_lines) + "\n", encoding="utf-8")
PY

sha256sum "${EVIDENCE_DIR}/snapshot.json" "${EVIDENCE_DIR}/versions.tsv" > "${EVIDENCE_DIR}/snapshot.sha256"

STAGE="summary"
ubuntu_versions="$(cut -f4 "${EVIDENCE_DIR}/versions.tsv" | tail -n +2 | sort -u | paste -sd, -)"
debian_versions="$(cut -f6 "${EVIDENCE_DIR}/versions.tsv" | tail -n +2 | sort -u | paste -sd, -)"
{
    echo "status=PASS"
    echo "authority=false"
    echo "role=packaging-reference-only"
    echo "selected_kde=${SELECTED_KDE}"
    echo "ubuntu_series=resolute"
    echo "ubuntu_reference_upstream_versions=${ubuntu_versions}"
    echo "debian_series=sid"
    echo "debian_reference_upstream_versions=${debian_versions}"
    echo "nodes=29"
    echo "framework_package_build_certification=pending"
} > "${EVIDENCE_DIR}/summary.env"

STATE="PASS"
STAGE="complete"
echo "KDE Frameworks Tier 1 packaging-reference snapshot: PASS"
echo "Captured Ubuntu Resolute and Debian sid source packaging metadata for 29 nodes."
echo "No Framework package or DAG state was promoted."
