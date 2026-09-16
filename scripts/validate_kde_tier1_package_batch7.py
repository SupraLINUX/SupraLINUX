#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
M=ROOT/"manifests/kde-tier1-package-campaign-batch7.json"
A=ROOT/"manifests/kde-tier1-package-batch7-attempts.json"
W=ROOT/".github/workflows/kde-tier1-package-batch7.yml"
R=ROOT/"scripts/run-kde-tier1-package-batch7-preflight.sh"

def fail(msg): raise SystemExit(msg)
def load(p): return json.loads(p.read_text())

m=load(M); a=load(A); expected={"kcalendarcore","kcoreaddons","kwidgetsaddons"}
if m.get("schema")!=2 or m.get("authority")!="kde-upstream" or m.get("frameworks_series")!="6.30.0": fail("Batch 7 manifest identity mismatch")
if set(m.get("selected_nodes",[]))!=expected or set(m.get("nodes",{}))!=expected: fail("Batch 7 node set mismatch")
if m.get("attempt_ledger")!="manifests/kde-tier1-package-batch7-attempts.json": fail("Batch 7 attempt ledger path mismatch")
if a.get("immutable_history") is not True or set(a.get("attempts",{}))!=expected: fail("Batch 7 history ledger mismatch")

hist_expect={
 "kcalendarcore":(["FAIL","FAIL","FAIL","FAIL","PASS"],[f"6.30.0-0supralinux{i}" for i in range(1,6)]),
 "kcoreaddons":(["FAIL","FAIL","FAIL","PASS"],[f"6.30.0-0supralinux{i}" for i in range(1,5)]),
 "kwidgetsaddons":(["FAIL","FAIL","FAIL","FAIL","FAIL"],[f"6.30.0-0supralinux{i}" for i in range(1,6)]),
}
for node,(results,versions) in hist_expect.items():
    hist=a["attempts"][node]
    if [x.get("result") for x in hist] != results: fail(f"{node}: retained result history mismatch")
    if [x.get("attempted_package_version") for x in hist] != versions: fail(f"{node}: historical revisions mismatch")

kc=m["nodes"]["kcalendarcore"]
if kc.get("package_version")!="6.30.0-0supralinux5" or kc.get("state")!="PASS" or kc.get("last_result")!="PASS" or kc.get("downstream_eligible") is not True: fail("KCalendarCore PASS state mismatch")
kcpe=kc.get("pass_evidence",{})
for key,value in {"workflow_run":35130213945,"job_id":104909057699,"artifact_id":10461386548,"artifact_sha256":"6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6","rootfs_sha256":"eb3e6bfe65b142c1308d8a1892e00c6bd57028126147ac09376778dec60692f6"}.items():
    if kcpe.get(key)!=value: fail(f"KCalendarCore PASS evidence mismatch: {key}")

ko=m["nodes"]["kcoreaddons"]
if ko.get("package_version")!="6.30.0-0supralinux4" or ko.get("state")!="PASS" or ko.get("last_result")!="PASS" or ko.get("downstream_eligible") is not True: fail("KCoreAddons PASS state mismatch")
kope=ko.get("pass_evidence",{})
for key,value in {"workflow_run":35122522242,"job_id":104883541991,"artifact_id":10457958023,"artifact_sha256":"c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64","rootfs_sha256":"dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794"}.items():
    if kope.get(key)!=value: fail(f"KCoreAddons PASS evidence mismatch: {key}")

kw=m["nodes"]["kwidgetsaddons"]
if kw.get("package_version")!="6.30.0-0supralinux6" or kw.get("state")!="remediation-pending-build" or kw.get("last_result")!="FAIL" or kw.get("downstream_eligible") is not False: fail("KWidgetsAddons -6 remediation state mismatch")
rem=kw.get("remediation",{}); part=rem.get("fixture_partition",{}); font=rem.get("font_fixture",{})
if part != {"total":27,"bare_xvfb":25,"xvfb_openbox":2,"openbox_tests":["ktwofingertaptest","ktwofingerswipetest"]}: fail("KWidgetsAddons fixture partition mismatch")
if font != {"resolver":"fontconfig","provider":"fonts-dejavu-core","generic":"sans-serif","expected_family_contains":"DejaVu Sans"}: fail("KWidgetsAddons font fixture mismatch")
if rem.get("tests_omitted") is not False or rem.get("source_change") is not False: fail("KWidgetsAddons must retain all upstream tests/source")
last=a["attempts"]["kwidgetsaddons"][-1]
for key,value in {"workflow_run":35134670336,"job_id":104923940192,"artifact_id":10462188593,"artifact_sha256":"f5c47f8efbf1ca2172e0578b104e472875f01966b17f33f34eeadf47daef8aa5","rootfs_sha256":"82eb0b91799d774ab0354ec2efb2a346a4557a1a6884bec860a93cbc678b7042","failure_substage":"tests/font-metric-fixture-before-openbox"}.items():
    if last.get(key)!=value: fail(f"KWidgetsAddons -5 FAIL evidence mismatch: {key}")

for node in expected:
    base=ROOT/"packages/kde"/node/"debian"; control=(base/"control").read_text(); rules=(base/"rules").read_text()
    for token in ("clang","libclang-dev","llvm-dev","python3-build","python3-setuptools"):
        if token not in control: fail(f"{node}: missing {token} build dependency")
    if "-DBUILD_PYTHON_BINDINGS=ON" not in rules or "-DBUILD_TESTING=ON" not in rules: fail(f"{node}: upstream Python/tests must remain enabled")

kcd=ROOT/"packages/kde/kcalendarcore/debian"
if "6.30.0-0supralinux5" not in (kcd/"changelog").read_text().splitlines()[0]: fail("KCalendarCore changelog not at -5")
if (kcd/"libkf6calendarcore-data.install").read_text().strip()!="usr/share/locale/*/LC_MESSAGES/kcalendarcore6_qt.qm": fail("KCalendarCore translation ownership mismatch")
overlay=(kcd/"libkf6calendarcore6.symbols.supralinux-overlay").read_text().splitlines()
if len(overlay)!=18 or sum(x.endswith(" 6.29.0") for x in overlay)!=10 or sum(x.endswith(" 6.30.0") for x in overlay)!=8: fail("KCalendarCore ABI overlay mismatch")
if "execute_before_dh_makeshlibs" not in (kcd/"rules").read_text(): fail("KCalendarCore ABI overlay hook missing")

kod=ROOT/"packages/kde/kcoreaddons/debian"
required={" _ZN10KAboutData6setUrlENS_7UrlTypeERK7QString@Base 6.29.0"," _ZNK10KAboutData3urlENS_7UrlTypeE@Base 6.29.0"}
if set((kod/"libkf6coreaddons6.symbols.supralinux-overlay").read_text().splitlines()) != required: fail("KCoreAddons ABI overlay regression")

kwd=ROOT/"packages/kde/kwidgetsaddons/debian"; kwc=(kwd/"control").read_text(); kwr=(kwd/"rules").read_text()
if "6.30.0-0supralinux6" not in (kwd/"changelog").read_text().splitlines()[0]: fail("KWidgetsAddons changelog not at -6")
for token in ("fontconfig <!nocheck>","fonts-dejavu-core <!nocheck>","openbox <!nocheck>","x11-utils <!nocheck>"):
    if token not in kwc: fail(f"KWidgetsAddons missing test fixture dependency {token}")
for token in ("-DBUILD_DESIGNERPLUGIN=ON","DEB_BUILD_OPTIONS"," nocheck ","fc-match","DejaVu Sans","ctest --test-dir","-N -E","-N -R","test \"$$total\" -eq 27","test \"$$nongesture\" -eq 25","test \"$$gesture\" -eq 2","ktwofingertaptest","ktwofingerswipetest","openbox","_NET_SUPPORTING_WM_CHECK"):
    if token not in kwr: fail(f"KWidgetsAddons deterministic fixture missing {token}")
if kwr.count("ctest --test-dir") < 5: fail("KWidgetsAddons must inventory both partitions and execute both partitions")

workflow=W.read_text(); runner=R.read_text()
for token in ("fail-fast: false","max-parallel: 3","kcalendarcore, kcoreaddons, kwidgetsaddons"):
    if token not in workflow: fail(f"Batch 7 workflow contract missing {token}")
for token in ("100% tests passed, 0 tests failed","Lintian:[[:space:]]+fail","python-import-smoke","consumer-runtime-closure","downstream_eligible=yes"):
    if token not in runner: fail(f"Batch 7 runner lost strict gate {token}")

print("KDE Tier 1 Batch 7 preparation: PASS")
print("KCalendarCore=PASS; KCoreAddons=PASS; KWidgetsAddons=-6 deterministic font/test fixture pending real build")
