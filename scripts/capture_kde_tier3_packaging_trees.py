#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"manifests/kde-tier3-package-contracts.json"
WORK=ROOT/".work/kde-tier3-packaging-tree"
EVIDENCE=ROOT/"evidence/kde-tier3-packaging-tree"
UBUNTU_LIST=WORK/"ubuntu.sources.list"
DEBIAN_LIST=WORK/"debian.sources.list"
UBUNTU_LISTS=WORK/"apt-lists-ubuntu"
DEBIAN_LISTS=WORK/"apt-lists-debian"

def run(args,**kwargs):
    print("+"," ".join(map(str,args)),flush=True)
    return subprocess.run([str(x) for x in args],check=True,**kwargs)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_result(result,stage,exit_code=0,**extra):
    data={
      "result":result,
      "stage":stage,
      "exit_code":exit_code,
      "claim":"technical-packaging-tree-only",
      "authoritative":False,
      "package_state_effect":"none",
    }
    data.update(extra)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (EVIDENCE/"result.json").write_text(json.dumps(data,indent=2)+"\n")

def parse_os_release():
    out={}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            k,v=line.split("=",1); out[k]=v.strip().strip('"')
    return out

def tree_record(root):
    rows=[]
    for path in sorted(root.rglob("*")):
        rel=path.relative_to(root).as_posix()
        st=path.lstat()
        mode=stat.S_IMODE(st.st_mode)
        if path.is_symlink():
            kind="symlink"; payload=os.readlink(path); digest=hashlib.sha256(("symlink:"+payload).encode()).hexdigest()
        elif path.is_file():
            kind="file"; payload=None; digest=sha(path)
        elif path.is_dir():
            continue
        else:
            kind="other"; payload=None; digest=""
        rows.append({"path":rel,"kind":kind,"mode":f"{mode:o}","sha256":digest,"target":payload})
    blob=(json.dumps(rows,sort_keys=True,separators=(",",":"))+"\n").encode()
    return hashlib.sha256(blob).hexdigest(),rows,blob

def parse_control(path):
    paras=[]; cur={}; key=None
    for line in path.read_text().splitlines():
        if not line.strip():
            if cur: paras.append(cur); cur={}; key=None
            continue
        if line[0].isspace() and key:
            cur[key]+=" "+line.strip(); continue
        if ":" in line:
            key,val=line.split(":",1); cur[key]=val.strip()
    if cur: paras.append(cur)
    fields=(
      "Source","Package","Architecture","Multi-Arch","Depends","Pre-Depends",
      "Recommends","Suggests","Provides","Replaces","Breaks","Conflicts",
      "Build-Depends","Build-Depends-Indep"
    )
    return [{k:p[k] for k in fields if k in p} for p in paras]

def packaging_files(root):
    suffixes=(".install",".symbols",".links",".triggers",".maintscript",".postinst",".postrm",".preinst",".prerm")
    selected=[]
    for p in sorted(root.rglob("*")):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        if rel in {"control","rules","changelog","copyright"} or rel.endswith(suffixes):
            selected.append({"path":rel,"sha256":sha(p)})
    return selected

def apt_opts(source_list,lists):
    return [
      "-o",f"Dir::Etc::sourcelist={source_list}",
      "-o","Dir::Etc::sourceparts=-",
      "-o",f"Dir::State::lists={lists}",
      "-o","APT::Get::List-Cleanup=0",
    ]

def main():
    osr=parse_os_release()
    if osr.get("ID")!="ubuntu" or osr.get("VERSION_ID")!="26.04":
        raise SystemExit("Expected Ubuntu 26.04")
    manifest=json.loads(MANIFEST.read_text())
    if manifest.get("state") not in {"packaging-tree-pending","packaging-tree-pass"}:
        raise SystemExit(f"Unexpected contract state: {manifest.get('state')}")
    rc=manifest.get("reference_capture",{})
    if rc.get("status")!="PASS":
        raise SystemExit("Reference capture must be PASS before packaging-tree capture")

    shutil.rmtree(WORK,ignore_errors=True)
    shutil.rmtree(EVIDENCE,ignore_errors=True)
    WORK.mkdir(parents=True)
    (EVIDENCE/"trees").mkdir(parents=True)

    stage="tooling"
    try:
        run(["sudo","apt-get","update"])
        run(["sudo","env","DEBIAN_FRONTEND=noninteractive","apt-get","install","-y","--no-install-recommends",
             "debian-archive-keyring","dpkg-dev","ubuntu-keyring","xz-utils"])

        UBUNTU_LIST.write_text(
          "deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute main universe\n"
          "deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute-updates main universe\n"
          "deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://security.ubuntu.com/ubuntu resolute-security main universe\n"
        )
        DEBIAN_LIST.write_text(
          "deb-src [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian sid main\n"
        )
        for p in (UBUNTU_LISTS,DEBIAN_LISTS):
            run(["sudo","mkdir","-p",str(p)])
            run(["sudo","chown","_apt:root",str(p)])

        uopts=apt_opts(UBUNTU_LIST,UBUNTU_LISTS)
        dopts=apt_opts(DEBIAN_LIST,DEBIAN_LISTS)
        run(["sudo","apt-get",*uopts,"update"])
        run(["sudo","apt-get",*dopts,"update"])

        stage="source-download-and-extraction"
        for node in manifest["selected_nodes"]:
            refs=manifest["nodes"][node]["technical_references"]
            for side,opts in (("ubuntu",uopts),("debian",dopts)):
                ref=refs[side]
                source=ref["source_package"]; version=ref["version"]
                work=WORK/side/node
                work.mkdir(parents=True)
                run(["apt-get",*opts,"source","--download-only",f"{source}={version}"],cwd=work)
                for prefix in ("dsc","debian_tar","orig_tar"):
                    file=work/ref[prefix+"_file"]
                    if not file.is_file():
                        raise SystemExit(f"{node}/{side}: missing pinned file {file.name}")
                    actual=sha(file)
                    if actual!=ref[prefix+"_sha256"]:
                        raise SystemExit(f"{node}/{side}: SHA mismatch {file.name}: {actual}")
                extract=work/"source"
                run(["dpkg-source","-x",str(work/ref["dsc_file"]),str(extract)])
                debian=extract/"debian"
                if not debian.is_dir():
                    raise SystemExit(f"{node}/{side}: extracted debian/ tree missing")
                dest=EVIDENCE/"trees"/side/node/"debian"
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copytree(debian,dest,symlinks=True)

        stage="normalization"
        index={"schema":1,"authority":False,"role":"technical-packaging-tree-only","selected_kde":"6.30.0","nodes":{}}
        for node in manifest["selected_nodes"]:
            index["nodes"][node]={}
            expected_sets=[]
            for side in ("ubuntu","debian"):
                root=EVIDENCE/"trees"/side/node/"debian"
                digest,rows,blob=tree_record(root)
                node_out=root.parent
                (node_out/"tree-files.json").write_bytes(blob)
                control=root/"control"
                if not control.is_file():
                    raise SystemExit(f"{node}/{side}: debian/control missing")
                summary=parse_control(control)
                summary_path=node_out/"control-summary.json"
                summary_path.write_text(json.dumps(summary,indent=2)+"\n")
                binaries=sorted(p["Package"] for p in summary if "Package" in p)
                expected=sorted(manifest["nodes"][node]["technical_references"][side]["binary_packages"])
                if binaries!=expected:
                    raise SystemExit(f"{node}/{side}: binary set drift expected={expected} actual={binaries}")
                expected_sets.append(binaries)
                pfiles=packaging_files(root)
                pfiles_path=node_out/"packaging-files.json"
                pfiles_path.write_text(json.dumps(pfiles,indent=2)+"\n")
                ref=manifest["nodes"][node]["technical_references"][side]
                index["nodes"][node][side]={
                  "source_package":ref["source_package"],
                  "source_version":ref["version"],
                  "tree_sha256":digest,
                  "file_count":len(rows),
                  "control_summary_sha256":sha(summary_path),
                  "packaging_files_sha256":sha(pfiles_path),
                  "binary_packages":binaries,
                }
            if expected_sets[0]!=expected_sets[1]:
                raise SystemExit(f"{node}: Ubuntu/Debian binary package identities diverged")

        index_path=EVIDENCE/"index.json"
        index_path.write_text(json.dumps(index,indent=2,sort_keys=True)+"\n")
        index_sha=sha(index_path)
        (EVIDENCE/"index.sha256").write_text(index_sha+"\n")
        write_result("PASS","complete",0,nodes=len(manifest["selected_nodes"]),sides=40,index_sha256=index_sha)
        print(json.dumps(index,indent=2))
        print("KDE Tier 3 packaging-tree capture: PASS")
    except Exception:
        write_result("FAIL",stage,1)
        raise

if __name__=="__main__":
    main()
