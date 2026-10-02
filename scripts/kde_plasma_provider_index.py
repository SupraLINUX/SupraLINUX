#!/usr/bin/env python3
import re
import subprocess

def apt_source_many(names):
    names=list(dict.fromkeys(names))
    result={name:{"source":name,"available":False,"records":[]} for name in names}
    if not names:
        return result
    p=subprocess.run(["apt-cache","showsrc",*names],text=True,capture_output=True)
    if p.returncode not in (0,100):
        raise RuntimeError(f"apt-cache showsrc batch failed: {p.stderr.strip()}")
    current={}
    last_key=None
    def flush():
        nonlocal current,last_key
        name=current.get("Package")
        if name in result and current.get("Version"):
            result[name]["available"]=True
            result[name]["records"].append({
                "version":current["Version"],
                "build_depends":current.get("Build-Depends",""),
                "build_depends_indep":current.get("Build-Depends-Indep",""),
            })
        current={}
        last_key=None
    for line in p.stdout.splitlines()+[""]:
        if not line.strip():
            flush()
            continue
        if line.startswith(" ") and last_key:
            current[last_key]=current.get(last_key,"")+" "+line.strip()
            continue
        if ": " in line:
            key,value=line.split(": ",1)
            if key in {"Package","Version","Build-Depends","Build-Depends-Indep"}:
                current[key]=value.strip()
                last_key=key
    return result

def parse_build_dep_packages(text):
    result=set()
    if not text:
        return result
    for group in text.split(","):
        for alternative in group.split("|"):
            token=alternative.strip()
            token=re.sub(r"\s*\([^)]*\)","",token)
            token=re.sub(r"\s*\[[^]]*\]","",token)
            token=re.sub(r"\s*<[^>]*>","",token)
            token=token.split(":",1)[0].strip()
            if re.fullmatch(r"[a-z0-9][a-z0-9+.-]*",token):
                result.add(token)
    return result

def build_dep_packages(source_entry):
    packages=set()
    for record in source_entry.get("records",[]):
        packages.update(parse_build_dep_packages(record.get("build_depends","")))
        packages.update(parse_build_dep_packages(record.get("build_depends_indep","")))
    return sorted(packages)

def apt_policy_many(packages):
    packages=list(dict.fromkeys(packages))
    if not packages:
        return {}
    p=subprocess.run(["apt-cache","policy",*packages],text=True,capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"apt-cache policy batch failed: {p.stderr.strip()}")
    result={pkg:None for pkg in packages}
    current=None
    for line in p.stdout.splitlines():
        if line and not line.startswith(" ") and line.endswith(":"):
            name=line[:-1].strip()
            current=name if name in result else None
        elif current and line.strip().startswith("Candidate:"):
            candidate=line.split(":",1)[1].strip()
            result[current]=None if candidate=="(none)" else candidate
    return result
