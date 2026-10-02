#!/usr/bin/env python3
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(c,m):
    if not c: errors.append(m)
dag=json.loads((ROOT/"manifests/kde-plasma-dag-candidate.json").read_text())
plasma=json.loads((ROOT/"manifests/kde-plasma.json").read_text())
deps=json.loads((ROOT/"manifests/kde-plasma-dependencies.json").read_text())
src=dag.get("source_discovery",{})
req(dag.get("state")=="candidate-review-required" and dag.get("candidate_only") is True,"Plasma DAG candidate state")
req(src.get("workflow_run_id")==36951077374 and src.get("artifact_id")==11204675088,"Plasma discovery evidence binding")
req(src.get("artifact_digest")=="sha256:9b6192b1145474cca5bd255d4cb517be2ea8ea4fcd87679f05dfa5aa039a39fd","Plasma discovery artifact digest")
req(src.get("dependencies_json_sha256")=="a6b2d066ced63231dd3de6adb6248dbbd7eba01cf0d776d49c6d2b091c0f82ef","Plasma dependency snapshot hash")
req(src.get("parser_revision")==4 and src.get("source_count")==75 and src.get("source_sha256_verified")==75,"Plasma discovery revision/source count")
req(src.get("kf6_component_references")==535 and src.get("internal_candidate_edge_count")==109 and src.get("ambiguous_provider_references")==0,"Plasma discovery candidate edge contract")
top=dag.get("topology",{})
req(top.get("acyclic") is True,"Plasma candidate DAG must be acyclic")
req(top.get("level_count")==6 and top.get("level_sizes")==[34,11,20,1,2,7],"Plasma candidate level cardinalities")
nodes=dag.get("nodes",{})
req(len(nodes)==75,"Plasma candidate node count")
req(sum(len(v.get("depends_on",[])) for v in nodes.values())==109,"Plasma candidate edge count")
for name,node in nodes.items():
    for dep in node.get("depends_on",[]):
        req(dep in nodes,f"{name}: missing dependency {dep}")
        if dep in nodes:
            req(nodes[dep].get("level",999)<node.get("level",-1),f"{name}: dependency {dep} must be in an earlier level")
req(nodes.get("kwin",{}).get("level")==3,"KWin candidate level")
req(nodes.get("plasma-workspace",{}).get("level")==4,"Plasma Workspace candidate level")
req(nodes.get("plasma-desktop",{}).get("level")==5,"Plasma Desktop candidate level")
req(dag.get("package_execution_authorized") is False and dag.get("consumes_package_attempt") is False,"candidate DAG package execution lock")
planning=plasma.get("planning",{})
req(planning.get("status")=="dag-candidate-review-pending" and planning.get("package_execution_authorized") is False,"Plasma DAG review live state")
req(deps.get("state")=="discovery-evidence-promoted" and deps.get("discovery",{}).get("result")=="PASS","Plasma discovery evidence promoted")
if errors:
    for e in errors: print(f"ERROR: {e}",file=sys.stderr)
    raise SystemExit(1)
print("KDE Plasma candidate DAG validation: PASS")
print("nodes=75 edges=109 levels=6 sizes=34,11,20,1,2,7")
print("package_execution_authorized=false")
