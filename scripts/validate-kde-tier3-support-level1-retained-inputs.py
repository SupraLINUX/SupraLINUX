#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/"manifests/kde-tier3-support-build-level1.json"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def meta(p):
    return (subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip(),
            subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip())
def validate(root,cfg,label):
    got={}
    for p in Path(root).rglob("*.deb"):
        pkg,ver=meta(p)
        if pkg in got: raise SystemExit(f"{label}: duplicate {pkg}")
        if ver!=cfg["version"]: raise SystemExit(f"{label}: {pkg} version {ver} != {cfg['version']}")
        got[pkg]=sha(p)
    if got!=cfg["debs"]: raise SystemExit(f"{label}: .deb set/hash mismatch\nexpected={cfg['debs']}\nactual={got}")
    if cfg["dev_package"] not in got: raise SystemExit(f"{label}: required package {cfg['dev_package']} absent")
    return got
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); args=ap.parse_args()
    root=Path(args.root); c=json.loads(CAMPAIGN.read_text())
    out={"schema":1,"batch":"tier3-support-build-level1","result":"PASS","inputs":{}}
    out["inputs"]["extra_cmake_modules"]=validate(root/"extra_cmake_modules",c["shared_predecessors"]["extra_cmake_modules"],"extra_cmake_modules")
    for section in ("retained_predecessors","package_dependency_closure"):
        for pred,cfg in sorted(c[section].items()):
            out["inputs"][pred]=validate(root/pred,cfg,pred)
    (root/"retained-inputs-validation.json").write_text(json.dumps(out,indent=2)+"\n")
    print("Tier 3 support level 1 retained inputs: PASS")
    print("validated="+",".join(sorted(out["inputs"])))
if __name__=="__main__": main()
