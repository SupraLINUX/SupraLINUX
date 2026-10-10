#!/usr/bin/env bash
# shellcheck disable=SC1090
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round16-diagnostic"
INPUTS="${WORK}/inputs"
APT_REPO="/tmp/supralinux-round16-repo"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round16-diagnostic"
RESULT="${EVIDENCE}/result.json"
DIAG_RESULT=DIAG_INFRA_FAIL
STAGE=initialization
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}" "${APT_REPO}"
mkdir -p "${INPUTS}" "${EVIDENCE}" "${APT_REPO}"
chmod 0755 "${APT_REPO}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

finish() {
  local rc="$1"
  local finished_at
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json,sys
from pathlib import Path
p,result,rc,stage,started,finished=sys.argv[1:]
Path(p).write_text(json.dumps({
 "schema":1,"node":"kio","round":16,"diagnostic_result":result,
 "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
 "claim":"non-promoting-kiconthemes-startup-kio-library-linkage-diagnostic",
 "package_attempted":False,"package_state_effect":"none"
},indent=2,sort_keys=True)+"\n")
PY
}
trap 'finish "$?"' EXIT

download_artifact() {
  local id="$1" sha="$2" dest="$3"
  mkdir -p "${dest}"
  local zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" -o "${zip}"
  printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}

STAGE=contract
python3 scripts/validate_kde_tier3_kio_round16_diagnostic.py

STAGE=host-tools
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential ca-certificates cmake curl dbus-daemon debhelper devscripts dpkg-dev equivs \
  g++ gzip ninja-build pkg-config python3 strace unzip xauth xvfb xz-utils qt6-svg-dev qt6-svg-plugins

STAGE=input-plan
python3 - "${LEVEL1}" "${EVIDENCE}/input-plan.tsv" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
n=m["nodes"]["kio"]
if n["package_version"]!="6.30.0-0supralinux7":
    raise SystemExit("unexpected KIO revision")
rows=[]
def add(i,c):
    rows.append((i,str(c["artifact_id"]),c["artifact_sha256"],c["version"]))
add("extra-cmake-modules",m["shared_predecessors"]["extra-cmake-modules"])
for i in n["retained_input_ids"]:
    add(i,m["retained_predecessors"][i])
if len({r[0] for r in rows})!=len(rows):
    raise SystemExit("duplicate input id")
Path(sys.argv[2]).write_text("\n".join("\t".join(r) for r in rows)+"\n")
PY

STAGE=source-download
download_artifact "10839162922" "ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c" "${INPUTS}/materialization"
DSC="$(find "${INPUTS}/materialization" -type f -name '*.dsc' -print -quit)"
[[ -n "${DSC}" && -s "${DSC}" ]]

STAGE=provider-download
TAB="$(printf '\t')"
while IFS="${TAB}" read -r input_id artifact_id artifact_sha version; do
  printf '%s\t%s\t%s\n' "${input_id}" "${version}" "${artifact_id}" >> "${EVIDENCE}/provider-plan.tsv"
  download_artifact "${artifact_id}" "${artifact_sha}" "${INPUTS}/${input_id}"
done < "${EVIDENCE}/input-plan.tsv"

STAGE=local-repository
find "${INPUTS}" -mindepth 2 -type f -name '*.deb' -exec cp -n {} "${APT_REPO}/" \;
(
  cd "${APT_REPO}"
  dpkg-scanpackages . /dev/null > Packages
  gzip -9c Packages > Packages.gz
  chmod 0644 Packages Packages.gz ./*.deb
)
echo "deb [trusted=yes] file:${APT_REPO} ./" | sudo tee /etc/apt/sources.list.d/supralinux-round16.list
sudo apt-get update

STAGE=source-extract
mkdir -p "${WORK}/source"
dpkg-source -x "${DSC}" "${WORK}/source/kio"
SRC="${WORK}/source/kio"
python3 - "${INPUTS}/materialization" <<'PY'
import json,sys
from pathlib import Path
xs=list(Path(sys.argv[1]).rglob("result.json"))
if len(xs)!=1: raise SystemExit("materialization result ambiguity")
r=json.loads(xs[0].read_text())
if r.get("result")!="PASS" or r.get("package_attempted") is not False or r.get("package_version")!="6.30.0-0supralinux7":
    raise SystemExit("source materialization identity drift")
PY

STAGE=build-dependencies
cd "${SRC}"
sudo mk-build-deps --install --remove --tool 'apt-get -y --no-install-recommends' debian/control
dpkg-checkbuilddeps |& tee "${EVIDENCE}/build-deps.txt"

STAGE=configure
export DEB_BUILD_OPTIONS="parallel=2"
debian/rules override_dh_auto_configure |& tee "${EVIDENCE}/configure.log"
OBJ="${SRC}/obj-$(dpkg-architecture -qDEB_HOST_GNU_TYPE)"
[[ -d "${OBJ}" ]]

STAGE=target-build
cmake --build "${OBJ}" --target kio_file kioworker kdirmodeltest knewfilemenutest --parallel 2 |& tee "${EVIDENCE}/target-build.log"
[[ -f "${OBJ}/bin/kf6/kio/kio_file.so" ]]
[[ -x "${OBJ}/bin/kioworker" ]]
[[ -x "${OBJ}/bin/kdirmodeltest" && -x "${OBJ}/bin/knewfilemenutest" ]]
export PATH="${OBJ}/bin:${PATH}"
ctest --test-dir "${OBJ}" -N -V -R '^(kiowidgets-kdirmodeltest|kiofilewidgets-knewfilemenutest)$' > "${EVIDENCE}/ctest-definition.txt"


source "${ROOT}/scripts/run-kde-tier3-kio-round16-probe-build.sh"
