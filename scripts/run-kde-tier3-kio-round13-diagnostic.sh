#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-kio-round13-diagnostic.json"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round13-diagnostic"
INPUTS="${WORK}/inputs"
LOCAL_REPO="${WORK}/repo"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round13-diagnostic"
RESULT="${EVIDENCE}/result.json"
DIAG_RESULT=DIAG_INFRA_FAIL
STAGE=initialization
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${INPUTS}" "${LOCAL_REPO}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

finish() {
  local rc=$? done
  done="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${done}" <<'PY'
import json,sys
from pathlib import Path
p,result,rc,stage,started,done=sys.argv[1:]
Path(p).write_text(json.dumps({
 "schema":1,"node":"kio","round":13,"diagnostic_result":result,
 "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":done,
 "claim":"non-promoting-kio-build-tree-process-diagnostic",
 "package_attempted":False,"package_state_effect":"none"
},indent=2,sort_keys=True)+"\n")
PY
}
trap finish EXIT

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
python3 scripts/validate_kde_tier3_kio_round13_diagnostic.py

STAGE=host-tools
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential ca-certificates cmake curl dbus-daemon debhelper devscripts dpkg-dev equivs \
  g++ gzip ninja-build pkg-config python3 strace unzip xauth xvfb xz-utils

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
while IFS=$'\t' read -r input_id artifact_id artifact_sha version; do
  download_artifact "${artifact_id}" "${artifact_sha}" "${INPUTS}/${input_id}"
done < "${EVIDENCE}/input-plan.tsv"

STAGE=local-repository
find "${INPUTS}" -mindepth 2 -type f -name '*.deb' -exec cp -n {} "${LOCAL_REPO}/" \;
( cd "${LOCAL_REPO}" && dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz )
echo "deb [trusted=yes] file:${LOCAL_REPO} ./" | sudo tee /etc/apt/sources.list.d/supralinux-round13.list
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
cmake --build "${OBJ}" --target kdirmodeltest knewfilemenutest --parallel 2 |& tee "${EVIDENCE}/target-build.log"
[[ -x "${OBJ}/bin/kdirmodeltest" && -x "${OBJ}/bin/knewfilemenutest" ]]
ctest --test-dir "${OBJ}" -N -V -R '^(kiowidgets-kdirmodeltest|kiofilewidgets-knewfilemenutest)$' > "${EVIDENCE}/ctest-definition.txt"

HOME_BASE="${WORK}/homes"
mkdir -p "${HOME_BASE}"

run_ctest_exact() {
  local label=ctest-exact-attempt7-environment
  mkdir -p "${HOME_BASE}/${label}"
  set +e
  HOME="${HOME_BASE}/${label}" KDECI_PLATFORM_PATH="${SRC}" \
  QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze \
  dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' \
    ctest --test-dir "${OBJ}" --verbose -j1 -R '^(kiowidgets-kdirmodeltest|kiofilewidgets-knewfilemenutest)$' \
    > "${EVIDENCE}/${label}.log" 2>&1
  echo "$?" > "${EVIDENCE}/${label}.rc"
  set -e
}

run_direct_pair() {
  local label="$1"; shift
  local home="${HOME_BASE}/${label}"
  mkdir -p "${home}"
  : > "${EVIDENCE}/${label}.log"
  local overall=0
  for bin in kdirmodeltest knewfilemenutest; do
    set +e
    env HOME="${home}" KDECI_PLATFORM_PATH="${SRC}" \
      QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze QT_PLUGIN_PATH="${OBJ}/bin" \
      "$@" dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' "${OBJ}/bin/${bin}" \
      >> "${EVIDENCE}/${label}.log" 2>&1
    rc=$?
    set -e
    [[ "${rc}" -eq 0 ]] || overall=1
  done
  echo "${overall}" > "${EVIDENCE}/${label}.rc"
}

STAGE=variant-execution
run_ctest_exact
run_direct_pair direct-exact-attempt7-environment
run_direct_pair direct-without-qt-plugin-path env -u QT_PLUGIN_PATH
run_direct_pair direct-without-kdeci-platform-path env -u KDECI_PLATFORM_PATH
run_direct_pair direct-with-explicit-xdg-data-dirs env XDG_DATA_DIRS=/usr/local/share:/usr/share

STAGE=trace-exact
for bin in kdirmodeltest knewfilemenutest; do
  label="trace-${bin}"
  mkdir -p "${HOME_BASE}/${label}"
  set +e
  HOME="${HOME_BASE}/${label}" KDECI_PLATFORM_PATH="${SRC}" \
  QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze QT_PLUGIN_PATH="${OBJ}/bin" QT_DEBUG_PLUGINS=1 \
  dbus-run-session -- xvfb-run -a -s '-screen 0 1280x1024x24' \
    strace -f -e trace=file -o "${EVIDENCE}/${label}.strace" "${OBJ}/bin/${bin}" \
    > "${EVIDENCE}/${label}.log" 2>&1
  echo "$?" > "${EVIDENCE}/${label}.rc"
  set -e
done

STAGE=classification
python3 - "${EVIDENCE}" <<'PY'
import json,re,sys
from pathlib import Path
ev=Path(sys.argv[1])
variants=[
 "ctest-exact-attempt7-environment",
 "direct-exact-attempt7-environment",
 "direct-without-qt-plugin-path",
 "direct-without-kdeci-platform-path",
 "direct-with-explicit-xdg-data-dirs",
]
def classify(name):
    text=(ev/f"{name}.log").read_text(errors="replace")
    rc=int((ev/f"{name}.rc").read_text().strip())
    kd_empty='Actual   (icon2.name()): ""' in text
    kn_empty='Actual   (iconLabel->property("iconName").toString()): ""' in text
    return {"rc":rc,"kdirmodel_empty_icon":kd_empty,"knewfilemenu_empty_icon":kn_empty,
            "both_primary_failures":kd_empty and kn_empty}
r={x:classify(x) for x in variants}
exact=r["direct-exact-attempt7-environment"]["both_primary_failures"]
def recovered(name):
    x=r[name]
    return exact and not x["kdirmodel_empty_icon"] and not x["knewfilemenu_empty_icon"] and x["rc"]==0
if not exact:
    conclusion="host-build-tree-does-not-reproduce-next-sbuild-unshare"
elif recovered("direct-without-qt-plugin-path"):
    conclusion="QT_PLUGIN_PATH-delta"
elif recovered("direct-without-kdeci-platform-path"):
    conclusion="KDECI_PLATFORM_PATH-delta"
elif recovered("direct-with-explicit-xdg-data-dirs"):
    conclusion="XDG_DATA_DIRS-delta"
else:
    conclusion="build-tree-reproduces-no-simple-env-recovery-inspect-traces"
trace={}
for bin in ("kdirmodeltest","knewfilemenutest"):
    s=(ev/f"trace-{bin}.strace").read_text(errors="replace")
    trace[bin]={
      "mentions_breeze":"/usr/share/icons/breeze" in s,
      "mentions_index_theme":"/usr/share/icons/breeze/index.theme" in s,
      "mentions_unknown":bool(re.search(r"/usr/share/icons/breeze/.*unknown",s)),
      "mentions_inode_directory":bool(re.search(r"/usr/share/icons/breeze/.*inode-directory",s)),
    }
(ev/"findings.json").write_text(json.dumps({
 "result":"DIAG_COMPLETE","package_attempted":False,"package_state_effect":"none",
 "variants":r,"trace_summary":trace,"conclusion":conclusion
},indent=2,sort_keys=True)+"\n")
print(conclusion)
PY

STAGE=complete
DIAG_RESULT=DIAG_COMPLETE
echo "KIO Round 13 build-tree diagnostic: COMPLETE (non-promoting)"
