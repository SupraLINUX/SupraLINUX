#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
errors: list[str] = []

def req(value, message):
    if not value:
        errors.append(message)

def load(path):
    return json.loads((R / path).read_text())

def txt(path):
    return (R / path).read_text()

c = load("manifests/kde-tier1-package-campaign-batch7.json")
t = load("manifests/kde-frameworks-tier1.json")
d = load("manifests/kde-dag.json")
tier = {x["id"]: x for x in t["nodes"]}
dag = d["nodes"]
selected = ["kcalendarcore", "kcoreaddons", "kwidgetsaddons"]

req(c.get("schema") == 1, "campaign schema")
req(c.get("batch") == "tier1-batch-7", "campaign id")
req(c.get("state") == "remediation-pending-build", "campaign remediation state")
req(c.get("authority") == "kde-upstream" and c.get("frameworks_series") == "6.30.0", "authority/version")
req(c.get("selected_nodes") == selected, "selected nodes/order")
req(c.get("canonical_snapshot") == {
    "state": "unpromoted-open-batch",
    "tier1": "18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED",
}, "canonical snapshot")

counts = {s: sum(x.get("state") == s for x in t["nodes"]) for s in ("PASS", "pending", "FAIL", "BLOCKED")}
req(counts == {"PASS": 18, "pending": 11, "FAIL": 0, "BLOCKED": 0}, f"Tier1 counts {counts}")

probe = c["shared_predecessors"]["upstream_layout_probe"]
req(probe.get("status") == "PASS" and probe.get("workflow_run") == 35086226149 and probe.get("job_id") == 104761571679, "layout probe identity")
req(probe.get("artifact_id") == 10443202060 and probe.get("artifact_sha256") == "c50a32b26e18ee84173b5a00cbd85e0c2b380660be9d939eb489c370f1317e77", "layout probe artifact")
req(probe.get("verified_defaults", {}).get("BUILD_PYTHON_BINDINGS") == "ON" and probe["verified_defaults"].get("BUILD_TESTING") == "ON", "layout defaults")

provider = c["shared_predecessors"]["dependency_provider"]
req(provider.get("status") == "PASS" and provider.get("workflow_run") == 35087361837 and provider.get("job_id") == 104765243282, "base provider evidence identity")
req(provider.get("artifact_id") == 10442512801 and provider.get("artifact_sha256") == "49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9", "base provider artifact")
req(provider.get("python_build", {}).get("import_status") == "PASS", "python build frontend provider")

backend = c["shared_predecessors"]["python_wheel_backend_provider"]
req(backend.get("status") == "PASS", "wheel backend provider status")
req(backend.get("workflow_run") == 35106561251 and backend.get("job_id") == 104829186807, "wheel backend provider identity")
req(backend.get("commit") == "78760b565dd49e981fa0891535da289120b40470", "wheel backend provider commit")
req(backend.get("artifact_id") == 10450572112, "wheel backend artifact id")
req(backend.get("artifact_sha256") == "488592048a0514b8f6234e8820c959817a151782fef41c138b71f7a8b7fe8fc4", "wheel backend artifact hash")
req(backend.get("authoritative") is False and backend.get("claim") == "provider-availability-only", "wheel backend provider claim")
req(backend.get("package") == "python3-setuptools" and backend.get("version") == "78.1.1-0.1build1", "setuptools provider/version")
req(backend.get("backend_module") == "setuptools.build_meta" and backend.get("backend_import_status") == "PASS", "setuptools backend import")

py = c["shared_packaging_inputs"]["python_policy"]
req(py.get("environment") == "DEB_PYTHON_INSTALL_LAYOUT=deb" and py.get("install_layout") == "deb_system", "python install policy")
req(py.get("build_bindings") is True and py.get("tests_enabled") is True and py.get("runtime_smoke") == "import-module", "python gates")

toolchain = c["shared_packaging_inputs"]["python_binding_toolchain"]
req(toolchain.get("status") == "validated" and toolchain.get("validated_by_run") == 35103681715, "Clang binding toolchain validation")
req(toolchain.get("build_depends") == ["clang", "libclang-dev", "llvm-dev"], "binding toolchain dependency set")
req(toolchain.get("discovered_by_run") == 35102198701, "binding toolchain discovery run")

wheel = c["shared_packaging_inputs"]["python_wheel_backend"]
req(wheel.get("status") == "PASS", "wheel backend contract status")
req(wheel.get("discovered_by_run") == 35103681715, "wheel backend discovery run")
req(wheel.get("build_depends") == ["python3-setuptools"], "wheel backend Build-Depends")
req(wheel.get("provider_workflow_run") == 35106561251 and wheel.get("provider_job_id") == 104829186807, "wheel backend provider proof")
req(wheel.get("backend_module") == "setuptools.build_meta" and wheel.get("backend_import_status") == "PASS", "wheel backend import proof")

expected = {
    "kcalendarcore": {
        "soname": "libKF6CalendarCore.so.6",
        "pypkg": "python3-kcalendarcore",
        "pymod": "KCalendarCore",
        "first": (104814147716, 10448034196, "c76b9900d622e5ae4ab5823771baeabcbe8e2e180811ed01ac18d42b99f792e4", "bf2f0a5c3e9ac32396439474c12dc3d8528622b626d2adcc8056e5f288bef970"),
        "second": (104819252283, 10449348134, "5e24d94981c060541e008c81ef6e76e3f785b5e52fe249206aa117920c9d7040", "dd795df9c016d6df5649d2bae706bb20704488d3bac5158ef8cd5040a68e8e29"),
    },
    "kcoreaddons": {
        "soname": "libKF6CoreAddons.so.6",
        "pypkg": "python3-kcoreaddons",
        "pymod": "KCoreAddons",
        "first": (104814147979, 10449051854, "d7943a390efd8610cdab14422085c6c534f0d5877ece6910f36d8a01288acba7", "350c778059425e3a06383b52d868440396e352b57b9afcb56474287a48f534cd"),
        "second": (104819252182, 10449846512, "17df43995650455389ee2f0d565ed966dd536abaeaf6f56bb44877c762c478af", "2005a540537cd84e6153502b5d8b781dd6728ec2fee46297a2a62896ab8e936e"),
    },
    "kwidgetsaddons": {
        "soname": "libKF6WidgetsAddons.so.6",
        "pypkg": "python3-kwidgetsaddons",
        "pymod": "KWidgetsAddons",
        "first": (104814148006, 10448668591, "227370b1da6151ed68155e2dfc65252db77f68e6ec03ee8f5737550709c8b995", "5e4efab6af0773d306e543a6f9089927881d1281efb017ccd8973587692e4e3d"),
        "second": (104819252378, 10449886366, "0ded038e3a2b7cac8bc94dc5eb61e8183cc1cdcc45284d0040ddbc4ee9670760", "cf6853445e63401a9066fa17db7bf2c23407bafe4cf3bf54f4f262700fa4aefd"),
    },
}

for n, spec in expected.items():
    x = c["nodes"][n]
    ver = "6.30.0-0supralinux3"
    req(x.get("state") == "remediation-pending-build" and x.get("last_result") == "FAIL", f"{n} remediation state")
    req(x.get("downstream_eligible") is False, f"{n} downstream eligibility")
    req(x.get("package_version") == ver and x.get("soname") == spec["soname"], f"{n} version/soname")
    req(x.get("python_package") == spec["pypkg"] and x.get("python_module") == spec["pymod"], f"{n} python contract")
    req(x.get("upstream_defaults", {}).get("BUILD_PYTHON_BINDINGS") == "ON" and x["upstream_defaults"].get("BUILD_TESTING") == "ON", f"{n} upstream defaults")
    if n == "kwidgetsaddons":
        req(x["upstream_defaults"].get("BUILD_DESIGNERPLUGIN") == "ON", "kwidgetsaddons designer default")
    req(tier[n].get("state") == "pending", f"{n} Tier1 must remain pending")
    req(n not in dag, f"{n} absent from promoted package DAG")

    evidence = x.get("evidence", [])
    req(len(evidence) == 2, f"{n} must retain two FAIL attempts")
    if len(evidence) == 2:
        e1, e2 = evidence
        j1, a1, h1, r1 = spec["first"]
        req(e1.get("result") == "FAIL" and e1.get("workflow_run") == 35102198701 and e1.get("job_id") == j1, f"{n} attempt1 identity")
        req(e1.get("commit") == "f4e1754a348f56e2a47c69cf334a12bba3d4338d" and e1.get("attempted_package_version") == "6.30.0-0supralinux1", f"{n} attempt1 revision")
        req(e1.get("artifact_id") == a1 and e1.get("artifact_sha256") == h1 and e1.get("rootfs_sha256") == r1, f"{n} attempt1 evidence")
        req(e1.get("failure_substage") == "python-bindings/clang-builtins-unavailable", f"{n} attempt1 classification")

        j2, a2, h2, r2 = spec["second"]
        req(e2.get("result") == "FAIL" and e2.get("workflow_run") == 35103681715 and e2.get("job_id") == j2, f"{n} attempt2 identity")
        req(e2.get("commit") == "1c950b3352631fa723456ace5de71c6f8cb973f8" and e2.get("attempted_package_version") == "6.30.0-0supralinux2", f"{n} attempt2 revision")
        req(e2.get("artifact_id") == a2 and e2.get("artifact_sha256") == h2 and e2.get("rootfs_sha256") == r2, f"{n} attempt2 evidence")
        req(e2.get("failure_stage") == "sbuild" and e2.get("failure_substage") == "python-wheel/setuptools-backend-unavailable", f"{n} attempt2 classification")
        req("setuptools.build_meta" in e2.get("cause", "") and "BackendUnavailable" in e2.get("cause", ""), f"{n} attempt2 cause")

    remediation = x.get("remediation", {})
    req(remediation.get("candidate_package_version") == ver and remediation.get("status") == "remediation-pending-build", f"{n} remediation version/state")
    req(remediation.get("source_change") is False, f"{n} source unchanged")
    changes = "\n".join(remediation.get("changes", []))
    req("python3-setuptools" in changes and "setuptools.build_meta" in changes, f"{n} setuptools remediation")

    base = R / "packages" / "kde" / n / "debian"
    for f in ("control", "rules", "changelog", "README.source", "copyright.reference", x["symbols"]["file"] + ".reference", "source/format", "upstream/signing-key.asc"):
        req((base / f).is_file(), f"{n} missing {f}")

    rules = (base / "rules").read_text()
    req("DEB_PYTHON_INSTALL_LAYOUT = deb" in rules, f"{n} Debian Python layout")
    req("-DBUILD_PYTHON_BINDINGS=ON" in rules and "-DBUILD_TESTING=ON" in rules, f"{n} Python/tests fail-closed")
    req("BUILD_TESTING=OFF" not in rules and "BUILD_PYTHON_BINDINGS=OFF" not in rules, f"{n} no feature disable")
    if n == "kwidgetsaddons":
        req("-DBUILD_DESIGNERPLUGIN=ON" in rules, "kwidgetsaddons designer rule")

    control = (base / "control").read_text()
    for token in ("dh-sequence-python3", "python3-build", "python3-setuptools", "python3-dev", "libshiboken6-dev", "libpyside6-dev", "clang,", "libclang-dev,", "llvm-dev,", f"Package: {spec['pypkg']}"):
        req(token in control, f"{n} control missing {token}")
    for token in ("clang", "libclang-dev", "llvm-dev", "python3-setuptools"):
        req(token in x.get("build_profile_tokens", []), f"{n} manifest build profile missing {token}")

    req(ver in (base / "changelog").read_text().splitlines()[0], f"{n} changelog revision")
    req(f"usr/lib/python3/dist-packages/{spec['pymod']}*.so" in (base / f"{spec['pypkg']}.install").read_text(), f"{n} python install path")
    devinstall = (base / f"{x['development_package']}.install").read_text()
    req("usr/include/PySide6/" in devinstall and "usr/share/PySide6/typesystems/" in devinstall, f"{n} exported PySide metadata")

req(tier["kguiaddons"].get("state") == "pending" and "kguiaddons" not in dag, "KGuiAddons remains pending")
reason = c["selection_rationale"]["deferred"].get("kguiaddons", "")
req("KCoreAddons" in reason and "PASS" in reason, "KGuiAddons deferral reason")

runner = txt("scripts/run-kde-tier1-package-batch7-preflight.sh")
for token in ("100% tests passed, 0 tests failed out of", "python-import-smoke", "import_module", "apt-get check", "lintian --fail-on error", "LD_LIBRARY_PATH", "DEB_PYTHON_INSTALL_LAYOUT"):
    req(token in runner, f"runner missing {token}")

scope = txt("scripts/kde-tier1-package-batch7-needed.sh")
req("kcalendarcore|kcoreaddons|kwidgetsaddons" in scope and "run-kde-tier1-package-batch7-preflight.sh" in scope, "scope selector")
wf = txt(".github/workflows/kde-tier1-package-batch7.yml")
req("node: [kcalendarcore, kcoreaddons, kwidgetsaddons]" in wf and "fail-fast: false" in wf and "max-parallel: 3" in wf, "workflow matrix/DAG")
req("10298635300" in wf and "10301938362" in wf, "retained inputs")

for path in (
    "docs/kde-tier1-package-batch7.md",
    "docs/status/2026-09-16-batch7.md",
    "docs/decisions/python-build-backend-provider-2026-09-16.md",
    "docs/status/2026-09-16-batch7-python-backend.md",
):
    s = txt(path)
    req("35103681715" in s, f"{path}: second attempt evidence")
    req("35106561251" in s, f"{path}: backend provider PASS evidence")
    req("python3-setuptools" in s and "setuptools.build_meta" in s, f"{path}: backend remediation")
    req("DEB_PYTHON_INSTALL_LAYOUT=deb" in s or "Debian Python" in s, f"{path}: Python layout/contract context")

if errors:
    for e in errors:
        print("ERROR:", e, file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 7 revision -3 preparation: PASS")
print("Selected: KCalendarCore, KCoreAddons, KWidgetsAddons")
print("Retained attempts: run 35102198701 = 3 FAIL; run 35103681715 = 3 FAIL")
print("Backend provider: run 35106561251 PASS, python3-setuptools 78.1.1-0.1build1, setuptools.build_meta import PASS")
print("Candidate revisions: 6.30.0-0supralinux3")
print("Canonical promoted Tier 1 unchanged: 18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED")
