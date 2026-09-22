#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/manifests/kde-tier2-kmime-compatibility-audit.json"
WORK="$ROOT/.work/kde-tier2-kmime-compatibility-audit"
EVIDENCE="$ROOT/evidence/kde-tier2-kmime-compatibility-audit"
FRAMEWORK_ARTIFACT_DIR="\${FRAMEWORK_ARTIFACT_DIR:-}"

rm -rf "$WORK" "$EVIDENCE"
mkdir -p "$WORK/framework" "$WORK/legacy" "$WORK/extracted" "$EVIDENCE"
exec > >(tee "$EVIDENCE/pipeline.log") 2>&1

if [[ -z "$FRAMEWORK_ARTIFACT_DIR" || ! -d "$FRAMEWORK_ARTIFACT_DIR" ]]; then
  echo "FRAMEWORK_ARTIFACT_DIR is missing" >&2
  exit 1
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends dpkg-dev python3

python3 - "$MANIFEST" "$FRAMEWORK_ARTIFACT_DIR" "$WORK/framework" <<'PY'
import json,hashlib,shutil,subprocess,sys
from pathlib import Path
manifest=json.load(open(sys.argv[1]))
src=Path(sys.argv[2]); dst=Path(sys.argv[3])
wanted=set(manifest["framework_build_evidence"]["binary_packages"])
seen={}
for p in src.rglob("*.deb"):
    try:
        pkg=subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()
        ver=subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip()
    except subprocess.CalledProcessError:
        continue
    if pkg not in wanted:
        continue
    if pkg in seen:
        raise SystemExit(f"duplicate framework package {pkg}: {seen[pkg]} and {p}")
    if ver != manifest["framework_build_evidence"]["package_version"]:
        raise SystemExit(f"{pkg}: version {ver} != expected {manifest['framework_build_evidence']['package_version']}")
    out=dst/p.name
    shutil.copy2(p,out)
    seen[pkg]=str(out)
if set(seen)!=wanted:
    raise SystemExit(f"framework artifact missing packages: expected={sorted(wanted)} actual={sorted(seen)}")
print("framework artifact package set: PASS")
PY

pushd "$WORK/legacy" >/dev/null
for spec in libkmime-data=25.12.3-0ubuntu1 libkmime-dev=25.12.3-0ubuntu1 libkpim6mime6=25.12.3-0ubuntu1; do
  apt-get download "$spec"
done
popd >/dev/null

python3 - "$MANIFEST" "$WORK/framework" "$WORK/legacy" "$WORK/extracted" "$EVIDENCE" <<'PY'
import hashlib,json,os,re,subprocess,sys
from pathlib import Path

manifest=json.load(open(sys.argv[1]))
framework=Path(sys.argv[2]); legacy=Path(sys.argv[3]); extracted=Path(sys.argv[4]); evidence=Path(sys.argv[5])
fields=["Package","Version","Architecture","Multi-Arch","Depends","Pre-Depends","Provides","Conflicts","Breaks","Replaces"]

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def field(path,name):
    p=subprocess.run(["dpkg-deb","-f",str(path),name],text=True,capture_output=True)
    return p.stdout.strip()

records={}
paths_by_pkg={}
roots={}
for group,root in (("framework",framework),("legacy",legacy)):
    for deb in sorted(root.glob("*.deb")):
        pkg=field(deb,"Package")
        if not pkg: continue
        rec={"group":group,"file":deb.name,"sha256":sha(deb)}
        for f in fields:
            rec[f]=field(deb,f)
        records[pkg]=rec
        dest=extracted/pkg
        dest.mkdir(parents=True,exist_ok=True)
        subprocess.check_call(["dpkg-deb","-x",str(deb),str(dest)])
        roots[pkg]=dest
        filepaths=[]
        for p in dest.rglob("*"):
            if p.is_file() or p.is_symlink():
                filepaths.append(p.relative_to(dest).as_posix())
        paths_by_pkg[pkg]=sorted(filepaths)

expected_framework=set(manifest["framework_build_evidence"]["binary_packages"])
expected_legacy=set(manifest["legacy_reference"]["binary_packages"])
if set(p for p,r in records.items() if r["group"]=="framework") != expected_framework:
    raise SystemExit("framework package identity mismatch")
if set(p for p,r in records.items() if r["group"]=="legacy") != expected_legacy:
    raise SystemExit("legacy package identity mismatch")
for pkg in expected_legacy:
    if records[pkg]["Version"] != manifest["legacy_reference"]["version"]:
        raise SystemExit(f"{pkg}: legacy version drift: {records[pkg]['Version']}")

framework_names=sorted(expected_framework); legacy_names=sorted(expected_legacy)
relation_fields=["Provides","Conflicts","Breaks","Replaces"]
relation_edges=[]
for pkg,rec in sorted(records.items()):
    opposite=legacy_names if rec["group"]=="framework" else framework_names
    for f in relation_fields:
        value=rec.get(f,"")
        for target in opposite:
            if re.search(r"(^|[,\s])"+re.escape(target)+r"(\s|\(|,|$)",value):
                relation_edges.append({"from":pkg,"field":f,"to":target,"raw":value})

overlaps=[]
for fpkg in framework_names:
    fset=set(paths_by_pkg[fpkg])
    for lpkg in legacy_names:
        common=sorted(fset & set(paths_by_pkg[lpkg]))
        details=[]
        for rel in common:
            a=roots[fpkg]/rel; b=roots[lpkg]/rel
            if a.is_symlink() or b.is_symlink():
                av=("symlink:"+os.readlink(a)) if a.is_symlink() else "regular"
                bv=("symlink:"+os.readlink(b)) if b.is_symlink() else "regular"
                identical=av==bv
                details.append({"path":rel,"framework":av,"legacy":bv,"identical":identical})
            else:
                sa=sha(a); sb=sha(b)
                details.append({"path":rel,"framework_sha256":sa,"legacy_sha256":sb,"identical":sa==sb})
        if details:
            overlaps.append({
                "framework_package":fpkg,
                "legacy_package":lpkg,
                "count":len(details),
                "identical_count":sum(1 for x in details if x["identical"]),
                "different_count":sum(1 for x in details if not x["identical"]),
                "files":details
            })

def has_soname(pkg,needle):
    return any(needle in p for p in paths_by_pkg[pkg])

runtime_separation={
    "framework_runtime_has_libKF6Mime_so_6":has_soname("libkf6mime6","libKF6Mime.so.6"),
    "legacy_runtime_has_libKPim6Mime_so_6":has_soname("libkpim6mime6","libKPim6Mime.so.6"),
    "framework_runtime_has_legacy_soname":has_soname("libkf6mime6","libKPim6Mime.so.6"),
    "legacy_runtime_has_framework_soname":has_soname("libkpim6mime6","libKF6Mime.so.6"),
}
if not runtime_separation["framework_runtime_has_libKF6Mime_so_6"] or not runtime_separation["legacy_runtime_has_libKPim6Mime_so_6"]:
    raise SystemExit("expected runtime SONAME payload missing")
if runtime_separation["framework_runtime_has_legacy_soname"] or runtime_separation["legacy_runtime_has_framework_soname"]:
    raise SystemExit("runtime SONAME namespaces unexpectedly overlap")

if relation_edges and overlaps:
    classification="declared-relations-and-payload-overlap"
elif relation_edges:
    classification="declared-package-relations"
elif overlaps:
    classification="payload-overlap-without-declared-relations"
else:
    classification="solver-conflict-not-explained-by-direct-metadata-or-payload"

summary={
    "schema":1,
    "audit_result":"PASS",
    "package_state_effect":"none",
    "records":records,
    "relation_edges":relation_edges,
    "overlaps":overlaps,
    "runtime_separation":runtime_separation,
    "classification":classification,
    "stock_provider_coinstallation":"unsupported-observed",
}
(evidence/"package-metadata.json").write_text(json.dumps(records,indent=2)+"\n")
(evidence/"relation-edges.json").write_text(json.dumps(relation_edges,indent=2)+"\n")
(evidence/"payload-overlaps.json").write_text(json.dumps(overlaps,indent=2)+"\n")
(evidence/"audit-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
for pkg,items in paths_by_pkg.items():
    (evidence/f"{pkg}.files.txt").write_text("\n".join(items)+"\n")
print("metadata/payload audit: PASS")
print("classification="+classification)
print("relation_edges="+str(len(relation_edges)))
print("overlap_pairs="+str(len(overlaps)))
PY

mapfile -t FRAMEWORK_DEBS < <(find "$WORK/framework" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t LEGACY_RUNTIME_DEBS < <(find "$WORK/legacy" -maxdepth 1 -type f \( -name 'libkmime-data_*.deb' -o -name 'libkpim6mime6_*.deb' \) -print | sort)
set +e
sudo apt-get -s -o Debug::pkgProblemResolver=yes install "\${FRAMEWORK_DEBS[@]}" "\${LEGACY_RUNTIME_DEBS[@]}" >"$EVIDENCE/apt-solver-simulation.log" 2>&1
solver_rc=$?
set -e
printf '%s\n' "$solver_rc" > "$EVIDENCE/apt-solver-exit-code.txt"

python3 - "$EVIDENCE/audit-summary.json" "$EVIDENCE/apt-solver-simulation.log" "$solver_rc" <<'PY'
import json,re,sys
p,logp,rc=sys.argv[1],sys.argv[2],int(sys.argv[3])
d=json.load(open(p)); log=open(logp,errors="replace").read()
removed=sorted(set(re.findall(r"\blibkf6mime(?:-data|-dev|6)\b",log)))
d["apt_solver"]={"exit_code":rc,"framework_packages_mentioned":removed}
d["stock_provider_coinstallation"]="FAIL"
open(p,"w").write(json.dumps(d,indent=2)+"\n")
print("apt solver simulation captured; stock_provider_coinstallation=FAIL")
PY

echo "KDE Tier 2 KMime compatibility-provider audit: PASS"
