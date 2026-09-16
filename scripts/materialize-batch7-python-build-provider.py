#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / "manifests/kde-frameworks-tier1-dependencies.json"
validator_path = ROOT / "scripts/validate_kde_tier1.py"
runner_path = ROOT / "scripts/run-kde-tier1-dependency-preflight.sh"
doc_path = ROOT / "docs/kde-tier1-dependencies.md"

# 1. Dependency model: ECMGeneratePythonBindings requires the Python 'build' module.
m = json.loads(manifest_path.read_text(encoding="utf-8"))
m["as_of"] = "2026-09-16"
old_provider = m["provider_candidate"]
m["provider_candidate"] = {
    "distribution": "ubuntu",
    "series": "resolute",
    "status": "revalidation-pending",
    "previous_evidence": old_provider["evidence"],
    "revalidation": {
        "reason": "ECM 6.30 ECMGeneratePythonBindings requires the Python build module; provider mapping now includes python3-build.",
        "discovered_by": {
            "workflow_run": 35054417698,
            "job_id": 104661454268,
            "artifact_id": 10429918034,
            "artifact_sha256": "86cd447eab87f42d088ba6569529b15012d26084f0974456651b143786a64fa8",
            "classification": "provider-mapping-omission",
        },
    },
}
m["requirements"]["python-build"] = {
    "name": "Python build frontend",
    "packages": ["python3-build"],
    "provider_note": "KDE ECM 6.30 ECMGeneratePythonBindings executes python -m build --wheel --no-isolation; Ubuntu Resolute provides the required build module through python3-build.",
}
for node_id in ("kcalendarcore", "kcoreaddons", "kguiaddons", "kwidgetsaddons"):
    ext = m["nodes"][node_id].setdefault("external", {})
    values = ext.setdefault("default_enabled", [])
    if "python-build" not in values:
        values.append("python-build")
manifest_path.write_text(json.dumps(m, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

# 2. Global Tier 1 validator: preserve old evidence as historical, require new provider mapping.
v = validator_path.read_text(encoding="utf-8")
old = "EXPECTED_PROVIDER_EVIDENCE = {'distribution':'ubuntu','series':'resolute','status':'hosted-preflight-pass','evidence':{'workflow_run':34700048774,'head_sha':'6ce61bc02c4aba146bcc33b16d17f56fb66f057a','artifact_id':10299608166,'artifact_sha256':'da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3','authoritative':False,'claim':'provider-availability-only'}}"
new = "EXPECTED_PROVIDER_PREVIOUS_EVIDENCE = {'workflow_run':34700048774,'head_sha':'6ce61bc02c4aba146bcc33b16d17f56fb66f057a','artifact_id':10299608166,'artifact_sha256':'da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3','authoritative':False,'claim':'provider-availability-only'}"
if old not in v and new not in v:
    raise SystemExit("validator provider evidence anchor missing")
v = v.replace(old, new, 1)
old = "require(deps.get('provider_candidate') == EXPECTED_PROVIDER_EVIDENCE, 'Provider availability evidence changed unexpectedly')"
new = """provider = deps.get('provider_candidate', {})
require(provider.get('distribution') == 'ubuntu' and provider.get('series') == 'resolute', 'Provider candidate must remain Ubuntu Resolute')
require(provider.get('status') == 'revalidation-pending', 'Provider candidate must remain revalidation-pending until python3-build evidence passes')
require(provider.get('previous_evidence') == EXPECTED_PROVIDER_PREVIOUS_EVIDENCE, 'Previous provider evidence must be retained')
require(provider.get('revalidation', {}).get('discovered_by', {}).get('workflow_run') == 35054417698, 'python3-build discovery run must be retained')
require(provider.get('revalidation', {}).get('discovered_by', {}).get('artifact_sha256') == '86cd447eab87f42d088ba6569529b15012d26084f0974456651b143786a64fa8', 'python3-build discovery artifact digest must be retained')"""
if old not in v and new not in v:
    raise SystemExit("validator provider check anchor missing")
v = v.replace(old, new, 1)
anchor = "require(requirement(deps, 'hspell').get('packages') == ['hspell'], 'HSpell provider mapping must use hspell')"
addition = anchor + "\nrequire(requirement(deps, 'python-build').get('packages') == ['python3-build'], 'Python build provider mapping must use python3-build')\nfor node_id in ('kcalendarcore','kcoreaddons','kguiaddons','kwidgetsaddons'):\n    require('python-build' in dep_nodes[node_id]['external'].get('default_enabled', []), f'{node_id}: default Python bindings require python-build provider')"
if addition not in v:
    if anchor not in v:
        raise SystemExit("validator python-build anchor missing")
    v = v.replace(anchor, addition, 1)
validator_path.write_text(v, encoding="utf-8")

# 3. Hosted provider preflight: prove the importable Python build frontend after APT install.
r = runner_path.read_text(encoding="utf-8")
anchor = "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \"${install_packages[@]}\"\n"
addition = anchor + "\npython3 - <<'PY' > \"${EVIDENCE}/python-build-provider.txt\"\nimport build\nprint(f'module=build')\nprint(f'version={getattr(build, \"__version__\", \"unknown\")}')\nprint('status=PASS')\nPY\n"
if addition not in r:
    if anchor not in r:
        raise SystemExit("dependency preflight install anchor missing")
    r = r.replace(anchor, addition, 1)
runner_path.write_text(r, encoding="utf-8")

# 4. Documentation: distinguish old evidence from the new mapping awaiting revalidation.
d = doc_path.read_text(encoding="utf-8")
d = d.replace(
    "Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping resolved; hosted provider preflight PASS; 18 package nodes PASS; 11 package nodes pending**",
    "Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping updated for ECM Python bindings; hosted provider revalidation pending; 18 package nodes PASS; 11 package nodes pending**",
    1,
)
old = "`kcalendarcore`, `kcoreaddons`, `kguiaddons` and `kwidgetsaddons` enable Python bindings by default on the selected Linux/shared-library paths. Their profile includes Python >= 3.9 development files, Shiboken6 and PySide6. Resolute maps these to `python3-dev`, `libshiboken6-dev` and `libpyside6-dev`.\n\nThe hosted provider PASS verifies that Shiboken6 and PySide6 normalize to the same upstream Qt patch level as the selected Ubuntu Qt candidate: **6.10.2**."
new = "`kcalendarcore`, `kcoreaddons`, `kguiaddons` and `kwidgetsaddons` enable Python bindings by default on the selected Linux/shared-library paths. Their profile includes Python >= 3.9 development files, Shiboken6, PySide6 and the Python `build` frontend used by ECM 6.30 to execute `python -m build --wheel --no-isolation`. Resolute maps these to `python3-dev`, `libshiboken6-dev`, `libpyside6-dev` and `python3-build`.\n\nThe earlier hosted provider PASS verified that Shiboken6 and PySide6 normalize to the same upstream Qt patch level as the selected Ubuntu Qt candidate: **6.10.2**, but it predates the `python3-build` mapping. Batch 7 discovery run `35054417698` (job `104661454268`, artifact `10429918034`, SHA-256 `86cd447eab87f42d088ba6569529b15012d26084f0974456651b143786a64fa8`) reached KCalendarCore configuration with Python/Shiboken/PySide present and failed only because ECM could not import `build`. The mapping is therefore corrected and provider revalidation is pending; Python bindings are not disabled to hide the omission."
if old not in d and new not in d:
    raise SystemExit("dependency documentation Python binding anchor missing")
d = d.replace(old, new, 1)
doc_path.write_text(d, encoding="utf-8")
