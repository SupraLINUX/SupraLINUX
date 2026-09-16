#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "manifests/kde-tier1-package-campaign-batch7.json"
A = ROOT / "manifests/kde-tier1-package-batch7-attempts.json"
W = ROOT / ".github/workflows/kde-tier1-package-batch7.yml"
R = ROOT / "scripts/run-kde-tier1-package-batch7-preflight.sh"

def fail(msg): raise SystemExit(msg)
def load(p): return json.loads(p.read_text())

m=load(M); a=load(A)
expected={"kcalendarcore","kcoreaddons","kwidgetsaddons"}
if m.get("schema") != 2 or m.get("authority") != "kde-upstream" or m.get("frameworks_series") != "6.30.0":
    fail("Batch 7 manifest identity mismatch")
if set(m.get("selected_nodes",[])) != expected or set(m.get("nodes",{})) != expected:
    fail("Batch 7 node set mismatch")
if m.get("attempt_ledger") != "manifests/kde-tier1-package-batch7-attempts.json":
    fail("Batch 7 attempt ledger path mismatch")
if a.get("immutable_history") is not True or set(a.get("attempts",{})) != expected:
    fail("Batch 7 history ledger mismatch")

hist_expect = {
    "kcalendarcore": ["FAIL","FAIL","FAIL","FAIL"],
    "kcoreaddons": ["FAIL","FAIL","FAIL","PASS"],
    "kwidgetsaddons": ["FAIL","FAIL","FAIL","FAIL"],
}
versions = [
    "6.30.0-0supralinux1","6.30.0-0supralinux2",
    "6.30.0-0supralinux3","6.30.0-0supralinux4",
]
for node in expected:
    hist=a["attempts"][node]
    if len(hist) != 4 or [x.get("result") for x in hist] != hist_expect[node]:
        fail(f"{node}: retained attempt history mismatch")
    if [x.get("attempted_package_version") for x in hist] != versions:
        fail(f"{node}: historical revisions mismatch")

kc=m["nodes"]["kcalendarcore"]
if kc.get("package_version") != "6.30.0-0supralinux5" or kc.get("state") != "remediation-pending-build":
    fail("KCalendarCore -5 remediation state mismatch")
if kc.get("last_result") != "FAIL" or kc.get("downstream_eligible") is not False:
    fail("KCalendarCore must remain unpromoted after -4 FAIL")
if kc.get("remediation",{}).get("baseline_groups") != {"6.29.0":10,"6.30.0":8}:
    fail("KCalendarCore ABI baseline grouping mismatch")

ko=m["nodes"]["kcoreaddons"]
if ko.get("package_version") != "6.30.0-0supralinux4" or ko.get("state") != "PASS":
    fail("KCoreAddons PASS state mismatch")
if ko.get("last_result") != "PASS" or ko.get("downstream_eligible") is not True:
    fail("KCoreAddons must be downstream eligible")
pe=ko.get("pass_evidence",{})
for key,value in {
    "workflow_run":35122522242,
    "job_id":104883541991,
    "artifact_id":10457958023,
    "artifact_sha256":"c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64",
    "rootfs_sha256":"dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794",
}.items():
    if pe.get(key) != value: fail(f"KCoreAddons PASS evidence mismatch: {key}")

kw=m["nodes"]["kwidgetsaddons"]
if kw.get("package_version") != "6.30.0-0supralinux4" or kw.get("state") != "remediation-pending-build":
    fail("KWidgetsAddons diagnostic state mismatch")
if kw.get("last_result") != "FAIL" or kw.get("downstream_eligible") is not False:
    fail("KWidgetsAddons must remain unpromoted")
if kw.get("remediation",{}).get("tests_filtered") is not False:
    fail("KWidgetsAddons test must not be filtered")

for node in expected:
    base=ROOT/"packages/kde"/node/"debian"
    control=(base/"control").read_text()
    for token in ("clang", "libclang-dev", "llvm-dev", "python3-build", "python3-setuptools"):
        if token not in control: fail(f"{node}: missing {token} build dependency")
    rules=(base/"rules").read_text()
    if "-DBUILD_PYTHON_BINDINGS=ON" not in rules or "-DBUILD_TESTING=ON" not in rules:
        fail(f"{node}: upstream Python/tests must remain enabled")

kcd=ROOT/"packages/kde/kcalendarcore/debian"
if "6.30.0-0supralinux5" not in (kcd/"changelog").read_text().splitlines()[0]:
    fail("KCalendarCore changelog not at -5")
if (kcd/"libkf6calendarcore-data.install").read_text().strip() != "usr/share/locale/*/LC_MESSAGES/kcalendarcore6_qt.qm":
    fail("KCalendarCore translation ownership mismatch")
overlay=(kcd/"libkf6calendarcore6.symbols.supralinux-overlay").read_text().splitlines()
if len(overlay) != 18:
    fail("KCalendarCore ABI overlay must contain exactly 18 symbols")
if sum(line.endswith(" 6.29.0") for line in overlay) != 10 or sum(line.endswith(" 6.30.0") for line in overlay) != 8:
    fail("KCalendarCore ABI overlay version grouping mismatch")
kcr=(kcd/"rules").read_text()
if "execute_before_dh_makeshlibs" not in kcr or "libkf6calendarcore6.symbols.supralinux-overlay" not in kcr:
    fail("KCalendarCore ABI overlay is not applied before dh_makeshlibs")

kod=ROOT/"packages/kde/kcoreaddons/debian"
ko_overlay=(kod/"libkf6coreaddons6.symbols.supralinux-overlay").read_text().splitlines()
required={" _ZN10KAboutData6setUrlENS_7UrlTypeERK7QString@Base 6.29.0"," _ZNK10KAboutData3urlENS_7UrlTypeE@Base 6.29.0"}
if set(ko_overlay) != required:
    fail("KCoreAddons ABI overlay regression")

kwd=ROOT/"packages/kde/kwidgetsaddons/debian"
kwc=(kwd/"control").read_text(); kwr=(kwd/"rules").read_text()
for token in ("openbox <!nocheck>", "x11-utils <!nocheck>"):
    if token not in kwc: fail(f"KWidgetsAddons missing test fixture dependency {token}")
for token in ("-DBUILD_DESIGNERPLUGIN=ON", "openbox", "_NET_SUPPORTING_WM_CHECK", "dh_auto_test --no-parallel"):
    if token not in kwr: fail(f"KWidgetsAddons test fixture missing {token}")
if "ctest -E" in kwr or "--exclude" in kwr:
    fail("KWidgetsAddons tests must not be filtered")

workflow=W.read_text(); runner=R.read_text()
for token in ("fail-fast: false", "max-parallel: 3", "kcalendarcore, kcoreaddons, kwidgetsaddons"):
    if token not in workflow: fail(f"Batch 7 workflow contract missing {token}")
for token in ("100% tests passed, 0 tests failed", "Lintian:[[:space:]]+fail", "python-import-smoke", "consumer-runtime-closure", "downstream_eligible=yes"):
    if token not in runner: fail(f"Batch 7 runner lost strict gate {token}")

print("KDE Tier 1 Batch 7 preparation: PASS")
