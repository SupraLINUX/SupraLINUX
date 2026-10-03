#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-package-campaign-batch3.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"
DAG = ROOT / "manifests/kde-dag.json"
DOC = ROOT / "docs/kde-tier1-package-batch3.md"
WORKFLOW = ROOT / ".github/workflows/kde-tier1-package-batch3.yml"
RUNNER = ROOT / "scripts/run-kde-tier1-package-batch3-preflight.sh"
SCOPE = ROOT / "scripts/kde-tier1-package-batch3-needed.sh"

EXPECTED = {
    "kitemmodels": {
        "version": "6.30.0-0supralinux1",
        "source": "f807e5b37aa913d2563ee1a21b2bce7d34495f32f38c7f35f16262d736bdfd55",
        "symbols": "d9cbc25df40c2ea378cb8e3e77dafcea63a7b542315dc90498cb27f087db1c1e",
        "runtime": "libkf6itemmodels6",
        "soname": "libKF6ItemModels.so.6",
        "run": 34896417969,
        "job": 104151531993,
        "commit": "806d16476b034e796658ea1ab9028eb3a9a14e1b",
        "artifact": 10369501432,
        "artifact_sha256": "b806eaf27f733c1a2b5cc1d108ca442fef673b6dc0a53cfc5fff38abd2bf6732",
        "tests": "13/13 PASS",
        "build": ["dh-sequence-qmldeps", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
    },
    "bluez-qt": {
        "version": "6.30.0-0supralinux2",
        "source": "f5045b14a6c689bbfded9437582f943dd4f8f74537085ab6115bcacdea2110d8",
        "symbols": "b72bea28842160da234b3bbab7975623616cd58f3e522b1e5d8705a279eef4f7",
        "runtime": "libkf6bluezqt6",
        "soname": "libKF6BluezQt.so.6",
        "run": 34945979836,
        "job": 104305337324,
        "commit": "b58b5e6072bb14487e304857d34a53659ec50f60",
        "artifact": 10387429776,
        "artifact_sha256": "db8a3718a31eaae00d5f9fbdb60014dfeb1faf1c2bc84a88f9ab0d9bffec07ed",
        "tests": "18/18 PASS",
        "build": ["dh-sequence-qmldeps", "dbus-daemon <!nocheck>", "python3", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
    },
    "kplotting": {
        "version": "6.30.0-0supralinux1",
        "source": "f5a67be85c21665e052371301889443196b9de5b3927aff353a3d3e27730dd11",
        "symbols": "de5fddb29e85c05edefee280b2acf547d285318e6334b63b4a58527f59260cdb",
        "runtime": "libkf6plotting6",
        "soname": "libKF6Plotting.so.6",
        "run": 34896417969,
        "job": 104151532320,
        "commit": "806d16476b034e796658ea1ab9028eb3a9a14e1b",
        "artifact": 10369086459,
        "artifact_sha256": "f4c4f7425e582b5001fdffced34d045dc46152074422bd2bcf994e544bb96bb8",
        "tests": "5/5 PASS",
        "build": ["qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
    },
}

errors: list[str] = []


def req(value: bool, message: str) -> None:
    if not value:
        errors.append(message)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_line_index(text: str, command: str) -> int:
    """Return the first Make recipe line that executes command, never a target name."""
    for index, line in enumerate(text.splitlines()):
        stripped = line.lstrip()
        if stripped == command or stripped.startswith(command + " "):
            return index
    return -1


campaign = load(CAMPAIGN)
tier1 = {item["id"]: item for item in load(TIER1)["nodes"]}
dag = load(DAG)["nodes"]

req(campaign.get("schema") == 1, "campaign schema")
req(campaign.get("authority") == "kde-upstream", "KDE authority")
req(campaign.get("frameworks_series") == "6.30.0", "Frameworks version")
req(campaign.get("batch") == "tier1-batch-3", "batch id")
req(campaign.get("state") == "PASS", "Batch 3 final PASS state")
req(campaign.get("selected_nodes") == list(EXPECTED), "selected nodes")
req(campaign["selection_rationale"]["deferred"].get("kconfig", "").startswith("Deferred because KConfig exports multiple ABI"), "KConfig deferral rationale")
req(campaign["shared_predecessors"]["extra_cmake_modules"]["version"] == "6.30.0-0supralinux3", "ECM predecessor")
req(campaign["shared_packaging_inputs"]["documentation_policy"]["qch_enabled"] is False, "QCH policy")
req(campaign["shared_packaging_inputs"]["lintian_policy"]["source_and_changes_required"] is True, "Lintian source+changes policy")

for node, expected in EXPECTED.items():
    data = campaign["nodes"][node]
    req(data["state"] == "PASS", f"{node}: campaign state")
    req(data["last_result"] == "PASS", f"{node}: last result")
    req(data["downstream_eligible"] is True, f"{node}: downstream eligibility")
    req(data["package_version"] == expected["version"], f"{node}: package revision")
    req(data["source_sha256"] == expected["source"], f"{node}: source hash")
    req(data["symbols"]["sha256"] == expected["symbols"], f"{node}: symbols baseline")
    req(data["symbols"]["tree_provider"] == "debian", f"{node}: symbols provider")
    req(data["runtime_package"] == expected["runtime"], f"{node}: runtime package")
    req(data["soname"] == expected["soname"], f"{node}: SONAME")

    final = data["evidence"][-1]
    req(final.get("result") == "PASS", f"{node}: final evidence result")
    req(final.get("workflow_run") == expected["run"], f"{node}: final workflow")
    req(final.get("job_id") == expected["job"], f"{node}: final job")
    req(final.get("commit") == expected["commit"], f"{node}: final evidence commit")
    req(final.get("artifact_id") == expected["artifact"], f"{node}: final artifact")
    req(final.get("artifact_sha256") == expected["artifact_sha256"], f"{node}: final artifact SHA-256")
    req(final.get("tests") == expected["tests"], f"{node}: tests")
    req(final.get("lintian") == "PASS-errors", f"{node}: Lintian")
    req(final.get("consumer_smoke") == "PASS", f"{node}: consumer smoke")
    req(final.get("downstream_eligible") is True, f"{node}: final downstream eligibility")

    deb = ROOT / "packages/kde" / node / "debian"
    control = (deb / "control").read_text(encoding="utf-8")
    rules = (deb / "rules").read_text(encoding="utf-8")
    readme = (deb / "README.source").read_text(encoding="utf-8")
    docinstall = (deb / data["documentation_package"].replace("-doc", "-doc.install")).read_text(encoding="utf-8")
    consumer = (ROOT / "packages/kde" / node / "consumer/CMakeLists.txt").read_text(encoding="utf-8")
    main = (ROOT / "packages/kde" / node / "consumer/main.cpp").read_text(encoding="utf-8")

    for token in ["debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", *expected["build"]]:
        req(token in control, f"{node}: missing Build-Depends {token}")
    req("Standards-Version: 4.7.3" in control, f"{node}: Standards-Version")
    req("documentation compatibility package" in control, f"{node}: documentation description")
    req("does not ship QCH documentation files" in control, f"{node}: QCH truth")
    req("Intentionally empty" in docinstall, f"{node}: empty documentation install")
    req("-DBUILD_QCH=OFF" in rules, f"{node}: QCH disabled")
    req("dh_auto_test" in rules, f"{node}: tests enabled")
    req("KDE Frameworks 6.30.0 is the source/build authority" in readme, f"{node}: authority documentation")
    req(sha(deb / "upstream/signing-key.asc") == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", f"{node}: signing key")
    req(data["cmake_package"] in consumer and data["cmake_target"] in consumer, f"{node}: CMake consumer")
    req(expected["soname"] in main and "dlopen" in main, f"{node}: runtime consumer")

    req(tier1[node]["state"] == "PASS", f"{node}: Tier 1 canonical PASS")
    req(tier1[node]["packaging"]["state"] == "PASS", f"{node}: Tier 1 packaging PASS")
    req(tier1[node]["packaging"]["package_version"] == expected["version"], f"{node}: Tier 1 package version")
    req(tier1[node]["packaging"]["downstream_eligible"] is True, f"{node}: Tier 1 downstream eligible")
    req(dag[node]["state"] == "PASS", f"{node}: DAG PASS")
    req(dag[node]["package_version"] == expected["version"], f"{node}: DAG package version")
    req(dag[node]["downstream_eligible"] is True, f"{node}: DAG downstream eligible")

bluez = campaign["nodes"]["bluez-qt"]
bluez_history = bluez["evidence"]
req(any(e.get("result") == "FAIL" and e.get("workflow_run") == 34896417969 and e.get("failure_substage") == "lintian" for e in bluez_history), "bluez-qt: historical FAIL must be retained")
req(any(e.get("result") == "PASS" and e.get("workflow_run") == 34945979836 for e in bluez_history), "bluez-qt: remediation PASS must be retained")
override = bluez["symbols"].get("reviewed_override", {})
req(override.get("method") == "deterministic-transform", "bluez-qt: reviewed symbols transform")
req(override.get("file_sha256") == "6e7f4a36c5b5b71c80728c23da82180af0772b4d9abf2f3feb834ffda0007565", "bluez-qt: transform SHA-256")
req(override.get("result_sha256") == "0fd10c9d93b303fa48aa5cd66aaf4727fbc27f4b784926f5ce5f8d20606bf37a", "bluez-qt: reviewed symbols result SHA-256")
transform = ROOT / "packages/kde/bluez-qt/debian/apply-symbols-delta.py"
req(transform.exists(), "bluez-qt: transform missing")
if transform.exists():
    req(sha(transform) == override.get("file_sha256"), "bluez-qt: transform file hash mismatch")

bluez_rules = (ROOT / "packages/kde/bluez-qt/debian/rules").read_text(encoding="utf-8")
transform_pos = command_line_index(bluez_rules, "python3 debian/apply-symbols-delta.py")
makeshlibs_pos = command_line_index(bluez_rules, "dh_makeshlibs")
req(transform_pos >= 0, "bluez-qt: symbols transform command missing")
req(makeshlibs_pos >= 0, "bluez-qt: dh_makeshlibs command invocation missing")
req(transform_pos >= 0 and makeshlibs_pos >= 0 and transform_pos < makeshlibs_pos, "bluez-qt: symbols transform must execute before dh_makeshlibs")

runner = RUNNER.read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")
scope = SCOPE.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")
for token in ["-name '*.ddeb'", 'lintian --fail-on error "${DSC}" "${CHANGES[0]}"', "Lintian:[[:space:]]+fail", "dpkg-source -b", "--chroot-mode=unshare", "consumer-smoke"]:
    req(token in runner, f"runner missing {token}")
for token in ["fail-fast: false", "max-parallel: 3", "kitemmodels", "bluez-qt", "kplotting", "run-kde-tier1-package-batch3-preflight.sh"]:
    req(token in workflow, f"workflow missing {token}")
req("kde-tier1-package-campaign-batch3.json" in scope, "scope campaign")
for token in ["34945979836", "104305337324", "10387429776", "db8a3718a31eaae00d5f9fbdb60014dfeb1faf1c2bc84a88f9ab0d9bffec07ed", "10 PASS / 19 pending / 0 current FAIL / 0 BLOCKED"]:
    req(token in doc, f"documentation missing {token}")
req("override_dh_makeshlibs:" in doc and "invocación real" in doc, "documentation must record validator false-positive remediation")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 3 validation: PASS")
print("KItemModels, BluezQt and KPlotting are canonical hosted-preflight PASS and downstream-eligible; Tier 1 is 10 PASS / 19 pending.")
