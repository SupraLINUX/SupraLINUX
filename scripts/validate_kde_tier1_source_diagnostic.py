#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M = ROOT / "manifests/kde-tier1-source-diagnostic.json"
T = ROOT / "manifests/kde-frameworks-tier1.json"
W = ROOT / ".github/workflows/kde-tier1-source-diagnostic.yml"
R = ROOT / "scripts/run-kde-tier1-source-diagnostic.sh"
S = ROOT / "scripts/kde-tier1-source-diagnostic-needed.sh"

def fail(msg):
    raise SystemExit(msg)

def load(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        fail(f"cannot parse {path.relative_to(ROOT)}: {exc}")

m=load(M); t=load(T)
expected=["kconfig","ki18n","sonnet","kirigami","kquickcharts","kuserfeedback","prison"]
if m.get("schema") != 1 or m.get("authority") != "kde-upstream" or m.get("frameworks_series") != "6.30.0":
    fail("source diagnostic identity mismatch")
if m.get("claim") != "non-promoting-source-diagnostic" or m.get("non_promoting") is not True:
    fail("source diagnostic must be explicitly non-promoting")
if m.get("dag_state_changes_allowed") is not False:
    fail("source diagnostic must not change DAG state")
if m.get("result_vocabulary") != ["DIAG_PASS","DIAG_FAIL"]:
    fail("source diagnostic result vocabulary mismatch")
if list(m.get("nodes",{})) != expected:
    fail("source diagnostic node order/set mismatch")

canonical={x["id"]:x for x in t.get("nodes",[])}
for node in expected:
    d=m["nodes"][node]
    c=canonical.get(node)
    if not c:
        fail(f"{node}: missing from canonical Tier 1 manifest")
    if d.get("source_sha256") != c.get("source_sha256") or d.get("source_url") != c.get("source_url"):
        fail(f"{node}: source authority/hash mismatch with canonical Tier 1 manifest")
    if not d.get("provider_packages"):
        fail(f"{node}: provider package set is empty")
    if not isinstance(d.get("cmake_defaults"),dict):
        fail(f"{node}: cmake_defaults must be an object")

expected_defaults={
    "kconfig":{"KCONFIG_USE_GUI":"ON","KCONFIG_USE_QML":"ON","USE_DBUS":"ON"},
    "ki18n":{"BUILD_WITH_QML":"ON"},
    "sonnet":{"SONNET_USE_WIDGETS":"ON","SONNET_USE_QML":"ON","SONNET_NO_BACKENDS":"OFF","BUILD_DESIGNERPLUGIN":"ON"},
    "kirigami":{"BUILD_SHARED_LIBS":"ON","DESKTOP_ENABLED":"ON","BUILD_EXAMPLES":"OFF","UBUNTU_TOUCH":"OFF","USE_DBUS":"ON"},
    "kquickcharts":{"BUILD_EXAMPLES":"OFF"},
    "kuserfeedback":{"ENABLE_SURVEY_TARGET_EXPRESSIONS":"ON","ENABLE_PHP":"ON","ENABLE_PHP_UNIT":"ON","ENABLE_DOCS":"ON","ENABLE_CONSOLE":"OFF"},
    "prison":{"WITH_DMTX":"ON","WITH_ZXING":"ON","WITH_QUICK":"ON","WITH_MULTIMEDIA":"ON"},
}
for node,defaults in expected_defaults.items():
    if m["nodes"][node]["cmake_defaults"] != defaults:
        fail(f"{node}: upstream default assertions changed")

required_provider_tokens={
    "kconfig":{"qt6-base-dev","qt6-declarative-dev"},
    "ki18n":{"qt6-base-dev","qt6-declarative-dev","iso-codes"},
    "sonnet":{"libaspell-dev","hspell","libhunspell-dev","libvoikko-dev"},
    "kirigami":{"qt6-base-private-dev","qt6-declarative-dev","qt6-svg-dev","qt6-shadertools-dev"},
    "kquickcharts":{"qt6-declarative-dev","qt6-shadertools-dev"},
    "kuserfeedback":{"flex","bison","php-cli","phpunit","qt6-charts-dev"},
    "prison":{"libqrencode-dev","libdmtx-dev","libzxing-dev","qt6-multimedia-dev"},
}
for node,tokens in required_provider_tokens.items():
    missing=tokens-set(m["nodes"][node]["provider_packages"])
    if missing:
        fail(f"{node}: diagnostic provider profile lost {sorted(missing)}")

ecm=m.get("ecm_predecessor",{})
if ecm.get("version") != "6.30.0-0supralinux3" or ecm.get("artifact_id") != 10298635300:
    fail("source diagnostic ECM predecessor mismatch")
if ecm.get("deb_sha256") != "ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f":
    fail("source diagnostic ECM predecessor hash mismatch")

workflow=W.read_text(); runner=R.read_text(); selector=S.read_text()
for token in ("fail-fast: false","max-parallel: 7","kconfig, ki18n, sonnet, kirigami, kquickcharts, kuserfeedback, prison"):
    if token not in workflow:
        fail(f"source diagnostic workflow missing {token}")
for token in (
    "non-promoting-source-diagnostic", "DIAG_PASS", "DIAG_FAIL", "-DBUILD_TESTING=ON",
    "sha256sum --check --strict", "upstream-default-validation", "cmake --build",
    "ctest --test-dir", "cmake --install", "_NET_SUPPORTING_WM_CHECK",
    '"package_gate": False', '"dag_state_change": False'
):
    if token not in runner:
        fail(f"source diagnostic runner lost gate {token}")
if "ctest -E" in runner or "--exclude" in runner:
    fail("source diagnostic must not filter upstream tests")
for token in ("kde-tier1-source-diagnostic.json","kde-frameworks-tier1-dependencies.json","run-kde-tier1-source-diagnostic.sh"):
    if token not in selector:
        fail(f"source diagnostic scope selector missing {token}")

print("KDE Tier 1 global source diagnostic policy: PASS")
print("nodes=7; result vocabulary=DIAG_PASS/DIAG_FAIL; package promotion disabled")
