#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-package-campaign-batch4.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"
DEPENDENCIES = ROOT / "manifests/kde-frameworks-tier1-dependencies.json"
DAG = ROOT / "manifests/kde-dag.json"
DOC = ROOT / "docs/kde-tier1-package-batch4.md"
DEPENDENCY_DOC = ROOT / "docs/kde-tier1-dependencies.md"
STATUS_DOC = ROOT / "docs/status/2026-09-15-batch4.md"
WORKFLOW = ROOT / ".github/workflows/kde-tier1-package-batch4.yml"
REPOSITORY_POLICY = ROOT / ".github/workflows/repository-policy.yml"
RUNNER = ROOT / "scripts/run-kde-tier1-package-batch4-preflight.sh"
SCOPE = ROOT / "scripts/kde-tier1-package-batch4-needed.sh"

EXPECTED = {
    "kitemviews": {
        "source": "9452f2b0cc5dd0214b88c4ce33297866be89af4177af14f5390cfb616e49c153",
        "blob": "d4abc8277881fff0ad85d06167b0f1e5c8e0977d",
        "symbols": "c95ecbc24ccee885f1aa50df1c2aab41f54eb561baf66b1b219a562a5ce372cf",
        "copyright": "add1ae526e4064439b04a0d2fa162e178f049c96411fe3922a9562a2f25304c6",
        "runtime": "libkf6itemviews6",
        "soname": "libKF6ItemViews.so.6",
        "cmake": "KF6ItemViews",
        "target": "KF6::ItemViews",
        "build": ["qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)", "xauth <!nocheck>", "xvfb <!nocheck>"],
        "packages": 4,
        "version": "6.30.0-0supralinux1",
        "pass": {"run":34999449194,"job":104483912528,"commit":"209f6234cbd94d0b4e02df509b25ae5a6e0922fd","artifact":10409267184,"digest":"7e34fa7ede21510cf6829448e7b45a5c2832aaf9ac2719b9cb4125d23b593e55","tests":"2/2 PASS"},
        "fails": [],
    },
    "kglobalaccel": {
        "source": "e532ebd4cbfc8d6d79c6c38c556f1871315fedae8db2b69b574b9c496f171473",
        "blob": "274623176b4c0f9b72edea3bd770530f76c8f607",
        "symbols": "967876c92b88b1a0654b06084c70604191464ecaded59df4bbf4dea71c0c6bb7",
        "copyright": "1991e59510c1a15e9f0eba6479a249ec17579ad2f97d3686e0ed975f8614de34",
        "runtime": "libkf6globalaccel6",
        "soname": "libKF6GlobalAccel.so.6",
        "cmake": "KF6GlobalAccel",
        "target": "KF6::GlobalAccel",
        "build": ["qt6-base-dev (>= 6.9.0~)", "qt6-base-private-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)", "xauth <!nocheck>", "xvfb <!nocheck>"],
        "packages": 4,
        "version": "6.30.0-0supralinux2",
        "pass": {"run":35006477086,"job":104507372240,"commit":"163cde7bedd95c2ffb16c031aa12dada99f84161","artifact":10412320520,"digest":"cb8143633cf15745a235937ea55ee096cb094cc96da3bd1fc39dc914f3acb3b1","tests":"1/1 PASS"},
        "fails": [{"run":34999449194,"job":104483912661,"artifact":10408264332,"digest":"1b7564f211967d1be8b61a96bc2a67389c6164f566e54dad79682d37a33bf6e5","version":"6.30.0-0supralinux1"}],
    },
    "syntax-highlighting": {
        "source": "fc429b093058bec4878306cbbfb3aa0560ff4a3f166c69504036c507fe72afcc",
        "blob": "cbd31a8f3c8b981931fc0d39ee5991f5c7f6903a",
        "symbols": "3dd1d9e56a8fa8b802ffb6708ec65984cef422bcbe7660583c907a827aec47dd",
        "copyright": "96abcf79db76923a43e841f4a22c41a2e81394a0ff074ce1f06009e962ba2d35",
        "runtime": "libkf6syntaxhighlighting6",
        "soname": "libKF6SyntaxHighlighting.so.6",
        "cmake": "KF6SyntaxHighlighting",
        "target": "KF6::SyntaxHighlighting",
        "build": ["dh-sequence-qmldeps", "libxerces-c-dev", "perl:any", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)", "xauth <!nocheck>", "xvfb <!nocheck>"],
        "packages": 6,
        "version": "6.30.0-0supralinux2",
        "pass": {"run":35006477086,"job":104507371855,"commit":"163cde7bedd95c2ffb16c031aa12dada99f84161","artifact":10411888269,"digest":"1ec0d1e7d046b1393fbb299c9a6fec7e85ee4ac59ed5deafa0c777ead67c0b5f","tests":"8/8 PASS"},
        "fails": [{"run":34999449194,"job":104483912313,"artifact":10408154532,"digest":"8601077898fcba1ea5708fbd4e5a1c0d877825f969b8b39999d7d6bf131fbfe4","version":"6.30.0-0supralinux1"}],
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

campaign = load(CAMPAIGN)
tier1 = {item["id"]: item for item in load(TIER1)["nodes"]}
deps = load(DEPENDENCIES)
dag = load(DAG)["nodes"]

req(campaign.get("schema") == 1, "campaign schema")
req(campaign.get("authority") == "kde-upstream", "KDE authority")
req(campaign.get("frameworks_series") == "6.30.0", "Frameworks version")
req(campaign.get("batch") == "tier1-batch-4", "batch id")
req(campaign.get("state") == "PASS", "Batch 4 must be closed PASS")
req(campaign.get("selected_nodes") == list(EXPECTED), "selected nodes/order")
req(campaign.get("canonical_snapshot", {}).get("tier1") == "13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED", "canonical snapshot count")
req(campaign.get("canonical_snapshot", {}).get("state") == "promoted-at-batch-closure", "canonical promotion state")
req(campaign.get("closure", {}).get("workflow_run") == 35006477086, "closure workflow run")
req(campaign.get("closure", {}).get("repository_policy_run") == 35006476864, "closure Repository Policy evidence")
req(campaign["shared_predecessors"]["extra_cmake_modules"]["version"] == "6.30.0-0supralinux3", "ECM predecessor")
req(campaign["shared_predecessors"]["packaging_trees"]["artifact_id"] == 10301938362, "packaging tree artifact")
req(campaign["shared_packaging_inputs"]["documentation_policy"]["qch_enabled"] is False, "QCH policy")
req(campaign["shared_packaging_inputs"]["lintian_policy"]["source_and_changes_required"] is True, "Lintian source+changes policy")

for node, expected in EXPECTED.items():
    data = campaign["nodes"][node]
    req(data["state"] == "PASS", f"{node}: campaign state")
    req(data["last_result"] == "PASS", f"{node}: last result")
    req(data["downstream_eligible"] is True, f"{node}: downstream eligibility")
    req(data["package_version"] == expected["version"], f"{node}: package revision")
    req(data["source_sha256"] == expected["source"], f"{node}: source hash")
    req(data["root_cmake_blob"] == expected["blob"], f"{node}: root CMake blob")
    req(data["symbols"]["sha256"] == expected["symbols"], f"{node}: symbols baseline")
    req(data["copyright"]["sha256"] == expected["copyright"], f"{node}: copyright reference")
    req(data["runtime_package"] == expected["runtime"], f"{node}: runtime package")
    req(data["soname"] == expected["soname"], f"{node}: SONAME")
    req(data["cmake_package"] == expected["cmake"], f"{node}: CMake package")
    req(data["cmake_target"] == expected["target"], f"{node}: CMake target")
    req(len(data["binary_contracts"]) == expected["packages"], f"{node}: binary package count")
    req(data["build_profile_tokens"] == expected["build"], f"{node}: build profile tokens")

    evidence = data.get("evidence", [])
    passes = [e for e in evidence if e.get("result") == "PASS"]
    fails = [e for e in evidence if e.get("result") == "FAIL"]
    req(len(passes) == 1, f"{node}: exactly one retained PASS")
    req(len(fails) == len(expected["fails"]), f"{node}: historical FAIL count")
    if passes:
        ev = passes[0]
        p = expected["pass"]
        for key, field in (("workflow_run","run"),("job_id","job"),("commit","commit"),("artifact_id","artifact"),("artifact_sha256","digest"),("tests","tests")):
            req(ev.get(key) == p[field], f"{node}: PASS {key}")
        req(ev.get("attempted_package_version") == expected["version"], f"{node}: PASS package revision")
        req(ev.get("stage") == "complete", f"{node}: PASS stage")
        req(ev.get("lintian") == "PASS-errors", f"{node}: Lintian")
        req(ev.get("consumer_smoke") == "PASS", f"{node}: consumer smoke")
        req(ev.get("abi_soname") == expected["soname"], f"{node}: PASS SONAME")
        req(ev.get("ecm_predecessor") == "6.30.0-0supralinux3", f"{node}: ECM evidence")
    for want in expected["fails"]:
        candidates = [e for e in fails if e.get("workflow_run") == want["run"]]
        req(len(candidates) == 1, f"{node}: retained FAIL run")
        if candidates:
            ev = candidates[0]
            req(ev.get("job_id") == want["job"], f"{node}: FAIL job")
            req(ev.get("artifact_id") == want["artifact"], f"{node}: FAIL artifact")
            req(ev.get("artifact_sha256") == want["digest"], f"{node}: FAIL digest")
            req(ev.get("attempted_package_version") == want["version"], f"{node}: FAIL version")
            req(ev.get("failure_substage") == "dh_auto_configure/CMake", f"{node}: FAIL substage")
            req("LinguistTools" in str(ev.get("cause", "")) and "qt6-tools-dev" in str(ev.get("cause", "")), f"{node}: retained root cause")
        rem = data.get("remediation", {})
        req(rem.get("status") == "validated", f"{node}: remediation validated")
        req(rem.get("validated_by_run_id") == 35006477086, f"{node}: remediation run")
        req(rem.get("source_change") is False, f"{node}: no source change")

    for key, digest in data.get("last_pass_files", {}).items():
        req(re.fullmatch(r"[0-9a-f]{64}", str(digest)) is not None, f"{node}: invalid PASS hash {key}")

    metadata = deps["metadata"][node]
    req(metadata["ref"] == "v6.30.0", f"{node}: dependency manifest ref")
    req(metadata["root_cmake_blob"] == expected["blob"], f"{node}: dependency manifest blob")
    if node == "kglobalaccel":
        req(set(deps["nodes"][node]["qt"].get("test", [])) == {"Test", "Qml"}, "kglobalaccel: QtQml test requirement")

    canonical = tier1[node]
    req(canonical.get("state") == "PASS", f"{node}: canonical Tier 1 PASS")
    req(canonical.get("packaging", {}).get("state") == "PASS", f"{node}: canonical packaging PASS")
    req(canonical.get("packaging", {}).get("package_version") == expected["version"], f"{node}: canonical version")
    req(canonical.get("packaging", {}).get("downstream_eligible") is True, f"{node}: canonical downstream eligible")

    dnode = dag.get(node, {})
    req(dnode.get("state") == "PASS", f"{node}: DAG PASS")
    req(dnode.get("package_version") == expected["version"], f"{node}: DAG version")
    req(dnode.get("downstream_eligible") is True, f"{node}: DAG downstream eligible")

    deb = ROOT / "packages/kde" / node / "debian"
    control = (deb / "control").read_text(encoding="utf-8")
    rules = (deb / "rules").read_text(encoding="utf-8")
    readme = (deb / "README.source").read_text(encoding="utf-8")
    changelog = (deb / "changelog").read_text(encoding="utf-8")
    docinstall = (deb / f"{data['documentation_package']}.install").read_text(encoding="utf-8")
    consumer = (ROOT / "packages/kde" / node / "consumer/CMakeLists.txt").read_text(encoding="utf-8")
    main = (ROOT / "packages/kde" / node / "consumer/main.cpp").read_text(encoding="utf-8")
    for token in ["debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", *expected["build"]]:
        req(token in control, f"{node}: missing Build-Depends {token}")
    req(changelog.startswith(f"{data['source_package']} ({expected['version']}) resolute;"), f"{node}: changelog revision")
    req("Standards-Version: 4.7.3" in control, f"{node}: Standards-Version")
    req("documentation compatibility package" in control, f"{node}: documentation description")
    req("does not ship QCH documentation files" in control, f"{node}: QCH truth")
    req("Intentionally empty" in docinstall, f"{node}: empty documentation install")
    req("-DBUILD_QCH=OFF" in rules, f"{node}: QCH disabled")
    req("dh_auto_test" in rules, f"{node}: tests enabled")
    req("KDE Frameworks 6.30.0 is the source/build authority" in readme, f"{node}: authority documentation")
    req(sha(deb / "upstream/signing-key.asc") == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", f"{node}: signing key")
    req(expected["cmake"] in consumer and expected["target"] in consumer, f"{node}: CMake consumer")
    req(expected["soname"] in main and "dlopen" in main, f"{node}: runtime consumer")

req(sum(1 for n in tier1.values() if n.get("state") == "PASS") == 29, "Current Tier 1 PASS count must be 29 after Batch 11 closure")
req(sum(1 for n in tier1.values() if n.get("state") == "pending") == 0, "Current Tier 1 pending count must be 0 after Batch 11 closure")

kg_control = (ROOT / "packages/kde/kglobalaccel/debian/control").read_text()
syntax_control = (ROOT / "packages/kde/syntax-highlighting/debian/control").read_text()
req("qt6-tools-dev (>= 6.9.0~)" in kg_control, "kglobalaccel: LinguistTools provider")
req("qt6-tools-dev (>= 6.9.0~)" in syntax_control, "syntax-highlighting: LinguistTools provider")
req("-DBUILD_DESIGNERPLUGIN=ON" in (ROOT / "packages/kde/kitemviews/debian/rules").read_text(), "kitemviews: Designer default")

runner = RUNNER.read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")
scope = SCOPE.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")
status_doc = STATUS_DOC.read_text(encoding="utf-8")
depdoc = DEPENDENCY_DOC.read_text(encoding="utf-8")
policy = REPOSITORY_POLICY.read_text(encoding="utf-8")
for token in ["-name '*.ddeb'", 'lintian --fail-on error "${DSC}" "${CHANGES[0]}"', "Lintian:[[:space:]]+fail", "dpkg-source -b", "--chroot-mode=unshare", "dependency_contracts", "recommendation_contracts", "consumer-smoke"]:
    req(token in runner, f"runner missing {token}")
for token in ["fail-fast: false", "max-parallel: 3", "kitemviews", "kglobalaccel", "syntax-highlighting", "run-kde-tier1-package-batch4-preflight.sh"]:
    req(token in workflow, f"workflow missing {token}")
req("kde-tier1-package-campaign-batch4.json" in scope, "scope campaign")
req("validate_kde_tier1_package_batch4.py" in policy, "Repository Policy Batch 4 validator step")
for token in ["3/3 PASS", "13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED", "35006477086", "10412320520", "10411888269", "qt6-tools-dev", "LinguistTools"]:
    req(token.lower() in doc.lower(), f"Batch 4 documentation missing {token}")
    req(token.lower() in status_doc.lower() or token == "3/3 PASS", f"Batch 4 status documentation missing {token}")
req("29 PASS / 0 pending" in depdoc, "dependency documentation current canonical count")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 4 canonical closure: PASS")
print("KItemViews, KGlobalAccel and KSyntaxHighlighting = 3/3 PASS/downstream-eligible")
print("Current canonical Tier 1: 29 PASS / 0 pending / 0 FAIL / 0 BLOCKED; Batch 4 historical closure remains 13/16")
