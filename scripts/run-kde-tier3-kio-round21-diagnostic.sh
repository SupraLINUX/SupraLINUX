#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round21-diagnostic"
INPUTS="${WORK}/inputs"
APT_REPO="/tmp/supralinux-round21-repo"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round21-diagnostic"
RESULT="${EVIDENCE}/result.json"
VISIBLE_ROOT="$(dirname "$(dirname "${GITHUB_WORKSPACE}")")/supralinux-krecent-visible-round21"
STAGE=initialization
DIAG_RESULT=DIAG_INFRA_FAIL
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}" "${APT_REPO}" "${VISIBLE_ROOT}"
mkdir -p "${INPUTS}" "${EVIDENCE}" "${APT_REPO}" "${VISIBLE_ROOT}"
chmod 0755 "${APT_REPO}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

finish() {
  local rc="$1" finished_at
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ -f "${EVIDENCE}/classification.json" ]]; then
    cp "${EVIDENCE}/classification.json" "${RESULT}"
  else
    python3 - "${RESULT}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json,sys
from pathlib import Path
p,result,rc,stage,started,finished=sys.argv[1:]
Path(p).write_text(json.dumps({
 "schema":1,"node":"kio","round":21,"diagnostic_result":result,
 "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
 "claim":"non-promoting-krecent-visible-cwd-timestamp-ordering-diagnostic",
 "package_attempted":False,"package_state_effect":"none"
},indent=2,sort_keys=True)+"\n")
PY
  fi
}
trap 'finish "$?"' EXIT

download_artifact() {
  local id="$1" sha="$2" dest="$3" zip
  mkdir -p "${dest}"
  zip="${dest}.zip"
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
    hidden=[part for part in p.parts if part.startswith(".") and part not in (".","..")]
    if hidden: raise SystemExit(f"hidden path component in {p}: {hidden}")
    if str(p)=="/tmp" or str(p).startswith("/tmp/"): raise SystemExit(f"path is under /tmp: {p}")
    print(p)
PY
}

STAGE=contract
python3 scripts/validate_kde_tier3_kio_round21_diagnostic.py

STAGE=host-tools
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential ca-certificates cmake curl debhelper devscripts dpkg-dev equivs \
  g++ gzip ninja-build pkg-config python3 unzip xz-utils

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
python3 - "${INPUTS}/materialization" <<'PY'
import json,sys
from pathlib import Path
xs=list(Path(sys.argv[1]).rglob("result.json"))
if len(xs)!=1: raise SystemExit("materialization result ambiguity")
r=json.loads(xs[0].read_text())
if r.get("result")!="PASS" or r.get("package_attempted") is not False or r.get("package_version")!="6.30.0-0supralinux8":
    raise SystemExit("source materialization identity drift")
PY

STAGE=provider-download
TAB="$(printf '\t')"
while IFS="${TAB}" read -r input_id artifact_id artifact_sha version; do
  printf '%s\t%s\t%s\n' "${input_id}" "${version}" "${artifact_id}" >> "${EVIDENCE}/provider-plan.tsv"
  download_artifact "${artifact_id}" "${artifact_sha}" "${INPUTS}/${input_id}"
done < "${EVIDENCE}/input-plan.tsv"

STAGE=local-repository
find "${INPUTS}" -mindepth 2 -type f -name '*.deb' -exec cp -n {} "${APT_REPO}/" \;
( cd "${APT_REPO}"; dpkg-scanpackages . /dev/null > Packages; gzip -9c Packages > Packages.gz; chmod 0644 Packages Packages.gz ./*.deb )
echo "deb [trusted=yes] file:${APT_REPO} ./" | sudo tee /etc/apt/sources.list.d/supralinux-round21.list
sudo apt-get update

STAGE=source-extract
mkdir -p "${WORK}/source"
dpkg-source -x "${DSC}" "${WORK}/source/kio"
SRC="${WORK}/source/kio"
RECENT_SRC="${SRC}/autotests/krecentdocumenttest.cpp"
cp "${RECENT_SRC}" "${EVIDENCE}/krecentdocumenttest.cpp.original"
sha256sum "${RECENT_SRC}" | tee "${EVIDENCE}/krecentdocument-source-before.sha256"

STAGE=build-dependencies
cd "${SRC}"
sudo mk-build-deps --install --remove --tool 'apt-get -y --no-install-recommends' debian/control
dpkg-checkbuilddeps |& tee "${EVIDENCE}/build-deps.txt"

STAGE=configure
export DEB_BUILD_OPTIONS="parallel=2"
debian/rules override_dh_auto_configure |& tee "${EVIDENCE}/configure.log"
OBJ="${SRC}/obj-$(dpkg-architecture -qDEB_HOST_GNU_TYPE)"
[[ -d "${OBJ}" ]]
export PATH="${OBJ}/bin:${PATH}"

apply_preserve_instrumentation() {
  python3 - "${RECENT_SRC}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text()
old='''void KRecentDocumentTest::cleanup()
{
    QFile(m_xbelPath).remove();
'''
new='''void KRecentDocumentTest::cleanup()
{
    if (qEnvironmentVariableIsSet("SUPRALINUX_PRESERVE_XBEL")) {
        return;
    }
    QFile(m_xbelPath).remove();
'''
if old not in s: raise SystemExit("cleanup instrumentation anchor missing")
p.write_text(s.replace(old,new,1))
PY
}
build_recent() {
  cmake --build "${OBJ}" --target krecentdocumenttest --parallel 2
  [[ -x "${OBJ}/bin/krecentdocumenttest" ]]
}
record_xbel() {
  local label="$1" run="$2" rc="$3" home="$4" cwd="$5"
  python3 - "${EVIDENCE}/recent-runs.jsonl" "${label}" "${run}" "${rc}" "${home}" "${cwd}" <<'PY'
import collections,json,sys,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path
out,label,run,rc,home,cwd=sys.argv[1:]
xbels=list(Path(home).rglob("recently-used.xbel"))
row={"label":label,"run":int(run),"rc":int(rc),"home":home,"cwd":cwd,"xbel_count":len(xbels),"xbel":"","entries":[],"duplicate_modified_groups":0}
if len(xbels)==1:
    xbel=xbels[0]; row["xbel"]=str(xbel); root=ET.parse(xbel).getroot()
    for e in root.iter():
        if str(e.tag).endswith("bookmark") and "href" in e.attrib:
            row["entries"].append({"file":urllib.parse.unquote(e.attrib["href"]).rstrip("/").split("/")[-1],"modified":e.attrib.get("modified","")})
    counts=collections.Counter(x["modified"] for x in row["entries"] if x["modified"])
    row["duplicate_modified_groups"]=sum(1 for v in counts.values() if v>1)
with open(out,"a",encoding="utf-8") as f: f.write(json.dumps(row,sort_keys=True)+"\n")
PY
}
run_recent_series() {
  local label="$1" reps="$2" i home cwd log rc
  : > "${EVIDENCE}/recent-${label}.tsv"
  for ((i=1; i<=reps; i++)); do
    home="${VISIBLE_ROOT}/homes/${label}-${i}"; cwd="${VISIBLE_ROOT}/runs/${label}-${i}"
    rm -rf "${home}" "${cwd}"; mkdir -p "${home}/.qttest/share" "${home}/.qttest/config" "${cwd}"
    audit_visible_path "${home}" "${cwd}" >> "${EVIDENCE}/visible-path-audit.txt"
    log="${EVIDENCE}/recent-${label}-${i}.log"
    set +e
    ( cd "${cwd}"; env -u XDG_DATA_HOME -u XDG_CONFIG_HOME -u XDG_CACHE_HOME \
      HOME="${home}" TMPDIR=/tmp TMP=/tmp TEMP=/tmp SUPRALINUX_PRESERVE_XBEL=1 QT_PLUGIN_PATH="${OBJ}/bin" \
      "${OBJ}/bin/krecentdocumenttest" testXbelBookmarkMaxEntries ) >"${log}" 2>&1
    rc=$?; set -e
    printf '%s\t%s\n' "${i}" "${rc}" >> "${EVIDENCE}/recent-${label}.tsv"
    record_xbel "${label}" "${i}" "${rc}" "${home}" "${cwd}"
  done
}

STAGE=baseline-build
cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT_SRC}"
apply_preserve_instrumentation
build_recent |& tee "${EVIDENCE}/baseline-build.log"
STAGE=baseline
run_recent_series baseline 30

STAGE=capture-all
cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT_SRC}"
apply_preserve_instrumentation
python3 - "${RECENT_SRC}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text()
start=s.index("void KRecentDocumentTest::testXbelBookmarkMaxEntries()"); end=s.index("\n}\n",start)+3; block=s[start:end]
for old,new in [
 ('config.writeEntry(QStringLiteral("MaxEntries"), 3);','config.writeEntry(QStringLiteral("MaxEntries"), 50);'),
 ('QCOMPARE(recentUrls.length(), 3);','QCOMPARE(recentUrls.length(), 15);')
]:
    if old not in block: raise SystemExit("capture anchor missing: "+old)
    block=block.replace(old,new,1)
old='''    for (int i = 0; i < 3; ++i) {
        QCOMPARE(recentUrls.at(i).fileName(), QStringLiteral("temp File %1").arg(QString::number(i + 12)));
    }

'''
if old not in block: raise SystemExit("ordering assertion anchor missing")
block=block.replace(old,'',1)
p.write_text(s[:start]+block+s[end:])
PY
build_recent |& tee "${EVIDENCE}/capture-all-build.log"
capture_home="${VISIBLE_ROOT}/homes/capture-all"; capture_cwd="${VISIBLE_ROOT}/runs/capture-all"
rm -rf "${capture_home}" "${capture_cwd}"; mkdir -p "${capture_home}/.qttest/share" "${capture_home}/.qttest/config" "${capture_cwd}"
audit_visible_path "${capture_home}" "${capture_cwd}" >> "${EVIDENCE}/visible-path-audit.txt"
set +e
( cd "${capture_cwd}"; env -u XDG_DATA_HOME -u XDG_CONFIG_HOME -u XDG_CACHE_HOME \
  HOME="${capture_home}" TMPDIR=/tmp TMP=/tmp TEMP=/tmp SUPRALINUX_PRESERVE_XBEL=1 QT_PLUGIN_PATH="${OBJ}/bin" \
  "${OBJ}/bin/krecentdocumenttest" testXbelBookmarkMaxEntries ) >"${EVIDENCE}/recent-capture-all.log" 2>&1
capture_rc=$?; set -e
record_xbel capture-all 1 "${capture_rc}" "${capture_home}" "${capture_cwd}"

STAGE=delayed-build
cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT_SRC}"
apply_preserve_instrumentation
python3 - "${RECENT_SRC}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text()
start=s.index("void KRecentDocumentTest::testXbelBookmarkMaxEntries()"); end=s.index("\n}\n",start)+3; block=s[start:end]
old='        KRecentDocument::add(QUrl::fromLocalFile(fileName), QStringLiteral("my-application"));\n'
new=old+'        QTest::qWait(5);\n'
if old not in block: raise SystemExit("delay anchor missing")
block=block.replace(old,new,1); p.write_text(s[:start]+block+s[end:])
PY
build_recent |& tee "${EVIDENCE}/delayed-build.log"
STAGE=delayed
run_recent_series delayed 30

STAGE=restore
cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT_SRC}"
sha256sum "${RECENT_SRC}" | tee "${EVIDENCE}/krecentdocument-source-after.sha256"
cmp -s "${RECENT_SRC}" "${EVIDENCE}/krecentdocumenttest.cpp.original"

STAGE=classification
python3 - "${EVIDENCE}" "${STARTED_AT}" <<'PY'
import json,sys
from pathlib import Path
ev=Path(sys.argv[1]); started=sys.argv[2]
rows=[json.loads(x) for x in (ev/"recent-runs.jsonl").read_text().splitlines() if x.strip()]
baseline=[x for x in rows if x["label"]=="baseline"]; delayed=[x for x in rows if x["label"]=="delayed"]; capture=next(x for x in rows if x["label"]=="capture-all")
def exact(label,row):
    log=(ev/f"recent-{label}-{row['run']}.log").read_text(errors="replace")
    return row["rc"]!=0 and "temp File 11" in log and "temp File 12" in log
baseline_fail=sum(x["rc"]!=0 for x in baseline); delayed_fail=sum(x["rc"]!=0 for x in delayed)
baseline_sig=sum(exact("baseline",x) for x in baseline); delayed_sig=sum(exact("delayed",x) for x in delayed)
baseline_valid=len(baseline)==30 and all(x["xbel_count"]==1 and len(x["entries"])==3 for x in baseline)
delayed_valid=len(delayed)==30 and all(x["xbel_count"]==1 and len(x["entries"])==3 for x in delayed)
capture_valid=capture["xbel_count"]==1 and len(capture["entries"])==15
env_valid=baseline_valid and delayed_valid and capture_valid; dupes=capture["duplicate_modified_groups"]
if not env_valid: conclusion="DIAG_INVALID-krecent-visible-environment"
elif baseline_sig>0 and dupes>0 and delayed_fail==0: conclusion="krecentdocument-timestamp-collision-ordering-confirmed"
elif baseline_sig>0 and (dupes==0 or delayed_sig>0): conclusion="krecentdocument-timestamp-collision-ordering-rejected"
elif baseline_sig==0: conclusion="krecentdocument-attempt8-failure-not-reproduced"
else: conclusion="krecentdocument-timestamp-hypothesis-not-confirmed"
result={"schema":1,"node":"kio","round":21,"claim":"non-promoting-krecent-visible-cwd-timestamp-ordering-diagnostic",
 "diagnostic_result":"DIAG_COMPLETE","package_attempted":False,"package_state_effect":"none","canonical_source_modified":False,"test_suppression":False,
 "environment_valid":env_valid,"baseline_runs":len(baseline),"baseline_failures":baseline_fail,"baseline_attempt8_signature_failures":baseline_sig,
 "delayed_runs":len(delayed),"delayed_failures":delayed_fail,"delayed_attempt8_signature_failures":delayed_sig,
 "capture_all_rc":capture["rc"],"capture_all_entries":len(capture["entries"]),"capture_all_entries_detail":capture["entries"],
 "capture_all_duplicate_modified_groups":dupes,"capture_all_xbel":capture["xbel"],"conclusion":conclusion,
 "next_scope":"remediation-definition-only-if-cause-confirmed-otherwise-narrower-krecent-diagnostic","started_at":started}
(ev/"classification.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps(result,indent=2,sort_keys=True))
PY
DIAG_RESULT=DIAG_COMPLETE
STAGE=complete
