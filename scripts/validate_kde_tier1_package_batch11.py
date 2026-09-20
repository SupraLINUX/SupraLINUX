#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def req(value,message):
    if not value:
        errors.append(message)

def text(path):
    return path.read_text(errors="replace")

def js(path):
    return json.loads(path.read_text())

campaign_path=ROOT/"manifests/kde-tier1-package-campaign-batch11.json"
attempts_path=ROOT/"manifests/kde-tier1-package-batch11-attempts.json"
req(campaign_path.is_file(),"Batch 11 campaign missing")
req(attempts_path.is_file(),"Batch 11 attempts ledger missing")
if not campaign_path.is_file() or not attempts_path.is_file():
    print("\n".join(errors),file=sys.stderr)
    raise SystemExit(1)

c=js(campaign_path)
a=js(attempts_path)

req(c.get("schema")==2 and c.get("batch")=="tier1-batch-11" and c.get("lane")=="multi-surface-optional","Batch 11 identity mismatch")
req(c.get("frameworks_series")=="6.30.0" and c.get("authority")=="kde-upstream" and c.get("provider_platform")=="ubuntu-resolute","authority/provider mismatch")
req(c.get("selected_nodes")==["kuserfeedback","prison"],"selected node order mismatch")
req(c.get("canonical_snapshot",{}).get("tier1")=="27 PASS / 2 pending / 0 current FAIL / 0 BLOCKED after Batch 10 canonical promotion","pre-Batch11 snapshot mismatch")

shared=c.get("shared_predecessors",{})
req(shared.get("extra_cmake_modules",{}).get("version")=="6.30.0-0supralinux3","ECM version mismatch")
req(shared.get("extra_cmake_modules",{}).get("artifact_id")==10298635300,"ECM artifact mismatch")
req(shared.get("packaging_trees",{}).get("artifact_id")==10301938362,"packaging-tree artifact mismatch")
req(shared.get("packaging_trees",{}).get("tree_hashes_tsv_sha256")=="abf95096bbc16718102a53a132a576c9f61252d13321c58027325ffb2819c09e","packaging-tree hash manifest mismatch")

for node in ("kuserfeedback","prison"):
    n=c.get("nodes",{}).get(node,{})
    req(n.get("upstream_version")=="6.30.0",f"{node}: upstream version mismatch")
    req(n.get("package_version","").startswith("6.30.0-0supralinux"),f"{node}: package version mismatch")
    req(n.get("kde_framework_build_dependencies")==[],f"{node}: Tier 1 build dependency regression")
    req(n.get("state") in {"prepared-pending-build","remediation-pending-build","FAIL","PASS"},f"{node}: invalid campaign state")
    req(len(n.get("abi_contracts",[]))==2,f"{node}: expected two runtime ABI surfaces")
    req(n.get("expected_test_count",0)>0,f"{node}: exact upstream test count missing")
    if n.get("state")=="PASS":
        req(isinstance(n.get("pass_evidence"),dict),f"{node}: PASS requires pass_evidence")
        req(n.get("downstream_eligible") is True,f"{node}: PASS must be downstream eligible")
    else:
        req(n.get("downstream_eligible") is False,f"{node}: non-PASS must not be downstream eligible")

req(c["nodes"]["kuserfeedback"].get("upstream_defaults")=={
    "ENABLE_SURVEY_TARGET_EXPRESSIONS":"ON",
    "ENABLE_PHP":"ON",
    "ENABLE_PHP_UNIT":"ON",
    "ENABLE_DOCS":"ON",
    "ENABLE_CONSOLE":"OFF",
    "BUILD_TESTING":"ON",
},"KUserFeedback upstream defaults mismatch")
req(c["nodes"]["prison"].get("upstream_defaults")=={
    "WITH_DMTX":"ON",
    "WITH_ZXING":"ON",
    "WITH_QUICK":"ON",
    "WITH_MULTIMEDIA":"ON",
    "BUILD_TESTING":"ON",
},"Prison upstream defaults mismatch")
req({x.get("required_root_module") for x in c["nodes"]["kuserfeedback"].get("qml_contracts",[])}=={"org.kde.userfeedback"},"KUserFeedback QML surface mismatch")
req({x.get("required_root_module") for x in c["nodes"]["prison"].get("qml_contracts",[])}=={"org.kde.prison","org.kde.prison.scanner"},"Prison QML surface mismatch")

req(a.get("schema")==1 and a.get("batch")=="tier1-batch-11" and a.get("lane")=="multi-surface-optional","Batch 11 attempts ledger identity mismatch")
for node in ("kuserfeedback","prison"):
    for attempt in a.get("real_attempts",{}).get(node,[]):
        req(attempt.get("package_attempted") is True and attempt.get("result") in {"PASS","FAIL"},f"{node}: invalid real attempt semantics")
    req(a.get("blocked_events",{}).get(node)==[],f"{node}: independent Batch 11 peer must not create BLOCKED")
for incident in a.get("infrastructure_incidents",[]):
    req(incident.get("package_state_effect")=="none","infrastructure incident must not alter package state")

provider_sets={
    "kuserfeedback":("bison","flex","php","phpunit","qt6-base-dev","qt6-charts-dev","qt6-declarative-dev","qt6-tools-dev"),
    "prison":("libdmtx-dev","libqrencode-dev","libzxing-dev","qt6-base-dev","qt6-declarative-dev","qt6-multimedia-dev"),
}
for node,providers in provider_sets.items():
    control=text(ROOT/f"packages/kde/{node}/debian/control")
    rules=text(ROOT/f"packages/kde/{node}/debian/rules")
    for provider in providers:
        req(provider in control,f"{node}: missing provider {provider}")
    for key,value in c["nodes"][node]["cmake_required_options"].items():
        req(f"-D{key}={value}" in rules,f"{node}: rules missing -D{key}={value}")

runner=text(ROOT/"scripts/run-kde-tier1-package-batch11-preflight.sh")
scope=text(ROOT/"scripts/kde-tier1-package-batch11-needed.sh")
workflow=text(ROOT/".github/workflows/kde-tier1-package-batch11.yml")
for token in (
    "tree-hashes.tsv",
    "tree-files.sha256",
    "source-development-contract",
    "development-contract",
    "feature_required_build_providers",
    "qmlimportscanner",
    "consumer-smoke",
    "sbuild --verbose",
):
    req(token in runner,f"Batch 11 runner missing {token}")
req("fail-fast: false" in workflow and "max-parallel: 2" in workflow and "node: [kuserfeedback, prison]" in workflow,"Batch 11 workflow parallel contract mismatch")
req("packages/kde/${NODE}/*" in scope,"Batch 11 selector package-tree scope missing")

router=text(ROOT/".github/workflows/pr-ci-router.yml")
policy=text(ROOT/".github/workflows/repository-policy.yml")
req("kde-tier1-package-batch11.yml" in router,"PR CI router missing Batch 11")
req("test-kde-tier1-package-batch11-scope.sh" in policy and "validate_kde_tier1_package_batch11.py" in policy,"Repository Policy missing Batch 11 gates")

audit=text(ROOT/"scripts/audit-kde-development-contract.py")
audit_test=text(ROOT/"scripts/test-kde-development-contract-audit.sh")
req("*Target.cmake" in audit and "*Targets.cmake" in audit,"development-contract audit must accept singular and plural KDE target-export file names")
req("KF6FooTarget.cmake" in audit_test,"development-contract audit test must exercise singular Target.cmake")

global_discovery=js(ROOT/"manifests/kde-tier1-global-discovery.json")
lane=global_discovery.get("lanes",{}).get("multi-surface-optional",{})
req(lane.get("status")=="implemented","Batch 11 global-discovery lane must be implemented")
req(set(lane.get("nodes",[]))=={"kuserfeedback","prison"},"Batch 11 lane node set mismatch")
req(lane.get("runner")=="scripts/run-kde-tier1-package-batch11-preflight.sh","Batch 11 lane runner mismatch")
req(lane.get("workflow")==".github/workflows/kde-tier1-package-batch11.yml","Batch 11 lane workflow mismatch")
for node in ("kuserfeedback","prison"):
    req(global_discovery.get("nodes",{}).get(node,{}).get("readiness")=="runnable",f"{node}: must be runnable after lane implementation")

doc=text(ROOT/"docs/kde-tier1-package-batch11.md")
for token in (
    "27 PASS / 2 pending",
    "KUserFeedback",
    "Prison",
    "WITH_DMTX=ON",
    "WITH_ZXING=ON",
    "WITH_QUICK=ON",
    "WITH_MULTIMEDIA=ON",
    "fail-fast",
    "10301938362",
):
    req(token in doc,f"Batch 11 documentation missing {token}")

if errors:
    for error in errors:
        print(f"ERROR: {error}",file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 11 preparation validation: PASS")
print("Nodes: kuserfeedback + prison; independent multi-surface/optional lane")
print("Canonical state remains 27 PASS / 2 pending / 0 current FAIL / 0 BLOCKED")
