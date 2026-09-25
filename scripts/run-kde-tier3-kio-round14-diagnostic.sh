#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round14-diagnostic"
INPUTS="${WORK}/inputs"
APT_REPO="/tmp/supralinux-round14-repo"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round14-diagnostic"
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
Path(p).write_text(json.dumps({"schema":1,"node":"kio","round":14,"diagnostic_result":result,"exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,"claim":"non-promoting-kiconthemes-engine-provider-diagnostic","package_attempted":False,"package_state_effect":"none"},indent=2,sort_keys=True)+"\n")
PY
}
trap 'finish "$?"' EXIT
download_artifact() {
  local id="$1" sha="$2" dest="$3"
  mkdir -p "${dest}"
  local zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" -o "${zip}"
  printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}
STAGE=contract
python3 scripts/validate_kde_tier3_kio_round14_diagnostic.py
STAGE=host-tools
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends build-essential ca-certificates cmake curl dbus-daemon debhelper devscripts dpkg-dev equivs g++ gzip pkg-config python3 unzip xauth xvfb xz-utils
STAGE=input-plan
python3 - "${LEVEL1}" "${EVIDENCE}/input-plan.tsv" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
n=m["nodes"]["kio"]
if n["package_version"]!="6.30.0-0supralinux7": raise SystemExit("unexpected KIO revision")
rows=[]
def add(i,c): rows.append((i,str(c["artifact_id"]),c["artifact_sha256"],c["version"]))
add("extra-cmake-modules",m["shared_predecessors"]["extra-cmake-modules"])
for i in n["retained_input_ids"]: add(i,m["retained_predecessors"][i])
if "kiconthemes" not in {x[0] for x in rows}: raise SystemExit("kiconthemes missing from retained KIO closure")
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
STAGE=engine-provider-proof
ENGINE_ARTIFACT_ID="$(awk -F '\t' '$1=="kiconthemes"{print $3}' "${EVIDENCE}/provider-plan.tsv")"
[[ "${ENGINE_ARTIFACT_ID}" == "10731249726" ]]
ENGINE_DEB="$(find "${INPUTS}/kiconthemes" -type f -name 'libkf6iconthemes-bin_*_amd64.deb' -print -quit)"
[[ -n "${ENGINE_DEB}" && -s "${ENGINE_DEB}" ]]
printf '%s  %s\n' '6806b7b03b3f30d21620c315118066c9c7f35714e6a12e0b3360e01cbcfaff0c' "${ENGINE_DEB}" | sha256sum --check --strict
dpkg-deb -f "${ENGINE_DEB}" Package Version Architecture | tee "${EVIDENCE}/engine-provider-control.txt"
STAGE=local-repository
find "${INPUTS}" -mindepth 2 -type f -name '*.deb' -exec cp -n {} "${APT_REPO}/" \;
( cd "${APT_REPO}" && dpkg-scanpackages . /dev/null > Packages && gzip -9c Packages > Packages.gz && chmod 0644 Packages Packages.gz ./*.deb )
echo "deb [trusted=yes] file:${APT_REPO} ./" | sudo tee /etc/apt/sources.list.d/supralinux-round14.list
sudo apt-get update
STAGE=source-extract
mkdir -p "${WORK}/source"
dpkg-source -x "${DSC}" "${WORK}/source/kio"
SRC="${WORK}/source/kio"
STAGE=build-dependencies
cd "${SRC}"
sudo mk-build-deps --install --remove --tool 'apt-get -y --no-install-recommends' debian/control
dpkg-checkbuilddeps |& tee "${EVIDENCE}/build-deps.txt"
if dpkg-query -W -f='${Status}\n' libkf6iconthemes-bin 2>/dev/null | grep -q 'install ok installed'; then echo "libkf6iconthemes-bin unexpectedly installed in baseline" >&2; exit 2; fi
STAGE=configure
export DEB_BUILD_OPTIONS="parallel=2"
debian/rules override_dh_auto_configure |& tee "${EVIDENCE}/configure.log"
OBJ="${SRC}/obj-$(dpkg-architecture -qDEB_HOST_GNU_TYPE)"
[[ -d "${OBJ}" ]]
STAGE=target-build
cmake --build "${OBJ}" --target kio_file kioworker kdirmodeltest knewfilemenutest --parallel 2 |& tee "${EVIDENCE}/target-build.log"
[[ -f "${OBJ}/bin/kf6/kio/kio_file.so" && -x "${OBJ}/bin/kioworker" && -x "${OBJ}/bin/kdirmodeltest" && -x "${OBJ}/bin/knewfilemenutest" ]]
export PATH="${OBJ}/bin:${PATH}"
TEST_TIMEOUT_SECONDS=180
HOME_BASE="${WORK}/homes"
mkdir -p "${HOME_BASE}"
run_direct_pair() {
  local label="$1" debug_plugins="$2" home="${HOME_BASE}/$1"
  local bin test_case rc overall=0
  mkdir -p "${home}"; : > "${EVIDENCE}/${label}.log"
  for bin in kdirmodeltest knewfilemenutest; do
    case "${bin}" in kdirmodeltest) test_case=testIcon ;; knewfilemenutest) test_case=testFolderIconCollection ;; *) return 2 ;; esac
    set +e
    HOME="${home}" KDECI_PLATFORM_PATH="${SRC}" QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze QT_PLUGIN_PATH="${OBJ}/bin" QT_DEBUG_PLUGINS="${debug_plugins}" timeout --signal=TERM --kill-after=10s "${TEST_TIMEOUT_SECONDS}s" dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' "${OBJ}/bin/${bin}" "${test_case}" >> "${EVIDENCE}/${label}.log" 2>&1
    rc=$?; set -e
    printf '%s\t%s\n' "${bin}" "${rc}" >> "${EVIDENCE}/${label}.rc.tsv"
    [[ "${rc}" -eq 0 ]] || overall=1
  done
  echo "${overall}" > "${EVIDENCE}/${label}.rc"
}
run_ctest_pair() {
  local label="$1" home="${HOME_BASE}/$1"
  mkdir -p "${home}"; set +e
  HOME="${home}" KDECI_PLATFORM_PATH="${SRC}" QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze timeout --signal=TERM --kill-after=10s "${TEST_TIMEOUT_SECONDS}s" dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' ctest --test-dir "${OBJ}" --verbose -j1 -R '^(kiowidgets-kdirmodeltest|kiofilewidgets-knewfilemenutest)$' > "${EVIDENCE}/${label}.log" 2>&1
  echo "$?" > "${EVIDENCE}/${label}.rc"; set -e
}
STAGE=baseline
run_direct_pair baseline-direct 0
run_ctest_pair baseline-ctest
STAGE=provider-install
sudo apt-get install -y --no-install-recommends "${ENGINE_DEB}"
[[ "$(dpkg-query -W -f='${Version}' libkf6iconthemes-bin)" == "6.30.0-0supralinux3" ]]
PLUGIN='/usr/lib/x86_64-linux-gnu/qt6/plugins/kiconthemes6/iconengines/KIconEnginePlugin.so'
[[ -f "${PLUGIN}" ]]
sha256sum "${PLUGIN}" | tee "${EVIDENCE}/engine-plugin-sha256.txt"
STAGE=provider-treatment
run_direct_pair provider-direct 1
run_ctest_pair provider-ctest
STAGE=classification
python3 - "${EVIDENCE}" <<'PY'
import json,sys
from pathlib import Path
ev=Path(sys.argv[1])
def load(name):
    text=(ev/f"{name}.log").read_text(errors="replace"); rc=int((ev/f"{name}.rc").read_text().strip())
    return {"rc":rc,"kdirmodel_empty_icon":'Actual   (icon2.name()): ""' in text,"knewfilemenu_empty_icon":'Actual   (iconLabel->property("iconName").toString()): ""' in text,"plugin_seen":"KIconEnginePlugin.so" in text}
b,bc,p,pc=(load(x) for x in ("baseline-direct","baseline-ctest","provider-direct","provider-ctest"))
baseline_reproduces=b["kdirmodel_empty_icon"] and b["knewfilemenu_empty_icon"] and b["rc"]!=0
provider_recovers=p["rc"]==0 and pc["rc"]==0 and not p["kdirmodel_empty_icon"] and not p["knewfilemenu_empty_icon"]
if not baseline_reproduces: conclusion,result="baseline-drift-invalid","DIAG_INVALID"
elif provider_recovers: conclusion,result="libkf6iconthemes-bin-recovers-both-kio-tests","DIAG_COMPLETE"
else: conclusion,result="libkf6iconthemes-bin-does-not-recover-both-kio-tests","DIAG_COMPLETE"
(ev/"findings.json").write_text(json.dumps({"result":result,"package_attempted":False,"package_state_effect":"none","baseline":{"direct":b,"ctest":bc},"provider":{"direct":p,"ctest":pc},"provider_plugin_seen":p["plugin_seen"],"conclusion":conclusion},indent=2,sort_keys=True)+"\n")
print(conclusion)
if result!="DIAG_COMPLETE": raise SystemExit(3)
PY
STAGE=complete
DIAG_RESULT=DIAG_COMPLETE
echo "KIO Round 14 KIconThemes engine-provider diagnostic: COMPLETE (non-promoting)"
