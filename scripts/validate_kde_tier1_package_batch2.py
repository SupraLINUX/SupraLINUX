#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-package-campaign-batch2.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"
DAG = ROOT / "manifests/kde-dag.json"
DOC = ROOT / "docs/kde-tier1-package-batch2.md"
GATE_DOC = ROOT / "docs/kde-tier1-package-batch2-ci-gate.md"
WORKFLOW = ROOT / ".github/workflows/kde-tier1-package-batch2.yml"
RUNNER = ROOT / "scripts/run-kde-tier1-package-batch2-preflight.sh"
VALIDATED_RUNNER = ROOT / "scripts/run-kde-tier1-package-batch2-validated.sh"
SCOPE = ROOT / "scripts/kde-tier1-package-batch2-needed.sh"

FINAL_RUN = 34884764702
FINAL_COMMIT = "e0f4e7c48dcf7541538eb919374a3f4b6c293b75"

EXPECTED = {
    "ktexttemplate": {
        "version": "6.30.0-0supralinux3",
        "source": "c3c229944d25294102e4e8a5b49fa0c0f481da9d33f8bec3782e8a53afd47493",
        "symbols": "552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273",
        "runtime": "libkf6texttemplate6",
        "soname": "libKF6TextTemplate.so.6",
        "job_id": 104112549851,
        "artifact_id": 10363863115,
        "artifact_sha256": "7b9d0390ed90c882f4b7ad1993924e722bfb7ad35238c2ced52bbd5809555bc9",
        "tests": "10/10 PASS",
        "build": ["python3", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)"],
    },
    "karchive": {
        "version": "6.30.0-0supralinux4",
        "source": "4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2",
        "symbols": "acd4b767ad9cc821345a973e09c1e42c63d45fc3eef45197a35d84475c83878e",
        "runtime": "libkf6archive6",
        "soname": "libKF6Archive.so.6",
        "job_id": 104112549742,
        "artifact_id": 10364726750,
        "artifact_sha256": "0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e",
        "tests": "5/5 PASS",
        "build": ["libbz2-dev", "liblzma-dev", "libssl-dev", "libzstd-dev", "pkgconf", "qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)", "zlib1g-dev", "zstd"],
    },
    "kholidays": {
        "version": "6.30.0-0supralinux4",
        "source": "02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b",
        "symbols": "b0be25ddbc4c7abeb121bb0d3c3ca053d33e2a9fa88695bea210c50d56c256cd",
        "runtime": "libkf6holidays6",
        "soname": "libKF6Holidays.so.6",
        "job_id": 104112549858,
        "artifact_id": 10364169061,
        "artifact_sha256": "62186f3d6d0c856fed7b055ae917ceec0b6cdf216b37b93e22126bf3ebc8f37a",
        "tests": "8/8 PASS",
        "build": ["dh-sequence-qmldeps", "bison (>= 2:3.3.2~)", "flex", "python3:any", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
    },
}

errors: list[str] = []


def req(ok: bool, message: str) -> None:
    if not ok:
        errors.append(message)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

campaign = load(CAMPAIGN)
tier1 = {item["id"]: item for item in load(TIER1)["nodes"]}
dag = load(DAG)["nodes"]

req(campaign.get("schema") == 1, "campaign schema")
req(campaign.get("authority") == "kde-upstream", "KDE authority")
req(campaign.get("frameworks_series") == "6.30.0", "Frameworks version")
req(campaign.get("batch") == "tier1-batch-2", "batch id")
req(campaign.get("state") == "PASS", "batch final PASS state")
req(campaign.get("selected_nodes") == list(EXPECTED), "selected nodes")
req(campaign["shared_predecessors"]["extra_cmake_modules"]["version"] == "6.30.0-0supralinux3", "ECM predecessor")
req(campaign["shared_packaging_inputs"]["documentation_policy"]["qch_enabled"] is False, "QCH policy")

for node, expected in EXPECTED.items():
    data = campaign["nodes"][node]
    req(data["state"] == "PASS", f"{node}: campaign state")
    req(data["last_result"] == "PASS", f"{node}: last result")
    req(data["downstream_eligible"] is True, f"{node}: downstream eligibility")
    req(data["package_version"] == expected["version"], f"{node}: package revision")
    req(data["source_sha256"] == expected["source"], f"{node}: source hash")
    req(data["runtime_package"] == expected["runtime"], f"{node}: runtime identity")
    req(data["soname"] == expected["soname"], f"{node}: SONAME")
    req(data["symbols"]["sha256"] == expected["symbols"], f"{node}: symbols baseline")
    req(data["symbols"]["tree_provider"] == "debian", f"{node}: symbols provider")

    final = data["evidence"][-1]
    req(final.get("result") == "PASS", f"{node}: final evidence result")
    req(final.get("workflow_run") == FINAL_RUN, f"{node}: final workflow")
    req(final.get("job_id") == expected["job_id"], f"{node}: final job")
    req(final.get("commit") == FINAL_COMMIT, f"{node}: final commit")
    req(final.get("artifact_id") == expected["artifact_id"], f"{node}: final artifact")
    req(final.get("artifact_sha256") == expected["artifact_sha256"], f"{node}: final artifact hash")
    req(final.get("tests") == expected["tests"], f"{node}: tests")
    req(final.get("lintian") == "PASS-errors", f"{node}: Lintian")
    req(final.get("consumer_smoke") == "PASS", f"{node}: consumer smoke")
    req(final.get("validated_gate") == "sbuild-summary-plus-dsc-plus-changes", f"{node}: validated gate")

    deb = ROOT / "packages/kde" / node / "debian"
    control = (deb / "control").read_text(encoding="utf-8")
    changelog = (deb / "changelog").read_text(encoding="utf-8")
    install = (deb / data["documentation_package"].replace("-doc", "-doc.install")).read_text(encoding="utf-8")
    readme = (deb / "README.source").read_text(encoding="utf-8")

    req(changelog.startswith(f"kf6-{node} ({expected['version']}) resolute;"), f"{node}: changelog revision")
    for token in ["debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", *expected["build"]]:
        req(token in control, f"{node}: missing Build-Depends {token}")
    req("documentation compatibility package" in control, f"{node}: doc compatibility description")
    req("does not ship QCH documentation files" in control, f"{node}: truthful QCH description")
    req("Intentionally empty" in install, f"{node}: empty doc package documented")
    req("KDE Frameworks 6.30.0 is the source/build authority" in readme, f"{node}: authority documentation")
    req((deb / "source/format").read_text(encoding="utf-8") == "3.0 (quilt)\n", f"{node}: source format")
    req(sha(deb / "upstream/signing-key.asc") == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", f"{node}: signing key")

    req(tier1[node]["state"] == "PASS", f"{node}: Tier 1 canonical PASS")
    req(tier1[node]["packaging"]["state"] == "PASS", f"{node}: Tier 1 packaging PASS")
    req(tier1[node]["packaging"]["package_version"] == expected["version"], f"{node}: Tier 1 package version")
    req(tier1[node]["packaging"]["downstream_eligible"] is True, f"{node}: Tier 1 downstream eligible")
    req(dag[node]["state"] == "PASS", f"{node}: DAG PASS")
    req(dag[node]["package_version"] == expected["version"], f"{node}: DAG package version")
    req(dag[node]["downstream_eligible"] is True, f"{node}: DAG downstream eligible")

kh_history = campaign["nodes"]["kholidays"]["evidence"]
req(any(e.get("workflow_run") == 34834818877 and e.get("result") == "FAIL" and e.get("pipeline_claim") == "PASS" for e in kh_history), "kholidays: false PASS retained")
req(any(e.get("failure_substage") == "rules-require-build-prerequisite" for e in kh_history), "kholidays: python prerequisite failure retained")

incidents = campaign.get("ci_harness_incidents", [])
req(any(i.get("workflow_run") == 34884049556 and i.get("validated_by_run") == FINAL_RUN for i in incidents), "Batch 2 CI harness incident retained")

wrapper = VALIDATED_RUNNER.read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")
scope = SCOPE.read_text(encoding="utf-8")
runner = RUNNER.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")
gate_doc = GATE_DOC.read_text(encoding="utf-8")

req("run-kde-tier1-package-batch2-preflight.sh" in wrapper, "validated runner delegates build")
req("Lintian:[[:space:]]+fail" in wrapper, "validated runner checks sbuild Lintian status")
req("-name '*.ddeb'" in wrapper, "validated runner preserves dbgsym evidence")
req('lintian --fail-on error "${DSCS[0]}" "${CHANGES[0]}"' in wrapper, "validated runner checks source and binary")
req("validated_result" in wrapper, "validated runner records validated result")
req("run-kde-tier1-package-batch2-validated.sh" in workflow, "workflow uses validated runner")
req("run-kde-tier1-package-batch2-validated.sh" in scope, "scope tracks validated runner")
req("kde-tier1-package-campaign-batch2.json" in runner, "base runner ledger")
for token in ["34884764702", "10363863115", "10364726750", "10364169061", "PASS", "QCH"]:
    req(token in doc, f"documentation missing {token}")
for token in ["34884049556", "infrastructure", ".ddeb", "34884764702"]:
    req(token in gate_doc, f"gate documentation missing {token}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 2 validation: PASS")
print("KTextTemplate, KArchive and KHolidays are canonical hosted-preflight PASS and downstream-eligible.")
