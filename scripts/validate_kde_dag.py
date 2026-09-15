#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "kde-dag.json"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-ecm-package-preflight.yml"
RUNNER = ROOT / "scripts" / "run-kde-ecm-package-preflight.sh"
DELTA = ROOT / "scripts" / "kde-ecm-preflight-needed.sh"
DOC = ROOT / "docs" / "kde-dag.md"
STATUS_DOC = ROOT / "docs" / "status" / "2026-09-12.md"
CURRENT_STATUS_DOC = ROOT / "docs" / "status" / "2026-09-15.md"
PACKAGE_DIR = ROOT / "packages" / "kde" / "extra-cmake-modules" / "debian"
CONTROL = PACKAGE_DIR / "control"
COPYRIGHT = PACKAGE_DIR / "copyright"
CHANGELOG = PACKAGE_DIR / "changelog"
RULES = PACKAGE_DIR / "rules"
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
UPLOAD_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
ECM_SHA256 = "22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e"
FIRST_FAIL = {
    "run_id": 34689672632,
    "artifact_id": 10296512341,
    "digest": "d47ac7361106ceb5f04729c1a3dcb4103b30255684e5b3f53b833edd6d4f6558",
}
SECOND_FAIL = {
    "run_id": 34690027788,
    "job_id": 103543538213,
    "artifact_id": 10296517706,
    "digest": "89ef0003fd8282965a4c253bcd0150b8f040fe134ca0385d1365cd8c31808239",
}
UNNECESSARY_SCOPE_RUN = {
    "run_id": 35009710506,
    "job_id": 104518322483,
    "artifact_id": 10413246489,
    "digest": "19f8ce8e17be9efab705df0a8974d89ef90ddcd06f5a9c53745f40ad227dcff4",
    "commit": "037b16b7954593641041953fa4a9452f819de314",
}
SCOPE_CONTRACT_RUN = {
    "run_id": 35010423516,
    "job_id": 104520693096,
    "commit": "906d8be5094f04d03a01de035e73b6c65ea0a58a",
}
CANDIDATE = "6.30.0-0supralinux3"
errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read(path: Path) -> str:
    if not path.exists():
        errors.append(f"required KDE DAG file missing: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


try:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot read {MANIFEST.relative_to(ROOT)}: {exc}", file=sys.stderr)
    raise SystemExit(1)

require(data.get("schema") == 1, "KDE DAG manifest schema must be 1")
require(data.get("frameworks_series") == "6.30.0", "KDE DAG Frameworks series must be 6.30.0")
require(data.get("authority") == "kde-upstream", "KDE DAG authority must remain kde-upstream")
require(data.get("states") == ["PASS", "FAIL", "BLOCKED", "pending"], "KDE DAG states must preserve PASS/FAIL/BLOCKED/pending semantics")

nodes = data.get("nodes", {})
ecm = nodes.get("extra-cmake-modules", {})
require(ecm.get("tier") == "build-system-root", "ECM must be the build-system-root node")
require(ecm.get("upstream_version") == "6.30.0", "ECM upstream version must be 6.30.0")
require(ecm.get("source_authority") == "kde-upstream", "ECM source authority must be KDE upstream")
require(ecm.get("package_provider") == "supralinux", "ECM package provider must be SupraLINUX")
require(ecm.get("source_package") == "kf6-extra-cmake-modules", "ECM source package name must preserve Ubuntu/Debian-compatible source naming")
require(ecm.get("binary_packages") == ["extra-cmake-modules"], "ECM binary package name must preserve Debian contract")
require(ecm.get("package_version") == CANDIDATE, "ECM remediation candidate package version is unexpected")
require(ecm.get("source_sha256") == ECM_SHA256, "ECM source SHA-256 must match KDE Frameworks 6.30.0 release metadata")
require(ecm.get("source_url") == "https://download.kde.org/stable/frameworks/6.30/extra-cmake-modules-6.30.0.tar.xz", "ECM source URL must use KDE stable release tarball")
require(ecm.get("source_evidence") == "https://kde.org/info/kde-frameworks-6.30.0/", "ECM source evidence must cite KDE release information")
require(ecm.get("depends_on") == [], "ECM root node must not depend on another KDE DAG node")
require(ecm.get("state") in {"pending", "PASS", "FAIL", "BLOCKED"}, "ECM DAG state is invalid")
require(ecm.get("state") != "BLOCKED", "ECM root node cannot be BLOCKED because it has no KDE DAG dependencies")

if ecm.get("state") in {"PASS", "FAIL"}:
    evidence = ecm.get("evidence", [])
    require(isinstance(evidence, list) and bool(evidence), f"{ecm.get('state')} ECM node requires retained evidence")
else:
    evidence = ecm.get("evidence", [])

if ecm.get("state") == "FAIL":
    by_run = {item.get("run_id"): item for item in evidence if isinstance(item, dict)}
    first = by_run.get(FIRST_FAIL["run_id"], {})
    second = by_run.get(SECOND_FAIL["run_id"], {})
    require(first.get("artifact_id") == FIRST_FAIL["artifact_id"], "ECM must retain first failure artifact ID")
    require(first.get("artifact_sha256") == FIRST_FAIL["digest"], "ECM must retain first failure artifact digest")
    require(first.get("failure_stage") == "dh_auto_test", "ECM must retain first failure stage")
    require("BUILD_TESTING=OFF" in str(first.get("cause", "")), "ECM must retain first failure root cause")
    require(second.get("job_id") == SECOND_FAIL["job_id"], "ECM must retain second failure job ID")
    require(second.get("artifact_id") == SECOND_FAIL["artifact_id"], "ECM must retain second failure artifact ID")
    require(second.get("artifact_sha256") == SECOND_FAIL["digest"], "ECM must retain second failure artifact digest")
    require(second.get("attempted_package_version") == "6.30.0-0supralinux2", "ECM must retain second attempted Debian revision")
    require(second.get("failure_stage") == "consumer-smoke", "ECM second failure must retain consumer-smoke final stage")
    cause = str(second.get("cause", ""))
    require("Lintian" in cause and "qtpaths6" in cause, "ECM second failure must retain both packaging-policy and Qt consumer causes")
    remediation = ecm.get("remediation", {})
    require(remediation.get("candidate_package_version") == CANDIDATE, "ECM FAIL remediation must use a new Debian revision")
    require(remediation.get("status") == "pending-validation", "ECM remediation must remain pending until actually rebuilt")

workflow = read(WORKFLOW)
runner = read(RUNNER)
delta = read(DELTA)
doc = read(DOC)
status_doc = read(STATUS_DOC)
current_status_doc = read(CURRENT_STATUS_DOC)
control = read(CONTROL)
copyright_text = read(COPYRIGHT)
changelog = read(CHANGELOG)
rules = read(RULES)

require("runs-on: ubuntu-26.04" in workflow, "ECM workflow must use explicit ubuntu-26.04")
require("ubuntu-latest" not in workflow, "ECM workflow must not use ubuntu-latest")
require("pull_request_target" not in workflow, "ECM workflow must not use pull_request_target")
require(f"actions/checkout@{CHECKOUT_SHA}" in workflow, "ECM workflow must pin approved checkout SHA")
require(f"actions/upload-artifact@{UPLOAD_SHA}" in workflow, "ECM workflow must pin approved upload-artifact SHA")
require("fetch-depth: 0" in workflow, "ECM workflow must fetch history for event-delta scope")
require("scripts/kde-ecm-preflight-needed.sh" in workflow, "ECM workflow must use event-delta scope detection")
require("if [[ \"${rc}\" -eq 1 ]]" in workflow, "ECM workflow must reserve selector exit 1 for intentional scope skip")
require("scripts/run-kde-ecm-package-preflight.sh" in workflow, "ECM workflow must execute clean package preflight")
require("evidence/kde-ecm-package-preflight/" in workflow, "ECM workflow must retain node evidence")

for token, message in (
    ("UPSTREAM_VERSION=\"6.30.0\"", "ECM runner must pin upstream version"),
    ("DEBIAN_VERSION=\"${UPSTREAM_VERSION}-0supralinux3\"", "ECM runner must use the current remediation Debian revision"),
    (ECM_SHA256, "ECM runner must pin KDE-published source SHA-256"),
    ("download.kde.org/stable/frameworks/6.30", "ECM runner must fetch from KDE stable release"),
    ("sha256sum --check --strict", "ECM runner must verify source SHA before extraction"),
    ("dpkg-buildpackage -S", "ECM runner must create a Debian source package"),
    ("${HOME}/.cache/sbuild/resolute-amd64.tar", "ECM runner must create reusable rootfs at sbuild expected cache path"),
    ("--format=tar", "ECM runner must create reusable sbuild rootfs as tar"),
    ("--skip=output/mknod", "ECM rootfs creation must use sbuild-compatible mmdebstrap profile"),
    ("--chroot-mode=unshare", "ECM runner must build in clean sbuild/unshare"),
    ("dpkg-deb -f", "ECM runner must verify binary package metadata"),
    ("lintian --fail-on error", "ECM runner must make Lintian errors fatal"),
    ("qt6-base-dev", "ECM consumer environment must install selected Ubuntu Qt development provider"),
    ("qtpaths6 --qt-version", "ECM runner must retain Qt consumer version evidence"),
    ("find_package(ECM 6.30.0 REQUIRED NO_MODULE)", "ECM runner must configure a downstream consumer against built artifact"),
    ("upstream_tests=not-run-in-package-preflight", "ECM evidence must state upstream tests are not claimed"),
    ("downstream_eligible=yes", "ECM runner must explicitly mark PASS artifact downstream-eligible"),
):
    require(token in runner, message)

require(runner.index('STAGE="artifact-capture"') < runner.index('STAGE="lintian"') < runner.index('STAGE="consumer-smoke"'), "ECM runner must capture build artifacts before post-build gates and run Lintian before consumer smoke")
require("override_dh_auto_test:" in rules, "ECM packaging must explicitly handle dh_auto_test when BUILD_TESTING is disabled")
require("BUILD_TESTING=OFF" in rules, "ECM package-preflight profile must explicitly record disabled upstream tests")

# Scope must follow actual package-consumed inputs. The runner does not consume
# canonical DAG state/evidence or documentation, so those changes must not
# rebuild a validated ECM package.
for tracked in (
    "packages/kde/extra-cmake-modules/*",
    "scripts/run-kde-ecm-package-preflight.sh",
    ".github/workflows/kde-ecm-package-preflight.yml",
):
    require(tracked in delta, f"ECM delta detector must track consumed input {tracked}")
for non_input in (
    "manifests/kde-dag.json",
    "docs/kde-dag.md",
    "scripts/kde-ecm-preflight-needed.sh",
):
    require(non_input in delta, f"ECM delta detector must document non-input {non_input}")
require("NOT build inputs" in delta, "ECM delta detector must explicitly document non-build inputs")
require("git diff --name-only" in delta, "ECM delta detector must compare exact event delta")
require("event delta changes no ECM package-consumed input; skip rebuild" in delta, "ECM delta detector must expose explicit skip reason")
require("0 = rebuild ECM" in delta and "1 = intentional scope skip" in delta, "ECM delta detector must document its exit-status contract")
require("exit 0" in delta and "exit 1" in delta, "ECM delta detector must return distinct statuses for rebuild and intentional skip")
require(delta.index("run=true") < delta.index("exit 0") < delta.index("run=false") < delta.index("exit 1"), "ECM delta detector must map run=true to exit 0 and run=false to exit 1")
# Non-input tokens may appear only in comments/documentation, not in the git-diff pathspec block.
pathspec_block = delta.split("git diff --name-only", 1)[1].split(")", 1)[0]
for non_input in ("manifests/kde-dag.json", "docs/kde-dag.md", "scripts/kde-ecm-preflight-needed.sh"):
    require(non_input not in pathspec_block, f"ECM non-input must not trigger rebuild: {non_input}")

require("Source: kf6-extra-cmake-modules" in control, "ECM control must preserve source package name")
require(re.search(r"^Package: extra-cmake-modules$", control, re.MULTILINE) is not None, "ECM control must preserve binary package name")
require(re.search(r"^Architecture: all$", control, re.MULTILINE) is not None, "ECM package must be architecture all")
require(re.search(r"^\s*python3:any,?$", control, re.MULTILINE) is not None, "ECM binary package must depend on python3:any for installed Python helpers")
require(re.search(r"^Suggests: qt6-base-dev$", control, re.MULTILINE) is not None, "ECM package must preserve Qt development suggestion")
require(changelog.startswith(f"kf6-extra-cmake-modules ({CANDIDATE}) resolute;"), "ECM changelog must start with current remediation package revision")
for license_name in ("BSD-3-Clause", "BSD-2-Clause", "MIT"):
    require(license_name in copyright_text, f"ECM copyright metadata must retain upstream license set: {license_name}")
require("per-file SPDX" in copyright_text, "ECM copyright metadata must preserve upstream per-file SPDX authority")

require(ECM_SHA256 in doc, "KDE DAG docs must record ECM upstream SHA-256")
require("Ubuntu 26.04 currently carries `extra-cmake-modules` 6.24.0-0ubuntu1" in doc, "KDE DAG docs must distinguish Ubuntu reference version")
require("technical packaging reference only" in doc, "KDE DAG docs must keep Ubuntu as reference/provider rather than KDE authority")
require("`BLOCKED` is never counted as `FAIL`" in doc, "KDE DAG docs must preserve BLOCKED semantics")
for value in (str(FIRST_FAIL["run_id"]), str(FIRST_FAIL["artifact_id"]), FIRST_FAIL["digest"], str(SECOND_FAIL["run_id"]), str(SECOND_FAIL["job_id"]), str(SECOND_FAIL["artifact_id"]), SECOND_FAIL["digest"]):
    require(value in doc, f"KDE DAG docs must retain failure evidence {value}")
    require(value in status_doc, f"current status doc must retain failure evidence {value}")
require("upstream test suite" in doc.lower() and "separate" in doc.lower(), "KDE DAG docs must not overclaim upstream test coverage")
require(CANDIDATE in doc and CANDIDATE in status_doc, "docs must identify the current ECM remediation candidate")
require("lintian --fail-on error" in doc and "qtpaths6" in doc, "KDE DAG docs must document second-failure remediation gates")
for value in (
    str(UNNECESSARY_SCOPE_RUN["run_id"]),
    str(UNNECESSARY_SCOPE_RUN["job_id"]),
    str(UNNECESSARY_SCOPE_RUN["artifact_id"]),
    UNNECESSARY_SCOPE_RUN["digest"],
    UNNECESSARY_SCOPE_RUN["commit"],
):
    require(value in doc, f"KDE DAG docs must retain ECM scope incident evidence {value}")
    require(value in current_status_doc, f"2026-09-15 status must retain ECM scope incident evidence {value}")
for value in (
    str(SCOPE_CONTRACT_RUN["run_id"]),
    str(SCOPE_CONTRACT_RUN["job_id"]),
    SCOPE_CONTRACT_RUN["commit"],
):
    require(value in doc, f"KDE DAG docs must retain ECM selector-contract incident evidence {value}")
    require(value in current_status_doc, f"2026-09-15 status must retain ECM selector-contract incident evidence {value}")
require("scope" in doc.lower() and "package_state_effect=none" in doc, "KDE DAG docs must classify ECM rebuild as scope-only with no package-state effect")
require("0 = rebuild" in doc and "1 = intentional skip" in doc, "KDE DAG docs must document ECM selector exit-status contract")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE DAG policy validation: PASS")
print(f"Frameworks series: {data['frameworks_series']}")
print(f"ECM: version={ecm['upstream_version']} package={ecm['package_version']} state={ecm['state']}")
print(f"ECM source SHA-256: {ecm['source_sha256']}")
print("ECM rebuild scope: package-consumed inputs only; DAG/docs/state-only changes skip")
