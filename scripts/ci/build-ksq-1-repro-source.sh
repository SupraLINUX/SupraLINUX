#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ORDER="${1:?source order required}"
CANDIDATE_DEBS="${2:?candidate DEB directory required}"
CANDIDATE_EVIDENCE="${3:?candidate evidence directory required}"
OUTPUT_ROOT="${4:?output root required}"
CLOSURE="${ROOT}/build/ksq-0/build-order.tsv"
ENV_FILE="${ROOT}/build/ksq-1/environment/build-environment.env"

fail() {
  echo "AURORA_KSQ_1_REPRO_BUILD_FAILURE: $*" >&2
  exit 1
}

[[ "${ORDER}" =~ ^[0-9]+$ ]] || fail "order must be numeric"
case "${ORDER}" in
  29|68|81|99|100|101) ;;
  *) fail "order ${ORDER} is outside the certified syntax-patch regression set" ;;
esac
[[ -f "${CLOSURE}" ]] || fail "KSQ-0 build order missing"
[[ -f "${ENV_FILE}" ]] || fail "KSQ-1 build environment missing"
[[ -d "${CANDIDATE_DEBS}" ]] || fail "candidate DEB directory missing"
[[ -d "${CANDIDATE_EVIDENCE}" ]] || fail "candidate evidence directory missing"

row="$(awk -F '\t' -v order="${ORDER}" 'NR > 1 && $1 == order {print; found++} END {if (found != 1) exit 7}' "${CLOSURE}")" \
  || fail "expected exactly one closure row for order ${ORDER}"
IFS=$'\t' read -r order source base_version family decision <<< "${row}"
[[ "${order}" == "${ORDER}" ]] || fail "closure order mismatch"

# shellcheck disable=SC1090
. "${ENV_FILE}"
TARBALL="${AURORA_KSQ_1_BUILD_ENV_TARBALL:?missing chroot tarball}"
[[ -s "${TARBALL}" ]] || fail "chroot tarball not found"

OUT="${OUTPUT_ROOT}/${ORDER}-${source}"
WORK="${OUT}/source-work"
DEPS="${OUT}/deps"
RESULT="${OUT}/result"
EVIDENCE="${OUT}/evidence"
rm -rf "${OUT}"
mkdir -p "${DEPS}" "${RESULT}" "${EVIDENCE}"

mapfile -t indexes < <(find "${CANDIDATE_EVIDENCE}" -type f -name binary-packages.tsv -print | sort)
((${#indexes[@]} > 0)) || fail "candidate binary indexes missing"

python3 - "${ORDER}" "${CANDIDATE_DEBS}" "${DEPS}" "${EVIDENCE}/dependency-inputs.tsv" "${indexes[@]}" <<'PY'
from __future__ import annotations
import csv
import hashlib
import shutil
import sys
from pathlib import Path

order = int(sys.argv[1])
candidate_debs = Path(sys.argv[2])
deps = Path(sys.argv[3])
out = Path(sys.argv[4])
indexes = [Path(p) for p in sys.argv[5:]]
header = ["order", "source_package", "binary_package", "filename", "version", "architecture"]
rows = []
seen_pkg = set()
seen_file = set()
for path in indexes:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != header:
            raise SystemExit(f"unexpected binary index header in {path}: {reader.fieldnames}")
        for row in reader:
            item_order = int(row["order"])
            if item_order >= order:
                continue
            package = row["binary_package"]
            filename = row["filename"]
            if package in seen_pkg or filename in seen_file:
                raise SystemExit(f"duplicate dependency binary {package}/{filename}")
            source = candidate_debs / filename
            if not source.is_file():
                raise SystemExit(f"candidate dependency DEB missing: {filename}")
            shutil.copy2(source, deps / filename)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            rows.append([row["order"], row["source_package"], package, filename, row["version"], row["architecture"], digest])
            seen_pkg.add(package)
            seen_file.add(filename)
if not rows:
    raise SystemExit("no candidate dependency DEBs selected")
with out.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
    writer.writerow(header + ["sha256"])
    writer.writerows(sorted(rows, key=lambda item: (int(item[0]), item[2])))
PY

bash "${ROOT}/scripts/ci/fetch-prepare-ksq-1-source.sh" "${source}" "${base_version}" "${WORK}"
# shellcheck disable=SC1090
. "${WORK}/prepared-source.env"
[[ "${AURORA_KSQ_1_SOURCE}" == "${source}" ]] || fail "prepared source mismatch"
[[ "${AURORA_KSQ_1_PACKAGING_BASE}" == "${base_version}" ]] || fail "prepared base mismatch"
supra_version="${AURORA_KSQ_1_VERSION}"

candidate_source_dir="$(find "${CANDIDATE_EVIDENCE}" -type f -path "*/${ORDER}-${source}/build-status.env" -printf '%h\n' | sort -u)"
[[ -n "${candidate_source_dir}" ]] || fail "candidate source evidence not found for ${ORDER}-${source}"
[[ "$(printf '%s\n' "${candidate_source_dir}" | sed '/^$/d' | wc -l)" -eq 1 ]] \
  || fail "candidate source evidence is ambiguous for ${ORDER}-${source}"

cmp "${WORK}/source/debian/control" "${candidate_source_dir}/debian-control" \
  || fail "prepared debian/control differs from authoritative candidate"
cmp "${WORK}/source/debian/changelog" "${candidate_source_dir}/debian-changelog" \
  || fail "prepared debian/changelog differs from authoritative candidate"

current_dsc="${AURORA_KSQ_1_PREPARED_DSC}"
candidate_dsc="$(find "${candidate_source_dir}" -maxdepth 1 -type f -name '*.dsc' -print)"
[[ "$(printf '%s\n' "${candidate_dsc}" | sed '/^$/d' | wc -l)" -eq 1 ]] || fail "candidate prepared dsc missing/ambiguous"
cmp "${current_dsc}" "${candidate_dsc}" || fail "prepared dsc differs from authoritative candidate"

mapfile -t current_deltas < <(find "${WORK}" -maxdepth 1 -type f -name '*~supra26.04.1*' ! -name '*.dsc' -printf '%f\n' | sort)
((${#current_deltas[@]} > 0)) || fail "prepared source delta missing"
for name in "${current_deltas[@]}"; do
  [[ -f "${candidate_source_dir}/${name}" ]] || fail "candidate evidence missing source delta ${name}"
  cmp "${WORK}/${name}" "${candidate_source_dir}/${name}" || fail "source delta differs: ${name}"
done
candidate_delta_count="$(find "${candidate_source_dir}" -maxdepth 1 -type f -name '*~supra26.04.1*' ! -name '*.dsc' | wc -l)"
[[ "${candidate_delta_count}" -eq "${#current_deltas[@]}" ]] || fail "candidate/current source delta set differs"

{
  echo "AURORA_KSQ_1_REPRO_SOURCE_IDENTITY=PASS"
  echo "AURORA_KSQ_1_REPRO_ORDER=${ORDER}"
  echo "AURORA_KSQ_1_REPRO_SOURCE=${source}"
  echo "AURORA_KSQ_1_REPRO_VERSION=${supra_version}"
  echo "AURORA_KSQ_1_REPRO_CANDIDATE_SOURCE_DIR=${candidate_source_dir}"
} > "${EVIDENCE}/source-identity.env"
(
  cd "${WORK}"
  sha256sum "$(basename "${current_dsc}")" "${current_deltas[@]}" | sort
) > "${EVIDENCE}/prepared-source.sha256"
cp -a "${WORK}/prepared-source.env" "${EVIDENCE}/"

normalize_result_filenames() {
  local dir="$1"
  while IFS= read -r -d '' file; do
    local base safe
    base="$(basename "${file}")"
    safe="${base//:/-}"
    if [[ "${base}" != "${safe}" ]]; then
      [[ ! -e "$(dirname "${file}")/${safe}" ]] || fail "result filename collision ${safe}"
      mv "${file}" "$(dirname "${file}")/${safe}"
    fi
  done < <(find "${dir}" -maxdepth 1 -type f -name '*:*' -print0)
}

DEB_BUILD_OPTIONS="parallel=2" sbuild \
  --chroot-mode=unshare \
  --chroot="${TARBALL}" \
  --dist=resolute \
  --arch=amd64 \
  --build-dir="${RESULT}" \
  --build-path=/build/supralinux-ksq1 \
  --jobs=2 \
  --no-enable-network \
  --no-run-lintian \
  --no-run-autopkgtest \
  --purge-build=always \
  --purge-deps=always \
  --resolve-alternatives \
  --bd-uninstallable-explainer=apt \
  --extra-package="${DEPS}" \
  "${current_dsc}"
normalize_result_filenames "${RESULT}"

python3 - "${ORDER}" "${source}" "${supra_version}" "${CANDIDATE_DEBS}" "${CANDIDATE_EVIDENCE}" "${RESULT}" "${EVIDENCE}/dedicated-proof.tsv" <<'PY'
from __future__ import annotations
import csv
import hashlib
import subprocess
import sys
from pathlib import Path

order = int(sys.argv[1])
source_name = sys.argv[2]
version = sys.argv[3]
candidate_debs = Path(sys.argv[4])
candidate_evidence = Path(sys.argv[5])
result = Path(sys.argv[6])
out = Path(sys.argv[7])
header = ["order", "source_package", "binary_package", "filename", "version", "architecture"]
rows = []
for index in sorted(candidate_evidence.rglob("binary-packages.tsv")):
    with index.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != header:
            raise SystemExit(f"unexpected binary index header in {index}: {reader.fieldnames}")
        for row in reader:
            if int(row["order"]) == order:
                rows.append(row)
rows.sort(key=lambda item: item["binary_package"])
if not rows:
    raise SystemExit(f"no candidate binaries recorded for order {order}")

built = {p.name: p for p in result.glob("*.deb")}
expected_names = {row["filename"] for row in rows}
if set(built) != expected_names:
    raise SystemExit(f"built DEB set differs: missing={sorted(expected_names-set(built))} extra={sorted(set(built)-expected_names)}")

proof = []
for row in rows:
    filename = row["filename"]
    built_deb = built[filename]
    candidate_deb = candidate_debs / filename
    if not candidate_deb.is_file():
        raise SystemExit(f"candidate DEB missing: {filename}")
    built_digest = hashlib.sha256(built_deb.read_bytes()).hexdigest()
    candidate_digest = hashlib.sha256(candidate_deb.read_bytes()).hexdigest()
    if built_digest != candidate_digest:
        raise SystemExit(f"non-reproducible candidate DEB: {filename}")
    package = subprocess.run(["dpkg-deb", "-f", str(built_deb), "Package"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    built_version = subprocess.run(["dpkg-deb", "-f", str(built_deb), "Version"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    architecture = subprocess.run(["dpkg-deb", "-f", str(built_deb), "Architecture"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    if (package, built_version, architecture) != (row["binary_package"], row["version"], row["architecture"]):
        raise SystemExit(f"binary metadata mismatch for {filename}")
    if built_version != version or row["source_package"] != source_name:
        raise SystemExit(f"source/version mismatch for {filename}")
    proof.append([str(order), source_name, package, filename, built_version, architecture, built_digest])

with out.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
    writer.writerow(header + ["sha256"])
    writer.writerows(proof)
PY

while IFS= read -r -d '' artifact; do
  cp -a "${artifact}" "${EVIDENCE}/"
done < <(find "${RESULT}" -maxdepth 1 -type f \( -name '*.build' -o -name '*.buildinfo' -o -name '*.changes' \) -print0)

{
  echo "AURORA_KSQ_1_REPRO_BUILD_STATUS=PASS"
  echo "AURORA_KSQ_1_REPRO_ORDER=${ORDER}"
  echo "AURORA_KSQ_1_REPRO_SOURCE=${source}"
  echo "AURORA_KSQ_1_REPRO_VERSION=${supra_version}"
  echo "AURORA_KSQ_1_REPRO_BYTE_IDENTICAL=yes"
  echo "AURORA_KSQ_1_FULL_CERTIFIED=no"
} > "${EVIDENCE}/status.env"
cat "${EVIDENCE}/status.env"
echo "AURORA_KSQ_1_REPRO_BUILD_SUCCESS order=${ORDER} source=${source}"
