#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1.json"
DEPENDENCY_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1-dependencies.json"

EXPECTED_SOURCE_HASHES = {'attica': '3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c', 'bluez-qt': 'f5045b14a6c689bbfded9437582f943dd4f8f74537085ab6115bcacdea2110d8', 'karchive': '4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2', 'kcalendarcore': 'e8bf60e398e2f8098a4db7db44c5475d70540ad8f8948a123c8bc109dc4db776', 'kcodecs': 'a42c79ff3237b73789d1c63cdfd848c0d59671ce5e93723a2efa128f00cb3450', 'kconfig': '0e98bac324cd716849202d4b246a948e363d6792a8eb09c78417cdde9559f56e', 'kcoreaddons': 'cc68fe15beb0fca2036cff8742f468c1345406bf99793fffacbf8f2a3f89bc4b', 'kdbusaddons': '063ef80460f76d86dc4b033ef04b65b69ba82ee0de410440fe609465e7f5a997', 'kglobalaccel': 'e532ebd4cbfc8d6d79c6c38c556f1871315fedae8db2b69b574b9c496f171473', 'kguiaddons': 'e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d', 'kholidays': '02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b', 'ki18n': 'dfbfc8af89b3bc68810b094bf87746db87c3eeb35b75caeb1882681ebed563bd', 'kidletime': '22873204292ddb757e5a0a57004c57debe1285cd0fd4e796d07e9de2402e60c3', 'kirigami': '6de811e559c20dc1086c0cf2c34bb98712dbe4d45f960c62c3c3f887332c95f8', 'kitemmodels': 'f807e5b37aa913d2563ee1a21b2bce7d34495f32f38c7f35f16262d736bdfd55', 'kitemviews': '9452f2b0cc5dd0214b88c4ce33297866be89af4177af14f5390cfb616e49c153', 'kplotting': 'f5a67be85c21665e052371301889443196b9de5b3927aff353a3d3e27730dd11', 'kquickcharts': '9fe8c0c78ffd23ccfb99cc36477550a229c114ad057def938f38cdec35f82ab1', 'syntax-highlighting': 'fc429b093058bec4878306cbbfb3aa0560ff4a3f166c69504036c507fe72afcc', 'ktexttemplate': 'c3c229944d25294102e4e8a5b49fa0c0f481da9d33f8bec3782e8a53afd47493', 'kuserfeedback': 'c8a463c8e570f6d532cbe150732220575c6385df97c91399b6c84450691771ca', 'kwidgetsaddons': 'ab1333c258678caa7562120a1c03bb71779f7232f1a0e75b9525d921dee3e0a3', 'kwindowsystem': '639a501b877446b19905399d27e2be2b6ebb0bb481abe3209dc4d535a12e12ca', 'modemmanager-qt': 'd7c4106dc130729fdfd435abaeaf85039a874fc18563a41755e14f7ea174ae21', 'networkmanager-qt': 'f6ba5f54d413ea0b2642207a6ebd0803e7cb8392b91fcf8a1679fd0c21062865', 'prison': '2cdb0a2689ab45b907c76c9a01c1dc14855b8e5329ad0a9cf65c1ad64e5fed1b', 'solid': 'bdbfdc9f26b87e12b951097825af2956f2dee3f14c701d780277b69701f2c74e', 'sonnet': '1574ef5c17f38e315de104b94580ccc1b7ec1db2650cb4bace2e14159bf61e10', 'threadweaver': 'e5400968a41820393e76190ab5dbb276c09513263d1b185d64b40f82dcd9b457'}
EXPECTED_ROOT_CMAKE_BLOBS = {'attica': '92ae57c6bf82a8fad6c412b5b47a8c45a8652d88', 'bluez-qt': '88dd15daf02a31098f230028b7222bb9355e6ba2', 'karchive': '6f86222fb967c7f3e29c15ecef40bf355d8004d0', 'kcalendarcore': '0414c1256b209ae14c41f2ccc0a99480f3298a17', 'kcodecs': 'a4844477467d5c7b47875f837fa6db0b22550397', 'kconfig': '1567b39f76304dcfdede6846c6ceb4b780ceb8d5', 'kcoreaddons': '05f43e4eadd696009eb619e7d0cae656608d66f4', 'kdbusaddons': '26cde2148db4d86adeea0f4bda597f0f9e610816', 'kglobalaccel': '274623176b4c0f9b72edea3bd770530f76c8f607', 'kguiaddons': '35571804fb913f4b86f52b8d98e4b7973014d0e7', 'kholidays': 'ee43159b9e7259c8c4cefe0db38e2ca715b73ad9', 'ki18n': '0a252c9696f8106205034b3ffc741f251ad54f3d', 'kidletime': '3617fd79358beaea36d862483b8b4947eef30508', 'kirigami': '15bb9d921461c4adafaf7901f1ad6b6758e27e83', 'kitemmodels': '3d20e22e28fc67fd7e4d10ec4a60d2f5d2095264', 'kitemviews': 'd4abc8277881fff0ad85d06167b0f1e5c8e0977d', 'kplotting': 'ee78f84b45359e54a309cecb4042faa7c60c6290', 'kquickcharts': 'b3e62a5fb195a484d50be09c3f50970714364d8a', 'syntax-highlighting': 'cbd31a8f3c8b981931fc0d39ee5991f5c7f6903a', 'ktexttemplate': 'e68c80cc6106c87e321d23729f882052ab386972', 'kuserfeedback': 'e478a36c6e029ca53d076e89ff07aa62d2979839', 'kwidgetsaddons': 'f76e59170f9edb461f097e17049fba9bc6355941', 'kwindowsystem': 'e8317948e1df27330ceddf45bf418aa2a02bde5b', 'modemmanager-qt': '1c253781f61fe39608b7d102a9359ca2f9afb1b0', 'networkmanager-qt': 'be28b0b1092c3b64a4561fcb28f0dbf811e6a939', 'prison': '0d267e718edbc28556da8eb0489d1274030b2c93', 'solid': '65681c1db745cd52a547659f1b778fa42bb3cb52', 'sonnet': '2b1e0306ee3c51d144fa33e1ef725abc06cb4fe6', 'threadweaver': '309efd1d962d925a71610ea65fed2a1007ef055d'}
EXPECTED_EXTRA_BLOBS = {'kitemviews': {'src/designer/CMakeLists.txt': '26a6cd08e9d558ee6092dc23ff7d620d900e18f5'}, 'kplotting': {'src/designer/CMakeLists.txt': 'f8d5cd8cf8677e7eaa69745ee6c8ca23a0c6bb94'}, 'kwidgetsaddons': {'src/designer/CMakeLists.txt': '32b9a587556ac3df8b4a6e1b97c1e839115809e9'}, 'sonnet': {'src/plugins/CMakeLists.txt': 'b835f521d75cb5a321d695d140f34f1a81503e0f'}}
EXPECTED_PASS = {'attica': {'version': '6.30.0-0supralinux2', 'run': 34706416753, 'artifact': 10301851297, 'digest': 'f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27', 'tests': '6/6 PASS', 'soname': 'libKF6Attica.so.6'}, 'kcodecs': {'version': '6.30.0-0supralinux4', 'run': 34716761551, 'job': 103615297758, 'artifact': 10305050385, 'digest': 'd83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45', 'tests': '8/8 PASS', 'soname': 'libKF6Codecs.so.6'}, 'kdbusaddons': {'version': '6.30.0-0supralinux3', 'run': 34713034164, 'job': 103605147881, 'artifact': 10304340428, 'digest': '2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799', 'tests': '3/3 PASS', 'soname': 'libKF6DBusAddons.so.6'}, 'threadweaver': {'version': '6.30.0-0supralinux3', 'run': 34713034164, 'job': 103605147772, 'artifact': 10303986419, 'digest': '6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8', 'tests': '8/8 PASS', 'soname': 'libKF6ThreadWeaver.so.6'}}
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

errors: list[str] = []

def require(value: bool, message: str) -> None:
    if not value:
        errors.append(message)

def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(value, dict):
        print(f"ERROR: {path.relative_to(ROOT)} must contain an object", file=sys.stderr)
        raise SystemExit(1)
    return value

def requirement(deps: dict, key: str) -> dict:
    item = deps.get("requirements", {}).get(key)
    if not isinstance(item, dict):
        errors.append(f"Missing dependency requirement registry entry: {key}")
        return {}
    return item

def validate_pass(node: dict) -> None:
    node_id = node["id"]
    expected = EXPECTED_PASS[node_id]
    packaging = node.get("packaging", {})
    require(node.get("state") == "PASS", f"{node_id}: node state must be PASS")
    require(packaging.get("state") == "PASS", f"{node_id}: packaging state must be PASS")
    require(packaging.get("package_version") == expected["version"], f"{node_id}: package version mismatch")
    require(packaging.get("claim") == "hosted-clean-package-preflight", f"{node_id}: claim mismatch")
    require(packaging.get("authoritative") is False, f"{node_id}: hosted PASS must remain non-authoritative")
    require(packaging.get("downstream_eligible") is True, f"{node_id}: PASS must be downstream eligible")
    evidence = packaging.get("evidence", [])
    passes = [item for item in evidence if isinstance(item, dict) and item.get("result") == "PASS"]
    require(len(passes) == 1, f"{node_id}: exactly one retained current PASS expected")
    if passes:
        item = passes[0]
        require(item.get("workflow_run") == expected["run"], f"{node_id}: PASS run mismatch")
        if "job" in expected:
            require(item.get("job_id") == expected["job"], f"{node_id}: PASS job mismatch")
        require(item.get("artifact_id") == expected["artifact"], f"{node_id}: PASS artifact mismatch")
        require(item.get("artifact_sha256") == expected["digest"], f"{node_id}: PASS digest mismatch")
        require(item.get("tests") == expected["tests"], f"{node_id}: test evidence mismatch")
        require(item.get("lintian") == "PASS-errors", f"{node_id}: Lintian error gate must pass")
        require(item.get("consumer_smoke") == "PASS", f"{node_id}: consumer smoke must pass")
        require(item.get("abi_soname") == expected["soname"], f"{node_id}: SONAME evidence mismatch")
        require(item.get("ecm_predecessor") == "6.30.0-0supralinux3", f"{node_id}: ECM predecessor mismatch")
        files = item.get("files", {})
        require(isinstance(files, dict) and bool(files), f"{node_id}: retained PASS file hashes required")
        for key, digest in files.items():
            require(re.fullmatch(r"[0-9a-f]{64}", str(digest)) is not None, f"{node_id}: invalid retained hash {key}")

source = load_json(SOURCE_MANIFEST)
deps = load_json(DEPENDENCY_MANIFEST)

require(source.get("schema") == 1, "Tier 1 source manifest schema must be 1")
require(source.get("authority") == "kde-upstream", "Tier 1 source authority must remain KDE upstream")
require(source.get("frameworks_series") == "6.30.0", "Tier 1 Frameworks series must be 6.30.0")
require(source.get("tier") == 1, "Tier 1 source manifest must identify tier 1")
require(source.get("tier_reference") == "https://api.kde.org/", "Tier classification must reference KDE API")
require(source.get("release_reference") == "https://kde.org/info/kde-frameworks-6.30.0/", "Release hashes must reference KDE 6.30 info page")
require(source.get("frameworks_qt_minimum") == "6.9.0", "Frameworks 6.30 Qt minimum must remain 6.9.0")
require(source.get("dependency_manifest") == "manifests/kde-frameworks-tier1-dependencies.json", "Tier 1 dependency manifest link changed")

qt_provider = source.get("selected_qt_provider", {})
require(qt_provider == {"provider":"ubuntu","series":"resolute","resolved_version":"6.10.2","status":"preflight-pass-final-certification-pending"}, "Selected Qt provider evidence changed unexpectedly")
ecm = source.get("ecm_prerequisite", {})
require(ecm == {"state":"PASS","version":"6.30.0-0supralinux3","evidence_run_id":34694951158,"deb_sha256":"ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f"}, "ECM predecessor evidence changed unexpectedly")

nodes = source.get("nodes", [])
require(isinstance(nodes, list) and len(nodes) == 29, "Tier 1 must contain exactly 29 nodes")
ids = [n.get("id") for n in nodes if isinstance(n, dict)]
require(len(ids) == len(set(ids)), "Tier 1 node IDs must be unique")
require(set(ids) == set(EXPECTED_SOURCE_HASHES), "Tier 1 node set must match KDE upstream classification")

for node in nodes:
    if not isinstance(node, dict):
        errors.append("Tier 1 node must be an object")
        continue
    node_id = node.get("id")
    require(node.get("upstream_tier") == 1, f"{node_id}: upstream tier must be 1")
    require(node.get("upstream_version") == "6.30.0", f"{node_id}: upstream version must be 6.30.0")
    require(node.get("source_sha256") == EXPECTED_SOURCE_HASHES.get(node_id), f"{node_id}: source SHA mismatch")
    require(node.get("source_url") == f"https://download.kde.org/stable/frameworks/6.30/{node_id}-6.30.0.tar.xz", f"{node_id}: source URL mismatch")
    require(node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: DAG must depend only on ECM")
    require(node.get("kde_framework_dependencies") == [], f"{node_id}: Tier 1 cannot depend on another Framework")
    require(node.get("external_dependencies") == {"status":"resolved","manifest":"manifests/kde-frameworks-tier1-dependencies.json","node":node_id}, f"{node_id}: dependency resolution reference mismatch")
    if node_id in EXPECTED_PASS:
        validate_pass(node)
    else:
        require(node.get("packaging") == {"state":"pending"}, f"{node_id}: unattempted packaging state must remain pending")
        require(node.get("state") == "pending", f"{node_id}: unattempted node state must remain pending")

require(sum(1 for n in nodes if n.get("state") == "PASS") == 4, "Tier 1 current PASS count must be 4")
require(sum(1 for n in nodes if n.get("state") == "pending") == 25, "Tier 1 current pending count must be 25")
require(not any(n.get("state") in {"FAIL","BLOCKED"} for n in nodes), "Tier 1 must have no current FAIL/BLOCKED nodes after batch 1 closure")

require(deps.get("schema") == 1, "Dependency manifest schema must be 1")
require(deps.get("authority") == "kde-upstream", "Dependency authority must remain KDE upstream")
require(deps.get("frameworks") == "6.30.0", "Dependency manifest must target Frameworks 6.30.0")
require(deps.get("target") == "linux", "Dependency manifest target must be Linux")
require(deps.get("provider_candidate") == EXPECTED_PROVIDER_EVIDENCE, "Provider availability evidence changed unexpectedly")
require(deps.get("common") == {"cmake_minimum":"3.29","ecm":"6.30.0","qt_minimum":"6.9.0"}, "Common Frameworks minima changed unexpectedly")

qt_map = deps.get("qt_provider_packages", {})
for component in ("Core","Gui","GuiPrivate","Qml","Quick","WaylandClient","ShaderTools","Multimedia","UiPlugin"):
    require(component in qt_map, f"Qt provider map missing {component}")
require(qt_map.get("Multimedia") == ["qt6-multimedia-dev"], "Qt Multimedia provider mapping changed")
require(qt_map.get("UiPlugin") == ["qt6-tools-dev"], "Qt UiPlugin provider mapping changed")

metadata = deps.get("metadata", {})
dep_nodes = deps.get("nodes", {})
require(set(metadata) == set(EXPECTED_SOURCE_HASHES), "Dependency metadata node set must match Tier 1")
require(set(dep_nodes) == set(EXPECTED_SOURCE_HASHES), "Dependency profile node set must match Tier 1")
for node_id in EXPECTED_SOURCE_HASHES:
    meta = metadata.get(node_id, {})
    require(meta.get("ref") == "v6.30.0", f"{node_id}: dependency metadata ref mismatch")
    require(meta.get("root_cmake_blob") == EXPECTED_ROOT_CMAKE_BLOBS[node_id], f"{node_id}: root CMake blob mismatch")
    require(meta.get("extra", {}) == EXPECTED_EXTRA_BLOBS.get(node_id, {}), f"{node_id}: extra metadata blob mismatch")

registry = deps.get("requirements", {})
for key, minimum in (("libical","3.0"),("python-dev","3.9"),("bison-3.3.2","3.3.2"),("wayland-client","1.9"),("plasma-wayland-protocols-1.15","1.15.0"),("wayland-protocols-1.46","1.46"),("modemmanager","1.0"),("libnm","1.4.0"),("zxing","1.4.0")):
    require(requirement(deps, key).get("minimum") == minimum, f"{key} minimum must remain {minimum}")
require(requirement(deps, "hspell").get("packages") == ["hspell"], "HSpell provider mapping must use hspell")
for node_id in ("kitemviews","kplotting","kwidgetsaddons"):
    require("UiPlugin" in dep_nodes[node_id]["qt"].get("default_enabled", []), f"{node_id}: designer plugin requires Qt UiPlugin")
sonnet_groups = dep_nodes["sonnet"]["external"].get("required_any_of", [])
require(len(sonnet_groups) == 1, "Sonnet must retain one backend alternative group")
if sonnet_groups:
    require(set(sonnet_groups[0].get("choices", [])) == {"aspell","hspell","hunspell","voikko"}, "Sonnet backend choices changed")
    require(sonnet_groups[0].get("provider_profile") == "install-all-available; gate-at-least-one", "Sonnet provider policy changed")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Frameworks 6.30 Tier 1 source/dependency validation: PASS")
print("Tier 1 package states: 4 PASS/downstream-eligible; 25 pending; 0 FAIL; 0 BLOCKED")
print("Ubuntu Resolute provider mapping: hosted preflight PASS; final certification pending")
