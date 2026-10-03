#!/usr/bin/env python3
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/"manifests/kde-tier3-support-build-level1.json"
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--github-output"); args=ap.parse_args()
    c=json.loads(CAMPAIGN.read_text()); runnable=[]
    for node in c["selected_nodes"]:
        n=c["nodes"][node]
        if n.get("state") in {"prepared-pending-build","remediation-pending-build"}:
            runnable.append({"node":node,"materialization_run":n["materialization"]["workflow_run"],"materialization_artifact_id":n["materialization"]["artifact_id"]})
    vals={"run":"true" if runnable else "false","matrix":json.dumps({"include":runnable},separators=(",",":"))}
    if args.github_output:
        with open(args.github_output,"a") as f:
            for k,v in vals.items(): f.write(f"{k}={v}\n")
    else: print(json.dumps(vals,indent=2))
if __name__=="__main__": main()
