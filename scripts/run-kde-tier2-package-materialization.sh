#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="${1:-}"
[[ -n "${NODE}" ]] || { echo "Usage: $0 <node>" >&2; exit 2; }

CONTRACTS="${ROOT}/manifests/kde-tier2-package-contracts.json"
TIER2="${ROOT}/manifests/kde-frameworks-tier2.json"
WORK="${ROOT}/.work/kde-tier2-materialization/${NODE}"
EVIDENCE="${ROOT}/evidence/kde-tier2-materialization/${NODE}"
BUILD="${WORK}/build"
REF="${WORK}/reference"
SRC="${BUILD}/source"
STATE=FAIL
STAGE=initialization

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${BUILD}" "${REF}" "${EVIDENCE}/source-package"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result() {
    local rc=$?
    python3 - "${EVIDENCE}/result.json" "${NODE}" "${STATE}" "${rc}" "${STAGE}" <<'PY'
import json,sys
from pathlib import Path
path,node,state,rc,stage=sys.argv[1:]
p=Path(path)
data={}
if p.exists() and p.stat().st_size:
    data=json.loads(p.read_text())
data.update({
    "schema":1,
    "node":node,
    "result":state,
    "exit_code":int(rc),
    "stage":stage,
    "claim":"deterministic-package-tree-materialization",
    "package_attempted":False,
    "package_state_effect":"none",
})
p.write_text(json.dumps(data,indent=2)+"\n")
PY
}
trap write_result EXIT

. /etc/os-release
[[ "${ID}" == "ubuntu" && "${VERSION_ID}" == "26.04" ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }

eval "$(python3 - "${CONTRACTS}" "${TIER2}" "${NODE}" <<'PY'
import json,shlex,sys
contracts=json.load(open(sys.argv[1]))
tier2=json.load(open(sys.argv[2]))
node_id=sys.argv[3]
node=contracts["nodes"][node_id]
canonical={n["id"]:n for n in tier2["nodes"]}[node_id]
vals={
 "SOURCE_PACKAGE":node["source_package"],
 "UPSTREAM_VERSION":node["upstream_version"],
 "PACKAGE_VERSION":node["package_version_candidate"],
 "SOURCE_SHA":node["source_sha256"],
 "SOURCE_URL":canonical["source_url"],
 "DEBIAN_VERSION":node["technical_references"]["debian"]["version"],
 "DEBIAN_DSC_SHA":node["technical_references"]["debian"]["dsc_sha256"],
 "DEBIAN_TAR_SHA":node["technical_references"]["debian"]["debian_tar_sha256"],
 "DEBIAN_ORIG_SHA":node["technical_references"]["debian"]["orig_tar_sha256"],
 "ORIG_MATCHES":str(node["technical_references"]["debian"].get("orig_matches_kde_authority",False)).lower(),
}
for k,v in vals.items():
    print(f"{k}={shlex.quote(str(v))}")
PY
)"

STAGE=tooling
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl debian-archive-keyring dpkg-dev xz-utils

SID_LIST="${WORK}/sid.sources.list"
SID_LISTS="${WORK}/apt-lists-sid"
cat > "${SID_LIST}" <<'EOF'
deb-src [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian sid main
EOF
sudo mkdir -p "${SID_LISTS}"
sudo chown _apt:root "${SID_LISTS}"
sid_apt=(-o "Dir::Etc::sourcelist=${SID_LIST}" -o "Dir::Etc::sourceparts=-" -o "Dir::State::lists=${SID_LISTS}" -o "APT::Get::List-Cleanup=0")
sudo apt-get "${sid_apt[@]}" update

STAGE=technical-reference
(
  cd "${REF}"
  apt-get "${sid_apt[@]}" source --download-only "${SOURCE_PACKAGE}=${DEBIAN_VERSION}"
)
DSC="${REF}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.dsc"
DEBTAR="${REF}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.debian.tar.xz"
DEBORIG="${REF}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
[[ -f "${DSC}" && -f "${DEBTAR}" && -f "${DEBORIG}" ]] || { echo "Incomplete Debian source reference" >&2; exit 1; }
echo "${DEBIAN_DSC_SHA}  ${DSC}" | sha256sum -c -
echo "${DEBIAN_TAR_SHA}  ${DEBTAR}" | sha256sum -c -
echo "${DEBIAN_ORIG_SHA}  ${DEBORIG}" | sha256sum -c -

if [[ "${ORIG_MATCHES}" == "true" ]]; then
    [[ "${DEBIAN_ORIG_SHA}" == "${SOURCE_SHA}" ]] || { echo "Reference orig claims authority match but hashes differ" >&2; exit 1; }
else
    [[ "${DEBIAN_ORIG_SHA}" != "${SOURCE_SHA}" ]] || { echo "Expected pinned reference-orig mismatch disappeared" >&2; exit 1; }
fi

STAGE=authority-source
AUTH_ORIG="${BUILD}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl -LfsS "${SOURCE_URL}" -o "${AUTH_ORIG}"
echo "${SOURCE_SHA}  ${AUTH_ORIG}" | sha256sum -c -
mkdir -p "${SRC}"
tar -xf "${AUTH_ORIG}" -C "${SRC}" --strip-components=1
tar -xf "${DEBTAR}" -C "${SRC}"

STAGE=supralinux-overlay
python3 "${ROOT}/scripts/materialize_kde_tier2_package.py" --node "${NODE}" --source-root "${SRC}" | tee "${EVIDENCE}/materialization.json"

STAGE=tree-contract
python3 - "${SRC}" "${EVIDENCE}" <<'PY'
import hashlib,json,os,stat,sys
from pathlib import Path
root=Path(sys.argv[1])
out=Path(sys.argv[2])

def make_manifest(base):
    rows=[]
    for path in sorted(base.rglob("*")):
        rel=path.relative_to(root).as_posix()
        if rel.startswith(".pc/") or "/.pc/" in f"/{rel}/":
            continue
        st=path.lstat()
        mode=stat.S_IMODE(st.st_mode)
        if path.is_symlink():
            rows.append({"path":rel,"mode":oct(mode),"type":"symlink","target":os.readlink(path)})
        elif path.is_file():
            rows.append({"path":rel,"mode":oct(mode),"type":"file","sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    blob=(json.dumps(rows,sort_keys=True,separators=(",",":"))+"\n").encode()
    return hashlib.sha256(blob).hexdigest(),blob

digest,blob=make_manifest(root)
(out/"tree-manifest.json").write_bytes(blob)
(out/"tree.sha256").write_text(digest+"\n")
ddigest,dblob=make_manifest(root/"debian")
(out/"debian-tree-manifest.json").write_bytes(dblob)
(out/"debian-tree.sha256").write_text(ddigest+"\n")
PY

mkdir -p "${EVIDENCE}/packaging-snippets"
cp "${SRC}/debian/control" "${SRC}/debian/rules" "${SRC}/debian/supralinux-materialization.json" "${EVIDENCE}/packaging-snippets/"
sed -n '1,24p' "${SRC}/debian/changelog" > "${EVIDENCE}/packaging-snippets/changelog-head.txt"

require_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "${actual}" != "${expected}" ]]; then
        printf 'tree-contract FAIL: %s expected=%q actual=%q\n' "${label}" "${expected}" "${actual}" >&2
        return 1
    fi
    printf 'tree-contract PASS: %s=%q\n' "${label}" "${actual}"
}

require_contains() {
    local label="$1" needle="$2" file="$3"
    if ! grep -Fq -- "${needle}" "${file}"; then
        printf 'tree-contract FAIL: %s missing %q in %s\n' "${label}" "${needle}" "${file}" >&2
        return 1
    fi
    printf 'tree-contract PASS: %s\n' "${label}"
}

changelog_source="$(dpkg-parsechangelog -l"${SRC}/debian/changelog" -S Source)"
changelog_version="$(dpkg-parsechangelog -l"${SRC}/debian/changelog" -S Version)"
require_eq "changelog-source" "${SOURCE_PACKAGE}" "${changelog_source}"
require_eq "changelog-version" "${PACKAGE_VERSION}" "${changelog_version}"
require_contains "maintainer" 'Maintainer: SupraLINUX Build System <build@supralinux.invalid>' "${SRC}/debian/control"
require_contains "original-maintainer" 'XSBC-Original-Maintainer:' "${SRC}/debian/control"

if python3 - "${CONTRACTS}" "${NODE}" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
raise SystemExit(0 if d["nodes"][sys.argv[2]].get("python_module") else 1)
PY
then
    PY_MODULE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]["python_module"])' "${CONTRACTS}" "${NODE}")"
    PY_PACKAGE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]["supralinux_additional_binary_packages"][0])' "${CONTRACTS}" "${NODE}")"
    require_contains "python-binding-cmake-profile" '-DBUILD_PYTHON_BINDINGS=ON' "${SRC}/debian/rules"
    require_contains "python-binary-package" "Package: ${PY_PACKAGE}" "${SRC}/debian/control"
    require_contains "python-install-module" "${PY_MODULE}" "${SRC}/debian/${PY_PACKAGE}.install"
fi

STAGE=source-package
(
  cd "${SRC}"
  dpkg-source -b .
)
cp "${BUILD}/"*.dsc "${BUILD}/"*.debian.tar.* "${AUTH_ORIG}" "${EVIDENCE}/source-package/"
sha256sum "${EVIDENCE}/source-package/"* > "${EVIDENCE}/source-package.sha256"

python3 - "${EVIDENCE}" "${NODE}" "${SOURCE_PACKAGE}" "${PACKAGE_VERSION}" <<'PY'
import json,sys
from pathlib import Path
out=Path(sys.argv[1])
result={}
result_path=out/"result.json"
if result_path.exists() and result_path.stat().st_size:
    result=json.loads(result_path.read_text())
result.update({
  "source_package":sys.argv[3],
  "package_version":sys.argv[4],
  "tree_sha256":(out/"tree.sha256").read_text().strip(),
  "debian_tree_sha256":(out/"debian-tree.sha256").read_text().strip(),
})
result_path.write_text(json.dumps(result,indent=2)+"\n")
PY

STATE=PASS
STAGE=complete
echo "KDE Tier 2 package materialization: PASS (${NODE})"
echo "package-attempted=false package-state-effect=none"
