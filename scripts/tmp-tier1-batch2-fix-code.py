#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(s): return (ROOT/s).read_text(encoding="utf-8")
def write(s,t): (ROOT/s).write_text(t,encoding="utf-8")
path="scripts/run-kde-tier1-package-batch2-preflight.sh"; r=read(path)
pairs=[('"SYMBOLS_REFERENCE_TREE": symbols["tree_provider"],','"SYMBOLS_REFERENCE_TREE": symbols["tree_provider"],\n    "SYMBOLS_REVIEW_PATCH": symbols.get("review_patch", ""),\n    "SYMBOLS_REVIEW_PATCH_SHA256": symbols.get("review_patch_sha256", ""),\n    "SYMBOLS_REVIEWED_SHA256": symbols.get("reviewed_sha256", ""),'),('cp -a "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}"\ncp -a "${COPYRIGHT_REFERENCE}" "${SOURCE_DIR}/debian/copyright"','cp -a "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}"\nif [[ -n "${SYMBOLS_REVIEW_PATCH}" ]]; then\n    REVIEW_PATCH="${PACKAGE_META}/${SYMBOLS_REVIEW_PATCH}"\n    test -s "${REVIEW_PATCH}"\n    printf \'%s  %s\\n\' "${SYMBOLS_REVIEW_PATCH_SHA256}" "${REVIEW_PATCH}" | sha256sum --check --strict\n    patch --batch --forward "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" "${REVIEW_PATCH}"\n    printf \'%s  %s\\n\' "${SYMBOLS_REVIEWED_SHA256}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" | sha256sum --check --strict\n    sha256sum "${REVIEW_PATCH}" > "${EVIDENCE_DIR}/symbols-review-patch-sha256.txt"\n    sha256sum "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" > "${EVIDENCE_DIR}/reviewed-symbols-sha256.txt"\nfi\ncp -a "${COPYRIGHT_REFERENCE}" "${SOURCE_DIR}/debian/copyright"'),('sha256sum "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" > "${EVIDENCE_DIR}/injected-symbols-sha256.txt"\nsha256sum "${SOURCE_DIR}/debian/copyright" > "${EVIDENCE_DIR}/injected-copyright-sha256.txt"\ncmp -s "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}"','sha256sum "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" > "${EVIDENCE_DIR}/injected-symbols-sha256.txt"\nsha256sum "${SOURCE_DIR}/debian/copyright" > "${EVIDENCE_DIR}/injected-copyright-sha256.txt"\nif [[ -z "${SYMBOLS_REVIEW_PATCH}" ]]; then\n    cmp -s "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/${SYMBOLS_FILE}"\nelse\n    [[ "$(sha256sum "${SOURCE_DIR}/debian/${SYMBOLS_FILE}" | awk \'{print $1}\')" == "${SYMBOLS_REVIEWED_SHA256}" ]]\nfi'),('    pkg-config \\\n    qt6-base-dev','    pkg-config \\\n    patch \\\n    qt6-base-dev')]
for a,b in pairs:
    assert a in r, a[:80]; r=r.replace(a,b,1)
write(path,r)

path="scripts/validate_kde_tier1.py"; v=read(path)
failmap='''EXPECTED_FAIL = {
    "karchive": (34720201713, 103624554004, 10305889632, "1850a0a6dd7f267870fda83f17f5990f806ec76ae8fe810144557c46af532d01"),
    "kholidays": (34720201713, 103624554109, 10305513311, "522257440d6e04563162178dd3d3ab3ae658dc56c129dcf7f482fef8219bb0dc"),
    "ktexttemplate": (34720201713, 103624554096, 10306265683, "c164640037e564a43479daaa740f55c0f7578d977a7c38bfeb691fbd6b88544a"),
}
'''
assert "EXPECTED_PROVIDER_EVIDENCE = {" in v; v=v.replace("EXPECTED_PROVIDER_EVIDENCE = {",failmap+"EXPECTED_PROVIDER_EVIDENCE = {",1)
old='''    if node_id in EXPECTED_PASS:
        validate_pass(node)
    else:
        require(node.get("packaging") == {"state":"pending"}, f"{node_id}: unattempted packaging state must remain pending")
        require(node.get("state") == "pending", f"{node_id}: unattempted node state must remain pending")

require(sum(1 for n in nodes if n.get("state") == "PASS") == 4, "Tier 1 current PASS count must be 4")
require(sum(1 for n in nodes if n.get("state") == "pending") == 25, "Tier 1 current pending count must be 25")
require(not any(n.get("state") in {"FAIL","BLOCKED"} for n in nodes), "Tier 1 must have no current FAIL/BLOCKED nodes after batch 1 closure")'''
new='''    if node_id in EXPECTED_PASS:
        validate_pass(node)
    elif node_id in EXPECTED_FAIL:
        run, job, artifact, digest = EXPECTED_FAIL[node_id]
        packaging = node.get("packaging", {})
        require(node.get("state") == "FAIL", f"{node_id}: current node state must record real FAIL")
        require(packaging.get("state") == "FAIL", f"{node_id}: packaging state must record real FAIL")
        require(packaging.get("downstream_eligible") is False, f"{node_id}: FAIL cannot feed downstream")
        evidence = [x for x in packaging.get("evidence", []) if isinstance(x, dict) and x.get("result") == "FAIL"]
        require(len(evidence) == 1, f"{node_id}: exactly one first-attempt FAIL expected")
        if evidence:
            item=evidence[0]
            require(item.get("workflow_run") == run and item.get("job_id") == job, f"{node_id}: FAIL run/job mismatch")
            require(item.get("artifact_id") == artifact and item.get("artifact_sha256") == digest, f"{node_id}: FAIL artifact mismatch")
            require(item.get("attempted_package_version") == "6.30.0-0supralinux1", f"{node_id}: first attempt revision")
        require(packaging.get("remediation", {}).get("next_package_version") == "6.30.0-0supralinux2", f"{node_id}: remediation revision")
    else:
        require(node.get("packaging") == {"state":"pending"}, f"{node_id}: unattempted packaging state must remain pending")
        require(node.get("state") == "pending", f"{node_id}: unattempted node state must remain pending")

require(sum(1 for n in nodes if n.get("state") == "PASS") == 4, "Tier 1 current PASS count must be 4")
require(sum(1 for n in nodes if n.get("state") == "pending") == 22, "Tier 1 current pending count must be 22")
require(sum(1 for n in nodes if n.get("state") == "FAIL") == 3, "Tier 1 current FAIL count must be 3")
require(not any(n.get("state") == "BLOCKED" for n in nodes), "Tier 1 must have no BLOCKED nodes; Batch 2 nodes are independent")'''
assert old in v; v=v.replace(old,new,1); v=v.replace('print("Tier 1 package states: 4 PASS/downstream-eligible; 25 pending; 0 FAIL; 0 BLOCKED")','print("Tier 1 package states: 4 PASS/downstream-eligible; 22 pending; 3 FAIL; 0 BLOCKED")'); write(path,v)

path="scripts/validate_kde_tier1_packaging_reference.py"; v=read(path); assert "PASS_NODES = {" in v; v=v.replace("PASS_NODES = {",'FAIL_NODES = {"karchive", "kholidays", "ktexttemplate"}\nPASS_NODES = {',1)
old='''    else:
        require(node.get("packaging") == {"state":"pending"}, f"{node_id}: unattempted packaging must remain pending")
        require(node.get("state") == "pending", f"{node_id}: unattempted node must remain pending")

require(sum(1 for node in source_nodes if node.get("state") == "PASS") == 4, "Reference validator expects 4 actual package PASS nodes")
require(sum(1 for node in source_nodes if node.get("state") == "pending") == 25, "Reference validator expects 25 pending nodes")'''
new='''    elif node_id in FAIL_NODES:
        require(node.get("state") == "FAIL", f"{node_id}: real package FAIL must remain visible")
        require(node.get("packaging", {}).get("state") == "FAIL", f"{node_id}: packaging FAIL must remain visible")
        require(node.get("packaging", {}).get("downstream_eligible") is False, f"{node_id}: FAIL cannot feed downstream")
    else:
        require(node.get("packaging") == {"state":"pending"}, f"{node_id}: unattempted packaging must remain pending")
        require(node.get("state") == "pending", f"{node_id}: unattempted node must remain pending")

require(sum(1 for node in source_nodes if node.get("state") == "PASS") == 4, "Reference validator expects 4 actual package PASS nodes")
require(sum(1 for node in source_nodes if node.get("state") == "pending") == 22, "Reference validator expects 22 pending nodes")
require(sum(1 for node in source_nodes if node.get("state") == "FAIL") == 3, "Reference validator expects 3 real FAIL nodes")'''
assert old in v; v=v.replace(old,new,1); v=v.replace('print("Actual package states: 4 PASS; 25 pending")','print("Actual package states: 4 PASS; 22 pending; 3 FAIL; 0 BLOCKED")'); write(path,v)

path="scripts/validate_kde_tier1_packaging_tree.py"; v=read(path); needle='PASS_NODES = {"attica", "kcodecs", "kdbusaddons", "threadweaver"}'; assert needle in v; v=v.replace(needle,needle+'\nFAIL_NODES = {"karchive", "kholidays", "ktexttemplate"}',1)
old='''    if node_id in PASS_NODES:
        require(node.get("state") == "PASS", f"{node_id}: later real package PASS must remain intact")
    else:
        require(node.get("state") == "pending", f"{node_id}: reference-tree work must not promote unattempted package state")

require(sum(1 for node in nodes if node.get("state") == "PASS") == 4, "Packaging-tree validator expects 4 actual package PASS nodes")
require(sum(1 for node in nodes if node.get("state") == "pending") == 25, "Packaging-tree validator expects 25 pending nodes")'''
new='''    if node_id in PASS_NODES:
        require(node.get("state") == "PASS", f"{node_id}: later real package PASS must remain intact")
    elif node_id in FAIL_NODES:
        require(node.get("state") == "FAIL", f"{node_id}: real package FAIL must remain visible")
    else:
        require(node.get("state") == "pending", f"{node_id}: reference-tree work must not promote unattempted package state")

require(sum(1 for node in nodes if node.get("state") == "PASS") == 4, "Packaging-tree validator expects 4 actual package PASS nodes")
require(sum(1 for node in nodes if node.get("state") == "pending") == 22, "Packaging-tree validator expects 22 pending nodes")
require(sum(1 for node in nodes if node.get("state") == "FAIL") == 3, "Packaging-tree validator expects 3 actual package FAIL nodes")'''
assert old in v; v=v.replace(old,new,1); v=v.replace('print("Reference work has no state authority; current real package state is 4 PASS / 25 pending")','print("Reference work has no state authority; current real package state is 4 PASS / 22 pending / 3 FAIL / 0 BLOCKED")'); write(path,v)

path="docs/kde-tier1.md"; x=read(path); x=x.replace("Status: **29-node source set fixed; 4 hosted package PASS; 25 package nodes pending; 0 current FAIL; 0 BLOCKED**","Status: **29-node source set fixed; 4 hosted package PASS; 22 package nodes pending; 3 current FAIL; 0 BLOCKED**"); x=x.replace("- PASS: **4**;\n- pending: **25**;\n- current FAIL: **0**;\n- BLOCKED: **0**.","- PASS: **4**;\n- pending: **22**;\n- current FAIL: **3** — KTextTemplate, KArchive, KHolidays;\n- BLOCKED: **0**."); x=x.replace("Batch 2 should prepare another group of independent low-dependency Tier 1 nodes from the remaining 25, preserving per-package binary contracts, symbols/ABI policy, optional features, tests and consumer smokes.","Batch 2 revision 2 remediation is prepared for KTextTemplate, KArchive and KHolidays. Retry all three independently; unrelated Tier 1 work remains non-blocked."); x += "\n## Batch 2 first-attempt evidence\n\nWorkflow `34720201713` produced three real FAILs. KArchive/KHolidays failed at configure because the ECM translation path lacked Qt6 LinguistTools; KTextTemplate passed 10/10 tests and failed at the symbols gate. See `docs/kde-tier1-package-batch2.md`.\n"; write(path,x)
path="docs/status/2026-09-12.md"; x=read(path); x=x.replace("Tier 1 package state is now **4 PASS, 25 pending, 0 current FAIL, 0 BLOCKED**: Attica, KCodecs, KDBusAddons and ThreadWeaver are PASS.","Tier 1 package state is now **4 PASS, 22 pending, 3 current FAIL, 0 BLOCKED**: Attica, KCodecs, KDBusAddons and ThreadWeaver are PASS; KTextTemplate, KArchive and KHolidays are current FAIL after Batch 2 attempt 1."); x=x.replace("Close Batch 1 with Repository Policy and a no-rebuild scope proof, then prepare Batch 2 from the remaining 25 independent Tier 1 nodes.","Retry Batch 2 revision 2 after the documented LinguistTools and KTextTemplate symbols remediation; independent Tier 1 work remains non-blocked."); x += "\n## Tier 1 Batch 2 — first real attempt\n\nRun `34720201713` on commit `5edf71b390088a551af81e7fc7e8d87a8378104f` attempted all three nodes. KTextTemplate job `103624554096` failed at `dpkg-gensymbols` after 10/10 tests PASS (artifact `10306265683`, SHA-256 `c164640037e564a43479daaa740f55c0f7578d977a7c38bfeb691fbd6b88544a`). KArchive job `103624554004` and KHolidays job `103624554109` failed at configure due missing Qt6 LinguistTools (artifacts `10305889632`/`1850a0a6dd7f267870fda83f17f5990f806ec76ae8fe810144557c46af532d01` and `10305513311`/`522257440d6e04563162178dd3d3ab3ae658dc56c129dcf7f482fef8219bb0dc`). Revision 2 remediation is prepared; no revision-2 PASS is claimed yet.\n"; write(path,x)
print("runner validators and docs generated")
