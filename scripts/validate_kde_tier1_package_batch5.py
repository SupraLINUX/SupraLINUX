#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-package-campaign-batch5.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"
DEPS = ROOT / "manifests/kde-frameworks-tier1-dependencies.json"
DAG = ROOT / "manifests/kde-dag.json"
WORKFLOW = ROOT / ".github/workflows/kde-tier1-package-batch5.yml"
POLICY = ROOT / ".github/workflows/repository-policy.yml"
RUNNER = ROOT / "scripts/run-kde-tier1-package-batch5-preflight.sh"
SCOPE = ROOT / "scripts/kde-tier1-package-batch5-needed.sh"
DOC = ROOT / "docs/kde-tier1-package-batch5.md"
STATUS = ROOT / "docs/status/2026-09-15-batch5.md"
CURRENT_STATUS = ROOT / "docs/status/2026-09-15.md"
DAG_DOC = ROOT / "docs/kde-dag.md"
PROVIDER_DOC = ROOT / "docs/decisions/modemmanager-provider-2026-09-15.md"
DEPENDENCY_DOC = ROOT / "docs/kde-tier1-dependencies.md"

EXPECTED = {
    "kidletime": {
        "source": "22873204292ddb757e5a0a57004c57debe1285cd0fd4e796d07e9de2402e60c3",
        "blob": "3617fd79358beaea36d862483b8b4947eef30508",
        "symbols": "1ae402305be324fc97b61bb099d3c6e001ec2bfc8eaf2ae09f1cd69eafbe914c",
        "copyright": "1afa9e5366e809877f085a8918ac733de4935be71be1aee3ff785362aee2bd0b",
        "version": "6.30.0-0supralinux1",
        "runtime": "libkf6idletime6",
        "soname": "libKF6IdleTime.so.6",
        "cmake": "KF6IdleTime",
        "target": "KF6::IdleTime",
        "packages": ["libkf6idletime-dev", "libkf6idletime-doc", "libkf6idletime6"],
        "run": 35014875475,
        "job": 104535671033,
        "commit": "30b5dcd293527b488c88cf0a861883ee869e3ea0",
        "artifact": 10414598079,
        "digest": "272ccad537d21905cf75a1add74e937d176c20c05c38bf967226fef4ab28b605",
        "tests": "1/1 PASS",
    },
    "modemmanager-qt": {
        "source": "d7c4106dc130729fdfd435abaeaf85039a874fc18563a41755e14f7ea174ae21",
        "blob": "1c253781f61fe39608b7d102a9359ca2f9afb1b0",
        "symbols": "70c9ebc08c99174f022c3b4b38ed4cde4a8725f0a2f8ea04a09371132312d6f2",
        "copyright": "6863209ef5575d5ac62b9e77d9ee6ee7a4c06e05622cb9671499686696c4605d",
        "version": "6.30.0-0supralinux3",
        "runtime": "libkf6modemmanagerqt6",
        "soname": "libKF6ModemManagerQt.so.6",
        "cmake": "KF6ModemManagerQt",
        "target": "KF6::ModemManagerQt",
        "packages": ["libkf6modemmanagerqt-dev", "libkf6modemmanagerqt-doc", "libkf6modemmanagerqt6"],
        "run": 35021323444,
        "job": 104557423664,
        "commit": "dea48cdc1184e0fc961ea4f3efc0b38e19a2fb8d",
        "artifact": 10417683848,
        "digest": "42d4f804effc6e4b9148e8c01887bdce6f95f0554ac4d03295e844a861a54eb7",
        "tests": "11/11 PASS",
    },
    "networkmanager-qt": {
        "source": "f6ba5f54d413ea0b2642207a6ebd0803e7cb8392b91fcf8a1679fd0c21062865",
        "blob": "be28b0b1092c3b64a4561fcb28f0dbf811e6a939",
        "symbols": "324a154e35a6dab6c2ab10c5857517a20253d7d65f279294a62e7ced3c8ebfaa",
        "copyright": "c6d6d851fc0ac1e99ab9d5535159213b3ba4a7deff6a4239f76e59fb51316e1e",
        "version": "6.30.0-0supralinux1",
        "runtime": "libkf6networkmanagerqt6",
        "soname": "libKF6NetworkManagerQt.so.6",
        "cmake": "KF6NetworkManagerQt",
        "target": "KF6::NetworkManagerQt",
        "packages": ["libkf6networkmanagerqt-dev", "libkf6networkmanagerqt-doc", "libkf6networkmanagerqt6", "qml6-module-org-kde-networkmanager"],
        "run": 35014875475,
        "job": 104535671250,
        "commit": "30b5dcd293527b488c88cf0a861883ee869e3ea0",
        "artifact": 10414714325,
        "digest": "abf927b5749b34094d2b5ee530831f64638ba116a83e8b82f925a758aa018ad4",
        "tests": "38/38 PASS",
    },
}
MM_FILES = {
    "libkf6modemmanagerqt_dev_deb_sha256": "1a9a69eff9542006535e52a4a3dfaba7378c506240c19dde6bf0599c73105302",
    "libkf6modemmanagerqt_doc_deb_sha256": "cf9102c482151ca33edd94f7e086ab767d44287858e6d73e8f2629e0d297bf0d",
    "libkf6modemmanagerqt6_deb_sha256": "7a52678aa62fc69eafdaff513a6bc4a9f72938ff3ea552a7bc99e58a3a3e0c4f",
    "libkf6modemmanagerqt6_dbgsym_ddeb_sha256": "563c0b886433ed461be1bd830f1f338ae36f47282b0e31b2c52264fff46c6222",
    "changes_sha256": "c2631cceca814bdfee0e7b7ce9e888fdcb97a198fff64c0089d088b1e0493a9d",
    "buildinfo_sha256": "5e93dfb613a2405b916839747aeb718485a12846889263d58eed62a75d889223",
    "dsc_sha256": "b02fcc77644d524af831543ac8282be48885296753e85c0517175d523d58115e",
    "orig_tar_sha256": "d7c4106dc130729fdfd435abaeaf85039a874fc18563a41755e14f7ea174ae21",
    "debian_tar_sha256": "648b8013108455bee99a09c93e79aa1132436df63d884dc6601828105a53934c",
    "rootfs_sha256": "d9545276368dd4116cb234e9925c59311b30e4c934ff18ac1b7558f9fa1e308b",
}

errors: list[str] = []

def req(value: bool, message: str) -> None:
    if not value:
        errors.append(message)

def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(value, dict):
        raise SystemExit(f"ERROR: {path.relative_to(ROOT)} must contain an object")
    return value

def text(path: Path) -> str:
    if not path.exists():
        errors.append(f"missing {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

campaign = load(CAMPAIGN)
tier_doc = load(TIER1)
tier = {n["id"]: n for n in tier_doc["nodes"]}
deps = load(DEPS)
dag = load(DAG)["nodes"]

req(campaign.get("schema") == 1, "campaign schema")
req(campaign.get("authority") == "kde-upstream", "KDE authority")
req(campaign.get("frameworks_series") == "6.30.0", "Frameworks series")
req(campaign.get("batch") == "tier1-batch-5", "batch id")
req(campaign.get("state") == "PASS", "Batch 5 must be canonically closed PASS")
req(campaign.get("selected_nodes") == list(EXPECTED), "selected node order")
req(campaign.get("canonical_snapshot") == {
    "state": "promoted-at-batch-closure",
    "tier1": "16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED",
}, "Batch 5 canonical snapshot")
req(campaign.get("closure") == {
    "workflow_run": 35021323444,
    "commit": "dea48cdc1184e0fc961ea4f3efc0b38e19a2fb8d",
    "repository_policy_run": 35021323425,
    "scope": {
        "kidletime": "scope-skip-retained-pass",
        "modemmanager-qt": "rebuilt-pass",
        "networkmanager-qt": "scope-skip-retained-pass",
    },
}, "Batch 5 closure evidence")

sp = campaign["shared_predecessors"]
req(sp["extra_cmake_modules"]["state"] == "PASS" and sp["extra_cmake_modules"]["artifact_id"] == 10298635300, "retained ECM PASS")
req(sp["packaging_trees"]["artifact_id"] == 10301938362, "retained packaging-tree artifact")
req(sp["dependency_provider"] == {
    "status": "PASS", "workflow_run": 35012023822, "job_id": 104526071758,
    "commit": "48fd01bfa7b254b5e5c8447b3d609f76a91f786f", "artifact_id": 10414525047,
    "artifact_sha256": "db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a",
    "authoritative": False, "claim": "provider-availability-only",
}, "provider revalidation evidence")

for node_id, expected in EXPECTED.items():
    node = campaign["nodes"][node_id]
    req(node.get("state") == "PASS", f"{node_id}: campaign state PASS")
    req(node.get("last_result") == "PASS", f"{node_id}: campaign last result PASS")
    req(node.get("downstream_eligible") is True, f"{node_id}: campaign downstream eligible")
    req(node.get("package_version") == expected["version"], f"{node_id}: package version")
    req(node.get("source_sha256") == expected["source"], f"{node_id}: source hash")
    req(node.get("root_cmake_blob") == expected["blob"], f"{node_id}: upstream CMake blob")
    req(node.get("runtime_package") == expected["runtime"], f"{node_id}: runtime package")
    req(node.get("soname") == expected["soname"], f"{node_id}: SONAME")
    req(node.get("cmake_package") == expected["cmake"] and node.get("cmake_target") == expected["target"], f"{node_id}: CMake contract")
    req(node["symbols"]["sha256"] == expected["symbols"], f"{node_id}: symbols reference")
    req(node["copyright"]["sha256"] == expected["copyright"], f"{node_id}: copyright reference")
    req([x["name"] for x in node["binary_contracts"]] == expected["packages"], f"{node_id}: binary contracts")
    req(deps["metadata"][node_id]["ref"] == "v6.30.0" and deps["metadata"][node_id]["root_cmake_blob"] == expected["blob"], f"{node_id}: dependency metadata")

    passes = [e for e in node.get("evidence", []) if e.get("result") == "PASS"]
    req(len(passes) == 1, f"{node_id}: exactly one current PASS evidence")
    if passes:
        ev = passes[0]
        req(ev.get("workflow_run") == expected["run"], f"{node_id}: PASS run")
        req(ev.get("job_id") == expected["job"], f"{node_id}: PASS job")
        req(ev.get("commit") == expected["commit"], f"{node_id}: PASS commit")
        req(ev.get("attempted_package_version") == expected["version"], f"{node_id}: PASS attempted version")
        req(ev.get("artifact_id") == expected["artifact"] and ev.get("artifact_sha256") == expected["digest"], f"{node_id}: PASS artifact")
        req(ev.get("stage") == "complete" and ev.get("tests") == expected["tests"], f"{node_id}: PASS stage/tests")
        req(ev.get("lintian") == "PASS-errors" and ev.get("consumer_smoke") == "PASS", f"{node_id}: PASS gates")
        req(ev.get("abi_soname") == expected["soname"], f"{node_id}: PASS SONAME evidence")
        req(ev.get("ecm_predecessor") == "6.30.0-0supralinux3", f"{node_id}: ECM predecessor")
        req(ev.get("downstream_eligible") is True, f"{node_id}: PASS downstream evidence")
    files = node.get("last_pass_files", {})
    req(isinstance(files, dict) and bool(files), f"{node_id}: retained PASS file hashes")
    for key, digest in files.items():
        req(re.fullmatch(r"[0-9a-f]{64}", str(digest)) is not None, f"{node_id}: invalid retained hash {key}")

    canonical = tier[node_id]
    req(canonical.get("state") == "PASS", f"{node_id}: Tier1 state PASS")
    packaging = canonical.get("packaging", {})
    req(packaging.get("state") == "PASS" and packaging.get("package_version") == expected["version"], f"{node_id}: Tier1 packaging PASS/version")
    req(packaging.get("claim") == "hosted-clean-package-preflight" and packaging.get("authoritative") is False, f"{node_id}: Tier1 claim boundary")
    req(packaging.get("downstream_eligible") is True, f"{node_id}: Tier1 downstream eligible")
    cp = [e for e in packaging.get("evidence", []) if e.get("result") == "PASS"]
    req(len(cp) == 1 and cp[0].get("artifact_sha256") == expected["digest"], f"{node_id}: Tier1 retained PASS evidence")
    if cp:
        req(cp[0].get("files") == files, f"{node_id}: Tier1 file hashes must match campaign")

    dag_node = dag.get(node_id, {})
    req(dag_node.get("tier") == 1 and dag_node.get("state") == "PASS", f"{node_id}: DAG PASS")
    req(dag_node.get("source_authority") == "kde-upstream" and dag_node.get("package_provider") == "supralinux", f"{node_id}: DAG authority/provider")
    req(dag_node.get("package_version") == expected["version"], f"{node_id}: DAG version")
    req(dag_node.get("binary_packages") == expected["packages"], f"{node_id}: DAG binary packages")
    req(dag_node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: DAG predecessor")
    req(dag_node.get("claim") == "hosted-clean-package-preflight" and dag_node.get("authoritative") is False, f"{node_id}: DAG claim boundary")
    req(dag_node.get("downstream_eligible") is True, f"{node_id}: DAG downstream eligible")
    req(dag_node.get("pass_files") == files, f"{node_id}: DAG PASS file hashes")

    deb = ROOT / "packages/kde" / node_id / "debian"
    control = text(deb / "control")
    rules = text(deb / "rules")
    changelog = text(deb / "changelog")
    readme = text(deb / "README.source")
    req(changelog.startswith(f"{node['source_package']} ({expected['version']}) resolute;"), f"{node_id}: changelog revision")
    for token in ("debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", "qt6-tools-dev (>= 6.9.0~)"):
        req(token in control, f"{node_id}: missing control token {token}")
    req("-DBUILD_QCH=OFF" in rules, f"{node_id}: QCH disabled")
    req("Debian 6.28.0 baseline" in readme, f"{node_id}: reference provenance")
    key = deb / "upstream/signing-key.asc"
    req(key.exists() and sha(key) == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", f"{node_id}: signing key")
    consumer = text(ROOT / "packages/kde" / node_id / "consumer/CMakeLists.txt")
    main = text(ROOT / "packages/kde" / node_id / "consumer/main.cpp")
    req(f"find_package({expected['cmake']} 6.30 REQUIRED)" in consumer and expected["target"] in consumer, f"{node_id}: consumer CMake")
    req(expected["soname"] in main and "dlopen" in main, f"{node_id}: runtime consumer")

req(sum(1 for n in tier.values() if n.get("state") == "PASS") == 25, "Tier1 current PASS count must be 25")
req(sum(1 for n in tier.values() if n.get("state") == "pending") == 4, "Tier1 current pending count must be 4")
req(not any(n.get("state") in {"FAIL", "BLOCKED"} for n in tier.values()), "Tier1 must have zero current FAIL/BLOCKED")

# ModemManagerQt must retain both real FAIL attempts before the validated -3 PASS.
mm = campaign["nodes"]["modemmanager-qt"]
mm_ev = mm.get("evidence", [])
req([e.get("result") for e in mm_ev] == ["FAIL", "FAIL", "PASS"], "ModemManagerQt evidence order must retain FAIL/FAIL/PASS history")
if len(mm_ev) >= 2:
    first, second = mm_ev[:2]
    req(first.get("workflow_run") == 35014875475 and first.get("job_id") == 104535671188, "ModemManagerQt -1 run/job")
    req(first.get("attempted_package_version") == "6.30.0-0supralinux1", "ModemManagerQt -1 revision")
    req(first.get("artifact_id") == 10415586492 and first.get("artifact_sha256") == "f79f98cc73f561e5750c4db7917917a043f260131af0ac19180fd835dee78af7", "ModemManagerQt -1 artifact")
    req(first.get("tests") == "11/11 PASS" and first.get("failure_substage") == "Lintian/symbols", "ModemManagerQt -1 failure boundary")
    req("_ZSt19piecewise_construct@Base" in first.get("cause", ""), "ModemManagerQt -1 root cause")
    req(second.get("workflow_run") == 35017509303 and second.get("job_id") == 104544555425, "ModemManagerQt -2 run/job")
    req(second.get("attempted_package_version") == "6.30.0-0supralinux2", "ModemManagerQt -2 revision")
    req(second.get("artifact_id") == 10416692119 and second.get("artifact_sha256") == "2b081f989d42f6d4820b238c9e739ccb4104080ceae7a49aa49cb20305eb66d7", "ModemManagerQt -2 artifact")
    req(second.get("tests") == "11/11 PASS" and second.get("symbols_transform") == "PASS", "ModemManagerQt -2 symbols/test evidence")
    req(second.get("failure_substage") == "Lintian/build-prerequisite" and "rules-require-build-prerequisite" in second.get("cause", ""), "ModemManagerQt -2 root cause")

rem = mm.get("remediation", {})
req(rem.get("candidate_package_version") == "6.30.0-0supralinux3", "ModemManagerQt remediation revision")
req(rem.get("status") == "validated" and rem.get("validated_by_run_id") == 35021323444, "ModemManagerQt remediation validation")
req(rem.get("source_change") is False, "ModemManagerQt remediation must not change KDE source")
req(rem.get("symbols_baseline_sha256") == "70c9ebc08c99174f022c3b4b38ed4cde4a8725f0a2f8ea04a09371132312d6f2", "ModemManagerQt baseline hash")
req(rem.get("symbols_result_sha256") == "b717475396376ac884bb3587ab2a0e898af5beb940836c45ee834758eec6820f", "ModemManagerQt transformed hash")
req(rem.get("symbols_transform_sha256") == "f468a9e752ecb79ccc05e3a7e344622f7b1e6aeae94fb71089a94f0f51d5559b", "ModemManagerQt transform hash")
req(mm.get("last_pass_files") == MM_FILES, "ModemManagerQt exact PASS file hashes")

dag_mm = dag["modemmanager-qt"]
req(dag_mm.get("remediation") == rem, "DAG must retain validated ModemManagerQt remediation")
req([e.get("result") for e in dag_mm.get("evidence", [])] == ["FAIL", "FAIL", "PASS"], "DAG must retain ModemManagerQt attempt history")

mm_control = text(ROOT / "packages/kde/modemmanager-qt/debian/control")
mm_rules = text(ROOT / "packages/kde/modemmanager-qt/debian/rules")
req("modemmanager-dev (>= 1.0)" in mm_control and "libmm-glib-dev" not in mm_control, "ModemManagerQt provider contract")
req("python3:any" in mm_control, "ModemManagerQt -3 Python build prerequisite")
req("dbus-run-session dh_auto_test -Skf6" in mm_rules, "ModemManagerQt D-Bus test session")
req("override_dh_makeshlibs:" in mm_rules and "python3 debian/apply-symbols-delta.py" in mm_rules, "ModemManagerQt symbols remediation")
transform = ROOT / "packages/kde/modemmanager-qt/debian/apply-symbols-delta.py"
req(transform.exists() and sha(transform) == "f468a9e752ecb79ccc05e3a7e344622f7b1e6aeae94fb71089a94f0f51d5559b", "ModemManagerQt transform script hash")

req("xvfb-run -a dh_auto_test" in text(ROOT / "packages/kde/kidletime/debian/rules"), "KIdleTime tests via Xvfb")
nm_control = text(ROOT / "packages/kde/networkmanager-qt/debian/control")
nm_rules = text(ROOT / "packages/kde/networkmanager-qt/debian/rules")
for token in ("dh-sequence-qmldeps", "libglib2.0-dev", "libnm-dev (>= 1.4.0~)", "qt6-declarative-dev (>= 6.9.0~)", "Package: qml6-module-org-kde-networkmanager"):
    req(token in nm_control, f"NetworkManagerQt missing {token}")
for test_name in ("managertest", "settingstest", "activeconnectiontest"):
    req(test_name in nm_rules, f"NetworkManagerQt must document isolated-service exclusion {test_name}")

workflow = text(WORKFLOW)
runner = text(RUNNER)
scope = text(SCOPE)
policy = text(POLICY)
for token in ("runs-on: ubuntu-26.04", "fail-fast: false", "max-parallel: 3", "node: [kidletime, modemmanager-qt, networkmanager-qt]", "artifact-ids: '10298635300'", "artifact-ids: '10301938362'", "scripts/kde-tier1-package-batch5-needed.sh", "scripts/run-kde-tier1-package-batch5-preflight.sh"):
    req(token in workflow, f"Batch5 workflow missing {token}")
req("ubuntu-latest" not in workflow and "pull_request_target" not in workflow, "Batch5 workflow runner/trigger boundary")
for token in ("dpkg-source -b", "sbuild --verbose --chroot-mode=unshare", "lintian --fail-on error", "readelf -d", 'cmake -S "${CONSUMER_META}"', "modemmanager-dev", "libnm-dev", "libglib2.0-dev", "EXPECTED_PACKAGES"):
    req(token in runner, f"Batch5 runner missing {token}")
for node_id in EXPECTED:
    req(node_id in scope, f"Batch5 scope missing {node_id}")
req("manifests/kde-tier1-package-campaign-batch5.json" in scope and "binary_contracts" in scope and "build_profile_tokens" in scope, "Batch5 semantic scope fingerprint")
req("python3 scripts/validate_kde_tier1_package_batch5.py" in policy, "Repository Policy must execute Batch5 validator")

for path in (DOC, STATUS):
    t = text(path)
    req("16 PASS" in t and "13 pending" in t, f"{path.name}: historical Batch 5 closure count")
t = text(CURRENT_STATUS)
req("18 PASS" in t and "11 pending" in t, f"{CURRENT_STATUS.name}: historical 2026-09-15 canonical count")
for path in (DAG_DOC, DEPENDENCY_DOC):
    t = text(path)
    req("25 PASS" in t and "4 pending" in t, f"{path.name}: current canonical count")
for path in (DOC, STATUS, PROVIDER_DOC, DEPENDENCY_DOC):
    t = text(path)
    req("35012023822" in t and "10414525047" in t and "db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a" in t, f"{path.name}: provider evidence")
for token in ("3/3 PASS", "35021323444", "104557423664", "10417683848", "42d4f804effc6e4b9148e8c01887bdce6f95f0554ac4d03295e844a861a54eb7", "11/11 PASS", "python3:any"):
    req(token.lower() in text(DOC).lower(), f"Batch5 documentation missing {token}")
    req(token.lower() in text(STATUS).lower(), f"Batch5 status missing {token}")
req("open remediation" not in text(DOC).lower() and "remediation pending" not in text(DOC).lower(), "Batch5 document must not claim open remediation")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 5 canonical closure: PASS")
print("KIdleTime, ModemManagerQt and NetworkManagerQt = 3/3 PASS/downstream-eligible")
print("Canonical Tier 1: 25 PASS / 4 pending / 0 FAIL / 0 BLOCKED")
