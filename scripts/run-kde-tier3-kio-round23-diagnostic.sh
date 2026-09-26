#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEVEL1="${ROOT}/manifests/kde-tier3-build-level1.json"
WORK="${ROOT}/.work/kde-tier3-kio-round23-diagnostic"
INPUTS="${WORK}/inputs"
ROOTFS_DIR="${WORK}/rootfs-artifact"
CHROOT="${WORK}/chroot"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round23-diagnostic"
RESULT="${EVIDENCE}/result.json"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STAGE=initialization
DIAG_RESULT=DIAG_INFRA_FAIL
MOUNTED=0
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${INPUTS}" "${ROOTFS_DIR}" "${CHROOT}" "${EVIDENCE}/xbels"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

cleanup() {
  set +e
  if (( MOUNTED )); then
    sudo umount -l "${CHROOT}/dev/pts" 2>/dev/null || true
    sudo umount -l "${CHROOT}/dev" 2>/dev/null || true
    sudo umount -l "${CHROOT}/sys" 2>/dev/null || true
    sudo umount -l "${CHROOT}/proc" 2>/dev/null || true
  fi
}
finish() {
  local rc="$1" finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ -f "${EVIDENCE}/classification.json" ]]; then cp "${EVIDENCE}/classification.json" "${RESULT}"
  else
    python3 - "${RESULT}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished}" <<'PY'
import json,sys
from pathlib import Path
p,result,rc,stage,started,finished=sys.argv[1:]
Path(p).write_text(json.dumps({"schema":1,"node":"kio","round":23,"diagnostic_result":result,
 "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
 "claim":"non-promoting-krecent-attempt8-rootfs-diagnostic","package_attempted":False,
 "package_state_effect":"none"},indent=2,sort_keys=True)+"\n")
PY
  fi
  cleanup
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

STAGE=contract
python3 scripts/validate_kde_tier3_kio_round23_diagnostic.py

STAGE=host-tools
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ca-certificates curl dpkg-dev gzip python3 unzip xz-utils

STAGE=attempt8-rootfs-download
download_artifact 10904512642 d689f1658d37e3dedcf57d7f4a233917a6d84ed592346d4ac87f60d626724afe "${ROOTFS_DIR}"
ROOTFS_TAR="$(find "${ROOTFS_DIR}" -type f -name 'resolute-amd64.tar' -print -quit)"
ROOTFS_SHA="$(find "${ROOTFS_DIR}" -type f -name 'rootfs.sha256' -print -quit)"
[[ -n "${ROOTFS_TAR}" && -s "${ROOTFS_TAR}" && -n "${ROOTFS_SHA}" && -s "${ROOTFS_SHA}" ]]
expected="$(awk '{print $1}' "${ROOTFS_SHA}")"
actual="$(sha256sum "${ROOTFS_TAR}" | awk '{print $1}')"
[[ "${expected}" == "${actual}" ]]
printf '%s\n' "${actual}" > "${EVIDENCE}/rootfs-tar.sha256"
cp "${ROOTFS_DIR}/provenance.txt" "${EVIDENCE}/attempt8-rootfs-provenance.txt" 2>/dev/null || true

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
for i in n.get("support_input_ids",[]): add(i,m["support_predecessors"][i])
if len({r[0] for r in rows})!=len(rows): raise SystemExit("duplicate provider input")
Path(sys.argv[2]).write_text("\n".join("\t".join(r) for r in rows)+"\n")
PY

STAGE=source-download
download_artifact 10898999142 c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d "${INPUTS}/materialization"
DSC="$(find "${INPUTS}/materialization" -type f -name '*.dsc' -print -quit)"
[[ -n "${DSC}" && -s "${DSC}" ]]

STAGE=provider-download
TAB="$(printf '\t')"
while IFS="${TAB}" read -r input_id artifact_id artifact_sha version; do
  printf '%s\t%s\t%s\n' "${input_id}" "${version}" "${artifact_id}" >> "${EVIDENCE}/provider-plan.tsv"
  download_artifact "${artifact_id}" "${artifact_sha}" "${INPUTS}/${input_id}"
done < "${EVIDENCE}/input-plan.tsv"

STAGE=rootfs-extract
sudo tar -xf "${ROOTFS_TAR}" -C "${CHROOT}"
sudo cp /etc/resolv.conf "${CHROOT}/etc/resolv.conf"
sudo mount -t proc proc "${CHROOT}/proc"
sudo mount --rbind /dev "${CHROOT}/dev"
sudo mount --make-rslave "${CHROOT}/dev"
sudo mount --rbind /sys "${CHROOT}/sys"
sudo mount --make-rslave "${CHROOT}/sys"
MOUNTED=1
sudo chroot "${CHROOT}" /bin/bash -lc 'set -e; . /etc/os-release; test "$ID" = ubuntu; test "$VERSION_ID" = 26.04; cat /etc/os-release' | tee "${EVIDENCE}/chroot-os-release.txt" >/dev/null

STAGE=stage-inputs
sudo mkdir -p "${CHROOT}/input/source" "${CHROOT}/opt/supralinux-repo" "${CHROOT}/build/reproducible-path"
mapfile -t SOURCE_INPUTS < <(find "${INPUTS}/materialization" -type f \( -name '*.dsc' -o -name '*.orig.tar.*' -o -name '*.debian.tar.*' \) -print | sort)
(( ${#SOURCE_INPUTS[@]} == 3 )) || { printf 'expected exactly 3 source files, got %s\n' "${#SOURCE_INPUTS[@]}" >&2; exit 1; }
sudo cp "${SOURCE_INPUTS[@]}" "${CHROOT}/input/source/"
[[ "$(find "${CHROOT}/input/source" -maxdepth 1 -type f -name '*.dsc' | wc -l)" -eq 1 ]]
find "${INPUTS}" -mindepth 2 -type f -name '*.deb' -exec sudo cp -n {} "${CHROOT}/opt/supralinux-repo/" \;
sudo chroot "${CHROOT}" /bin/bash -lc '
 set -e
 export DEBIAN_FRONTEND=noninteractive
 apt-get update
 apt-get install -y --no-install-recommends devscripts equivs dpkg-dev xauth xvfb dbus-daemon ca-certificates
 cd /opt/supralinux-repo
 dpkg-scanpackages . /dev/null > Packages
 gzip -9c Packages > Packages.gz
 echo "deb [trusted=yes] file:/opt/supralinux-repo ./" > /etc/apt/sources.list.d/supralinux-round23.list
 apt-get update
'

STAGE=source-extract
sudo chroot "${CHROOT}" /bin/bash -lc '
 set -e
 rm -rf /build/reproducible-path/kf6-kio-6.30.0
 dpkg-source -x /input/source/*.dsc /build/reproducible-path/kf6-kio-6.30.0
 if ! getent passwd sbuild >/dev/null; then useradd --system --home /sbuild-nonexistent --shell /bin/bash sbuild; fi
 chown -R sbuild:sbuild /build/reproducible-path
'
SRC="/build/reproducible-path/kf6-kio-6.30.0"
HOST_SRC="${CHROOT}${SRC}"
RECENT="${HOST_SRC}/autotests/krecentdocumenttest.cpp"
cp "${RECENT}" "${EVIDENCE}/krecentdocumenttest.cpp.original"
sha256sum "${RECENT}" > "${EVIDENCE}/source-before.sha256"

STAGE=build-dependencies
sudo chroot "${CHROOT}" /bin/bash -lc '
 set -e
 export DEBIAN_FRONTEND=noninteractive
 cd /build/reproducible-path/kf6-kio-6.30.0
 mk-build-deps --install --remove --tool "apt-get -y --no-install-recommends" debian/control
 dpkg-checkbuilddeps
' |& tee "${EVIDENCE}/build-deps.log"

STAGE=instrument
sudo python3 - "${RECENT}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text()
start=s.index("void KRecentDocumentTest::testXbelBookmarkMaxEntries()")
end=s.index("\n}\n",start)+3
block=s[start:end]
anchor="    const auto recentUrls = KRecentDocument::recentUrls();\n"
insert=anchor+'''    const QString capturePath = qEnvironmentVariable("SUPRALINUX_CAPTURE_XBEL");
    if (!capturePath.isEmpty()) {
        QFile::remove(capturePath);
        QFile::copy(m_xbelPath, capturePath);
    }
'''
if anchor not in block: raise SystemExit("instrumentation anchor missing")
p.write_text(s[:start]+block.replace(anchor,insert,1)+s[end:])
PY
sudo chown sbuild:sbuild "${RECENT}"

STAGE=configure-build
sudo chroot "${CHROOT}" /bin/bash -lc '
 set -e
 cd /build/reproducible-path/kf6-kio-6.30.0
 su -s /bin/bash sbuild -c "DEB_BUILD_OPTIONS=parallel=2 debian/rules override_dh_auto_configure"
 su -s /bin/bash sbuild -c "DEB_BUILD_OPTIONS=parallel=2 debian/rules override_dh_auto_build"
' |& tee "${EVIDENCE}/configure-build.log"
OBJ="${SRC}/obj-x86_64-linux-gnu"
HOST_OBJ="${CHROOT}${OBJ}"
[[ -x "${HOST_OBJ}/bin/krecentdocumenttest" ]]
if find "${HOST_SRC}/.." -maxdepth 1 \( -name '*.deb' -o -name '*.changes' -o -name '*.buildinfo' \) -print -quit | grep -q .; then
  echo "package artifact unexpectedly produced" >&2; exit 1
fi

run_lane() {
  local lane="$1" count="$2" ctest_args="$3" i home cap log rc
  for ((i=1;i<=count;i++)); do
    home="${SRC}/debian/.supralinux-test-home/sbuild"
    sudo rm -rf "${CHROOT}${home}"
    sudo mkdir -p "${CHROOT}${home}"
    sudo chroot "${CHROOT}" chown -R sbuild:sbuild "${home}"
    sudo rm -f "${HOST_OBJ}/autotests"/temp\ File*
    cap="/tmp/round23-${lane}-${i}.xbel"
    sudo rm -f "${CHROOT}${cap}"
    log="${EVIDENCE}/${lane}-${i}.log"
    set +e
    sudo chroot "${CHROOT}" /bin/bash -lc "
      cd '${OBJ}'
      su -s /bin/bash sbuild -c 'env -u XDG_DATA_HOME -u XDG_CONFIG_HOME -u XDG_CACHE_HOME -u XDG_RUNTIME_DIR \
        HOME=\"${home}\" LANG=C.UTF-8 LC_ALL=C.UTF-8 LOGNAME=sbuild USER=sbuild \
        QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze KDECI_PLATFORM_PATH=\"${SRC}\" \
        SUPRALINUX_CAPTURE_XBEL=\"${cap}\" \
        dbus-run-session -- xvfb-run -a -s \"-screen 0 1280x1024x24\" ctest --verbose -j1 ${ctest_args}'
    " 2>&1 | tee "${log}" >/dev/null
    rc=${PIPESTATUS[0]}
    set -e
    if [[ -f "${CHROOT}${cap}" ]]; then sudo cp "${CHROOT}${cap}" "${EVIDENCE}/xbels/${lane}-${i}.xbel"; fi
    python3 - "${EVIDENCE}/runs.jsonl" "${lane}" "${i}" "${rc}" "${EVIDENCE}/xbels/${lane}-${i}.xbel" "${log}" <<'PY'
import collections,json,sys,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path
out,lane,run,rc,cap,log=sys.argv[1:]
p=Path(cap); text=Path(log).read_text(errors="replace")
row={"lane":lane,"run":int(run),"rc":int(rc),"capture_exists":p.is_file(),
     "attempt8_signature":("temp File 11" in text and "temp File 12" in text),
     "krecent_failed":("kiocore-krecentdocumenttest" in text and ("***Failed" in text or "FAIL!" in text)),
     "entries":[],"duplicate_modified_groups":0}
if p.is_file():
    root=ET.parse(p).getroot()
    for e in root.iter():
        if str(e.tag).endswith("bookmark") and "href" in e.attrib:
            row["entries"].append({"file":urllib.parse.unquote(e.attrib["href"]).rstrip("/").split("/")[-1],
                                   "modified":e.attrib.get("modified","")})
    c=collections.Counter(x["modified"] for x in row["entries"] if x["modified"])
    row["duplicate_modified_groups"]=sum(1 for n in c.values() if n>1)
with open(out,"a") as f: f.write(json.dumps(row,sort_keys=True)+"\n")
PY
  done
}

STAGE=isolated-krecent
run_lane isolated-krecent 100 "-R '^kiocore-krecentdocumenttest$'"

STAGE=prefix-through-krecent
run_lane prefix-through-krecent 30 "-I 1,26"

STAGE=full-suite
run_lane full-suite 3 ""

STAGE=restore
sudo cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT}"
sha256sum "${RECENT}" > "${EVIDENCE}/source-after.sha256"
cmp -s "${RECENT}" "${EVIDENCE}/krecentdocumenttest.cpp.original"

STAGE=classification
python3 - "${EVIDENCE}" "${STARTED_AT}" <<'PY'
import json,sys
from pathlib import Path
ev=Path(sys.argv[1]); started=sys.argv[2]
rows=[json.loads(x) for x in (ev/"runs.jsonl").read_text().splitlines() if x.strip()]
expected={"isolated-krecent":100,"prefix-through-krecent":30,"full-suite":3}
summary={}
for lane,n in expected.items():
    xs=[x for x in rows if x["lane"]==lane]
    summary[lane]={
      "runs":len(xs),
      "attempt8_signature_failures":sum(x["attempt8_signature"] for x in xs),
      "krecent_failed_runs":sum(x["krecent_failed"] for x in xs),
      "valid_captures":sum(x["capture_exists"] and len(x["entries"])==3 for x in xs),
      "duplicate_modified_runs":sum(x["duplicate_modified_groups"]>0 for x in xs),
    }
valid=(summary["isolated-krecent"]["runs"]==100 and summary["isolated-krecent"]["valid_captures"]==100 and
       summary["prefix-through-krecent"]["runs"]==30 and summary["prefix-through-krecent"]["valid_captures"]==30 and
       summary["full-suite"]["runs"]==3 and summary["full-suite"]["valid_captures"]==3)
i=summary["isolated-krecent"]["attempt8_signature_failures"]
p=summary["prefix-through-krecent"]["attempt8_signature_failures"]
f=summary["full-suite"]["attempt8_signature_failures"]
if not valid: conclusion="DIAG_INVALID-attempt8-rootfs"
elif i>0: conclusion="krecentdocument-attempt8-signature-reproduced-isolated-in-attempt8-rootfs"
elif p>0: conclusion="krecentdocument-attempt8-signature-requires-prior-ctest-prefix-in-attempt8-rootfs"
elif f>0: conclusion="krecentdocument-attempt8-signature-reproduced-only-in-full-suite-attempt8-rootfs"
else: conclusion="krecentdocument-attempt8-failure-not-reproduced-in-attempt8-rootfs"
result={"schema":1,"node":"kio","round":23,"diagnostic_result":"DIAG_COMPLETE",
 "claim":"non-promoting-krecent-attempt8-rootfs-diagnostic","package_attempted":False,
 "package_state_effect":"none","environment_valid":valid,"matrix":summary,
 "conclusion":conclusion,"started_at":started}
(ev/"classification.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
PY
DIAG_RESULT=DIAG_COMPLETE
STAGE=complete
