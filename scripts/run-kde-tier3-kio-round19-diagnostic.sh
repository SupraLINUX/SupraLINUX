#!/usr/bin/env bash
# shellcheck disable=SC1090
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round19-diagnostic"
INPUTS="${WORK}/inputs"
APT_REPO="/tmp/supralinux-round19-repo"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round19-diagnostic"
RESULT="${EVIDENCE}/result.json"
STAGE=initialization
DIAG_RESULT=DIAG_INFRA_FAIL
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}" "${APT_REPO}"
mkdir -p "${INPUTS}" "${EVIDENCE}" "${APT_REPO}"
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
 "schema":1,"node":"kio","round":19,"diagnostic_result":result,
 "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
 "claim":"non-promoting-kio-residual-test-root-cause-diagnostic",
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
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" -o "${zip}"
  printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}

STAGE=contract
python3 scripts/validate_kde_tier3_kio_round19_diagnostic.py

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
m=json.loads(Path(sys.argv[1]).read_text())
n=m["nodes"]["kio"]
if n["package_version"]!="6.30.0-0supralinux8":
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
download_artifact "10898999142" "c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d" "${INPUTS}/materialization"
DSC="$(find "${INPUTS}/materialization" -type f -name '*.dsc' -print -quit)"
[[ -n "${DSC}" && -s "${DSC}" ]]
python3 - "${INPUTS}/materialization" <<'PY'
import json,sys
from pathlib import Path
xs=list(Path(sys.argv[1]).rglob("result.json"))
if len(xs)!=1:
    raise SystemExit("materialization result ambiguity")
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
(
  cd "${APT_REPO}"
  dpkg-scanpackages . /dev/null > Packages
  gzip -9c Packages > Packages.gz
  chmod 0644 Packages Packages.gz ./*.deb
)
echo "deb [trusted=yes] file:${APT_REPO} ./" | sudo tee /etc/apt/sources.list.d/supralinux-round19.list
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

STAGE=target-build
cmake --build "${OBJ}" --target kio_file kioworker krecentdocumenttest kdirmodeltest --parallel 2 |& tee "${EVIDENCE}/target-build.log"
[[ -x "${OBJ}/bin/krecentdocumenttest" && -x "${OBJ}/bin/kdirmodeltest" ]]
export PATH="${OBJ}/bin:${PATH}"

record_xbel() {
  local label="$1" run="$2" rc="$3" home="$4" xbel
  xbel="$(find "${home}" -type f -name recently-used.xbel -print -quit || true)"
  python3 - "${EVIDENCE}/recent-runs.jsonl" "${label}" "${run}" "${rc}" "${xbel}" <<'PY'
import json,sys,urllib.parse,collections,xml.etree.ElementTree as ET
out,label,run,rc,xbel=sys.argv[1:]
row={"label":label,"run":int(run),"rc":int(rc),"xbel":xbel,"entries":[],"duplicate_modified_groups":0}
if xbel:
    root=ET.parse(xbel).getroot()
    for e in root.iter():
        if str(e.tag).endswith("bookmark") and "href" in e.attrib:
            row["entries"].append({
                "file":urllib.parse.unquote(e.attrib["href"]).rstrip("/").split("/")[-1],
                "modified":e.attrib.get("modified","")
            })
    counts=collections.Counter(x["modified"] for x in row["entries"] if x["modified"])
    row["duplicate_modified_groups"]=sum(1 for v in counts.values() if v>1)
with open(out,"a",encoding="utf-8") as f:
    f.write(json.dumps(row,sort_keys=True)+"\n")
PY
}

run_recent_series() {
  local label="$1" reps="$2" i home log rc
  : > "${EVIDENCE}/recent-${label}.tsv"
  for ((i=1; i<=reps; i++)); do
    home="${WORK}/homes/recent-${label}-${i}"
    rm -rf "${home}"; mkdir -p "${home}"
    log="${EVIDENCE}/recent-${label}-${i}.log"
    set +e
    (
      cd "${OBJ}/autotests"
      HOME="${home}" QT_PLUGIN_PATH="${OBJ}/bin" "${OBJ}/bin/krecentdocumenttest" testXbelBookmarkMaxEntries
    ) >"${log}" 2>&1
    rc=$?
    set -e
    printf '%s\t%s\n' "${i}" "${rc}" >> "${EVIDENCE}/recent-${label}.tsv"
    record_xbel "${label}" "${i}" "${rc}" "${home}"
  done
}

STAGE=recent-baseline
run_recent_series baseline 30

STAGE=recent-capture-all
python3 - "${RECENT_SRC}" <<'PY'
from pathlib import Path
p=Path(sys.argv[1]) if False else None
PY
python3 - "${RECENT_SRC}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1])
s=p.read_text()
start=s.index("void KRecentDocumentTest::testXbelBookmarkMaxEntries()")
end=s.index("\n}\n",start)+3
block=s[start:end]
for old,new in (
    ('config.writeEntry(QStringLiteral("MaxEntries"), 3);','config.writeEntry(QStringLiteral("MaxEntries"), 50);'),
    ('QCOMPARE(recentUrls.length(), 3);','QCOMPARE(recentUrls.length(), 15);'),
    ('for (int i = 0; i < 3; ++i) {','for (int i = 0; i < 15; ++i) {'),
    ('QString::number(i + 12)','QString::number(i)'),
):
    if old not in block:
        raise SystemExit("capture-all patch anchor missing: "+old)
    block=block.replace(old,new,1)
p.write_text(s[:start]+block+s[end:])
PY
cmake --build "${OBJ}" --target krecentdocumenttest --parallel 2 |& tee "${EVIDENCE}/recent-capture-all-build.log"
capture_home="${WORK}/homes/recent-capture-all"
rm -rf "${capture_home}"; mkdir -p "${capture_home}"
set +e
(
  cd "${OBJ}/autotests"
  HOME="${capture_home}" QT_PLUGIN_PATH="${OBJ}/bin" "${OBJ}/bin/krecentdocumenttest" testXbelBookmarkMaxEntries
) >"${EVIDENCE}/recent-capture-all.log" 2>&1
capture_rc=$?
set -e
record_xbel capture-all 1 "${capture_rc}" "${capture_home}"

STAGE=recent-delayed
cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT_SRC}"
python3 - "${RECENT_SRC}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text()
start=s.index("void KRecentDocumentTest::testXbelBookmarkMaxEntries()")
end=s.index("\n}\n",start)+3
block=s[start:end]
old='        KRecentDocument::add(QUrl::fromLocalFile(fileName), QStringLiteral("my-application"));\n'
new=old+'        QTest::qWait(5);\n'
if old not in block:
    raise SystemExit("delay patch anchor missing")
block=block.replace(old,new,1)
p.write_text(s[:start]+block+s[end:])
PY
cmake --build "${OBJ}" --target krecentdocumenttest --parallel 2 |& tee "${EVIDENCE}/recent-delayed-build.log"
run_recent_series delayed 30
cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT_SRC}"
sha256sum "${RECENT_SRC}" | tee "${EVIDENCE}/krecentdocument-source-after.sha256"
cmp -s "${RECENT_SRC}" "${EVIDENCE}/krecentdocumenttest.cpp.original"

run_kdir() {
  local label="$1" home="$2" log rc
  rm -rf "${home}"; mkdir -p "${home}"
  log="${EVIDENCE}/kdir-${label}.log"
  set +e
  (
    cd "${OBJ}/autotests"
    HOME="${home}" \
    QT_PLUGIN_PATH="${OBJ}/bin" \
    QT_QPA_PLATFORM=xcb \
    QT_QPA_SYSTEM_ICON_THEME=breeze \
    KDECI_PLATFORM_PATH="${SRC}" \
    dbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24" "${OBJ}/bin/kdirmodeltest"
  ) >"${log}" 2>&1
  rc=$?
  set -e
  printf '%s\t%s\t%s\n' "${label}" "${rc}" "${home}" >> "${EVIDENCE}/kdir-runs.tsv"
}

STAGE=kdir-hidden-initial
: > "${EVIDENCE}/kdir-runs.tsv"
run_kdir hidden-initial "${SRC}/debian/.supralinux-test-home/sbuild"

STAGE=kdir-visible
run_kdir visible "${SRC}/debian/supralinux-test-home/sbuild"

STAGE=kdir-hidden-repeat
run_kdir hidden-repeat "${SRC}/debian/.supralinux-test-home/sbuild"

STAGE=classification
python3 - "${EVIDENCE}" "${STARTED_AT}" <<'PY'
import json,sys,collections
from pathlib import Path
ev=Path(sys.argv[1]); started=sys.argv[2]

def read_series(label):
    rows=[]
    for line in (ev/f"recent-{label}.tsv").read_text().splitlines():
        run,rc=line.split("\t")
        rows.append({"run":int(run),"rc":int(rc)})
    return rows

recent_rows=[json.loads(x) for x in (ev/"recent-runs.jsonl").read_text().splitlines() if x.strip()]
baseline=read_series("baseline")
delayed=read_series("delayed")
capture=next(x for x in recent_rows if x["label"]=="capture-all")
baseline_fail=sum(x["rc"]!=0 for x in baseline)
delayed_fail=sum(x["rc"]!=0 for x in delayed)
capture_dupes=capture["duplicate_modified_groups"]

kdir={}
for line in (ev/"kdir-runs.tsv").read_text().splitlines():
    label,rc,home=line.split("\t",2)
    log=(ev/f"kdir-{label}.log").read_text(errors="replace")
    kdir[label]={
        "rc":int(rc),"home":home,
        "show_root_fail":"FAIL!  : KDirModelTest::testShowRoot()" in log,
        "show_root_expand_fail":"FAIL!  : KDirModelTest::testShowRootAndExpandToUrl()" in log,
        "trailing_slash_pass":"PASS   : KDirModelTest::testShowRootWithTrailingSlash()" in log,
        "test_icon_pass":"PASS   : KDirModelTest::testIcon()" in log,
    }

recent_conclusion="inconclusive"
if baseline_fail>0 and capture_dupes>0 and delayed_fail==0:
    recent_conclusion="krecentdocument-timestamp-collision-ordering-confirmed"
elif delayed_fail>0:
    recent_conclusion="krecentdocument-pruning-semantics-require-deeper-diagnostic"
elif baseline_fail==0 and capture_dupes>0:
    recent_conclusion="timestamp-collisions-observed-baseline-failure-not-reproduced"

def exact_hidden(x):
    return x["show_root_fail"] and x["show_root_expand_fail"] and x["trailing_slash_pass"]
vis=kdir["visible"]
if exact_hidden(kdir["hidden-initial"]) and exact_hidden(kdir["hidden-repeat"]) and not vis["show_root_fail"] and not vis["show_root_expand_fail"]:
    kdir_conclusion="hidden-home-component-controls-kdirmodel-showroot-failure"
elif not kdir["hidden-initial"]["show_root_fail"] and not kdir["hidden-repeat"]["show_root_fail"]:
    kdir_conclusion="diagnostic-invalid-cannot-reproduce-attempt8-showroot-failure"
else:
    kdir_conclusion="kdirmodel-expand-state-requires-deeper-diagnostic"

result={
 "schema":1,"node":"kio","round":19,"diagnostic_result":"DIAG_COMPLETE",
 "claim":"non-promoting-kio-residual-test-root-cause-diagnostic",
 "package_attempted":False,"package_state_effect":"none",
 "canonical_source_modified":False,"test_suppression":False,
 "started_at":started,
 "recent":{
   "baseline_runs":len(baseline),"baseline_failures":baseline_fail,
   "delayed_runs":len(delayed),"delayed_failures":delayed_fail,
   "capture_all_entries":len(capture["entries"]),
   "capture_all_duplicate_modified_groups":capture_dupes,
   "capture_all_entries_detail":capture["entries"],
   "conclusion":recent_conclusion
 },
 "kdirmodel":{"modes":kdir,"conclusion":kdir_conclusion},
 "next_scope":"remediation-definition-if-both-causes-confirmed-otherwise-targeted-followup"
}
(ev/"classification.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
PY
DIAG_RESULT=DIAG_COMPLETE
STAGE=complete
