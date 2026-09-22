#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-support-package-contracts.json"
WORK="${ROOT}/.work/kde-tier3-support-packaging-tree"
EVIDENCE="${ROOT}/evidence/kde-tier3-support-packaging-tree"
UBUNTU_LIST="${WORK}/ubuntu.sources.list"
DEBIAN_LIST="${WORK}/debian.sources.list"
UBUNTU_LISTS="${WORK}/apt-lists-ubuntu"
DEBIAN_LISTS="${WORK}/apt-lists-debian"
STATE=FAIL
STAGE=initialization

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}" "${EVIDENCE}/trees"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result() {
  local rc=$?
  python3 - "${EVIDENCE}/result.json" "${STATE}" "${rc}" "${STAGE}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); data={}
if p.exists():
    try: data=json.loads(p.read_text())
    except Exception: data={}
data.update({
 "result":sys.argv[2],
 "exit_code":int(sys.argv[3]),
 "stage":sys.argv[4],
 "claim":"technical-packaging-tree-only",
 "authoritative":False,
 "package_state_effect":"none",
})
p.write_text(json.dumps(data,indent=2)+"\n")
PY
}
trap write_result EXIT

. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }
python3 "${ROOT}/scripts/validate_kde_tier3_support_packaging_tree.py"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends debian-archive-keyring dpkg-dev ubuntu-keyring xz-utils

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

mapfile -t rows < <(python3 - "${MANIFEST}" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
for node in m["packaging_tree_capture"]["selected_components"]:
    refs=m["technical_references"][node]
    for side in m["packaging_tree_capture"]["selected_sides"]:
        r=refs[side]
        checks={x["file"]:x["sha256"] for x in r["checksums_sha256"]}
        dsc=next((f for f in checks if f.endswith(".dsc")),None)
        deb=next((f for f in checks if ".debian.tar." in f),None)
        orig=next((f for f in checks if ".orig.tar." in f and not f.endswith(".asc")),None)
        if not all((dsc,deb,orig)):
            raise SystemExit(f"{node}/{side}: incomplete source checksum contract")
        print("\t".join([node,side,r["source_package"],r["version"],dsc,checks[dsc],deb,checks[deb],orig,checks[orig]]))
PY
)

STAGE=source-download
for row in "${rows[@]}"; do
  IFS=$'\t' read -r node side source version dsc_file dsc_sha deb_file deb_sha orig_file orig_sha <<<"${row}"
  dir="${WORK}/${side}/${node}"
  mkdir -p "${dir}"
  pushd "${dir}" >/dev/null
  if [[ "${side}" == ubuntu ]]; then
    apt-get "${ubuntu_apt[@]}" source --download-only "${source}=${version}"
  else
    apt-get "${debian_apt[@]}" source --download-only "${source}=${version}"
  fi
  popd >/dev/null

  for spec in "${dsc_file}:${dsc_sha}" "${deb_file}:${deb_sha}" "${orig_file}:${orig_sha}"; do
    file="${spec%%:*}"
    expected="${spec#*:}"
    actual="$(sha256sum "${dir}/${file}" | awk '{print $1}')"
    [[ "${actual}" == "${expected}" ]] || { echo "${node}/${side}: SHA mismatch for ${file}" >&2; exit 1; }
  done

  extract="${dir}/source"
  dpkg-source -x "${dir}/${dsc_file}" "${extract}" >/dev/null
  [[ -d "${extract}/debian" ]] || { echo "${node}/${side}: debian tree missing" >&2; exit 1; }
  mkdir -p "${EVIDENCE}/trees/${side}/${node}"
  cp -a "${extract}/debian" "${EVIDENCE}/trees/${side}/${node}/"
done

STAGE=normalization
python3 - "${MANIFEST}" "${EVIDENCE}" <<'PY'
import hashlib,json,os,stat,sys
from pathlib import Path

manifest=json.load(open(sys.argv[1]))
out=Path(sys.argv[2])

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tree_record(root):
    lines=[]; files=[]
    for path in sorted(root.rglob("*")):
        rel=path.relative_to(root).as_posix()
        st=path.lstat()
        mode=stat.S_IMODE(st.st_mode)
        if path.is_symlink():
            target=os.readlink(path)
            digest=hashlib.sha256(("symlink:"+target).encode()).hexdigest()
            kind="symlink"
        elif path.is_file():
            digest=sha(path)
            kind="file"
        elif path.is_dir():
            continue
        else:
            kind="other"
            digest=""
        lines.append(f"{kind}\t{mode:o}\t{digest}\t{rel}")
        files.append({"path":rel,"kind":kind,"mode":f"{mode:o}","sha256":digest})
    payload="\n".join(lines)+"\n"
    return hashlib.sha256(payload.encode()).hexdigest(),files,payload

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
    fields=("Source","Package","Architecture","Multi-Arch","Depends","Pre-Depends","Recommends","Suggests","Provides","Replaces","Breaks","Conflicts","Build-Depends","Build-Depends-Indep")
    return [{k:p[k] for k in fields if k in p} for p in paras]

index={"schema":1,"authority":False,"role":"technical-packaging-tree-only","nodes":{}}
for node in manifest["packaging_tree_capture"]["selected_components"]:
    index["nodes"][node]={}
    for side in manifest["packaging_tree_capture"]["selected_sides"]:
        root=out/"trees"/side/node/"debian"
        digest,files,payload=tree_record(root)
        (out/"trees"/side/node/"tree-files.sha256").write_text(payload)
        control=root/"control"
        if not control.exists():
            raise SystemExit(f"{node}/{side}: debian/control missing")
        summary=parse_control(control)
        (out/"trees"/side/node/"control-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
        ref=manifest["technical_references"][node][side]
        index["nodes"][node][side]={
          "source_package":ref["source_package"],
          "source_version":ref["version"],
          "tree_sha256":digest,
          "file_count":len(files),
          "control_summary_sha256":sha(out/"trees"/side/node/"control-summary.json"),
        }

(out/"index.json").write_text(json.dumps(index,indent=2,sort_keys=True)+"\n")
(out/"result.json").write_text(json.dumps({
 "schema":1,
 "result":"PASS",
 "claim":"technical-packaging-tree-only",
 "authoritative":False,
 "package_state_effect":"none",
 "index_sha256":sha(out/"index.json"),
},indent=2)+"\n")
print(json.dumps(index,indent=2))
PY

sha256sum "${EVIDENCE}/index.json" > "${EVIDENCE}/index.sha256"
STATE=PASS
STAGE=complete
echo "KDE Tier 3 support packaging-tree capture: PASS"
