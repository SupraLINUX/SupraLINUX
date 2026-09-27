#!/usr/bin/env bash
set -Eeuo pipefail
PKGDIR="${1:?missing package build directory}"
EVIDENCE=/media
EXPECTED=/build/reproducible-path/kf6-kio-6.30.0
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[[ "${PKGDIR}" == "${EXPECTED}" ]]
[[ "$(id -un)" == root ]]
getent passwd sbuild > "${EVIDENCE}/sbuild-passwd.txt"
id sbuild > "${EVIDENCE}/sbuild-id.txt"
dpkg-query -W | sort > "${EVIDENCE}/chroot-packages.tsv"

run_as_sbuild() {
  runuser -p -u sbuild -- env HOME=/sbuild-nonexistent LANG=C.UTF-8 LC_ALL=C.UTF-8 LOGNAME=sbuild USER=sbuild \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games "$@"
}

cd "${PKGDIR}"
run_as_sbuild debian/rules clean
run_as_sbuild dh_update_autotools_config
run_as_sbuild dh_autoreconf
RECENT="${PKGDIR}/autotests/krecentdocumenttest.cpp"
cp "${RECENT}" "${EVIDENCE}/krecentdocumenttest.cpp.original"
sha256sum "${RECENT}" > "${EVIDENCE}/source-before.sha256"

run_as_sbuild python3 - "${RECENT}" <<'PY'
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

run_as_sbuild env DEB_BUILD_OPTIONS=parallel=4 debian/rules override_dh_auto_configure
run_as_sbuild env DEB_BUILD_OPTIONS=parallel=4 debian/rules override_dh_auto_build
OBJ="${PKGDIR}/obj-x86_64-linux-gnu"
[[ -x "${OBJ}/bin/krecentdocumenttest" ]]
if find /build/reproducible-path -maxdepth 1 \( -name '*.deb' -o -name '*.changes' -o -name '*.buildinfo' \) -print -quit | grep -q .; then
  echo "package artifact unexpectedly present before diagnostic" >&2; exit 82
fi

run_lane() {
  local lane="$1" count="$2"
  shift 2
  local -a ctest_args=("$@")
  local i home cap log rc
  cd "${OBJ}"
  for ((i=1; i<=count; i++)); do
    home="${PKGDIR}/debian/.supralinux-test-home/sbuild"
    rm -rf "${home}"; mkdir -p "${home}"; chown -R sbuild:sbuild "${home}"
    rm -f "${OBJ}/autotests"/temp\ File*
    cap="${EVIDENCE}/xbels/${lane}-${i}.xbel"
    log="${EVIDENCE}/${lane}-${i}.log"
    rm -f "${cap}" "${log}"
    set +e
    runuser -p -u sbuild -- env -u XDG_DATA_HOME -u XDG_CONFIG_HOME -u XDG_CACHE_HOME -u XDG_RUNTIME_DIR \
      HOME="${home}" LANG=C.UTF-8 LC_ALL=C.UTF-8 LOGNAME=sbuild USER=sbuild \
      QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze KDECI_PLATFORM_PATH="${PKGDIR}" \
      SUPRALINUX_CAPTURE_XBEL="${cap}" dbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24" \
      ctest --verbose -j1 "${ctest_args[@]}" >"${log}" 2>&1
    rc=$?
    set -e
    python3 - "${EVIDENCE}/runs.jsonl" "${lane}" "${i}" "${rc}" "${cap}" "${log}" <<'PY'
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

run_lane isolated-krecent 100 -R "^kiocore-krecentdocumenttest$"
run_lane prefix-through-krecent 30 -I 1,26
run_lane full-suite 3

cp "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT}"
chown sbuild:sbuild "${RECENT}"
sha256sum "${RECENT}" > "${EVIDENCE}/source-after.sha256"
cmp -s "${RECENT}" "${EVIDENCE}/krecentdocumenttest.cpp.original"

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
if not valid: conclusion="DIAG_INVALID-attempt8-rootfs-sbuild-unshare"
elif i>0: conclusion="krecentdocument-attempt8-signature-reproduced-isolated-in-attempt8-sbuild-unshare"
elif p>0: conclusion="krecentdocument-attempt8-signature-requires-prior-ctest-prefix-in-attempt8-sbuild-unshare"
elif f>0: conclusion="krecentdocument-attempt8-signature-reproduced-only-in-full-suite-attempt8-sbuild-unshare"
else: conclusion="krecentdocument-attempt8-failure-not-reproduced-in-attempt8-sbuild-unshare"
result={"schema":1,"node":"kio","round":23,"diagnostic_result":"DIAG_COMPLETE",
 "claim":"non-promoting-krecent-attempt8-rootfs-diagnostic","package_attempted":False,
 "package_state_effect":"none","environment_valid":valid,"containment":"sbuild-0.91.2ubuntu3-unshare","matrix":summary,
 "conclusion":conclusion,"started_at":started}
(ev/"classification.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,indent=2,sort_keys=True))
PY
touch "${EVIDENCE}/hook-complete"
exit 86
