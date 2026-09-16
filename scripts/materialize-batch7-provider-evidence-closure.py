#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/kde-frameworks-tier1-dependencies.json"
VALIDATOR = ROOT / "scripts/validate_kde_tier1.py"
DOC = ROOT / "docs/kde-tier1-dependencies.md"
STATUS = ROOT / "docs/status/2026-09-16-batch7.md"

NEW_EVIDENCE = {
    "workflow_run": 35087361837,
    "job_id": 104765243282,
    "head_sha": "a60cf80e2adae2f40c994c8ca8e661d23822b0b6",
    "artifact_id": 10442512801,
    "artifact_sha256": "49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9",
    "manifest_sha256": "ccf4ff9fc8e4227787208fd4950812b0244552ab3463e58aae41df424842b2a8",
    "authoritative": False,
    "claim": "provider-availability-only",
    "python_build": {
        "package": "python3-build",
        "package_version": "1.4.0-1",
        "module": "build",
        "module_version": "1.4.0",
        "import_status": "PASS",
    },
    "qt_upstream": "6.10.2",
}

# Promote only the provider evidence. The dependency contract itself is unchanged
# from the preceding python3-build mapping commit.
m = json.loads(MANIFEST.read_text(encoding="utf-8"))
p = m["provider_candidate"]
if p.get("status") not in {"revalidation-pending", "hosted-preflight-pass"}:
    raise SystemExit(f"unexpected provider transition state: {p.get('status')}")
p["status"] = "hosted-preflight-pass"
p["evidence"] = NEW_EVIDENCE
p.setdefault("previous_evidence", {
    "workflow_run":34700048774,
    "head_sha":"6ce61bc02c4aba146bcc33b16d17f56fb66f057a",
    "artifact_id":10299608166,
    "artifact_sha256":"da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3",
    "authoritative":False,
    "claim":"provider-availability-only",
})
r = p.setdefault("revalidation", {})
r["status"] = "PASS"
r["validated_by"] = NEW_EVIDENCE
MANIFEST.write_text(json.dumps(m, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")

# Validator now requires the real closure evidence while retaining discovery and
# previous broad-provider evidence.
v = VALIDATOR.read_text(encoding="utf-8")
constant_anchor = "EXPECTED_PROVIDER_PREVIOUS_EVIDENCE = {'workflow_run':34700048774,'head_sha':'6ce61bc02c4aba146bcc33b16d17f56fb66f057a','artifact_id':10299608166,'artifact_sha256':'da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3','authoritative':False,'claim':'provider-availability-only'}"
constant_new = constant_anchor + "\nEXPECTED_PROVIDER_CURRENT_EVIDENCE = {'workflow_run':35087361837,'job_id':104765243282,'head_sha':'a60cf80e2adae2f40c994c8ca8e661d23822b0b6','artifact_id':10442512801,'artifact_sha256':'49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9','manifest_sha256':'ccf4ff9fc8e4227787208fd4950812b0244552ab3463e58aae41df424842b2a8','authoritative':False,'claim':'provider-availability-only','python_build':{'package':'python3-build','package_version':'1.4.0-1','module':'build','module_version':'1.4.0','import_status':'PASS'},'qt_upstream':'6.10.2'}"
if "EXPECTED_PROVIDER_CURRENT_EVIDENCE" not in v:
    if constant_anchor not in v:
        raise SystemExit("provider evidence constant anchor missing")
    v = v.replace(constant_anchor, constant_new, 1)
old_block = """require(provider.get('status') == 'revalidation-pending', 'Provider candidate must remain revalidation-pending until python3-build evidence passes')
require(provider.get('previous_evidence') == EXPECTED_PROVIDER_PREVIOUS_EVIDENCE, 'Previous provider evidence must be retained')
require(provider.get('revalidation', {}).get('discovered_by', {}).get('workflow_run') == 35054417698, 'python3-build discovery run must be retained')
require(provider.get('revalidation', {}).get('discovered_by', {}).get('artifact_sha256') == '86cd447eab87f42d088ba6569529b15012d26084f0974456651b143786a64fa8', 'python3-build discovery artifact digest must be retained')"""
new_block = """require(provider.get('status') == 'hosted-preflight-pass', 'Provider candidate must be hosted-preflight-pass after python3-build revalidation')
require(provider.get('previous_evidence') == EXPECTED_PROVIDER_PREVIOUS_EVIDENCE, 'Previous provider evidence must be retained')
require(provider.get('evidence') == EXPECTED_PROVIDER_CURRENT_EVIDENCE, 'Current provider revalidation evidence changed unexpectedly')
require(provider.get('revalidation', {}).get('status') == 'PASS', 'python3-build provider revalidation must be PASS')
require(provider.get('revalidation', {}).get('validated_by') == EXPECTED_PROVIDER_CURRENT_EVIDENCE, 'python3-build validated_by evidence must match current evidence')
require(provider.get('revalidation', {}).get('discovered_by', {}).get('workflow_run') == 35054417698, 'python3-build discovery run must be retained')
require(provider.get('revalidation', {}).get('discovered_by', {}).get('artifact_sha256') == '86cd447eab87f42d088ba6569529b15012d26084f0974456651b143786a64fa8', 'python3-build discovery artifact digest must be retained')"""
if new_block not in v:
    if old_block not in v:
        raise SystemExit("provider validator transition block missing")
    v = v.replace(old_block, new_block, 1)
VALIDATOR.write_text(v, encoding="utf-8")

# Primary dependency documentation: current state must now say PASS and record
# the exact revalidation evidence.
d = DOC.read_text(encoding="utf-8")
d = d.replace(
    "Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping updated for ECM Python bindings; hosted provider revalidation pending; 18 package nodes PASS; 11 package nodes pending**",
    "Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping validated for ECM Python bindings; hosted provider preflight PASS; 18 package nodes PASS; 11 package nodes pending**",
    1,
)
d = d.replace(
    "The mapping is therefore corrected and provider revalidation is pending; Python bindings are not disabled to hide the omission.",
    "The mapping was corrected without disabling Python bindings. Real revalidation then passed in run `35087361837`, job `104765243282`, artifact `10442512801`, ZIP SHA-256 `49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9`: Resolute installed `python3-build 1.4.0-1`, `import build` reported module version `1.4.0`, and the existing PySide6/Shiboken6 checks remained aligned to Qt `6.10.2`. This is provider-availability evidence only, not a Framework package PASS.",
    1,
)
provider_marker = "Current targeted evidence for the corrected ModemManager provider mapping:\n"
insert = """Current provider revalidation for ECM Python bindings:\n\n- run `35087361837`;\n- job `104765243282`;\n- commit `a60cf80e2adae2f40c994c8ca8e661d23822b0b6`;\n- artifact `10442512801`;\n- artifact SHA-256 `49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9`;\n- `python3-build 1.4.0-1`, Python module `build 1.4.0`: PASS;\n- PySide6/Shiboken6 remain aligned to Qt `6.10.2`;\n- result: PASS; provider-availability evidence only.\n\n"""
if insert not in d:
    if provider_marker not in d:
        raise SystemExit("provider evidence documentation anchor missing")
    d = d.replace(provider_marker, insert + provider_marker, 1)
DOC.write_text(d, encoding="utf-8")

STATUS.write_text("""# SupraLINUX status — 2026-09-16 — Tier 1 Batch 7 preparation

Status: **provider mapping revalidated PASS; Batch 7 packaging preparation active**

Canonical KDE Frameworks Tier 1 remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. No Batch 7 Framework package has been promoted yet.

## Stable authority snapshot

The official stable snapshot was revalidated on 2026-09-16 before Batch 7 work: KDE Frameworks `6.30.0`, Plasma `6.7.5`, KDE Gear `26.08.1`. Plasma 6.8 remains pre-release and does not replace the selected stable Plasma.

## Batch 7 selection

The independent package candidates are **KCalendarCore, KCoreAddons and KWidgetsAddons**. Their KDE 6.30 Linux/shared-library defaults keep Python bindings enabled; KWidgetsAddons also keeps its Designer plugin and upstream tests enabled. SupraLINUX does not inherit downstream `BUILD_PYTHON_BINDINGS=OFF` or `BUILD_TESTING=OFF` choices merely for packaging convenience.

KGuiAddons is deliberately deferred to the next package level. Although upstream classifies it as Tier 1 for Framework build dependencies, its public KImageCache development surface includes `kshareddatacache.h`; the resulting `-dev` package contract requires KCoreAddons. Under the SupraLINUX DAG rule, only a retained local PASS artifact may feed that dependent package.

## Python build-provider discovery and correction

Upstream-layout probe run `35054417698`, job `104661454268`, artifact `10429918034`, ZIP SHA-256 `86cd447eab87f42d088ba6569529b15012d26084f0974456651b143786a64fa8`, reached KCalendarCore configuration with Python 3.14, Shiboken6 6.10.2 and PySide6 6.10.2 available, then failed because ECM 6.30 `ECMGeneratePythonBindings` could not import Python module `build`.

Classification: `provider-mapping-omission`; package-state effect: **none**. No Framework package attempt occurred, so this is not a Framework FAIL.

The provider mapping now includes `python-build -> python3-build` for KCalendarCore, KCoreAddons, KGuiAddons and KWidgetsAddons. Real Resolute revalidation passed in run `35087361837`, job `104765243282`, commit `a60cf80e2adae2f40c994c8ca8e661d23822b0b6`, artifact `10442512801`, SHA-256 `49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9`. The evidence records `python3-build 1.4.0-1`, module `build 1.4.0` import PASS, and Qt/PySide/Shiboken alignment at `6.10.2`.

This remains non-authoritative hosted provider evidence. Actual Batch 7 package PASS still requires clean Resolute sbuild, upstream tests, Lintian, ABI/SONAME checks, C++ consumer smoke and Python import smoke for the locally built artifacts.

## Dependency-preflight scope policy

Provider evidence/status and documentation are not build inputs. The dependency-preflight selector therefore uses a semantic fingerprint containing only the consumed provider contract: Framework/target identity, provider distribution/series, common minima, Qt provider packages, requirements and per-node dependency profiles. Changes to that contract or to the provider runner/workflow trigger the expensive preflight; evidence-only, status-only, validator-only and documentation-only changes do not.

Repository Policy carries a functional test proving both sides of this contract: evidence-only/docs-only deltas scope-skip, while provider-contract and provider-runner changes trigger execution.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
""", encoding="utf-8")
