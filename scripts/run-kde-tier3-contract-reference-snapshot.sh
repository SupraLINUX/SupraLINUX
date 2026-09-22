#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-package-contracts.json"
AUDIT="${ROOT}/manifests/kde-tier3-provider-audit.json"
WORK="${ROOT}/.work/kde-tier3-contract-reference"
EVIDENCE="${ROOT}/evidence/kde-tier3-contract-reference"
UBUNTU_LIST="${WORK}/ubuntu.sources.list"
DEBIAN_LIST="${WORK}/debian.sources.list"
UBUNTU_LISTS="${WORK}/apt-lists-ubuntu"
DEBIAN_LISTS="${WORK}/apt-lists-debian"
STATE=FAIL
STAGE=initialization

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}" "${EVIDENCE}/source-records/ubuntu" "${EVIDENCE}/source-records/debian"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result(){
  local rc=$?
  python3 - "${EVIDENCE}/result.json" "${STATE}" "${rc}" "${STAGE}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); d={}
if p.exists() and p.stat().st_size:
    try: d=json.loads(p.read_text())
    except Exception: d={}
d.update({
 "result":sys.argv[2],
 "exit_code":int(sys.argv[3]),
 "stage":sys.argv[4],
 "authoritative":False,
 "claim":"packaging-reference-snapshot-only",
 "package_state_effect":"none",
})
p.write_text(json.dumps(d,indent=2)+"\n")
PY
}
trap write_result EXIT

. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }
python3 "${ROOT}/scripts/validate_kde_tier3_package_contracts.py"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends debian-archive-keyring dpkg-dev ubuntu-keyring

cat > "${UBUNTU_LIST}" <<'EOF'
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://archive.ubuntu.com/ubuntu resolute-updates main universe
deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] http://security.ubuntu.com/ubuntu resolute-security main universe
EOF
cat > "${DEBIAN_LIST}" <<'EOF'
deb-src [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian sid main
EOF

sudo mkdir -p "${UBUNTU_LISTS}" "${DEBIAN_LISTS}"
sudo chown _apt:root "${UBUNTU_LISTS}" "${DEBIAN_LISTS}"
ubuntu_apt=(-o "Dir::Etc::sourcelist=${UBUNTU_LIST}" -o "Dir::Etc::sourceparts=-" -o "Dir::State::lists=${UBUNTU_LISTS}" -o "APT::Get::List-Cleanup=0")
debian_apt=(-o "Dir::Etc::sourcelist=${DEBIAN_LIST}" -o "Dir::Etc::sourceparts=-" -o "Dir::State::lists=${DEBIAN_LISTS}" -o "APT::Get::List-Cleanup=0")
sudo apt-get "${ubuntu_apt[@]}" update
sudo apt-get "${debian_apt[@]}" update

STAGE="source-record-capture"
mapfile -t rows < <(python3 - "${MANIFEST}" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
for node in m["selected_nodes"]:
    c=m["nodes"][node]
    print(node+"\t"+c["source_package"])
PY
)
for row in "${rows[@]}"; do
  IFS=$'\t' read -r node source <<<"${row}"
  apt-cache "${ubuntu_apt[@]}" showsrc "${source}" > "${EVIDENCE}/source-records/ubuntu/${node}.txt"
  apt-cache "${debian_apt[@]}" showsrc "${source}" > "${EVIDENCE}/source-records/debian/${node}.txt"
  [[ -s "${EVIDENCE}/source-records/ubuntu/${node}.txt" && -s "${EVIDENCE}/source-records/debian/${node}.txt" ]] || {
    echo "${node}: missing source record" >&2
    exit 1
  }
done

STAGE="normalization"
python3 - "${MANIFEST}" "${AUDIT}" "${EVIDENCE}" <<'PY'
import functools,json,subprocess,sys
from pathlib import Path
manifest=json.load(open(sys.argv[1]))
audit=json.load(open(sys.argv[2]))
out=Path(sys.argv[3])
selected="6.30.0"

def paragraphs(text):
    result=[]; cur={}; key=None
    for line in text.splitlines():
        if not line.strip():
            if cur: result.append(cur); cur={}; key=None
            continue
        if line[0].isspace() and key:
            cur[key]+="\n"+line.strip(); continue
        if ":" in line:
            key,val=line.split(":",1); cur[key]=val.lstrip()
    if cur: result.append(cur)
    return result

def cmpver(a,b):
    va,vb=a["Version"],b["Version"]
    if subprocess.run(["dpkg","--compare-versions",va,"gt",vb]).returncode==0: return 1
    if subprocess.run(["dpkg","--compare-versions",va,"lt",vb]).returncode==0: return -1
    return 0

def upstream(v):
    v=v.split(":",1)[-1]
    return v.rsplit("-",1)[0] if "-" in v else v

def checksums(r):
    result=[]
    for line in r.get("Checksums-Sha256","").splitlines():
        p=line.split()
        if len(p)==3:
            result.append({"sha256":p[0],"size":int(p[1]),"file":p[2]})
    return result

def choose(path,source,prefer_exact):
    rs=[r for r in paragraphs(path.read_text()) if r.get("Package")==source]
    if not rs: raise SystemExit(f"missing source record {source}")
    eligible=[]
    for r in rs:
        up=upstream(r["Version"])
        if subprocess.run(["dpkg","--compare-versions",up,"le",selected]).returncode==0:
            eligible.append(r)
    if not eligible:
        raise SystemExit(f"{source}: no technical reference at or below selected KDE {selected}")
    exact=[r for r in eligible if upstream(r["Version"])==selected]
    pool=exact if prefer_exact and exact else eligible
    r=sorted(pool,key=functools.cmp_to_key(cmpver))[-1]
    cks=checksums(r)
    names=[x["file"] for x in cks]
    if not any(x.endswith(".dsc") for x in names):
        raise SystemExit(f"{source}: selected record lacks .dsc checksum")
    if not any(".debian.tar." in x for x in names):
        raise SystemExit(f"{source}: selected record lacks Debian tar checksum")
    if not any(".orig.tar." in x and not x.endswith(".asc") for x in names):
        raise SystemExit(f"{source}: selected record lacks orig tar checksum")
    up=upstream(r["Version"])
    return {
      "source_package":source,
      "version":r["Version"],
      "upstream_version":up,
      "exact_selected_kde":up==selected,
      "binary_packages":[x.strip() for x in r.get("Binary","").split(",") if x.strip()],
      "build_depends":" ".join(r.get("Build-Depends","").split()),
      "build_depends_indep":" ".join(r.get("Build-Depends-Indep","").split()) or None,
      "vcs_git":r.get("Vcs-Git"),
      "vcs_browser":r.get("Vcs-Browser"),
      "checksums_sha256":cks,
    }

snapshot={"schema":1,"authority":False,"role":"packaging-reference-only","selected_kde":selected,"nodes":{}}
rows=["node\tubuntu-version\tdebian-version\tdebian-exact-6.30"]
for node in manifest["selected_nodes"]:
    c=manifest["nodes"][node]
    source=c["source_package"]
    u=choose(out/"source-records"/"ubuntu"/f"{node}.txt",source,False)
    d=choose(out/"source-records"/"debian"/f"{node}.txt",source,True)
    audited=audit["components"][node]
    if u["version"] != audited["ubuntu_candidate"]:
        raise SystemExit(f"{node}: Ubuntu source candidate drift: audit={audited['ubuntu_candidate']} capture={u['version']}")
    if audited["provider_decision"]!="supralinux-required":
        raise SystemExit(f"{node}: provider audit is not supralinux-required")
    snapshot["nodes"][node]={"ubuntu":u,"debian":d}
    rows.append("\t".join([node,u["version"],d["version"],"yes" if d["exact_selected_kde"] else "no"]))

(out/"snapshot.json").write_text(json.dumps(snapshot,indent=2,sort_keys=True)+"\n")
(out/"versions.tsv").write_text("\n".join(rows)+"\n")
exact=sum(1 for n in snapshot["nodes"].values() if n["debian"]["exact_selected_kde"])
(out/"result.json").write_text(json.dumps({
 "result":"PASS",
 "claim":"packaging-reference-snapshot-only",
 "authoritative":False,
 "package_state_effect":"none",
 "nodes":len(snapshot["nodes"]),
 "debian_exact_selected_kde":exact,
},indent=2)+"\n")
PY

sha256sum "${MANIFEST}" > "${EVIDENCE}/manifest.sha256"
sha256sum "${EVIDENCE}/snapshot.json" "${EVIDENCE}/versions.tsv" > "${EVIDENCE}/snapshot.sha256"
echo "Reference versions:"
cat "${EVIDENCE}/versions.tsv"
STATE=PASS
STAGE=complete
echo "KDE Tier 3 contract reference snapshot: PASS"
