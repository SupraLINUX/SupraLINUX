#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-support-materialization.json"
CONTRACTS="${ROOT}/manifests/kde-tier3-support-package-contracts.json"
NODE="${1:-}"
[[ -n "${NODE}" ]] || { echo "Usage: $0 <node>" >&2; exit 2; }

WORK="${ROOT}/.work/kde-tier3-support-materialization/${NODE}"
EVIDENCE="${ROOT}/evidence/kde-tier3-support-materialization/${NODE}"
LIST="${WORK}/debian.sources.list"
LISTS="${WORK}/apt-lists-debian"
REFERENCE="${WORK}/reference"
SOURCE_PARENT="${WORK}/source"
STATE=FAIL
STAGE=initialization

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${REFERENCE}" "${SOURCE_PARENT}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result() {
  local rc=$?
  python3 - "${EVIDENCE}/result.json" "${STATE}" "${rc}" "${STAGE}" "${NODE}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); d={}
if p.exists():
    try: d=json.loads(p.read_text())
    except Exception: d={}
d.update({
 "result":sys.argv[2],
 "exit_code":int(sys.argv[3]),
 "stage":sys.argv[4],
 "node":sys.argv[5],
 "package_attempted":False,
 "package_state_effect":"none",
})
p.write_text(json.dumps(d,indent=2)+"\n")
PY
}
trap write_result EXIT

. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }
python3 "${ROOT}/scripts/validate_kde_tier3_support_materialization.py"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends debian-archive-keyring dpkg-dev xz-utils

cat > "${LIST}" <<'EOF'
deb-src [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian sid main
EOF
sudo mkdir -p "${LISTS}"
sudo chown _apt:root "${LISTS}"
apt_opts=(-o "Dir::Etc::sourcelist=${LIST}" -o "Dir::Etc::sourceparts=-" -o "Dir::State::lists=${LISTS}" -o "APT::Get::List-Cleanup=0")
sudo apt-get "${apt_opts[@]}" update

mapfile -t cfg < <(python3 - "${MANIFEST}" "${CONTRACTS}" "${NODE}" <<'PY'
import json,sys
m=json.load(open(sys.argv[1])); c=json.load(open(sys.argv[2])); node=sys.argv[3]
if node not in m["selected_nodes"]: raise SystemExit(f"unknown support node {node}")
n=m["nodes"][node]; r=c["technical_references"][node]["debian"]
checks={x["file"]:x["sha256"] for x in r["checksums_sha256"]}
dsc=next(f for f in checks if f.endswith(".dsc"))
deb=next(f for f in checks if ".debian.tar." in f)
orig=next(f for f in checks if ".orig.tar." in f and not f.endswith(".asc"))
values=[
 n["source_package"],n["packaging_reference_version"],n["package_version"],
 n["upstream_version"],n["upstream_source_sha256"],
 dsc,checks[dsc],deb,checks[deb],orig,checks[orig],
 m["common_adaptations"]["maintainer"],
]
for v in values: print(v)
for p in n["expected_binary_packages"]: print("BIN="+p)
PY
)

SOURCE_PACKAGE="${cfg[0]}"
REFERENCE_VERSION="${cfg[1]}"
PACKAGE_VERSION="${cfg[2]}"
UPSTREAM_VERSION="${cfg[3]}"
UPSTREAM_SHA="${cfg[4]}"
DSC_FILE="${cfg[5]}"
DSC_SHA="${cfg[6]}"
DEBIAN_FILE="${cfg[7]}"
DEBIAN_SHA="${cfg[8]}"
ORIG_FILE="${cfg[9]}"
ORIG_SHA="${cfg[10]}"
MAINTAINER="${cfg[11]}"
EXPECTED_BINS=()
for value in "${cfg[@]:12}"; do EXPECTED_BINS+=("${value#BIN=}"); done

STAGE="source-download"
pushd "${REFERENCE}" >/dev/null
apt-get "${apt_opts[@]}" source --download-only "${SOURCE_PACKAGE}=${REFERENCE_VERSION}"
popd >/dev/null

for spec in "${DSC_FILE}:${DSC_SHA}" "${DEBIAN_FILE}:${DEBIAN_SHA}" "${ORIG_FILE}:${ORIG_SHA}"; do
  file="${spec%%:*}"; expected="${spec#*:}"
  actual="$(sha256sum "${REFERENCE}/${file}" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || { echo "SHA mismatch for ${file}" >&2; exit 1; }
done
[[ "${ORIG_SHA}" == "${UPSTREAM_SHA}" ]] || { echo "Debian orig tar differs from KDE authority source" >&2; exit 1; }

STAGE="source-extract"
SRC="${SOURCE_PARENT}/${SOURCE_PACKAGE}-${UPSTREAM_VERSION}"
dpkg-source -x "${REFERENCE}/${DSC_FILE}" "${SRC}" >/dev/null
cp -a "${REFERENCE}/${ORIG_FILE}" "${SOURCE_PARENT}/${ORIG_FILE}"

STAGE="packaging-adaptation"
python3 - "${SRC}/debian/control" "${SRC}/debian/changelog" "${NODE}" "${PACKAGE_VERSION}" "${MAINTAINER}" "${SOURCE_PACKAGE}" <<'PY'
import sys
from pathlib import Path

control=Path(sys.argv[1]); changelog=Path(sys.argv[2])
node=sys.argv[3]; version=sys.argv[4]; maintainer=sys.argv[5]; source_package=sys.argv[6]

text=control.read_text()
paragraphs=text.split("\n\n")
if not paragraphs: raise SystemExit("empty debian/control")
source=paragraphs[0]
lines=source.splitlines()
out=[]; skip_cont=False; seen_maint=False
for line in lines:
    if line.startswith(("Uploaders:","Vcs-Git:","Vcs-Browser:")):
        skip_cont=True
        continue
    if skip_cont and (line.startswith(" ") or line.startswith("\t")):
        continue
    skip_cont=False
    if line.startswith("Maintainer:"):
        out.append("Maintainer: "+maintainer); seen_maint=True
    else:
        out.append(line)
if not seen_maint: raise SystemExit("source Maintainer field missing")
source="\n".join(out)
old="debhelper-compat (= 14)"; new="debhelper-compat (= 13)"
if source.count(old)!=1: raise SystemExit(f"expected exactly one {old!r} in source paragraph")
source=source.replace(old,new)
paragraphs[0]=source
control.write_text("\n\n".join(paragraphs))

entry=f"""{source_package} ({version}) resolute; urgency=medium

  * SupraLINUX KDE Frameworks 6.30 support-component packaging.
  * Preserve KDE upstream source; adapt Debian 6.30 packaging to
    Ubuntu Resolute packaging-tool compatibility.

 -- SupraLINUX Build System <build@supralinux.invalid>  Tue, 22 Sep 2026 07:00:00 +0000

"""
changelog.write_text(entry+changelog.read_text())
PY

python3 - "${SRC}/debian/control" "${SRC}/debian/changelog" "${NODE}" "${PACKAGE_VERSION}" "${EXPECTED_BINS[@]}" <<'PY'
import re,subprocess,sys
control=sys.argv[1]; changelog_file=sys.argv[2]; node=sys.argv[3]; version=sys.argv[4]; expected=sys.argv[5:]
text=open(control).read()
if "debhelper-compat (= 14)" in text: raise SystemExit("debhelper compat 14 remains")
if "debhelper-compat (= 13)" not in text: raise SystemExit("debhelper compat 13 missing")
if "Uploaders:" in text or "Vcs-Git:" in text or "Vcs-Browser:" in text:
    raise SystemExit("reference maintainer/VCS metadata remains")
packages=re.findall(r"(?m)^Package:\s*(\S+)\s*$",text)
if packages!=expected:
    raise SystemExit(f"binary package set/order mismatch expected={expected} actual={packages}")
if node=="breeze-icons":
    required=[
      "Package: breeze-icon-theme","Package: breeze-icon-theme-rcc",
      "Package: kf6-breeze-icon-theme","Package: kf6-breeze-icon-theme-rcc",
      "Replaces: kf6-breeze-icon-theme (<< 6.28.0-3~)",
      "Breaks: kf6-breeze-icon-theme (<< 6.28.0-3~)",
      "breeze-icon-theme (>= ${source:Version})",
      "breeze-icon-theme-rcc (>= ${source:Version})",
    ]
    for token in required:
        if token not in text: raise SystemExit(f"Breeze transition contract missing: {token}")
changelog=subprocess.check_output(["dpkg-parsechangelog","-l"+changelog_file,"-S","Version"],text=True).strip()
if changelog!=version:
    raise SystemExit(f"changelog version mismatch {changelog} != {version}")
print("adapted source control contract: PASS")
PY

case "${NODE}" in
  breeze-icons)
    grep -F -- '-DBINARY_ICONS_RESOURCE=' "${SRC}/debian/rules"
    grep -F -- '-DWITH_ICON_GENERATION=' "${SRC}/debian/rules"
    grep -F -- '-DSKIP_INSTALL_ICONS=' "${SRC}/debian/rules"
    ;;
  kdoctools)
    grep -F -- '-DBUILD_QCH=ON' "${SRC}/debian/rules"
    ;;
  kded)
    grep -F -- '--without build_stamp' "${SRC}/debian/rules"
    ;;
esac

STAGE="source-package-build"
pushd "${SOURCE_PARENT}" >/dev/null
dpkg-source -b "${SRC}" >/dev/null
popd >/dev/null

NORMALIZED_VERSION="${PACKAGE_VERSION#*:}"
NEW_DSC="$(find "${SOURCE_PARENT}" -maxdepth 1 -type f -name "${SOURCE_PACKAGE}_${NORMALIZED_VERSION}.dsc" -print -quit)"
NEW_DEBIAN="$(find "${SOURCE_PARENT}" -maxdepth 1 -type f -name "${SOURCE_PACKAGE}_${NORMALIZED_VERSION}.debian.tar.*" -print -quit)"
[[ -n "${NEW_DSC}" && -n "${NEW_DEBIAN}" ]]

cp -a "${NEW_DSC}" "${NEW_DEBIAN}" "${SOURCE_PARENT}/${ORIG_FILE}" "${EVIDENCE}/"

STAGE=evidence
python3 - "${EVIDENCE}/result.json" "${NODE}" "${SOURCE_PACKAGE}" "${PACKAGE_VERSION}" "${UPSTREAM_SHA}" "${NEW_DSC}" "${NEW_DEBIAN}" "${SOURCE_PARENT}/${ORIG_FILE}" "${SRC}/debian/control" <<'PY'
import hashlib,json,sys
from pathlib import Path
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
result={
 "result":"PASS",
 "node":sys.argv[2],
 "source_package":sys.argv[3],
 "package_version":sys.argv[4],
 "package_attempted":False,
 "package_state_effect":"none",
 "orig_tar_sha256":sha(sys.argv[8]),
 "dsc_sha256":sha(sys.argv[6]),
 "debian_tar_sha256":sha(sys.argv[7]),
 "adapted_control_sha256":sha(sys.argv[9]),
 "debhelper_compat":"13",
}
if result["orig_tar_sha256"]!=sys.argv[5]: raise SystemExit("authoritative source hash changed")
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
PY

sha256sum "${EVIDENCE}"/*.dsc "${EVIDENCE}"/*.debian.tar.* "${EVIDENCE}"/*.orig.tar.* > "${EVIDENCE}/artifact-sha256.txt"

STATE=PASS
STAGE=complete
echo "Tier 3 support materialization ${NODE}: PASS"
