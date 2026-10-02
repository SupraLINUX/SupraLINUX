#!/usr/bin/env python3
import re
import subprocess

def _chunks(items, size):
    items=list(items)
    for i in range(0, len(items), size):
        yield items[i:i+size]

def apt_file_search_many(patterns, chunk_size=12):
    patterns=list(dict.fromkeys(patterns))
    result={pattern:set() for pattern in patterns}
    for chunk in _chunks(patterns, chunk_size):
        combined="(?:" + "|".join(f"(?:{pattern})" for pattern in chunk) + ")"
        p=subprocess.run(["apt-file","search","-x",combined],text=True,capture_output=True)
        if p.returncode not in (0,1):
            raise RuntimeError(f"apt-file chunk failed: {p.stderr.strip()}")
        compiled={pattern:re.compile(pattern) for pattern in chunk}
        for line in p.stdout.splitlines():
            if ":" not in line:
                continue
            pkg,path=line.split(":",1)
            pkg=pkg.strip()
            path=path.strip()
            if not pkg:
                continue
            for pattern,regex in compiled.items():
                if regex.search(path):
                    result[pattern].add(pkg)
    return {pattern:sorted(pkgs) for pattern,pkgs in result.items()}

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
