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
if m.get("schema") != 2 or m.get("authority") != "kde-upstream" or m.get("frameworks_series") != "6.30.0": fail("Batch 7 manifest identity mismatch")
if set(m.get("selected_nodes",[])) != expected or set(m.get("nodes",{})) != expected: fail("Batch 7 node set mismatch")
if m.get("attempt_ledger") != "manifests/kde-tier1-package-batch7-attempts.json": fail("Batch 7 attempt ledger path mismatch")
if a.get("immutable_history") is not True or set(a.get("attempts",{})) != expected: fail("Batch 7 history ledger mismatch")
for node in expected:
    hist=a["attempts"][node]
    if len(hist) != 3 or [x.get("result") for x in hist] != ["FAIL","FAIL","FAIL"]: fail(f"{node}: expected exactly three retained FAIL attempts")
    if [x.get("attempted_package_version") for x in hist] != ["6.30.0-0supralinux1","6.30.0-0supralinux2","6.30.0-0supralinux3"]: fail(f"{node}: historical revisions mismatch")
    n=m["nodes"][node]
    if n.get("package_version") != "6.30.0-0supralinux4" or n.get("state") != "remediation-pending-build" or n.get("last_result") != "FAIL" or n.get("downstream_eligible") is not False: fail(f"{node}: -4 remediation state mismatch")
    base=ROOT/"packages/kde"/node/"debian"
    if "6.30.0-0supralinux4" not in (base/"changelog").read_text().splitlines()[0]: fail(f"{node}: changelog not at -4")
    control=(base/"control").read_text()
    for token in ("clang", "libclang-dev", "llvm-dev", "python3-build", "python3-setuptools"):
        if token not in control: fail(f"{node}: missing {token} build dependency")
    rules=(base/"rules").read_text()
    if "-DBUILD_PYTHON_BINDINGS=ON" not in rules or "-DBUILD_TESTING=ON" not in rules: fail(f"{node}: upstream Python/tests must remain enabled")

kc=ROOT/"packages/kde/kcalendarcore/debian"
kcc=(kc/"control").read_text()
for token in ("Package: libkf6calendarcore-data", "libkf6calendarcore-data (= ${source:Version})"):
    if token not in kcc: fail("KCalendarCore data split contract missing")
if (kc/"libkf6calendarcore-data.install").read_text().strip() != "usr/share/locale/*/LC_MESSAGES/kcalendarcore6_qt.qm": fail("KCalendarCore translation ownership mismatch")
if not any(x["name"]=="libkf6calendarcore-data" for x in m["nodes"]["kcalendarcore"]["binary_contracts"]): fail("KCalendarCore manifest lacks data package")

ko=ROOT/"packages/kde/kcoreaddons/debian"
overlay=(ko/"libkf6coreaddons6.symbols.supralinux-overlay").read_text().splitlines()
required={" _ZN10KAboutData6setUrlENS_7UrlTypeERK7QString@Base 6.29.0"," _ZNK10KAboutData3urlENS_7UrlTypeE@Base 6.29.0"}
if set(overlay) != required: fail("KCoreAddons ABI overlay must contain exactly the two upstream-6.29 symbols")
kor=(ko/"rules").read_text()
if "execute_before_dh_makeshlibs" not in kor or "symbols.supralinux-overlay" not in kor: fail("KCoreAddons ABI overlay is not applied before dh_makeshlibs")

kw=ROOT/"packages/kde/kwidgetsaddons/debian"
kwc=(kw/"control").read_text(); kwr=(kw/"rules").read_text()
for token in ("openbox <!nocheck>", "x11-utils <!nocheck>"):
    if token not in kwc: fail(f"KWidgetsAddons missing test fixture dependency {token}")
for token in ("-DBUILD_DESIGNERPLUGIN=ON", "openbox", "_NET_SUPPORTING_WM_CHECK", "dh_auto_test --no-parallel"):
    if token not in kwr: fail(f"KWidgetsAddons test fixture missing {token}")
if "ctest -E" in kwr or "--exclude" in kwr: fail("KWidgetsAddons tests must not be filtered")

workflow=W.read_text(); runner=R.read_text()
for token in ("fail-fast: false", "max-parallel: 3", "kcalendarcore, kcoreaddons, kwidgetsaddons"):
    if token not in workflow: fail(f"Batch 7 workflow contract missing {token}")
for token in ("100% tests passed, 0 tests failed", "Lintian:[[:space:]]+fail", "python-import-smoke", "consumer-runtime-closure", "downstream_eligible=yes"):
    if token not in runner: fail(f"Batch 7 runner lost strict gate {token}")

print("KDE Tier 1 Batch 7 preparation: PASS")
