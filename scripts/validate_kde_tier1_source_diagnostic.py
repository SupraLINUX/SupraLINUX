#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
M=ROOT/"manifests/kde-tier1-source-diagnostic.json"
T=ROOT/"manifests/kde-frameworks-tier1.json"
W=ROOT/".github/workflows/kde-tier1-source-diagnostic.yml"
R=ROOT/"scripts/run-kde-tier1-source-diagnostic.sh"
S=ROOT/"scripts/kde-tier1-source-diagnostic-needed.sh"

def fail(msg): raise SystemExit(msg)
def load(p):
    try: return json.loads(p.read_text())
    except Exception as exc: fail(f"cannot parse {p.relative_to(ROOT)}: {exc}")

m=load(M); t=load(T)
expected=["kconfig","ki18n","sonnet","kirigami","kquickcharts","kuserfeedback","prison"]
if m.get("schema")!=1 or m.get("authority")!="kde-upstream" or m.get("frameworks_series")!="6.30.0": fail("source diagnostic identity mismatch")
if m.get("claim")!="non-promoting-source-diagnostic" or m.get("non_promoting") is not True: fail("source diagnostic must be explicitly non-promoting")
if m.get("dag_state_changes_allowed") is not False or m.get("result_vocabulary") != ["DIAG_PASS","DIAG_FAIL"]: fail("source diagnostic state vocabulary mismatch")
if list(m.get("nodes",{})) != expected: fail("source diagnostic node order/set mismatch")

canonical={x["id"]:x for x in t.get("nodes",[])}
for node in expected:
    d=m["nodes"][node]; c=canonical.get(node)
    if not c: fail(f"{node}: missing from canonical Tier 1 manifest")
    if d.get("source_sha256")!=c.get("source_sha256") or d.get("source_url")!=c.get("source_url"): fail(f"{node}: source authority/hash mismatch")
    if not d.get("provider_packages") or not isinstance(d.get("cmake_defaults"),dict): fail(f"{node}: invalid diagnostic profile")

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
    if m["nodes"][node]["cmake_defaults"] != defaults: fail(f"{node}: upstream defaults changed")

required_provider_tokens={
 "kconfig":{"qt6-base-dev","qt6-base-private-dev","qt6-declarative-dev"},
 "ki18n":{"qt6-base-dev","qt6-declarative-dev","iso-codes","language-pack-fr-base","locales-all"},
 "sonnet":{"libaspell-dev","hspell","libhunspell-dev","libvoikko-dev"},
 "kirigami":{"qt6-base-private-dev","qt6-declarative-dev","qt6-svg-dev","qt6-shadertools-dev"},
 "kquickcharts":{"qt6-declarative-dev","qt6-shadertools-dev"},
 "kuserfeedback":{"flex","bison","php-cli","phpunit","qt6-charts-dev"},
 "prison":{"libqrencode-dev","libdmtx-dev","libzxing-dev","qt6-multimedia-dev"},
}
for node,tokens in required_provider_tokens.items():
    missing=tokens-set(m["nodes"][node]["provider_packages"])
    if missing: fail(f"{node}: provider profile lost {sorted(missing)}")
if m["nodes"]["kconfig"].get("provider_assertions") != ["qt-core-private-versioned-includes"]: fail("KConfig provider assertion mismatch")
ki=m["nodes"]["ki18n"]
if ki.get("provider_assertions") != ["iso-3166-french-catalogs"]: fail("KI18n provider assertion mismatch")
if ki.get("required_locales") != ["en_US.UTF-8","fr_CH.UTF-8"]: fail("KI18n required locale contract mismatch")
if ki.get("test_environment") != {"LANG":"en_US.UTF-8","LC_ALL":None}: fail("KI18n test locale fixture mismatch")

ecm=m.get("ecm_predecessor",{})
if ecm.get("version")!="6.30.0-0supralinux3" or ecm.get("artifact_id")!=10298635300 or ecm.get("deb_sha256")!="ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f": fail("ECM predecessor mismatch")

campaign=m.get("last_campaign",{})
if campaign.get("workflow_run") != 35138333645 or campaign.get("commit") != "6b3a8b9f408c5fff4bceec81ac9ffb3e47a4dbd3": fail("diagnostic campaign evidence mismatch")
results=campaign.get("results",{})
if set(results)!=set(expected): fail("diagnostic campaign result set mismatch")
if {n:results[n].get("result") for n in expected} != {n:"DIAG_PASS" for n in expected}: fail("third diagnostic campaign must be 7/7 DIAG_PASS")
expected_evidence={
 "kconfig":(104936243505,10464074545,"9f05b0e368c4d1a7eb3dbec441680b423fd3f8b4a7fc2a0cdcbf9edbb3ca6e68"),
 "ki18n":(104936243967,10463404553,"86b5f05313d164358ac36e1cc4982b72fad90bad3175114d2b2b493691a6bec3"),
 "sonnet":(104936243844,10464073832,"6b17c7f02213282a520f4127feb010e9a37dbbafce9c8ab17d7f76164b22d7b6"),
 "kirigami":(104936243949,10464419377,"f83a7e508fa2031dcf5401a7590e9598ab3d5888230af60b153c4b77d4b53185"),
 "kquickcharts":(104936243779,10463808939,"5d1023d260fe167d846a8b3f16310c6771bb08f79688095bd27ba5ea79798a28"),
 "kuserfeedback":(104936243847,10463474227,"490be26e6790ac56114948be44e0b068061479e448c1ba1b3ee227c231902d39"),
 "prison":(104936243826,10464172535,"cee0b26d3c3dbad53b0924d8c15cde6b11813863a4e800634a8b9ae2cfdb90b5"),
}
for n,(job,artifact,digest) in expected_evidence.items():
    item=results[n]
    if item.get("job_id")!=job or item.get("artifact_id")!=artifact or item.get("artifact_sha256")!=digest: fail(f"{n}: third campaign evidence mismatch")

workflow=W.read_text(); runner=R.read_text(); selector=S.read_text()
for token in ("fail-fast: false","max-parallel: 7","kconfig, ki18n, sonnet, kirigami, kquickcharts, kuserfeedback, prison",'"${{ matrix.node }}"'):
    if token not in workflow: fail(f"source diagnostic workflow missing {token}")
for token in ("non-promoting-source-diagnostic","DIAG_PASS","DIAG_FAIL","-DBUILD_TESTING=ON","sha256sum --check --strict","provider-surface-validation","qt6-base-private-dev","iso_3166-1.mo","iso_3166-2.mo","REQUIRED_LOCALES","locale -a","TEST_LC_ALL_UNSET","unset LC_ALL","test-environment.txt","upstream-default-validation","cmake --build","ctest --test-dir","cmake --install","_NET_SUPPORTING_WM_CHECK",'"package_gate":False','"dag_state_change":False'):
    if token not in runner: fail(f"source diagnostic runner lost gate {token}")
if "ctest -E" in runner or "--exclude" in runner: fail("source diagnostic must not filter upstream tests")
for token in ("Usage: $0 <before-sha> <after-sha> <node>","last_campaign","nodes","kde-frameworks-tier1-dependencies.json","run-kde-tier1-source-diagnostic.sh"):
    if token not in selector: fail(f"per-node diagnostic selector missing {token}")

print("KDE Tier 1 global source diagnostic policy: PASS")
print("nodes=7; third campaign=7 DIAG_PASS / 0 DIAG_FAIL; package promotion disabled")
