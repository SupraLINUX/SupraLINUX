#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,subprocess

ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/"manifests/kde-tier2-package-campaign-batch4.json"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def deb_meta(path: Path):
    pkg=subprocess.check_output(["dpkg-deb","-f",str(path),"Package"],text=True).strip()
    ver=subprocess.check_output(["dpkg-deb","-f",str(path),"Version"],text=True).strip()
    return pkg,ver

def validate_dir(root: Path, cfg: dict, label: str):
    actual={}
    for p in root.rglob("*.deb"):
        pkg,ver=deb_meta(p)
        if pkg in actual:
            raise SystemExit(f"{label}: duplicate binary {pkg}")
        if ver!=cfg["version"]:
            raise SystemExit(f"{label}: {pkg} version {ver} != {cfg['version']}")
        actual[pkg]=sha(p)
    if actual!=cfg["debs"]:
        raise SystemExit(f"{label}: .deb set/hash mismatch\nexpected={cfg['debs']}\nactual={actual}")
    return actual

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    args=ap.parse_args()
    root=Path(args.root)
    c=json.loads(CAMPAIGN.read_text())
    result={"schema":1,"batch":c["batch"],"result":"PASS","inputs":{}}
    ecm=c["shared_predecessors"]["extra_cmake_modules"]
    result["inputs"]["extra_cmake_modules"]=validate_dir(root/"extra_cmake_modules",ecm,"extra_cmake_modules")
    for pred_id,cfg in sorted(c["retained_predecessors"].items()):
        actual=validate_dir(root/pred_id,cfg,pred_id)
        if cfg["dev_package"] not in actual:
            raise SystemExit(f"{pred_id}: retained dev package absent")
        result["inputs"][pred_id]=actual
    (root/"retained-inputs-validation.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Tier 2 Batch 4 retained input bundle: PASS")
    print("validated="+",".join(sorted(result["inputs"])))
if __name__=="__main__":
    main()
