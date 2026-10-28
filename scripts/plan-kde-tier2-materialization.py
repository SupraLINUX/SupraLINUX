#!/usr/bin/env python3
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--github-output"); args=ap.parse_args()
    contracts=json.loads((ROOT/"manifests/kde-tier2-package-contracts.json").read_text())
    tier2=json.loads((ROOT/"manifests/kde-frameworks-tier2.json").read_text())
    canonical={n["id"]:n for n in tier2["nodes"]}
    materialization=contracts.get("materialization",{})
    targets=set(materialization.get("targets",[]))
    nodes=[]
    if contracts.get("state") not in {"reference-capture-pass","materialized"} or materialization.get("status") not in {"pending-ci","PASS"}:
        payload={"run":"false","matrix":json.dumps({"node":[]},separators=(",",":"))}
        if args.github_output:
            with open(args.github_output,"a") as fh:
                for k,v in payload.items(): fh.write(f"{k}={v}\n")
        else: print(json.dumps(payload,indent=2))
        return
    for node_id in contracts.get("selected_nodes",[]):
        n=canonical[node_id]
        if node_id not in targets: continue
        if n.get("state")=="PASS": continue
        if n.get("planning",{}).get("readiness")!="package-contract-ready": continue
        if n.get("planning",{}).get("package_contract")!="not-materialized": continue
        nodes.append(node_id)
    payload={"run":"true" if nodes else "false","matrix":json.dumps({"node":nodes},separators=(",",":"))}
    if args.github_output:
        with open(args.github_output,"a") as fh:
            for k,v in payload.items(): fh.write(f"{k}={v}\n")
    else: print(json.dumps(payload,indent=2))
if __name__=="__main__": main()
