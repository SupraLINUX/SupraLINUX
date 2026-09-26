#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-support-package-contracts.json"
WORK="${ROOT}/.work/kde-tier3-support-contract-reference"
EVIDENCE="${ROOT}/evidence/kde-tier3-support-contract-reference"
UBUNTU_LIST="${WORK}/ubuntu.sources.list"
DEBIAN_LIST="${WORK}/debian.sources.list"
UBUNTU_LISTS="${WORK}/apt-lists-ubuntu"
DEBIAN_LISTS="${WORK}/apt-lists-debian"
STATE=FAIL
STAGE=initialization

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}" "${EVIDENCE}/source-records/ubuntu" "${EVIDENCE}/source-records/debian"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result() {
  local rc=$?
  python3 - "${EVIDENCE}/result.json" "${STATE}" "${rc}" "${STAGE}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
data={}
if p.exists():
    try: data=json.loads(p.read_text())
    except Exception: data={}
data.update({
  "result":sys.argv[2],
  "exit_code":int(sys.argv[3]),
  "stage":sys.argv[4],
  "claim":"packaging-reference-snapshot-only",
  "authoritative":False,
  "package_state_effect":"none",
})
p.write_text(json.dumps(data,indent=2)+"\n")
PY
}
trap write_result EXIT

. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }

python3 "${ROOT}/scripts/validate_kde_tier3_support_package_contracts.py"

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

STAGE=source-record-capture
mapfile -t rows < <(python3 - "${MANIFEST}" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
for node in m["selected_components"]:
    c=m["components"][node]
    refs=c["reference_sources"]
    print(node+"\t"+refs["ubuntu"]+"\t"+refs["debian"])
PY
)

for row in "${rows[@]}"; do
  IFS=$'\t' read -r node ubuntu_source debian_source <<<"${row}"
  apt-cache "${ubuntu_apt[@]}" showsrc "${ubuntu_source}" > "${EVIDENCE}/source-records/ubuntu/${node}.txt"
  apt-cache "${debian_apt[@]}" showsrc "${debian_source}" > "${EVIDENCE}/source-records/debian/${node}.txt"
  [[ -s "${EVIDENCE}/source-records/ubuntu/${node}.txt" ]]
  [[ -s "${EVIDENCE}/source-records/debian/${node}.txt" ]]
done

STAGE=normalization
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

def vercmp(a,b):
    if subprocess.run(["dpkg","--compare-versions",a,"gt",b]).returncode==0: return 1
    if subprocess.run(["dpkg","--compare-versions",a,"lt",b]).returncode==0: return -1
    return 0

def upstream(version):
    v=version.split(":",1)[-1]
    return v.rsplit("-",1)[0] if "-" in v else v

def checksums(record):
    result=[]
    for line in record.get("Checksums-Sha256","").splitlines():
        p=line.split()
        if len(p)==3:
            result.append({"sha256":p[0],"size":int(p[1]),"file":p[2]})
    return result

def select(path,source,side):
    rs=[r for r in paragraphs(path.read_text()) if r.get("Package")==source]
    if not rs: raise SystemExit(f"{side}: missing source record {source}")
    if side=="debian":
        exact=[r for r in rs if upstream(r["Version"])=="6.30.0"]
        if exact:
            rs=exact
        else:
            rs=[r for r in rs if subprocess.run(["dpkg","--compare-versions",upstream(r["Version"]),"le","6.30.0"]).returncode==0]
            if not rs: raise SystemExit(f"{source}: no Debian reference at or below KDE 6.30.0")
    r=sorted(rs,key=functools.cmp_to_key(lambda a,b:vercmp(a["Version"],b["Version"])))[-1]
    return {
      "source_package":source,
      "version":r["Version"],
      "upstream_version":upstream(r["Version"]),
      "binary_packages":[x.strip() for x in r.get("Binary","").split(",") if x.strip()],
      "build_depends":" ".join(r.get("Build-Depends","").split()),
      "build_depends_indep":" ".join(r.get("Build-Depends-Indep","").split()) or None,
      "vcs_git":r.get("Vcs-Git"),
      "vcs_browser":r.get("Vcs-Browser"),
      "checksums_sha256":checksums(r),
    }

snapshot={
  "schema":1,
  "authority":False,
  "role":"packaging-reference-only",
  "selected_kde":"6.30.0",
  "nodes":{},
}
versions=["component\tubuntu-source\tubuntu-version\tdebian-source\tdebian-version"]
for node in manifest["selected_components"]:
    c=manifest["components"][node]
    refs=c["reference_sources"]
    u=select(out/"source-records"/"ubuntu"/f"{node}.txt",refs["ubuntu"],"ubuntu")
    d=select(out/"source-records"/"debian"/f"{node}.txt",refs["debian"],"debian")
    if d["upstream_version"]!="6.30.0":
        raise SystemExit(f"{node}: Debian exact KDE 6.30.0 technical reference unavailable; got {d['version']}")
    snapshot["nodes"][node]={"ubuntu":u,"debian":d}
    versions.append("\t".join([node,u["source_package"],u["version"],d["source_package"],d["version"]]))

(out/"snapshot.json").write_text(json.dumps(snapshot,indent=2,sort_keys=True)+"\n")
(out/"versions.tsv").write_text("\n".join(versions)+"\n")
(out/"result.json").write_text(json.dumps({
  "schema":1,
  "result":"PASS",
  "claim":"packaging-reference-snapshot-only",
  "authoritative":False,
  "package_state_effect":"none",
  "components":manifest["selected_components"],
},indent=2)+"\n")
PY

sha256sum "${MANIFEST}" > "${EVIDENCE}/manifest.sha256"
sha256sum "${EVIDENCE}/snapshot.json" "${EVIDENCE}/versions.tsv" > "${EVIDENCE}/snapshot.sha256"

echo "Reference versions:"
cat "${EVIDENCE}/versions.tsv"
echo "Snapshot digests:"
cat "${EVIDENCE}/snapshot.sha256"

STATE=PASS
STAGE=complete
echo "KDE Tier 3 support contract-reference capture: PASS"
