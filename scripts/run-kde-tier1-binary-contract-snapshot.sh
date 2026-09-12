#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REFERENCE_MANIFEST="${ROOT}/manifests/kde-frameworks-tier1-packaging-reference.json"
WORK_DIR="${ROOT}/.work/kde-tier1-binary-contract-reference"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-binary-contract-reference"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
UBUNTU_LISTS="${WORK_DIR}/apt-lists-ubuntu"
DEBIAN_LISTS="${WORK_DIR}/apt-lists-debian"
UBUNTU_SOURCES="${WORK_DIR}/ubuntu.list"
DEBIAN_SOURCES="${WORK_DIR}/debian.list"
SELECTED_KDE="6.30.0"
STATE="FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p \
    "${WORK_DIR}" \
    "${EVIDENCE_DIR}/source-records/ubuntu" \
    "${EVIDENCE_DIR}/source-records/debian" \
    "${EVIDENCE_DIR}/binary-records/ubuntu" \
    "${EVIDENCE_DIR}/binary-records/debian"

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
    "node": "kde-frameworks-tier1-binary-contract-reference",
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": False,
    "claim": "binary-packaging-contract-reference-only",
    "framework_package_build_certification": "pending",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "KDE Frameworks Tier 1 binary-contract reference snapshot"
echo "Ubuntu/Debian binary metadata is read from isolated indexes only; no reference binary package is installed."

STAGE="host-validation"
. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    echo "Expected Ubuntu 26.04; got ${PRETTY_NAME}" >&2
    exit 1
fi

python3 - "${REFERENCE_MANIFEST}" <<'PY'
import json
import sys
from pathlib import Path
m = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if m.get("authority") is not False or m.get("role") != "packaging-reference-only":
    raise SystemExit("Packaging reference manifest must remain non-authoritative")
if m.get("selected_kde") != "6.30.0" or len(m.get("nodes", {})) != 29:
    raise SystemExit("Packaging reference manifest does not describe selected KDE Frameworks 6.30 Tier 1")
if m.get("snapshot", {}).get("status") != "PASS":
    raise SystemExit("Source packaging-reference snapshot must be PASS before binary-contract capture")
PY

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates \
    debian-archive-keyring \
    dpkg-dev \
    ubuntu-keyring

STAGE="archive-index-setup"
cat > "${UBUNTU_SOURCES}" <<'EOF_UBUNTU'
deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute main universe
deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute-updates main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute-updates main universe
deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://security.ubuntu.com/ubuntu resolute-security main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://security.ubuntu.com/ubuntu resolute-security main universe
EOF_UBUNTU

cat > "${DEBIAN_SOURCES}" <<'EOF_DEBIAN'
deb [arch=amd64 signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian sid main
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
cp "${UBUNTU_SOURCES}" "${EVIDENCE_DIR}/ubuntu.list"
cp "${DEBIAN_SOURCES}" "${EVIDENCE_DIR}/debian.list"
sha256sum "${REFERENCE_MANIFEST}" > "${EVIDENCE_DIR}/input-manifest.sha256"

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
    apt-cache "${ubuntu_apt[@]}" showsrc "${source_package}" > "${EVIDENCE_DIR}/source-records/ubuntu/${node_id}.txt"
    apt-cache "${debian_apt[@]}" showsrc "${source_package}" > "${EVIDENCE_DIR}/source-records/debian/${node_id}.txt"
    if [[ ! -s "${EVIDENCE_DIR}/source-records/ubuntu/${node_id}.txt" || ! -s "${EVIDENCE_DIR}/source-records/debian/${node_id}.txt" ]]; then
        echo "Missing source metadata for ${source_package}" >&2
        exit 1
    fi
done

STAGE="binary-query-plan"
python3 - "${REFERENCE_MANIFEST}" "${EVIDENCE_DIR}" <<'PY'
import functools
import json
import subprocess
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2])


def parse_paragraphs(text):
    paragraphs, current, key = [], {}, None
    for line in text.splitlines():
        if not line.strip():
            if current:
                paragraphs.append(current)
                current, key = {}, None
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


def compare_versions(left, right):
    if subprocess.run(["dpkg", "--compare-versions", left, "gt", right], check=False).returncode == 0:
        return 1
    if subprocess.run(["dpkg", "--compare-versions", left, "lt", right], check=False).returncode == 0:
        return -1
    return 0

rows = ["provider\tnode\tsource-package\tsource-version\tbinary-package"]
for provider in ("ubuntu", "debian"):
    for node_id in sorted(manifest["nodes"]):
        source_package = manifest["nodes"][node_id]["source_package"]
        path = out / "source-records" / provider / f"{node_id}.txt"
        records = [r for r in parse_paragraphs(path.read_text(encoding="utf-8")) if r.get("Package") == source_package]
        if not records:
            raise SystemExit(f"No exact source record for {provider}:{source_package}")
        selected = sorted(records, key=functools.cmp_to_key(lambda a, b: compare_versions(a["Version"], b["Version"])))[-1]
        binaries = [p.strip() for p in selected.get("Binary", "").split(",") if p.strip()]
        if not binaries:
            raise SystemExit(f"No binary package list for {provider}:{source_package}")
        for binary in sorted(binaries):
            rows.append("\t".join([provider, node_id, source_package, selected["Version"], binary]))
(out / "binary-query-plan.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
PY

while IFS=$'\t' read -r provider node_id source_package source_version binary_package; do
    [[ "${provider}" != "provider" ]] || continue
    record_path="${EVIDENCE_DIR}/binary-records/${provider}/${binary_package}.txt"
    if [[ -s "${record_path}" ]]; then
        continue
    fi
    echo "Capturing ${provider}:${binary_package} for ${node_id} (${source_package} ${source_version})"
    if [[ "${provider}" == "ubuntu" ]]; then
        apt-cache "${ubuntu_apt[@]}" show "${binary_package}" > "${record_path}"
    else
        apt-cache "${debian_apt[@]}" show "${binary_package}" > "${record_path}"
    fi
    if [[ ! -s "${record_path}" ]]; then
        echo "Missing binary metadata for ${provider}:${binary_package}" >&2
        exit 1
    fi
done < "${EVIDENCE_DIR}/binary-query-plan.tsv"

STAGE="binary-contract-normalization"
python3 - "${EVIDENCE_DIR}" "${SELECTED_KDE}" <<'PY'
import functools
import json
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1])
selected_kde = sys.argv[2]


def parse_paragraphs(text):
    paragraphs, current, key = [], {}, None
    for line in text.splitlines():
        if not line.strip():
            if current:
                paragraphs.append(current)
                current, key = {}, None
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


def compare_versions(left, right):
    if subprocess.run(["dpkg", "--compare-versions", left, "gt", right], check=False).returncode == 0:
        return 1
    if subprocess.run(["dpkg", "--compare-versions", left, "lt", right], check=False).returncode == 0:
        return -1
    return 0


def upstream_version(version):
    no_epoch = version.split(":", 1)[-1]
    return no_epoch.rsplit("-", 1)[0] if "-" in no_epoch else no_epoch


def normalize(value):
    return None if value is None else " ".join(value.split())

plan = []
for line in (out / "binary-query-plan.tsv").read_text(encoding="utf-8").splitlines()[1:]:
    plan.append(line.split("\t"))

contracts = {
    "schema": 1,
    "authority": False,
    "role": "binary-packaging-contract-reference-only",
    "selected_kde": selected_kde,
    "framework_package_build_certification": "pending",
    "providers": {"ubuntu": {}, "debian": {}},
}

for provider, node_id, source_package, source_version, binary_package in plan:
    path = out / "binary-records" / provider / f"{binary_package}.txt"
    records = [r for r in parse_paragraphs(path.read_text(encoding="utf-8")) if r.get("Package") == binary_package]
    if not records:
        raise SystemExit(f"No exact binary record for {provider}:{binary_package}")
    selected = sorted(records, key=functools.cmp_to_key(lambda a, b: compare_versions(a["Version"], b["Version"])))[-1]
    source_field = selected.get("Source", binary_package)
    source_name = source_field.split()[0]
    if source_name != source_package:
        raise SystemExit(f"Source mismatch for {provider}:{binary_package}: {source_field} != {source_package}")
    upstream = upstream_version(selected["Version"])
    if subprocess.run(["dpkg", "--compare-versions", upstream, "gt", selected_kde], check=False).returncode == 0:
        raise SystemExit(f"{provider}:{binary_package} {selected['Version']} is newer than selected KDE {selected_kde}")
    contracts["providers"][provider][binary_package] = {
        "node": node_id,
        "source_package": source_package,
        "source_version": source_version,
        "version": selected["Version"],
        "upstream_version": upstream,
        "architecture": normalize(selected.get("Architecture")),
        "multi_arch": normalize(selected.get("Multi-Arch")),
        "pre_depends": normalize(selected.get("Pre-Depends")),
        "depends": normalize(selected.get("Depends")),
        "recommends": normalize(selected.get("Recommends")),
        "suggests": normalize(selected.get("Suggests")),
        "enhances": normalize(selected.get("Enhances")),
        "provides": normalize(selected.get("Provides")),
        "breaks": normalize(selected.get("Breaks")),
        "replaces": normalize(selected.get("Replaces")),
        "conflicts": normalize(selected.get("Conflicts")),
        "section": normalize(selected.get("Section")),
        "priority": normalize(selected.get("Priority")),
    }

fields = ["architecture", "multi_arch", "pre_depends", "depends", "recommends", "suggests", "enhances", "provides", "breaks", "replaces", "conflicts", "section", "priority"]
ubuntu_names = set(contracts["providers"]["ubuntu"])
debian_names = set(contracts["providers"]["debian"])
differences = []
for package in sorted(ubuntu_names & debian_names):
    ubuntu = contracts["providers"]["ubuntu"][package]
    debian = contracts["providers"]["debian"][package]
    changed = {field: {"ubuntu": ubuntu[field], "debian": debian[field]} for field in fields if ubuntu[field] != debian[field]}
    if changed:
        differences.append({"package": package, "fields": changed})
contracts["comparison"] = {
    "ubuntu_binary_packages": len(ubuntu_names),
    "debian_binary_packages": len(debian_names),
    "common_binary_packages": len(ubuntu_names & debian_names),
    "ubuntu_only_binary_packages": sorted(ubuntu_names - debian_names),
    "debian_only_binary_packages": sorted(debian_names - ubuntu_names),
    "packages_with_contract_differences": differences,
}

(out / "binary-contracts.json").write_text(json.dumps(contracts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
lines = ["provider\tpackage\tversion\tarchitecture\tmulti-arch\tsource-package"]
for provider in ("ubuntu", "debian"):
    for package, record in sorted(contracts["providers"][provider].items()):
        lines.append("\t".join([provider, package, record["version"], record["architecture"] or "", record["multi_arch"] or "", record["source_package"]]))
(out / "binary-contracts.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

sha256sum \
    "${EVIDENCE_DIR}/binary-query-plan.tsv" \
    "${EVIDENCE_DIR}/binary-contracts.json" \
    "${EVIDENCE_DIR}/binary-contracts.tsv" > "${EVIDENCE_DIR}/contracts.sha256"

STAGE="summary"
python3 - "${EVIDENCE_DIR}/binary-contracts.json" "${EVIDENCE_DIR}/summary.env" <<'PY'
import json
import sys
from pathlib import Path
c = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cmp = c["comparison"]
Path(sys.argv[2]).write_text(
    "status=PASS\n"
    "authority=false\n"
    "role=binary-packaging-contract-reference-only\n"
    f"ubuntu_binary_packages={cmp['ubuntu_binary_packages']}\n"
    f"debian_binary_packages={cmp['debian_binary_packages']}\n"
    f"common_binary_packages={cmp['common_binary_packages']}\n"
    f"ubuntu_only_binary_packages={len(cmp['ubuntu_only_binary_packages'])}\n"
    f"debian_only_binary_packages={len(cmp['debian_only_binary_packages'])}\n"
    f"packages_with_contract_differences={len(cmp['packages_with_contract_differences'])}\n"
    "framework_package_build_certification=pending\n",
    encoding="utf-8",
)
PY

STATE="PASS"
STAGE="complete"
echo "KDE Frameworks Tier 1 binary-contract reference snapshot: PASS"
echo "No reference binary package was installed and no Framework DAG state was promoted."
