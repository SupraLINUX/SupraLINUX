#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1.json"
DEPENDENCY_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1-dependencies.json"

EXPECTED_SOURCE_HASHES = {
    "attica":"3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c",
    "bluez-qt":"f5045b14a6c689bbfded9437582f943dd4f8f74537085ab6115bcacdea2110d8",
    "karchive":"4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2",
    "kcalendarcore":"e8bf60e398e2f8098a4db7db44c5475d70540ad8f8948a123c8bc109dc4db776",
    "kcodecs":"a42c79ff3237b73789d1c63cdfd848c0d59671ce5e93723a2efa128f00cb3450",
    "kconfig":"0e98bac324cd716849202d4b246a948e363d6792a8eb09c78417cdde9559f56e",
    "kcoreaddons":"cc68fe15beb0fca2036cff8742f468c1345406bf99793fffacbf8f2a3f89bc4b",
    "kdbusaddons":"063ef80460f76d86dc4b033ef04b65b69ba82ee0de410440fe609465e7f5a997",
    "kglobalaccel":"e532ebd4cbfc8d6d79c6c38c556f1871315fedae8db2b69b574b9c496f171473",
    "kguiaddons":"e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d",
    "kholidays":"02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b",
    "ki18n":"dfbfc8af89b3bc68810b094bf87746db87c3eeb35b75caeb1882681ebed563bd",
    "kidletime":"22873204292ddb757e5a0a57004c57debe1285cd0fd4e796d07e9de2402e60c3",
    "kirigami":"6de811e559c20dc1086c0cf2c34bb98712dbe4d45f960c62c3c3f887332c95f8",
    "kitemmodels":"f807e5b37aa913d2563ee1a21b2bce7d34495f32f38c7f35f16262d736bdfd55",
    "kitemviews":"9452f2b0cc5dd0214b88c4ce33297866be89af4177af14f5390cfb616e49c153",
    "kplotting":"f5a67be85c21665e052371301889443196b9de5b3927aff353a3d3e27730dd11",
    "kquickcharts":"9fe8c0c78ffd23ccfb99cc36477550a229c114ad057def938f38cdec35f82ab1",
    "syntax-highlighting":"fc429b093058bec4878306cbbfb3aa0560ff4a3f166c69504036c507fe72afcc",
    "ktexttemplate":"c3c229944d25294102e4e8a5b49fa0c0f481da9d33f8bec3782e8a53afd47493",
    "kuserfeedback":"c8a463c8e570f6d532cbe150732220575c6385df97c91399b6c84450691771ca",
    "kwidgetsaddons":"ab1333c258678caa7562120a1c03bb71779f7232f1a0e75b9525d921dee3e0a3",
    "kwindowsystem":"639a501b877446b19905399d27e2be2b6ebb0bb481abe3209dc4d535a12e12ca",
    "modemmanager-qt":"d7c4106dc130729fdfd435abaeaf85039a874fc18563a41755e14f7ea174ae21",
    "networkmanager-qt":"f6ba5f54d413ea0b2642207a6ebd0803e7cb8392b91fcf8a1679fd0c21062865",
    "prison":"2cdb0a2689ab45b907c76c9a01c1dc14855b8e5329ad0a9cf65c1ad64e5fed1b",
    "solid":"bdbfdc9f26b87e12b951097825af2956f2dee3f14c701d780277b69701f2c74e",
    "sonnet":"1574ef5c17f38e315de104b94580ccc1b7ec1db2650cb4bace2e14159bf61e10",
    "threadweaver":"e5400968a41820393e76190ab5dbb276c09513263d1b185d64b40f82dcd9b457",
}
EXPECTED_ROOT_CMAKE_BLOBS = {
    "attica":"92ae57c6bf82a8fad6c412b5b47a8c45a8652d88","bluez-qt":"88dd15daf02a31098f230028b7222bb9355e6ba2",
    "karchive":"6f86222fb967c7f3e29c15ecef40bf355d8004d0","kcalendarcore":"0414c1256b209ae14c41f2ccc0a99480f3298a17",
    "kcodecs":"a4844477467d5c7b47875f837fa6db0b22550397","kconfig":"1567b39f76304dcfdede6846c6ceb4b780ceb8d5",
    "kcoreaddons":"05f43e4eadd696009eb619e7d0cae656608d66f4","kdbusaddons":"26cde2148db4d86adeea0f4bda597f0f9e610816",
    "kglobalaccel":"274623176b4c0f9b72edea3bd770530f76c8f607","kguiaddons":"35571804fb913f4b86f52b8d98e4b7973014d0e7",
    "kholidays":"ee43159b9e7259c8c4cefe0db38e2ca715b73ad9","ki18n":"0a252c9696f8106205034b3ffc741f251ad54f3d",
    "kidletime":"3617fd79358beaea36d862483b8b4947eef30508","kirigami":"15bb9d921461c4adafaf7901f1ad6b6758e27e83",
    "kitemmodels":"3d20e22e28fc67fd7e4d10ec4a60d2f5d2095264","kitemviews":"d4abc8277881fff0ad85d06167b0f1e5c8e0977d",
    "kplotting":"ee78f84b45359e54a309cecb4042faa7c60c6290","kquickcharts":"b3e62a5fb195a484d50be09c3f50970714364d8a",
    "syntax-highlighting":"cbd31a8f3c8b981931fc0d39ee5991f5c7f6903a","ktexttemplate":"e68c80cc6106c87e321d23729f882052ab386972",
    "kuserfeedback":"e478a36c6e029ca53d076e89ff07aa62d2979839","kwidgetsaddons":"f76e59170f9edb461f097e17049fba9bc6355941",
    "kwindowsystem":"e8317948e1df27330ceddf45bf418aa2a02bde5b","modemmanager-qt":"1c253781f61fe39608b7d102a9359ca2f9afb1b0",
    "networkmanager-qt":"be28b0b1092c3b64a4561fcb28f0dbf811e6a939","prison":"0d267e718edbc28556da8eb0489d1274030b2c93",
    "solid":"65681c1db745cd52a547659f1b778fa42bb3cb52","sonnet":"2b1e0306ee3c51d144fa33e1ef725abc06cb4fe6",
    "threadweaver":"309efd1d962d925a71610ea65fed2a1007ef055d",
}
EXPECTED_EXTRA_BLOBS = {
    "kitemviews":{"src/designer/CMakeLists.txt":"26a6cd08e9d558ee6092dc23ff7d620d900e18f5"},
    "kplotting":{"src/designer/CMakeLists.txt":"f8d5cd8cf8677e7eaa69745ee6c8ca23a0c6bb94"},
    "kwidgetsaddons":{"src/designer/CMakeLists.txt":"32b9a587556ac3df8b4a6e1b97c1e839115809e9"},
    "sonnet":{"src/plugins/CMakeLists.txt":"b835f521d75cb5a321d695d140f34f1a81503e0f"},
}
EXPECTED_PROVIDER_EVIDENCE = {
    "distribution": "ubuntu",
    "series": "resolute",
    "status": "hosted-preflight-pass",
    "evidence": {
        "workflow_run": 34700048774,
        "head_sha": "6ce61bc02c4aba146bcc33b16d17f56fb66f057a",
        "artifact_id": 10299608166,
        "artifact_sha256": "da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3",
        "authoritative": False,
        "claim": "provider-availability-only",
    },
}

ATTICA_PASS = {
    "package_version": "6.30.0-0supralinux2",
    "workflow_run": 34706416753,
    "commit": "9945bfa92d776d432c76e17516b0ff9452b6d159",
    "artifact_id": 10301851297,
    "artifact_sha256": "f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27",
}
ATTICA_FAIL = {
    "workflow_run": 34705165994,
    "commit": "c18c8dcd1934a5bba874e642ba9b14729d2e69df",
    "artifact_id": 10300903114,
    "artifact_sha256": "171cfe8553aba2af8f42a640ee5f50f82988005edbd104b737d93b639dc38300",
}

errors: list[str] = []


def require(value: bool, message: str) -> None:
    if not value:
        errors.append(message)


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    require(isinstance(data, dict), f"{path.relative_to(ROOT)} must contain a JSON object")
    return data


def requirement(deps: dict, key: str) -> dict:
    item = deps.get("requirements", {}).get(key)
    if not isinstance(item, dict):
        errors.append(f"Missing dependency requirement registry entry: {key}")
        return {}
    return item


def require_min(deps: dict, key: str, minimum: str) -> None:
    require(requirement(deps, key).get("minimum") == minimum, f"{key} minimum must remain {minimum}")


def validate_attica_state(node: dict) -> None:
    packaging = node.get("packaging", {})
    require(packaging.get("state") == "PASS", "attica: packaging state must be PASS")
    require(packaging.get("package_version") == ATTICA_PASS["package_version"], "attica: validated package revision mismatch")
    require(packaging.get("claim") == "hosted-clean-package-preflight", "attica: hosted claim mismatch")
    require(packaging.get("authoritative") is False, "attica: hosted PASS must remain non-authoritative")
    require(packaging.get("downstream_eligible") is True, "attica: PASS artifact must be downstream eligible")
    require(node.get("state") == "PASS", "attica: DAG state must be PASS")
    evidence = packaging.get("evidence", [])
    require(isinstance(evidence, list) and len(evidence) == 2, "attica: exactly two retained attempts expected")
    if not isinstance(evidence, list):
        return
    by_result = {item.get("result"): item for item in evidence if isinstance(item, dict)}
    fail = by_result.get("FAIL", {})
    passed = by_result.get("PASS", {})
    require(fail.get("workflow_run") == ATTICA_FAIL["workflow_run"], "attica: first FAIL run mismatch")
    require(fail.get("commit") == ATTICA_FAIL["commit"], "attica: first FAIL commit mismatch")
    require(fail.get("attempted_package_version") == "6.30.0-0supralinux1", "attica: first attempted revision mismatch")
    require(fail.get("artifact_id") == ATTICA_FAIL["artifact_id"], "attica: first FAIL artifact mismatch")
    require(fail.get("artifact_sha256") == ATTICA_FAIL["artifact_sha256"], "attica: first FAIL digest mismatch")
    require(fail.get("failure_stage") == "source-package", "attica: first FAIL stage mismatch")
    require("dh-sequence-kf6" in str(fail.get("cause", "")), "attica: first FAIL root cause must be retained")
    require(passed.get("workflow_run") == ATTICA_PASS["workflow_run"], "attica: PASS run mismatch")
    require(passed.get("commit") == ATTICA_PASS["commit"], "attica: PASS commit mismatch")
    require(passed.get("attempted_package_version") == ATTICA_PASS["package_version"], "attica: PASS revision mismatch")
    require(passed.get("artifact_id") == ATTICA_PASS["artifact_id"], "attica: PASS artifact mismatch")
    require(passed.get("artifact_sha256") == ATTICA_PASS["artifact_sha256"], "attica: PASS digest mismatch")
    require(passed.get("stage") == "complete", "attica: PASS stage must be complete")
    require(passed.get("tests") == "6/6 PASS", "attica: upstream test evidence mismatch")
    require(passed.get("lintian") == "PASS-errors", "attica: Lintian error gate must pass")
    require(passed.get("consumer_smoke") == "PASS", "attica: consumer smoke must pass")
    require(passed.get("abi_soname") == "libKF6Attica.so.6", "attica: SONAME evidence mismatch")
    require(passed.get("ecm_predecessor") == "6.30.0-0supralinux3", "attica: ECM predecessor evidence mismatch")
    files = passed.get("files", {})
    expected_files = {
        "libkf6attica-dev_deb_sha256":"884e917a29b9618000621029d0dd42c00d4f2e1c925aa03cbf905978b82f0a4b",
        "libkf6attica-doc_deb_sha256":"30bb8e97a2a087809a1ca6d017f6beb8dcee5933d416d958c555033020d77a83",
        "libkf6attica6_deb_sha256":"5f52b2ce38c6dc1ad884d16e9d616c781b098a0445a68485d24087c4572d86de",
        "changes_sha256":"859b76c5cd99a7c949071098e44ae43943e8619a7174c120cfe2a1cf4ebc428e",
        "buildinfo_sha256":"5e10c1f72d07f6f61beff17e3ed3f0cf0254016d23d8c2bd0d1dec9c983bd5f4",
        "dsc_sha256":"25a0a2993787329d3ceae7a6485c9134605a3a188aed492bbc073ec5d5edbc72",
        "debian_tar_sha256":"0fcfabd68df435228170d657754641259c92d75147e00925c5d4766eeb105aa0",
        "orig_tar_sha256":"3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c",
        "rootfs_sha256":"37cef66de0b97f406f0fb59be51d7cbb221b68936db998b5e5a91804cbe97763",
    }
    require(files == expected_files, "attica: retained PASS artifact hashes changed without review")


source = load_json(SOURCE_MANIFEST)
deps = load_json(DEPENDENCY_MANIFEST)

require(source.get("schema") == 1, "Tier 1 source manifest schema must be 1")
require(source.get("authority") == "kde-upstream", "Tier 1 source authority must be KDE upstream")
require(source.get("frameworks_series") == "6.30.0", "Tier 1 Frameworks series must be 6.30.0")
require(source.get("tier") == 1, "Tier 1 source manifest must identify tier 1")
require(source.get("tier_reference") == "https://api.kde.org/", "Tier classification must reference KDE API")
require(source.get("release_reference") == "https://kde.org/info/kde-frameworks-6.30.0/", "Release hashes must reference KDE 6.30 info page")
require(source.get("frameworks_qt_minimum") == "6.9.0", "Frameworks 6.30 Qt minimum must remain 6.9.0")
require(source.get("dependency_manifest") == "manifests/kde-frameworks-tier1-dependencies.json", "Source manifest must link dependency manifest")

qt_provider = source.get("selected_qt_provider", {})
require(qt_provider.get("provider") == "ubuntu" and qt_provider.get("series") == "resolute", "Selected Qt provider must remain Ubuntu Resolute")
require(qt_provider.get("resolved_version") == "6.10.2", "Selected Qt provider evidence must remain 6.10.2")
require(qt_provider.get("status") == "preflight-pass-final-certification-pending", "Qt provider must not be promoted beyond current evidence")

ecm = source.get("ecm_prerequisite", {})
require(ecm.get("state") == "PASS", "Tier 1 requires a PASS ECM predecessor")
require(ecm.get("version") == "6.30.0-0supralinux3", "Tier 1 must consume validated ECM package revision")
require(ecm.get("evidence_run_id") == 34694951158, "Tier 1 must retain ECM PASS workflow run")
require(ecm.get("deb_sha256") == "ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f", "Tier 1 must pin ECM PASS .deb hash")

source_nodes = source.get("nodes", [])
require(isinstance(source_nodes, list) and len(source_nodes) == 29, "Tier 1 must contain exactly 29 nodes")
source_ids = [n.get("id") for n in source_nodes if isinstance(n, dict)]
require(len(source_ids) == len(set(source_ids)), "Tier 1 source node IDs must be unique")
require(set(source_ids) == set(EXPECTED_SOURCE_HASHES), "Tier 1 source node set must match KDE upstream classification")
for node in source_nodes:
    if not isinstance(node, dict):
        errors.append("Tier 1 source node entry must be an object")
        continue
    node_id = node.get("id")
    require(node.get("upstream_tier") == 1, f"{node_id}: upstream tier must be 1")
    require(node.get("upstream_version") == "6.30.0", f"{node_id}: upstream version must be 6.30.0")
    require(node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: DAG must depend on PASS ECM")
    require(node.get("kde_framework_dependencies") == [], f"{node_id}: Tier 1 cannot depend on another KDE Framework")
    require(node.get("external_dependencies") == {"status":"resolved","manifest":"manifests/kde-frameworks-tier1-dependencies.json","node":node_id}, f"{node_id}: external dependency resolution reference mismatch")
    if node_id == "attica":
        validate_attica_state(node)
    else:
        require(node.get("packaging") == {"state":"pending"}, f"{node_id}: packaging must remain pending until attempted")
        require(node.get("state") == "pending", f"{node_id}: node must remain pending until attempted")
    require(node.get("source_url") == f"https://download.kde.org/stable/frameworks/6.30/{node_id}-6.30.0.tar.xz", f"{node_id}: source URL must be KDE stable tarball")
    source_hash = str(node.get("source_sha256", ""))
    require(re.fullmatch(r"[0-9a-f]{64}", source_hash) is not None, f"{node_id}: source SHA-256 must be lowercase 64-hex")
    require(source_hash == EXPECTED_SOURCE_HASHES.get(node_id), f"{node_id}: source SHA-256 does not match pinned KDE release metadata")

require(deps.get("schema") == 1, "Tier 1 dependency manifest schema must be 1")
require(deps.get("authority") == "kde-upstream", "Dependency authority must remain KDE upstream")
require(deps.get("frameworks") == "6.30.0", "Dependency manifest must target Frameworks 6.30.0")
require(deps.get("target") == "linux", "Dependency manifest target must be Linux")
require(deps.get("provider_candidate") == EXPECTED_PROVIDER_EVIDENCE, "Provider candidate must retain the hosted Resolute PASS evidence and remain non-authoritative")
require(deps.get("common") == {"cmake_minimum":"3.29","ecm":"6.30.0","qt_minimum":"6.9.0"}, "Common Frameworks 6.30 build minima changed unexpectedly")

qt_map = deps.get("qt_provider_packages", {})
require(isinstance(qt_map, dict), "Qt provider-package registry must be an object")
for component in ("Core","Gui","GuiPrivate","Qml","Quick","WaylandClient","ShaderTools","Multimedia","UiPlugin"):
    require(component in qt_map, f"Qt provider map is missing {component}")
require(qt_map.get("Multimedia") == ["qt6-multimedia-dev"], "Qt Multimedia must map to qt6-multimedia-dev")
require(qt_map.get("UiPlugin") == ["qt6-tools-dev"], "Qt UiPlugin must map to qt6-tools-dev")

registry = deps.get("requirements", {})
require(isinstance(registry, dict), "External dependency registry must be an object")
for key, item in registry.items():
    require(isinstance(item, dict), f"Requirement {key} must be an object")
    if not isinstance(item, dict):
        continue
    packages = item.get("packages")
    require(isinstance(packages, list), f"Requirement {key} packages must be a list")
    for package in packages or []:
        require(isinstance(package, str) and bool(package), f"Requirement {key} has invalid provider package")
        require(package != "libhspell-dev", "Do not invent libhspell-dev; HSpell maps through hspell")

metadata = deps.get("metadata", {})
dep_nodes = deps.get("nodes", {})
require(set(metadata) == set(EXPECTED_SOURCE_HASHES), "Dependency metadata node set must match Tier 1 exactly")
require(set(dep_nodes) == set(EXPECTED_SOURCE_HASHES), "Dependency profile node set must match Tier 1 exactly")
allowed_qt = {"required","default_enabled","recommended","provider_implied","optional","test"}
allowed_ext = {"required","default_enabled","recommended","optional","runtime","required_any_of"}
for node_id in EXPECTED_SOURCE_HASHES:
    meta = metadata.get(node_id, {})
    require(meta.get("ref") == "v6.30.0", f"{node_id}: dependency metadata must be pinned to v6.30.0")
    require(meta.get("root_cmake_blob") == EXPECTED_ROOT_CMAKE_BLOBS[node_id], f"{node_id}: root CMake blob pin mismatch")
    require(meta.get("extra", {}) == EXPECTED_EXTRA_BLOBS.get(node_id, {}), f"{node_id}: extra metadata blob pins mismatch")
    profile = dep_nodes.get(node_id, {})
    qt = profile.get("qt", {})
    require(isinstance(qt, dict), f"{node_id}: Qt profile must be an object")
    for category, components in qt.items():
        require(category in allowed_qt, f"{node_id}: unknown Qt category {category}")
        require(isinstance(components, list), f"{node_id}: Qt category {category} must be a list")
        if isinstance(components, list):
            require(len(components) == len(set(components)), f"{node_id}: duplicate Qt component in {category}")
            for component in components:
                require(component in qt_map, f"{node_id}: Qt component {component} lacks provider mapping")
    external = profile.get("external", {})
    require(isinstance(external, dict), f"{node_id}: external profile must be an object")
    for category, refs in external.items():
        require(category in allowed_ext, f"{node_id}: unknown external category {category}")
        require(isinstance(refs, list), f"{node_id}: external category {category} must be a list")
        if category == "required_any_of" and isinstance(refs, list):
            for group in refs:
                require(isinstance(group, dict), f"{node_id}: required_any_of entries must be objects")
                if isinstance(group, dict):
                    choices = group.get("choices", [])
                    require(isinstance(choices, list) and bool(choices), f"{node_id}: required_any_of needs choices")
                    for key in choices:
                        require(key in registry, f"{node_id}: unknown alternative requirement {key}")
        elif isinstance(refs, list):
            for key in refs:
                require(key in registry, f"{node_id}: unknown requirement {key}")

for key, minimum in (("libical","3.0"),("python-dev","3.9"),("bison-3.3.2","3.3.2"),("wayland-client","1.9"),("plasma-wayland-protocols-1.15","1.15.0"),("wayland-protocols-1.46","1.46"),("modemmanager","1.0"),("libnm","1.4.0"),("zxing","1.4.0")):
    require_min(deps, key, minimum)
require(requirement(deps, "hspell").get("packages") == ["hspell"], "HSpell provider mapping must use hspell")
for node_id in ("kitemviews","kplotting","kwidgetsaddons"):
    require("UiPlugin" in dep_nodes[node_id]["qt"].get("default_enabled", []), f"{node_id}: default designer plugin requires Qt UiPlugin")
sonnet_groups = dep_nodes["sonnet"]["external"].get("required_any_of", [])
require(len(sonnet_groups) == 1, "sonnet must have exactly one backend alternative group")
if sonnet_groups:
    group = sonnet_groups[0]
    require(group.get("name") == "spell-checker-backend", "sonnet backend group name mismatch")
    require(set(group.get("choices", [])) == {"aspell","hspell","hunspell","voikko"}, "sonnet backend choices must match upstream")
    require(group.get("provider_profile") == "install-all-available; gate-at-least-one", "sonnet provider policy changed unexpectedly")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Frameworks 6.30 Tier 1 source/dependency validation: PASS")
print(f"Tier 1 nodes: {len(source_nodes)}")
print("Upstream external dependency metadata: resolved and blob-pinned")
print("Ubuntu Resolute provider mapping: hosted preflight PASS; final certification pending")
print("Tier 1 package states: attica PASS/downstream-eligible; 28 pending")
