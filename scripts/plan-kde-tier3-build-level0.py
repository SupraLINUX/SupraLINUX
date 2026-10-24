#!/usr/bin/env python3
from pathlib import Path
import argparse
import json

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"manifests/kde-tier3-build-level0.json"
RUNNABLE={"prepared-pending-build","prepared-pending-revalidation","remediation-pending-build"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--github-output")
    args=ap.parse_args()
    m=json.loads(MANIFEST.read_text())
    include=[]
    if m.get("execution_authorized") is True:
        for node in m.get("selected_nodes",[]):
            n=m["nodes"][node]
            if n.get("state") not in RUNNABLE:
                continue
            mat=n["materialization"]
            include.append({
                "node":node,
                "materialization_run":mat["workflow_run"],
                "materialization_artifact_id":mat["artifact_id"],
            })
    payload={
        "run":"true" if include else "false",
        "matrix":json.dumps({"include":include},separators=(",",":")),
    }
    if args.github_output:
        with open(args.github_output,"a") as fh:
            for k,v in payload.items():
                fh.write(f"{k}={v}\n")
    else:
        print(json.dumps(payload,indent=2))

if __name__=="__main__":
    main()
