#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier2-package-contracts.json"
WORK="${ROOT}/.work/kde-tier2-contract-reference"
EVIDENCE="${ROOT}/evidence/kde-tier2-contract-reference"
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
Path(sys.argv[1]).write_text(json.dumps({
 "node":"kde-tier2-contract-reference",
 "state":sys.argv[2],
 "exit_code":int(sys.argv[3]),
 "stage":sys.argv[4],
 "authoritative":False,
 "claim":"packaging-reference-snapshot-only",
 "package_state_effect":"none",
},indent=2)+"\n")
PY
}
trap write_result EXIT

. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }
python3 "${ROOT}/scripts/validate_kde_tier2_package_contracts.py"

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
    refs=c.get("reference_sources",{})
    print(node+"\t"+refs.get("ubuntu",c["source_package"])+"\t"+refs.get("debian",c["source_package"]))
PY
)
for row in "${rows[@]}"; do
  IFS=$'\t' read -r node ubuntu_source debian_source <<<"${row}"
  apt-cache "${ubuntu_apt[@]}" showsrc "${ubuntu_source}" > "${EVIDENCE}/source-records/ubuntu/${node}.txt"
  apt-cache "${debian_apt[@]}" showsrc "${debian_source}" > "${EVIDENCE}/source-records/debian/${node}.txt"
  [[ -s "${EVIDENCE}/source-records/ubuntu/${node}.txt" && -s "${EVIDENCE}/source-records/debian/${node}.txt" ]] || exit 1
done
STAGE="normalization"
python3 - "${MANIFEST}" "${EVIDENCE}" <<'PY'
import functools,json,subprocess,sys
from pathlib import Path
manifest=json.load(open(sys.argv[1]))
out=Path(sys.argv[2])

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

def cmp(a,b):
    va,vb=a["Version"],b["Version"]
    if subprocess.run(["dpkg","--compare-versions",va,"gt",vb]).returncode==0:return 1
    if subprocess.run(["dpkg","--compare-versions",va,"lt",vb]).returncode==0:return -1
    return 0

def upstream(v):
    v=v.split(":",1)[-1]
    return v.rsplit("-",1)[0] if "-" in v else v

def checksums(r):
    out=[]
    for line in r.get("Checksums-Sha256","").splitlines():
        p=line.split()
        if len(p)==3: out.append({"sha256":p[0],"size":int(p[1]),"file":p[2]})
    return out

def select(path,source,enforce_selected_kde_upper_bound=True):
    rs=[r for r in paragraphs(path.read_text()) if r.get("Package")==source]
    if not rs: raise SystemExit(f"missing source record {source}")
    r=sorted(rs,key=functools.cmp_to_key(cmp))[-1]
    up=upstream(r["Version"])
    if enforce_selected_kde_upper_bound and subprocess.run(["dpkg","--compare-versions",up,"gt","6.30.0"]).returncode==0:
        raise SystemExit(f"reference newer than selected KDE: {source} {r['Version']}")
    return {
      "source_package":source,"version":r["Version"],"upstream_version":up,
      "binary_packages":[x.strip() for x in r.get("Binary","").split(",") if x.strip()],
      "build_depends":" ".join(r.get("Build-Depends","").split()),
      "build_depends_indep":" ".join(r.get("Build-Depends-Indep","").split()) or None,
      "vcs_git":r.get("Vcs-Git"),"vcs_browser":r.get("Vcs-Browser"),
      "checksums_sha256":checksums(r),
    }

snapshot={"schema":1,"authority":False,"role":"packaging-reference-only","selected_kde":"6.30.0","nodes":{}}
rows=["node\tubuntu-source\tdebian-source\tubuntu-version\tdebian-version"]
for node in manifest["selected_nodes"]:
    c=manifest["nodes"][node]
    refs=c.get("reference_sources",{})
    ubuntu_source=refs.get("ubuntu",c["source_package"])
    debian_source=refs.get("debian",c["source_package"])
    policy=c.get("reference_version_policy",{})
    u=select(
        out/"source-records"/"ubuntu"/f"{node}.txt",
        ubuntu_source,
        policy.get("ubuntu","selected-kde-series") != "legacy-line-allowed",
    )
    d=select(
        out/"source-records"/"debian"/f"{node}.txt",
        debian_source,
        policy.get("debian","selected-kde-series") != "legacy-line-allowed",
    )
    expected=c.get("reference_expected_binary_packages",{})
    fallback=c.get("compatibility_binary_packages",c.get("target_binary_packages",[]))
    ubuntu_expected=set(expected.get("ubuntu",fallback))
    debian_expected=set(expected.get("debian",[]))
    missing=ubuntu_expected-set(u["binary_packages"])
    if missing: raise SystemExit(f"{node}: Ubuntu reference missing expected binaries: {sorted(missing)}")
    missing=debian_expected-set(d["binary_packages"])
    if missing: raise SystemExit(f"{node}: Debian reference missing expected binaries: {sorted(missing)}")
    snapshot["nodes"][node]={"ubuntu":u,"debian":d}
    rows.append("\t".join([node,ubuntu_source,debian_source,u["version"],d["version"]]))
(out/"snapshot.json").write_text(json.dumps(snapshot,indent=2,sort_keys=True)+"\n")
(out/"versions.tsv").write_text("\n".join(rows)+"\n")
PY

sha256sum "${MANIFEST}" > "${EVIDENCE}/manifest.sha256"
sha256sum "${EVIDENCE}/snapshot.json" "${EVIDENCE}/versions.tsv" > "${EVIDENCE}/snapshot.sha256"
{
 echo "status=PASS"
 echo "authority=false"
 echo "role=packaging-reference-only"
 echo "nodes=$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["selected_nodes"]))' "${MANIFEST}")"
 echo "package_state_effect=none"
} > "${EVIDENCE}/summary.env"
echo "Reference versions:"
cat "${EVIDENCE}/versions.tsv"
echo "Normalized reference snapshot:"
cat "${EVIDENCE}/snapshot.json"
echo "Reference evidence hashes:"
cat "${EVIDENCE}/snapshot.sha256"
STATE=PASS
STAGE=complete
echo "KDE Tier 2 contract reference snapshot: PASS"
