#!/usr/bin/env python3
import argparse,json,re,subprocess,sys,tempfile
from pathlib import Path

FIND_DEP_RE=re.compile(r"\bfind_dependency\s*\(\s*([A-Za-z0-9_.+\-]+)")
TARGET_RE=re.compile(r"\badd_(?:library|executable)\s*\(\s*([A-Za-z0-9_.:+\-]+)")
FIND_PACKAGE_RE=re.compile(r"\bfind_package\s*\(\s*([A-Za-z0-9_.+\-]+)")
KF_TARGET_RE=re.compile(r"\b(KF6::[A-Za-z0-9_.+\-]+)\b")
PROVIDER_MAP={"ECM":"extra-cmake-modules"}

def run(cmd): return subprocess.check_output(cmd,text=True).strip()

def control_paragraphs(text):
    out=[]
    for raw in re.split(r"\n\s*\n",text.strip()):
        if not raw.strip(): continue
        fields={}; current=None
        for line in raw.splitlines():
            if line[:1].isspace() and current:
                fields[current]+=" "+line.strip(); continue
            if ":" not in line: continue
            key,value=line.split(":",1); current=key.strip(); fields[current]=value.strip()
        out.append(fields)
    return out

def field_has_package(field,package):
    pat=rf"(?<![A-Za-z0-9+.-]){re.escape(package)}(?=(?::[A-Za-z0-9_-]+)?(?:\s|\(|,|\||$))"
    return re.search(pat,field or "") is not None

def cmake_dependencies(paths):
    found={}
    for path in paths:
        try: content=path.read_text(errors="replace")
        except OSError: continue
        deps=sorted(set(FIND_DEP_RE.findall(content)))
        if deps: found[str(path)]=deps
    return found

def finish(path,payload,errors):
    payload["result"]="FAIL" if errors else "PASS"; payload["errors"]=errors
    Path(path).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    if errors:
        for error in errors: print(f"ERROR: {error}",file=sys.stderr)
        raise SystemExit(1)

def source_mode(args):
    campaign=json.loads(Path(args.campaign).read_text()); node=campaign["nodes"][args.node]
    source_dir=Path(args.source_dir); paragraphs=control_paragraphs(Path(args.control).read_text(errors="replace"))
    if not paragraphs: raise SystemExit("debian/control contains no paragraphs")
    build_depends=paragraphs[0].get("Build-Depends","")
    dev=[p for p in paragraphs[1:] if p.get("Package","").endswith("-dev")]
    errors=[]; qml_required=[]
    for dep in node.get("package_validation_dependencies",[]):
        if dep.get("required_during_dh_qmldeps") is True: qml_required.extend(dep.get("required_local_packages",[]))
    for package in sorted(set(qml_required)):
        if not field_has_package(build_depends,package): errors.append(f"Build-Depends missing dh_qmldeps provider {package}")
    configs=[p for p in source_dir.rglob("*") if p.is_file() and "debian" not in p.parts and (p.name.endswith("Config.cmake.in") or p.name.endswith("Config.cmake"))]
    dependencies=cmake_dependencies(configs); flattened=sorted({d for ds in dependencies.values() for d in ds}); checks=[]
    for dep in flattened:
        provider=PROVIDER_MAP.get(dep)
        if not provider: continue
        providers=[p.get("Package") for p in dev if field_has_package(p.get("Depends",""),provider)]
        checks.append({"cmake_dependency":dep,"debian_provider":provider,"dev_packages":providers})
        if not providers: errors.append(f"upstream development contract find_dependency({dep}) lacks {provider} in every -dev Depends")
    finish(args.output,{"schema":1,"mode":"source","node":args.node,"qml_build_depends_required":sorted(set(qml_required)),"upstream_config_find_dependencies":dependencies,"known_provider_checks":checks},errors)

def artifact_mode(args):
    campaign=json.loads(Path(args.campaign).read_text()); node=campaign["nodes"][args.node]
    consumer=Path(args.consumer_cmake).read_text(errors="replace")
    consumer_packages=sorted(set(FIND_PACKAGE_RE.findall(consumer))); consumer_targets=sorted(set(KF_TARGET_RE.findall(consumer)))
    errors=[]; dev_contracts=[]; all_targets=set(); all_configs=set(); qml=[]
    debs=sorted(Path(args.debs_dir).glob("*.deb"))
    if not debs: errors.append("no .deb artifacts found")
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        for i,deb in enumerate(debs):
            package=run(["dpkg-deb","-f",str(deb),"Package"])
            depends=subprocess.run(["dpkg-deb","-f",str(deb),"Depends"],text=True,capture_output=True).stdout.strip()
            extract=root/f"p{i}"; extract.mkdir(); subprocess.run(["dpkg-deb","-x",str(deb),str(extract)],check=True)
            for qmldir in extract.rglob("qmldir"):
                for line in qmldir.read_text(errors="replace").splitlines():
                    line=line.strip()
                    if line.startswith("module "): qml.append({"module":line.split(None,1)[1].strip(),"package":package})
            if not package.endswith("-dev"): continue
            configs=sorted(extract.rglob("*Config.cmake")); targets=sorted(set(extract.rglob("*Target.cmake")) | set(extract.rglob("*Targets.cmake")))
            dep_map=cmake_dependencies(configs)
            exported=sorted({t for path in targets for t in TARGET_RE.findall(path.read_text(errors="replace"))})
            all_targets.update(exported); all_configs.update(path.name for path in configs); checks=[]
            for dep in sorted({d for ds in dep_map.values() for d in ds}):
                provider=PROVIDER_MAP.get(dep)
                if not provider: continue
                ok=field_has_package(depends,provider); checks.append({"cmake_dependency":dep,"debian_provider":provider,"declared":ok})
                if not ok: errors.append(f"{package}: find_dependency({dep}) requires Depends on {provider}")
            dev_contracts.append({"package":package,"depends":depends,"configs":[p.name for p in configs],"find_dependencies":dep_map,"exported_targets":exported,"known_provider_checks":checks})
    for package in consumer_packages:
        if package.startswith("KF6") and f"{package}Config.cmake" not in all_configs: errors.append(f"consumer requests {package}, but no {package}Config.cmake is packaged")
    for target in consumer_targets:
        if target not in all_targets: errors.append(f"consumer requires target {target}, but packaged CMake exports are {sorted(all_targets)}")
    expected=sorted({q["required_root_module"] for q in node.get("qml_contracts",[])})
    observed=sorted({x["module"] for x in qml})
    for module in expected:
        if module not in observed: errors.append(f"required QML module {module} is not declared by packaged qmldir metadata")
    finish(args.output,{"schema":1,"mode":"artifact","node":args.node,"development_packages":dev_contracts,"consumer":{"find_packages":consumer_packages,"kf6_targets":consumer_targets},"packaged_cmake_configs":sorted(all_configs),"packaged_cmake_targets":sorted(all_targets),"qml_modules":sorted(qml,key=lambda x:(x["module"],x["package"])),"required_qml_modules":expected},errors)

def main():
    p=argparse.ArgumentParser(description="Audit KDE development/QML package contracts before consumer smoke"); sub=p.add_subparsers(dest="mode",required=True)
    s=sub.add_parser("source"); s.add_argument("--node",required=True); s.add_argument("--campaign",required=True); s.add_argument("--source-dir",required=True); s.add_argument("--control",required=True); s.add_argument("--output",required=True); s.set_defaults(func=source_mode)
    a=sub.add_parser("artifact"); a.add_argument("--node",required=True); a.add_argument("--campaign",required=True); a.add_argument("--debs-dir",required=True); a.add_argument("--consumer-cmake",required=True); a.add_argument("--output",required=True); a.set_defaults(func=artifact_mode)
    args=p.parse_args(); args.func(args)
if __name__=="__main__": main()
