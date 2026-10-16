#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round22-diagnostic"
INPUTS="${WORK}/inputs"
APT_REPO="/tmp/supralinux-round22-repo"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round22-diagnostic"
RESULT="${EVIDENCE}/result.json"
VISIBLE_ROOT="$(dirname "$(dirname "${GITHUB_WORKSPACE}")")/supralinux-krecent-visible-round22"
STAGE=initialization
DIAG_RESULT=DIAG_INFRA_FAIL
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}" "${APT_REPO}" "${VISIBLE_ROOT}"
mkdir -p "${INPUTS}" "${EVIDENCE}/xbels" "${APT_REPO}" "${VISIBLE_ROOT}/source"
chmod 0755 "${APT_REPO}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

finish() {
  local rc="$1" finished_at
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ -f "${EVIDENCE}/classification.json" ]]; then cp "${EVIDENCE}/classification.json" "${RESULT}"
  else
    python3 - "${RESULT}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json,sys
from pathlib import Path
p,result,rc,stage,started,finished=sys.argv[1:]
Path(p).write_text(json.dumps({"schema":1,"node":"kio","round":22,"diagnostic_result":result,
 "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
 "claim":"non-promoting-krecent-ctest-home-matrix-diagnostic","package_attempted":False,
 "package_state_effect":"none"},indent=2,sort_keys=True)+"\n")
PY
  fi
}
trap 'finish "$?"' EXIT

download_artifact() {
  local id="$1" sha="$2" dest="$3" zip
  mkdir -p "${dest}"; zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" -o "${zip}"
  printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}

audit_visible_path() {
  python3 - "$@" <<'PY'
import sys
from pathlib import Path
for raw in sys.argv[1:]:
    p=Path(raw).resolve()
    hidden=[x for x in p.parts if x.startswith(".") and x not in (".","..")]
    if hidden: raise SystemExit(f"hidden component in visible path {p}: {hidden}")
    if str(p)=="/tmp" or str(p).startswith("/tmp/"): raise SystemExit(f"visible path unexpectedly under /tmp: {p}")
    print(p)
PY
}

STAGE=contract
python3 scripts/validate_kde_tier3_kio_round22_diagnostic.py

STAGE=host-tools
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential ca-certificates cmake curl dbus-daemon debhelper devscripts dpkg-dev equivs \
  g++ gzip ninja-build pkg-config python3 unzip xauth xvfb xz-utils

STAGE=input-plan
python3 - "${LEVEL1}" "${EVIDENCE}/input-plan.tsv" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text()); n=m["nodes"]["kio"]
if n["package_version"]!="6.30.0-0supralinux8": raise SystemExit("unexpected KIO revision")
rows=[]
def add(i,c): rows.append((i,str(c["artifact_id"]),c["artifact_sha256"],c["version"]))
add("extra-cmake-modules",m["shared_predecessors"]["extra-cmake-modules"])
for i in n["retained_input_ids"]: add(i,m["retained_predecessors"][i])
if len({r[0] for r in rows})!=len(rows): raise SystemExit("duplicate input id")
Path(sys.argv[2]).write_text("\n".join("\t".join(r) for r in rows)+"\n")
PY

STAGE=source-download
download_artifact "10898999142" "c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d" "${INPUTS}/materialization"
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
( cd "${APT_REPO}"; dpkg-scanpackages . /dev/null > Packages; gzip -9c Packages > Packages.gz; chmod 0644 Packages Packages.gz ./*.deb )
echo "deb [trusted=yes] file:${APT_REPO} ./" | sudo tee /etc/apt/sources.list.d/supralinux-round22.list
sudo apt-get update

STAGE=source-extract
SRC="${VISIBLE_ROOT}/source/kio"
dpkg-source -x "${DSC}" "${SRC}"
audit_visible_path "${VISIBLE_ROOT}" "${SRC}" | tee "${EVIDENCE}/visible-path-audit.txt"
RECENT_SRC="${SRC}/autotests/krecentdocumenttest.cpp"
cp "${RECENT_SRC}" "${EVIDENCE}/krecentdocumenttest.cpp.original"
sha256sum "${RECENT_SRC}" | tee "${EVIDENCE}/source-before.sha256"

STAGE=build-dependencies
cd "${SRC}"
sudo mk-build-deps --install --remove --tool 'apt-get -y --no-install-recommends' debian/control
dpkg-checkbuilddeps |& tee "${EVIDENCE}/build-deps.txt"

STAGE=configure
export DEB_BUILD_OPTIONS="parallel=2"
debian/rules override_dh_auto_configure |& tee "${EVIDENCE}/configure.log"
OBJ="${SRC}/obj-$(dpkg-architecture -qDEB_HOST_GNU_TYPE)"
CWD="${OBJ}/autotests"
audit_visible_path "${OBJ}" "${CWD}" >> "${EVIDENCE}/visible-path-audit.txt"

STAGE=instrument
python3 - "${RECENT_SRC}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text()
start=s.index("void KRecentDocumentTest::testXbelBookmarkMaxEntries()")
end=s.index("\n}\n",start)+3
block=s[start:end]
old="    const auto recentUrls = KRecentDocument::recentUrls();\n"
new=old+'''    const QString capturePath = qEnvironmentVariable("SUPRALINUX_CAPTURE_XBEL");
    if (!capturePath.isEmpty()) {
        QFile::remove(capturePath);
        QFile::copy(m_xbelPath, capturePath);
    }
'''
if old not in block: raise SystemExit("capture instrumentation anchor missing")
block=block.replace(old,new,1)
p.write_text(s[:start]+block+s[end:])
PY
cmake --build "${OBJ}" --target krecentdocumenttest --parallel 2 |& tee "${EVIDENCE}/target-build.log"
[[ -x "${OBJ}/bin/krecentdocumenttest" ]]

record_capture() {
  local mode="$1" run="$2" rc="$3" cap="$4" home="$5" style="$6"
  python3 - "${EVIDENCE}/runs.jsonl" "${mode}" "${run}" "${rc}" "${cap}" "${home}" "${style}" <<'PY'
import collections,json,sys,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path
out,mode,run,rc,cap,home,style=sys.argv[1:]
p=Path(cap)
row={"mode":mode,"run":int(run),"rc":int(rc),"capture_exists":p.is_file(),"capture":cap,"home":home,"style":style,
     "entries":[],"duplicate_modified_groups":0}
if p.is_file():
    root=ET.parse(p).getroot()
    for e in root.iter():
        if str(e.tag).endswith("bookmark") and "href" in e.attrib:
            row["entries"].append({"file":urllib.parse.unquote(e.attrib["href"]).rstrip("/").split("/")[-1],
                                   "modified":e.attrib.get("modified","")})
    counts=collections.Counter(x["modified"] for x in row["entries"] if x["modified"])
    row["duplicate_modified_groups"]=sum(1 for n in counts.values() if n>1)
with open(out,"a",encoding="utf-8") as f: f.write(json.dumps(row,sort_keys=True)+"\n")
PY
}

run_mode() {
  local mode="$1" style="$2" home_kind="$3" i home cap log rc
  : > "${EVIDENCE}/${mode}.tsv"
  for ((i=1;i<=30;i++)); do
    if [[ "${home_kind}" == hidden ]]; then
      home="${SRC}/debian/.supralinux-test-home/sbuild"
    else
      home="${VISIBLE_ROOT}/homes/${mode}-${i}/sbuild"
      audit_visible_path "${home}" >> "${EVIDENCE}/visible-path-audit.txt"
    fi
    rm -rf "${home}"; mkdir -p "${home}"
    rm -f "${CWD}"/temp\ File*
    cap="${EVIDENCE}/xbels/${mode}-${i}.xbel"; rm -f "${cap}"
    log="${EVIDENCE}/${mode}-${i}.log"
    set +e
    if [[ "${style}" == ctest ]]; then
      (
        cd "${OBJ}"
        env -u XDG_DATA_HOME -u XDG_CONFIG_HOME -u XDG_CACHE_HOME -u XDG_RUNTIME_DIR \
          HOME="${home}" LANG=C.UTF-8 LC_ALL=C.UTF-8 LOGNAME=sbuild USER=sbuild \
          QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze KDECI_PLATFORM_PATH="${SRC}" \
          SUPRALINUX_CAPTURE_XBEL="${cap}" \
          dbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24" \
          ctest --verbose -R '^kiocore-krecentdocumenttest$' -j1
      ) >"${log}" 2>&1
    else
      (
        cd "${CWD}"
        env -u XDG_DATA_HOME -u XDG_CONFIG_HOME -u XDG_CACHE_HOME -u XDG_RUNTIME_DIR \
          HOME="${home}" LANG=C.UTF-8 LC_ALL=C.UTF-8 LOGNAME=sbuild USER=sbuild \
          QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze KDECI_PLATFORM_PATH="${SRC}" \
          QT_PLUGIN_PATH="${OBJ}/bin" SUPRALINUX_CAPTURE_XBEL="${cap}" \
          dbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24" \
          "${OBJ}/bin/krecentdocumenttest" testXbelBookmarkMaxEntries
      ) >"${log}" 2>&1
    fi
    rc=$?; set -e
    printf '%s\t%s\n' "${i}" "${rc}" >> "${EVIDENCE}/${mode}.tsv"
    record_capture "${mode}" "${i}" "${rc}" "${cap}" "${home}" "${style}"
  done
}

STAGE=matrix-direct-visible
run_mode direct-visible direct visible
STAGE=matrix-direct-hidden
run_mode direct-hidden direct hidden
STAGE=matrix-ctest-visible
run_mode ctest-visible ctest visible
STAGE=matrix-ctest-hidden
run_mode ctest-hidden ctest hidden

STAGE=restore
cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT_SRC}"
sha256sum "${RECENT_SRC}" | tee "${EVIDENCE}/source-after.sha256"
cmp -s "${RECENT_SRC}" "${EVIDENCE}/krecentdocumenttest.cpp.original"

STAGE=classification
python3 - "${EVIDENCE}" "${STARTED_AT}" <<'PY'
import json,sys
from pathlib import Path
ev=Path(sys.argv[1]); started=sys.argv[2]
rows=[json.loads(x) for x in (ev/"runs.jsonl").read_text().splitlines() if x.strip()]
modes=["direct-visible","direct-hidden","ctest-visible","ctest-hidden"]
summary={}
for mode in modes:
    xs=[x for x in rows if x["mode"]==mode]
    def sig(x):
        log=(ev/f"{mode}-{x['run']}.log").read_text(errors="replace")
        return x["rc"]!=0 and "temp File 11" in log and "temp File 12" in log
    summary[mode]={
      "runs":len(xs),"failures":sum(x["rc"]!=0 for x in xs),
      "attempt8_signature_failures":sum(sig(x) for x in xs),
      "valid_captures":sum(x["capture_exists"] and len(x["entries"])==3 for x in xs),
      "duplicate_modified_runs":sum(x["duplicate_modified_groups"]>0 for x in xs),
    }
valid=all(v["runs"]==30 and v["valid_captures"]==30 for v in summary.values())
dv,dh,cv,ch=[summary[x]["attempt8_signature_failures"] for x in modes]
if not valid:
    conclusion="DIAG_INVALID-krecent-ctest-home-matrix"
elif ch>0 and cv==0 and dh==0:
    conclusion="krecentdocument-ctest-hidden-home-combination-reproduces-attempt8"
elif dh>0 and dv==0 and cv==0:
    conclusion="krecentdocument-hidden-home-controls-attempt8-signature"
elif (cv>0 or ch>0) and dv==0 and dh==0:
    conclusion="krecentdocument-ctest-suite-context-controls-attempt8-signature"
elif dv==0 and dh==0 and cv==0 and ch==0:
    conclusion="krecentdocument-attempt8-failure-not-reproduced-outside-sbuild"
else:
    conclusion="krecentdocument-matrix-mixed-reproduction"

result={"schema":1,"node":"kio","round":22,"diagnostic_result":"DIAG_COMPLETE",
 "claim":"non-promoting-krecent-ctest-home-matrix-diagnostic","package_attempted":False,
 "package_state_effect":"none","canonical_source_modified":False,"test_suppression":False,
 "environment_valid":valid,"matrix":summary,"conclusion":conclusion,
 "next_scope":"sbuild-contained-krecent-diagnostic-if-attempt8-remains-unreproduced-otherwise-confirm-controlling-factor",
 "started_at":started}
(ev/"classification.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
PY
DIAG_RESULT=DIAG_COMPLETE
STAGE=complete
