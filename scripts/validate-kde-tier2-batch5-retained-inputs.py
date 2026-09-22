#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/"manifests/kde-tier2-package-campaign-batch5.json"
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def deb_meta(path):
    return (
      subprocess.check_output(["dpkg-deb","-f",str(path),"Package"],text=True).strip(),
      subprocess.check_output(["dpkg-deb","-f",str(path),"Version"],text=True).strip(),
    )
def validate_dir(root,cfg,label):
    actual={}
    for p in root.rglob("*.deb"):
        pkg,ver=deb_meta(p)
        if pkg in actual: raise SystemExit(f"{label}: duplicate binary {pkg}")
        if ver!=cfg["version"]: raise SystemExit(f"{label}: {pkg} version {ver} != {cfg['version']}")
        actual[pkg]=sha(p)
    if actual!=cfg["debs"]: raise SystemExit(f"{label}: .deb set/hash mismatch\nexpected={cfg['debs']}\nactual={actual}")
    return actual
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); args=ap.parse_args()
    root=Path(args.root); c=json.loads(CAMPAIGN.read_text())
    result={"schema":1,"batch":c["batch"],"result":"PASS","inputs":{}}
    ecm=c["shared_predecessors"]["extra_cmake_modules"]
    result["inputs"]["extra_cmake_modules"]=validate_dir(root/"extra_cmake_modules",ecm,"extra_cmake_modules")
    cfg=c["retained_predecessors"]["kcodecs"]
    actual=validate_dir(root/"kcodecs",cfg,"kcodecs")
    if cfg["dev_package"] not in actual: raise SystemExit("kcodecs: retained dev package absent")
    result["inputs"]["kcodecs"]=actual
    (root/"retained-inputs-validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Tier 2 Batch 5 retained input bundle: PASS")
if __name__=="__main__": main()
