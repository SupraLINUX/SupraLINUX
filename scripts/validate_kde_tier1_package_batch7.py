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
 "kwidgetsaddons":(["FAIL"]*6,[f"6.30.0-0supralinux{i}" for i in range(1,7)]),
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
if kw.get("package_version")!="6.30.0-0supralinux7" or kw.get("state")!="remediation-pending-build" or kw.get("last_result")!="FAIL" or kw.get("downstream_eligible") is not False: fail("KWidgetsAddons -7 remediation state mismatch")
rem=kw.get("remediation",{}); part=rem.get("fixture_partition",{}); font=rem.get("font_fixture",{})
if part != {"total":27,"bare_xvfb":25,"xvfb_openbox":2,"openbox_tests":["ktwofingertaptest","ktwofingerswipetest"]}: fail("KWidgetsAddons fixture partition mismatch")
if font != {"resolver":"fontconfig","provider":"fonts-dejavu-core","generic":"sans-serif","expected_family_contains":"DejaVu Sans"}: fail("KWidgetsAddons font fixture mismatch")
if rem.get("tests_omitted") is not False or rem.get("source_change") is not False: fail("KWidgetsAddons must retain all upstream tests/source")
if rem.get("dependency_fix",{}).get("substvar") != "${shlibs:Depends}": fail("KWidgetsAddons dev shlibs remediation missing")
abi=rem.get("abi_overlay",{})
expected_kde=["_ZN11KColorCombo14dragEnterEventEP15QDragEnterEvent@Base","_ZN11KColorCombo16contextMenuEventEP17QContextMenuEvent@Base","_ZN11KColorCombo9dropEventEP10QDropEvent@Base","_ZN12KColorButton16contextMenuEventEP17QContextMenuEvent@Base","_ZNK16KAssistantDialog10onLastPageEv@Base"]
if abi.get("kde_minimum_6_29") != expected_kde or abi.get("toolchain_minimum_6_30") != ["_ZSt19piecewise_construct@Base"]: fail("KWidgetsAddons reviewed ABI classification mismatch")
last=a["attempts"]["kwidgetsaddons"][-1]
for key,value in {"workflow_run":35138333353,"job_id":104936243365,"artifact_id":10464950275,"artifact_sha256":"6ec80fbeeeecb7f119bea3bc2aa2ddaee665b27f52d636119260abccdcbfd883","rootfs_sha256":"08c582c7f007c64c03c476739a554527b6d8edda4905c8515f0f3224e7810ceb","failure_substage":"lintian/dev-shlibs-and-new-symbol-minima","tests":"27/27 PASS"}.items():
    if last.get(key)!=value: fail(f"KWidgetsAddons -6 FAIL evidence mismatch: {key}")

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
if "6.30.0-0supralinux7" not in (kwd/"changelog").read_text().splitlines()[0]: fail("KWidgetsAddons changelog not at -7")
for token in ("fontconfig <!nocheck>","fonts-dejavu-core <!nocheck>","openbox <!nocheck>","x11-utils <!nocheck>"):
    if token not in kwc: fail(f"KWidgetsAddons missing test fixture dependency {token}")
if "Package: libkf6widgetsaddons-dev" not in kwc or "${shlibs:Depends}" not in kwc.split("Package: libkf6widgetsaddons-dev",1)[1].split("Package:",1)[0]: fail("KWidgetsAddons dev package must consume shlibs substvar")
for token in ("-DBUILD_DESIGNERPLUGIN=ON","DEB_BUILD_OPTIONS"," nocheck ","fc-match","DejaVu Sans","ctest --test-dir","-N -E","-N -R","test \"$$total\" -eq 27","test \"$$nongesture\" -eq 25","test \"$$gesture\" -eq 2","ktwofingertaptest","ktwofingerswipetest","openbox","_NET_SUPPORTING_WM_CHECK","execute_before_dh_makeshlibs","libkf6widgetsaddons6.symbols.supralinux-overlay"):
    if token not in kwr: fail(f"KWidgetsAddons deterministic fixture/ABI hook missing {token}")
if kwr.count("ctest --test-dir") < 5: fail("KWidgetsAddons must inventory both partitions and execute both partitions")
expected_overlay={
 " _ZN11KColorCombo14dragEnterEventEP15QDragEnterEvent@Base 6.29.0",
 " _ZN11KColorCombo16contextMenuEventEP17QContextMenuEvent@Base 6.29.0",
 " _ZN11KColorCombo9dropEventEP10QDropEvent@Base 6.29.0",
 " _ZN12KColorButton16contextMenuEventEP17QContextMenuEvent@Base 6.29.0",
 " _ZNK16KAssistantDialog10onLastPageEv@Base 6.29.0",
 " (optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0",
}
actual_overlay=set((kwd/"libkf6widgetsaddons6.symbols.supralinux-overlay").read_text().splitlines())
if actual_overlay != expected_overlay: fail("KWidgetsAddons ABI overlay contents mismatch")

workflow=W.read_text(); runner=R.read_text()
for token in ("fail-fast: false","max-parallel: 3","kcalendarcore, kcoreaddons, kwidgetsaddons"):
    if token not in workflow: fail(f"Batch 7 workflow contract missing {token}")
for token in ("100% tests passed, 0 tests failed","Lintian:[[:space:]]+fail","python-import-smoke","consumer-runtime-closure","downstream_eligible=yes"):
    if token not in runner: fail(f"Batch 7 runner lost strict gate {token}")

print("KDE Tier 1 Batch 7 preparation: PASS")
print("KCalendarCore=PASS; KCoreAddons=PASS; KWidgetsAddons=-7 ABI/dev-dependency remediation pending real build")
