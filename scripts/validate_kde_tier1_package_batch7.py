#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "manifests/kde-tier1-package-campaign-batch7.json"
A = ROOT / "manifests/kde-tier1-package-batch7-attempts.json"
W = ROOT / ".github/workflows/kde-tier1-package-batch7.yml"
R = ROOT / "scripts/run-kde-tier1-package-batch7-preflight.sh"


def fail(msg):
    raise SystemExit(msg)


def load(path):
    return json.loads(path.read_text())


m = load(M)
a = load(A)
expected = {"kcalendarcore", "kcoreaddons", "kwidgetsaddons"}

if m.get("schema") != 2 or m.get("authority") != "kde-upstream" or m.get("frameworks_series") != "6.30.0":
    fail("Batch 7 manifest identity mismatch")
if m.get("state") != "PASS":
    fail("Batch 7 must be technically closed PASS")
if m.get("canonical_snapshot") != {
    "state": "technical-closure-awaiting-canonical-promotion",
    "tier1": "18 PASS / 11 pending in canonical manifest; all three Batch 7 nodes have retained PASS evidence and are ready for atomic canonical promotion",
}:
    fail("Batch 7 pre-promotion canonical snapshot mismatch")
if set(m.get("selected_nodes", [])) != expected or set(m.get("nodes", {})) != expected:
    fail("Batch 7 node set mismatch")
if m.get("attempt_ledger") != "manifests/kde-tier1-package-batch7-attempts.json":
    fail("Batch 7 attempt ledger path mismatch")
if a.get("immutable_history") is not True or set(a.get("attempts", {})) != expected:
    fail("Batch 7 history ledger mismatch")

hist_expect = {
    "kcalendarcore": (["FAIL", "FAIL", "FAIL", "FAIL", "PASS"], [f"6.30.0-0supralinux{i}" for i in range(1, 6)]),
    "kcoreaddons": (["FAIL", "FAIL", "FAIL", "PASS"], [f"6.30.0-0supralinux{i}" for i in range(1, 5)]),
    "kwidgetsaddons": (["FAIL"] * 6 + ["PASS"], [f"6.30.0-0supralinux{i}" for i in range(1, 8)]),
}
for node, (results, versions) in hist_expect.items():
    hist = a["attempts"][node]
    if [x.get("result") for x in hist] != results:
        fail(f"{node}: retained result history mismatch")
    if [x.get("attempted_package_version") for x in hist] != versions:
        fail(f"{node}: historical revisions mismatch")

pass_expect = {
    "kcalendarcore": {
        "version": "6.30.0-0supralinux5", "run": 35130213945, "job": 104909057699,
        "artifact": 10461386548, "digest": "6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6",
        "rootfs": "eb3e6bfe65b142c1308d8a1892e00c6bd57028126147ac09376778dec60692f6",
        "tests": "507/507 PASS", "soname": "libKF6CalendarCore.so.6",
    },
    "kcoreaddons": {
        "version": "6.30.0-0supralinux4", "run": 35122522242, "job": 104883541991,
        "artifact": 10457958023, "digest": "c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64",
        "rootfs": "dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794",
        "tests": "34/34 PASS", "soname": "libKF6CoreAddons.so.6",
    },
    "kwidgetsaddons": {
        "version": "6.30.0-0supralinux7", "run": 35145607543, "job": 104960718770,
        "artifact": 10467164025, "digest": "f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e",
        "rootfs": "d381a2d238103d21dbce47af60377b48ca77b385ab8598d135d30386ac17cf12",
        "tests": "27/27 PASS", "soname": "libKF6WidgetsAddons.so.6",
    },
}
for node, exp in pass_expect.items():
    n = m["nodes"][node]
    if n.get("package_version") != exp["version"] or n.get("state") != "PASS" or n.get("last_result") != "PASS" or n.get("downstream_eligible") is not True:
        fail(f"{node}: PASS state mismatch")
    ev = n.get("pass_evidence", {})
    for key, value in {
        "workflow_run": exp["run"], "job_id": exp["job"], "artifact_id": exp["artifact"],
        "artifact_sha256": exp["digest"], "rootfs_sha256": exp["rootfs"], "tests": exp["tests"],
        "lintian": "PASS-errors", "consumer_smoke": "PASS", "python_import": "PASS",
        "apt_check": "PASS", "abi_soname": exp["soname"],
    }.items():
        if ev.get(key) != value:
            fail(f"{node}: PASS evidence mismatch: {key}")
    files = n.get("last_pass_files", {})
    if not files or files.get("rootfs_sha256") != exp["rootfs"]:
        fail(f"{node}: retained file/rootfs hashes missing")
    if any(len(str(v)) != 64 for v in files.values()):
        fail(f"{node}: invalid retained SHA-256 length")
    hist_pass = a["attempts"][node][-1]
    if hist_pass.get("result") != "PASS" or hist_pass.get("workflow_run") != exp["run"] or hist_pass.get("artifact_id") != exp["artifact"] or hist_pass.get("artifact_sha256") != exp["digest"]:
        fail(f"{node}: final immutable ledger PASS mismatch")

kw_last = a["attempts"]["kwidgetsaddons"][-2]
for key, value in {
    "workflow_run": 35138333353,
    "job_id": 104936243365,
    "artifact_id": 10464950275,
    "artifact_sha256": "6ec80fbeeeecb7f119bea3bc2aa2ddaee665b27f52d636119260abccdcbfd883",
    "rootfs_sha256": "08c582c7f007c64c03c476739a554527b6d8edda4905c8515f0f3224e7810ceb",
    "failure_substage": "lintian/dev-shlibs-and-new-symbol-minima",
    "tests": "27/27 PASS",
}.items():
    if kw_last.get(key) != value:
        fail(f"KWidgetsAddons -6 FAIL evidence mismatch: {key}")

for node in expected:
    base = ROOT / "packages/kde" / node / "debian"
    control = (base / "control").read_text()
    rules = (base / "rules").read_text()
    for token in ("clang", "libclang-dev", "llvm-dev", "python3-build", "python3-setuptools"):
        if token not in control:
            fail(f"{node}: missing {token} build dependency")
    if "-DBUILD_PYTHON_BINDINGS=ON" not in rules or "-DBUILD_TESTING=ON" not in rules:
        fail(f"{node}: upstream Python/tests must remain enabled")

kcd = ROOT / "packages/kde/kcalendarcore/debian"
if "6.30.0-0supralinux5" not in (kcd / "changelog").read_text().splitlines()[0]:
    fail("KCalendarCore changelog not at -5")
if (kcd / "libkf6calendarcore-data.install").read_text().strip() != "usr/share/locale/*/LC_MESSAGES/kcalendarcore6_qt.qm":
    fail("KCalendarCore translation ownership mismatch")
kcal_overlay = (kcd / "libkf6calendarcore6.symbols.supralinux-overlay").read_text().splitlines()
if len(kcal_overlay) != 18 or sum(x.endswith(" 6.29.0") for x in kcal_overlay) != 10 or sum(x.endswith(" 6.30.0") for x in kcal_overlay) != 8:
    fail("KCalendarCore ABI overlay mismatch")

kod = ROOT / "packages/kde/kcoreaddons/debian"
required = {" _ZN10KAboutData6setUrlENS_7UrlTypeERK7QString@Base 6.29.0", " _ZNK10KAboutData3urlENS_7UrlTypeE@Base 6.29.0"}
if set((kod / "libkf6coreaddons6.symbols.supralinux-overlay").read_text().splitlines()) != required:
    fail("KCoreAddons ABI overlay regression")

kwd = ROOT / "packages/kde/kwidgetsaddons/debian"
kwc = (kwd / "control").read_text()
kwr = (kwd / "rules").read_text()
if "6.30.0-0supralinux7" not in (kwd / "changelog").read_text().splitlines()[0]:
    fail("KWidgetsAddons changelog not at -7")
for token in ("fontconfig <!nocheck>", "fonts-dejavu-core <!nocheck>", "openbox <!nocheck>", "x11-utils <!nocheck>"):
    if token not in kwc:
        fail(f"KWidgetsAddons missing test fixture dependency {token}")
if "Package: libkf6widgetsaddons-dev" not in kwc or "${shlibs:Depends}" not in kwc.split("Package: libkf6widgetsaddons-dev", 1)[1].split("Package:", 1)[0]:
    fail("KWidgetsAddons dev package must consume shlibs substvar")
for token in ("-DBUILD_DESIGNERPLUGIN=ON", "fc-match", "DejaVu Sans", "ktwofingertaptest", "ktwofingerswipetest", "openbox", "_NET_SUPPORTING_WM_CHECK", "execute_before_dh_makeshlibs", "libkf6widgetsaddons6.symbols.supralinux-overlay"):
    if token not in kwr:
        fail(f"KWidgetsAddons deterministic fixture/ABI hook missing {token}")
expected_overlay = {
    " _ZN11KColorCombo14dragEnterEventEP15QDragEnterEvent@Base 6.29.0",
    " _ZN11KColorCombo16contextMenuEventEP17QContextMenuEvent@Base 6.29.0",
    " _ZN11KColorCombo9dropEventEP10QDropEvent@Base 6.29.0",
    " _ZN12KColorButton16contextMenuEventEP17QContextMenuEvent@Base 6.29.0",
    " _ZNK16KAssistantDialog10onLastPageEv@Base 6.29.0",
    " (optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0",
}
if set((kwd / "libkf6widgetsaddons6.symbols.supralinux-overlay").read_text().splitlines()) != expected_overlay:
    fail("KWidgetsAddons ABI overlay contents mismatch")

workflow = W.read_text()
runner = R.read_text()
for token in ("fail-fast: false", "max-parallel: 3", "kcalendarcore, kcoreaddons, kwidgetsaddons"):
    if token not in workflow:
        fail(f"Batch 7 workflow contract missing {token}")
for token in ("100% tests passed, 0 tests failed", "Lintian:[[:space:]]+fail", "python-import-smoke", "consumer-runtime-closure", "downstream_eligible=yes"):
    if token not in runner:
        fail(f"Batch 7 runner lost strict gate {token}")

print("KDE Tier 1 Batch 7 technical closure: PASS")
print("KCalendarCore, KCoreAddons and KWidgetsAddons = 3/3 retained PASS/downstream-eligible")
print("Canonical Tier 1 promotion remains a separate atomic state update: currently 18 PASS / 11 pending")
