#!/usr/bin/env python3
from pathlib import Path
import argparse,json

ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/"manifests/kde-tier3-support-build-level0.json"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--github-output")
    args=ap.parse_args()
    c=json.loads(CAMPAIGN.read_text())
    runnable=[]
    for node in c["selected_nodes"]:
        n=c["nodes"][node]
        if n["state"] not in {"prepared-pending-build","remediation-pending-build"}:
            continue
        m=n["materialization"]
        runnable.append({
            "node":node,
            "materialization_run":m["workflow_run"],
            "materialization_artifact_id":m["artifact_id"],
        })
    matrix={"include":runnable}
    values={"run":"true" if runnable else "false","matrix":json.dumps(matrix,separators=(",",":"))}
    if args.github_output:
        with open(args.github_output,"a") as f:
            for k,v in values.items(): f.write(f"{k}={v}\n")
    else:
        print(json.dumps(values,indent=2))
if __name__=="__main__":
    main()
