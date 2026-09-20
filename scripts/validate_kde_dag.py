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

kgui = nodes.get("kguiaddons", {})
require(kgui.get("tier") == 1, "KGuiAddons must be a promoted Tier 1 DAG node")
require(kgui.get("upstream_version") == "6.30.0", "KGuiAddons DAG upstream version mismatch")
require(kgui.get("source_sha256") == "e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d", "KGuiAddons DAG source SHA-256 mismatch")
require(kgui.get("depends_on") == ["extra-cmake-modules"], "KGuiAddons DAG build dependency must remain ECM-only")
require(kgui.get("state") == "PASS" and kgui.get("downstream_eligible") is True, "KGuiAddons DAG must be PASS/downstream-eligible")
require(kgui.get("package_version") == "6.30.0-0supralinux2", "KGuiAddons DAG package version mismatch")
require(kgui.get("attempt_ledger") == "manifests/kde-tier1-package-batch8-attempts.json", "KGuiAddons DAG attempt ledger mismatch")
kgui_passes = [item for item in kgui.get("evidence", []) if isinstance(item, dict) and item.get("result") == "PASS"]
require(len(kgui_passes) == 1, "KGuiAddons DAG requires exactly one retained PASS")
if kgui_passes:
    item = kgui_passes[0]
    require(item.get("workflow_run") == 35185562846 and item.get("job_id") == 105086774400, "KGuiAddons DAG PASS run/job mismatch")
    require(item.get("commit") == "de47462c5b6b21bc2c485f5dd2c39035a32f7f45", "KGuiAddons DAG PASS commit mismatch")
    require(item.get("artifact_id") == 10482007092 and item.get("artifact_sha256") == "71d32ecb50f6617ba198325a552e68e995c20c9050c7ae21f6a69d5b680184ca", "KGuiAddons DAG PASS artifact mismatch")
    require(item.get("tests") == "9/9 PASS" and item.get("lintian") == "PASS-errors", "KGuiAddons DAG build/test gate mismatch")
require(kgui.get("pass_files", {}).get("rootfs_sha256") == "c68681aacfd32976c6e0bf471ec1928179fd80e402faf2293706e53f88ad25c6", "KGuiAddons DAG rootfs evidence mismatch")
require(len(nodes) == 31, "Canonical DAG must contain ECM + 29 Tier 1 PASS nodes + promoted KAuth Tier 2")

kauth = nodes.get("kauth", {})
require(kauth.get("tier") == 2 and kauth.get("upstream_version") == "6.30.0", "KAuth promoted Tier 2 identity mismatch")
require(kauth.get("source_sha256") == "60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9", "KAuth DAG source SHA mismatch")
require(kauth.get("depends_on") == ["extra-cmake-modules","kcoreaddons","kwindowsystem"], "KAuth DAG predecessor set mismatch")
require(kauth.get("state") == "PASS" and kauth.get("downstream_eligible") is True, "KAuth DAG must be PASS/downstream-eligible")
require(kauth.get("package_version") == "6.30.0-0supralinux3", "KAuth DAG package version mismatch")
require(kauth.get("attempt_ledger") == "manifests/kde-tier2-package-batch1-attempts.json", "KAuth DAG attempt ledger mismatch")
require(kauth.get("binary_packages") == ["libkf6auth-data","libkf6auth-dev","libkf6auth-dev-bin","libkf6auth-doc","libkf6authcore6"], "KAuth DAG binary package split mismatch")
require(kauth.get("abi_sonames") == ["libKF6AuthCore.so.6"], "KAuth DAG SONAME mismatch")
require(kauth.get("backend_profile") == {"KAUTH_BACKEND_NAME":"POLKITQT6-1","KAUTH_HELPER_BACKEND_NAME":"DBUS"}, "KAuth DAG backend profile mismatch")
kauth_passes = [item for item in kauth.get("evidence", []) if isinstance(item, dict) and item.get("result") == "PASS"]
require(len(kauth_passes) == 1, "KAuth DAG requires exactly one retained PASS")
if kauth_passes:
    item = kauth_passes[0]
    require(item.get("workflow_run") == 35497461178 and item.get("job_id") == 106043001431, "KAuth DAG PASS run/job mismatch")
    require(item.get("commit") == "3f67c5446e56d3029551bb5e481882ad3e208cfa", "KAuth DAG PASS commit mismatch")
    require(item.get("artifact_id") == 10601382235 and item.get("artifact_sha256") == "443a47a67188a52faae6c20b03c2c53203d5a9386dbbb5765af4f69e0cd1744b", "KAuth DAG PASS artifact mismatch")
    require(item.get("tests") == "6/6 PASS" and item.get("lintian") == "PASS-errors", "KAuth DAG test/Lintian gate mismatch")
    require(item.get("consumer_smoke") == "PASS" and item.get("apt_check") == "PASS" and item.get("development_contract") == "PASS", "KAuth DAG consumer/APT/development gates mismatch")
    require(item.get("backend") == "POLKITQT6-1" and item.get("helper_backend") == "DBUS", "KAuth DAG backend evidence mismatch")
    require(item.get("symbols_adjusted_sha256") == "b8cf2fa877c94255f015cee08b89816d538cba23f1064d0360a329189fee0b78", "KAuth DAG adjusted symbols evidence mismatch")
require(kauth.get("pass_files", {}).get("rootfs_sha256") == "15113b108b939e2575758c6696fc34808dfa925fa2dd3cc5e6c13e65e7be4668", "KAuth DAG rootfs evidence mismatch")

batch9_expected = {
    "kconfig": {
        "version":"6.30.0-0supralinux4","sha":"0e98bac324cd716849202d4b246a948e363d6792a8eb09c78417cdde9559f56e",
        "run":35360530830,"job":105650448776,"commit":"bfb02cdc6f6086ed41092cc900563dfa3be86e64",
        "artifact":10554715051,"digest":"bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e",
        "tests":"90/90 PASS","rootfs":"cf14256f216dd3ec9a67a7bca3bd46e8624391ffe40b2c08567dc1fe90a4b9e3",
        "sonames":["libKF6ConfigCore.so.6","libKF6ConfigGui.so.6","libKF6ConfigQml.so.6"],
        "binaries":["libkf6config-bin","libkf6config-data","libkf6config-dev","libkf6config-dev-bin","libkf6config-doc","libkf6configcore6","libkf6configgui6","libkf6configqml6","qml6-module-org-kde-config"],
    },
    "ki18n": {
        "version":"6.30.0-0supralinux1","sha":"dfbfc8af89b3bc68810b094bf87746db87c3eeb35b75caeb1882681ebed563bd",
        "run":35358920602,"job":105645094825,"commit":"1048fd52df303957d2db82c29988c8170b6fd656",
        "artifact":10553916882,"digest":"2a0d66f2760c49ba1128b8b51c741173a72e6f3ab51f3eb17c3584896d30a678",
        "tests":"17/17 PASS","rootfs":"c3a542cadce65b491d0997f7fa61cfabc2b44188a2021c151858349766fd148d",
        "sonames":["libKF6I18n.so.6","libKF6I18nLocaleData.so.6","libKF6I18nQml.so.6"],
        "binaries":["libkf6i18n-data","libkf6i18n-dev","libkf6i18n-doc","libkf6i18n6","libkf6i18nlocaledata6","libkf6i18nqml6","qml6-module-org-kde-i18n-localedata","qml6-module-org-kde-ki18n"],
    },
    "sonnet": {
        "version":"6.30.0-0supralinux3","sha":"1574ef5c17f38e315de104b94580ccc1b7ec1db2650cb4bace2e14159bf61e10",
        "run":35358920602,"job":105645094787,"commit":"1048fd52df303957d2db82c29988c8170b6fd656",
        "artifact":10554216487,"digest":"ae5a33cf8699b96b7b7b8c1a83bc4d37a484878029818c1885b4f4f44f15b431",
        "tests":"8/8 PASS","rootfs":"38f9fcd9dd6cb379bd5ba1fbfb5c93f57b49db71c166615415ff663366fc54bb",
        "sonames":["libKF6SonnetCore.so.6","libKF6SonnetUi.so.6"],
        "binaries":["sonnet6-plugins","libkf6sonnet-data","libkf6sonnet-dev","libkf6sonnet-dev-bin","libkf6sonnet-doc","libkf6sonnetcore6","libkf6sonnetui6","qml6-module-org-kde-sonnet"],
    },
}
for node_id, expected in batch9_expected.items():
    node = nodes.get(node_id, {})
    require(node.get("tier") == 1 and node.get("upstream_version") == "6.30.0", f"{node_id}: promoted Tier 1 identity mismatch")
    require(node.get("source_sha256") == expected["sha"], f"{node_id}: DAG source SHA mismatch")
    require(node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: DAG dependency must remain ECM-only")
    require(node.get("state") == "PASS" and node.get("downstream_eligible") is True, f"{node_id}: DAG must be PASS/downstream-eligible")
    require(node.get("package_version") == expected["version"], f"{node_id}: DAG package version mismatch")
    require(node.get("attempt_ledger") == "manifests/kde-tier1-package-batch9-attempts.json", f"{node_id}: DAG attempt ledger mismatch")
    require(node.get("binary_packages") == expected["binaries"], f"{node_id}: DAG binary package split mismatch")
    require(node.get("abi_sonames") == expected["sonames"], f"{node_id}: DAG multi-ABI SONAME set mismatch")
    passes = [item for item in node.get("evidence", []) if isinstance(item, dict) and item.get("result") == "PASS"]
    require(len(passes) == 1, f"{node_id}: DAG requires exactly one retained current PASS")
    if passes:
        item = passes[0]
        require(item.get("workflow_run") == expected["run"] and item.get("job_id") == expected["job"], f"{node_id}: DAG PASS run/job mismatch")
        require(item.get("commit") == expected["commit"], f"{node_id}: DAG PASS commit mismatch")
        require(item.get("artifact_id") == expected["artifact"] and item.get("artifact_sha256") == expected["digest"], f"{node_id}: DAG PASS artifact mismatch")
        require(item.get("tests") == expected["tests"] and item.get("lintian") == "PASS-errors", f"{node_id}: DAG test/Lintian gate mismatch")
        require(item.get("consumer_smoke") == "PASS" and item.get("apt_check") == "PASS" and item.get("qml_import_smoke") == "PASS", f"{node_id}: DAG runtime/QML gates mismatch")
        require(item.get("abi_sonames") == expected["sonames"], f"{node_id}: DAG PASS ABI SONAME evidence mismatch")
    require(node.get("pass_files", {}).get("rootfs_sha256") == expected["rootfs"], f"{node_id}: DAG rootfs evidence mismatch")

batch10_expected = {
    "kirigami": {
        "version":"6.30.0-0supralinux2","sha":"6de811e559c20dc1086c0cf2c34bb98712dbe4d45f960c62c3c3f887332c95f8",
        "run":35398956698,"job":105774229788,"commit":"25af7164a76a925f27814aabe1986727a53d49bf",
        "artifact":10569258322,"digest":"6a008366edda84f8c285e5cf0a6b18a4b1089fc88e530d6e61b0f4f885dd7e30",
        "tests":"44/44 PASS","rootfs":"8a1e3d09d8788ad38c81cb7071f7149c114f3582ee3c59d489114c3b81497a35",
        "sonames":["libKirigami.so.6","libKirigamiControls.so.6","libKirigamiDelegates.so.6","libKirigamiDialogs.so.6","libKirigamiForms.so.6","libKirigamiFormsPrivateCards.so.6","libKirigamiFormsPrivateFlat.so.6","libKirigamiFormsPrivateTemplates.so.6","libKirigamiLayouts.so.6","libKirigamiLayoutsPrivate.so.6","libKirigamiPlatform.so.6","libKirigamiPolyfill.so.6","libKirigamiPrimitives.so.6","libKirigamiPrivate.so.6","libKirigamiTemplates.so.6"],
        "binaries":["libkirigami-data","libkirigami-dev","libkirigami-doc","libkirigami6","libkirigamicontrols6","libkirigamidelegates6","libkirigamidialogs6","libkirigamiforms6","libkirigamiformsprivatecards6","libkirigamiformsprivateflat6","libkirigamiformsprivatetemplates6","libkirigamilayouts6","libkirigamilayoutsprivate6","libkirigamiplatform6","libkirigamipolyfill6","libkirigamiprimitives6","libkirigamiprivate6","libkirigamitemplates6","qml6-module-org-kde-kirigami"],
    },
    "kquickcharts": {
        "version":"6.30.0-0supralinux4","sha":"9fe8c0c78ffd23ccfb99cc36477550a229c114ad057def938f38cdec35f82ab1",
        "run":35409521636,"job":105806202814,"commit":"43adf80f4a16a848f1ca7ea77fc608585ddb6345",
        "artifact":10573605864,"digest":"dc233607ea647780580405b49e8b12855af5aaaf3b2d2bfea50c75fe7ed91780",
        "tests":"8/8 PASS","rootfs":"b1e79e0fbc11672c017acc812efa74116f1681a56596deb87f0f770b47e3d01d",
        "sonames":["libQuickCharts.so.1","libQuickChartsControls.so.1"],
        "binaries":["libquickcharts-dev","libquickcharts1","libquickchartscontrols1","qml6-module-org-kde-quickcharts"],
    },
}
for node_id, expected in batch10_expected.items():
    node = nodes.get(node_id, {})
    require(node.get("tier") == 1 and node.get("upstream_version") == "6.30.0", f"{node_id}: Batch 10 promoted Tier 1 identity mismatch")
    require(node.get("source_sha256") == expected["sha"], f"{node_id}: Batch 10 DAG source SHA mismatch")
    require(node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: Batch 10 DAG dependency must remain ECM-only")
    require(node.get("state") == "PASS" and node.get("downstream_eligible") is True, f"{node_id}: Batch 10 DAG must be PASS/downstream-eligible")
    require(node.get("package_version") == expected["version"], f"{node_id}: Batch 10 DAG package version mismatch")
    require(node.get("attempt_ledger") == "manifests/kde-tier1-package-batch10-attempts.json", f"{node_id}: Batch 10 DAG attempt ledger mismatch")
    require(node.get("binary_packages") == expected["binaries"], f"{node_id}: Batch 10 DAG binary package split mismatch")
    require(node.get("abi_sonames") == expected["sonames"], f"{node_id}: Batch 10 DAG ABI SONAME set mismatch")
    passes = [item for item in node.get("evidence", []) if isinstance(item, dict) and item.get("result") == "PASS"]
    require(len(passes) == 1, f"{node_id}: Batch 10 DAG requires exactly one retained current PASS")
    if passes:
        item = passes[0]
        require(item.get("workflow_run") == expected["run"] and item.get("job_id") == expected["job"], f"{node_id}: Batch 10 DAG PASS run/job mismatch")
        require(item.get("commit") == expected["commit"], f"{node_id}: Batch 10 DAG PASS commit mismatch")
        require(item.get("artifact_id") == expected["artifact"] and item.get("artifact_sha256") == expected["digest"], f"{node_id}: Batch 10 DAG PASS artifact mismatch")
        require(item.get("tests") == expected["tests"] and item.get("lintian") == "PASS-errors", f"{node_id}: Batch 10 DAG test/Lintian gate mismatch")
        require(item.get("consumer_smoke") == "PASS" and item.get("apt_check") == "PASS" and item.get("qml_import_smoke") == "PASS", f"{node_id}: Batch 10 DAG runtime/QML gates mismatch")
        require(item.get("abi_sonames") == expected["sonames"], f"{node_id}: Batch 10 DAG PASS ABI SONAME evidence mismatch")
        require(item.get("ecm_predecessor") == "6.30.0-0supralinux3", f"{node_id}: Batch 10 ECM predecessor mismatch")
    require(node.get("pass_files", {}).get("rootfs_sha256") == expected["rootfs"], f"{node_id}: Batch 10 DAG rootfs evidence mismatch")


batch11_expected = {
    "kuserfeedback": {
        "version":"6.30.0-0supralinux5","sha":"c8a463c8e570f6d532cbe150732220575c6385df97c91399b6c84450691771ca",
        "run":35489771315,"job":106022610412,"commit":"69d271891f96f75ada404623611ffa42bc061090",
        "artifact":10597923863,"digest":"0a057d591a198f74cf6eee24d3b1ef4355f2a0d6073d48de8e220ac37f0a38b7",
        "tests":"15/15 PASS","rootfs":"8b5518bea1704ffb9830b4d9a3259e2655ca69efb6dff108b9a9709e66d87e39",
        "sonames":["libKF6UserFeedbackCore.so.6","libKF6UserFeedbackWidgets.so.6"],
        "binaries":["libkf6userfeedback-data","libkf6userfeedback-dev","libkf6userfeedback-doc","libkf6userfeedbackcore6","libkf6userfeedbackwidgets6","qml6-module-org-kde-userfeedback"],
    },
    "prison": {
        "version":"6.30.0-0supralinux1","sha":"2cdb0a2689ab45b907c76c9a01c1dc14855b8e5329ad0a9cf65c1ad64e5fed1b",
        "run":35488901554,"job":106020266290,"commit":"7f4a42af54c4d3a1603f9b7cca95a5b45786ff58",
        "artifact":10597829797,"digest":"f0074c8da29cfda08018fa568fce9cabbf6fc23669416caf20c714c25ff7773f",
        "tests":"9/9 PASS","rootfs":"a1ae6cb653ec18a6dba7142f4ee5acd94210076a9adba23d9d67d03ac03885e7",
        "sonames":["libKF6Prison.so.6","libKF6PrisonScanner.so.6"],
        "binaries":["libkf6prison-dev","libkf6prison-doc","libkf6prison6","libkf6prisonscanner6","qml6-module-org-kde-prison"],
    },
}
for node_id, expected in batch11_expected.items():
    node = nodes.get(node_id, {})
    require(node.get("tier") == 1 and node.get("upstream_version") == "6.30.0", f"{node_id}: Batch 11 promoted Tier 1 identity mismatch")
    require(node.get("source_sha256") == expected["sha"], f"{node_id}: Batch 11 DAG source SHA mismatch")
    require(node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: Batch 11 DAG dependency must remain ECM-only")
    require(node.get("state") == "PASS" and node.get("downstream_eligible") is True, f"{node_id}: Batch 11 DAG must be PASS/downstream-eligible")
    require(node.get("package_version") == expected["version"], f"{node_id}: Batch 11 DAG package version mismatch")
    require(node.get("attempt_ledger") == "manifests/kde-tier1-package-batch11-attempts.json", f"{node_id}: Batch 11 DAG attempt ledger mismatch")
    require(node.get("binary_packages") == expected["binaries"], f"{node_id}: Batch 11 DAG binary package split mismatch")
    require(node.get("abi_sonames") == expected["sonames"], f"{node_id}: Batch 11 DAG ABI SONAME set mismatch")
    passes = [item for item in node.get("evidence", []) if isinstance(item, dict) and item.get("result") == "PASS"]
    require(len(passes) == 1, f"{node_id}: Batch 11 DAG requires exactly one retained PASS")
    if passes:
        item = passes[0]
        require(item.get("workflow_run") == expected["run"] and item.get("job_id") == expected["job"], f"{node_id}: Batch 11 DAG PASS run/job mismatch")
        require(item.get("commit") == expected["commit"], f"{node_id}: Batch 11 DAG PASS commit mismatch")
        require(item.get("artifact_id") == expected["artifact"] and item.get("artifact_sha256") == expected["digest"], f"{node_id}: Batch 11 DAG PASS artifact mismatch")
        require(item.get("tests") == expected["tests"] and item.get("lintian") == "PASS-errors", f"{node_id}: Batch 11 test/Lintian gate mismatch")
        require(item.get("consumer_smoke") == "PASS" and item.get("apt_check") == "PASS" and item.get("qml_import_smoke") == "PASS" and item.get("development_contract") == "PASS", f"{node_id}: Batch 11 runtime/QML/development gates mismatch")
        require(item.get("abi_sonames") == expected["sonames"], f"{node_id}: Batch 11 PASS ABI SONAME evidence mismatch")
    require(node.get("pass_files", {}).get("rootfs_sha256") == expected["rootfs"], f"{node_id}: Batch 11 DAG rootfs evidence mismatch")

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
