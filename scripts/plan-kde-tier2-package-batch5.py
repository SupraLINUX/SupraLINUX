#!/usr/bin/env python3
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
RUNNABLE={"prepared-pending-build","remediation-pending-build"}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--github-output"); args=ap.parse_args()
    c=json.loads((ROOT/"manifests/kde-tier2-package-campaign-batch5.json").read_text())
    include=[]
    for node_id in c["selected_nodes"]:
        n=c["nodes"][node_id]
        if n.get("state") not in RUNNABLE: continue
        include.append({"node":node_id,"materialization_run":n["materialization"]["workflow_run"],"materialization_artifact_id":n["materialization"]["artifact_id"]})
    matrix={"include":include}
    payload={"run":"true" if include else "false","matrix":json.dumps(matrix,separators=(",",":"))}
    if args.github_output:
        with open(args.github_output,"a") as fh:
            for k,v in payload.items(): fh.write(f"{k}={v}\n")
    else: print(json.dumps(payload,indent=2))
if __name__=="__main__": main()
