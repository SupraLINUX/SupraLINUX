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
 "DEBHELPER_COMPAT_LEVEL":contracts["provider_adaptations"]["ubuntu-resolute"]["debhelper_compat"]["selected_level"],
 "CHANGELOG_DISTRIBUTION":contracts["provider_adaptations"]["ubuntu-resolute"]["changelog_distribution"]["selected"],
 "SHIBOKEN_PROVIDER_PACKAGES":" ".join(contracts["provider_adaptations"]["ubuntu-resolute"]["shiboken_clang_discovery"]["provider_packages"]),
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
AUTHORITY_ORIG="${WORK}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.kde-authority.tar.xz"
PACKAGE_ORIG="${BUILD}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl -LfsS "${SOURCE_URL}" -o "${AUTHORITY_ORIG}"
echo "${SOURCE_SHA}  ${AUTHORITY_ORIG}" | sha256sum -c -

if [[ "${ORIG_MATCHES}" == "true" ]]; then
    cp "${AUTHORITY_ORIG}" "${PACKAGE_ORIG}"
else
    STAGE=verified-files-excluded-repack
    AUTH_TREE="${WORK}/authority-tree"
    REF_TREE="${WORK}/reference-orig-tree"
    REF_META="${WORK}/reference-packaging"
    mkdir -p "${AUTH_TREE}" "${REF_TREE}" "${REF_META}"
    tar -xf "${AUTHORITY_ORIG}" -C "${AUTH_TREE}" --strip-components=1
    tar -xf "${DEBORIG}" -C "${REF_TREE}" --strip-components=1
    tar -xf "${DEBTAR}" -C "${REF_META}"
    python3 - "${AUTH_TREE}" "${REF_TREE}" "${REF_META}/debian/copyright" "${EVIDENCE}/repack-verification.json" <<'PY'
import fnmatch,hashlib,json,os,stat,sys
from pathlib import Path

authority=Path(sys.argv[1]); reference=Path(sys.argv[2]); copyright_path=Path(sys.argv[3]); output=Path(sys.argv[4])
lines=copyright_path.read_text().splitlines()
fields={}; current=None
for line in lines:
    if not line.strip(): break
    if line[:1].isspace() and current:
        fields[current]+=" "+line.strip()
    elif ":" in line:
        current,value=line.split(":",1); current=current.strip(); fields[current]=value.strip()
patterns=fields.get("Files-Excluded","").split()
if not patterns:
    raise SystemExit("reference orig differs from KDE authority but Files-Excluded is empty")

def entry_manifest(root):
    out={}
    for p in sorted(root.rglob("*")):
        rel=p.relative_to(root).as_posix()
        st=p.lstat()
        if p.is_symlink():
            out[rel]={"type":"symlink","target":os.readlink(p)}
        elif p.is_file():
            out[rel]={"type":"file","sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"executable":bool(st.st_mode & stat.S_IXUSR)}
    return out

def excluded(path):
    for pattern in patterns:
        base=pattern.rstrip("/")
        if fnmatch.fnmatch(path,pattern) or path==base or path.startswith(base+"/"):
            return True
    return False

auth=entry_manifest(authority)
ref=entry_manifest(reference)
matched=sorted(path for path in auth if excluded(path))
if not matched:
    raise SystemExit("Files-Excluded matched no KDE-authority files")
if any(excluded(path) for path in ref):
    raise SystemExit("reference repack still contains a Files-Excluded path")
filtered={path:value for path,value in auth.items() if not excluded(path)}
if filtered != ref:
    missing=sorted(set(filtered)-set(ref))
    extra=sorted(set(ref)-set(filtered))
    changed=sorted(path for path in set(filtered)&set(ref) if filtered[path]!=ref[path])
    raise SystemExit(f"reference orig differs beyond Files-Excluded: missing={missing[:20]} extra={extra[:20]} changed={changed[:20]}")
payload={"result":"PASS","policy":"verified-files-excluded-repack","patterns":patterns,"excluded_paths":matched,
         "authority_entries":len(auth),"distribution_entries":len(ref)}
output.write_text(json.dumps(payload,indent=2)+"\n")
PY
    cp "${DEBORIG}" "${PACKAGE_ORIG}"
fi

mkdir -p "${SRC}"
tar -xf "${PACKAGE_ORIG}" -C "${SRC}" --strip-components=1
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

if [[ "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("materialization",{}).get("status",""))' "${CONTRACTS}")" == "PASS" ]]; then
    STAGE=materialization-revalidation
    python3 - "${CONTRACTS}" "${NODE}" "${EVIDENCE}/tree.sha256" "${EVIDENCE}/debian-tree.sha256" <<'PY'
import json,sys
contracts_path,node,tree_path,debian_tree_path=sys.argv[1:]
contracts=json.load(open(contracts_path))
expected=contracts.get("materialization",{}).get("evidence",{}).get(node,{})
actual_tree=open(tree_path).read().strip()
actual_debian=open(debian_tree_path).read().strip()
if expected.get("result") != "PASS":
    raise SystemExit(f"{node}: pinned materialization evidence is not PASS")
if expected.get("tree_sha256") != actual_tree:
    raise SystemExit(f"{node}: full-tree content drift: expected {expected.get('tree_sha256')} actual {actual_tree}")
if expected.get("debian_tree_sha256") != actual_debian:
    raise SystemExit(f"{node}: Debian-tree content drift: expected {expected.get('debian_tree_sha256')} actual {actual_debian}")
print(f"materialization revalidation PASS: {node}")
print(f"tree_sha256={actual_tree}")
print(f"debian_tree_sha256={actual_debian}")
PY
fi

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
changelog_distribution="$(dpkg-parsechangelog -l"${SRC}/debian/changelog" -S Distribution)"
require_eq "changelog-source" "${SOURCE_PACKAGE}" "${changelog_source}"
require_eq "changelog-version" "${PACKAGE_VERSION}" "${changelog_version}"
# Value is assigned by the validated Python-to-eval map above.
# shellcheck disable=SC2153
require_eq "changelog-distribution" "${CHANGELOG_DISTRIBUTION}" "${changelog_distribution}"
require_contains "maintainer" 'Maintainer: SupraLINUX Build System <build@supralinux.invalid>' "${SRC}/debian/control"
require_contains "original-maintainer" 'XSBC-Original-Maintainer:' "${SRC}/debian/control"
require_contains "debhelper-compat-provider-level" "debhelper-compat (= ${DEBHELPER_COMPAT_LEVEL})" "${SRC}/debian/control"

python3 - "${CONTRACTS}" "${NODE}" "${SRC}/debian/control" "${SRC}/debian/rules" <<'PY'
import json,re,sys
contracts,node,control_path,rules_path=sys.argv[1:]
c=json.load(open(contracts))["nodes"][node]
control=open(control_path).read()
source=control.split("\n\n",1)[0]
match=re.search(r"^Build-Depends:\s*(.*(?:\n[ \t].*)*)",source,re.M)
if not match:
    raise SystemExit(f"{node}: generated control lacks Build-Depends")
field=" ".join(line.strip() for line in match.group(1).splitlines())
deps=[x.strip() for x in field.split(",") if x.strip()]
names={re.split(r"\s|\(",dep,maxsplit=1)[0] for dep in deps}
for removed in c.get("build_depends_remove",[]):
    if removed in names:
        raise SystemExit(f"{node}: removed technical-reference Build-Depends still present: {removed}")
rules=open(rules_path).read()
for key,value in c.get("selected_profile",{}).items():
    if key=="BUILD_QML_IF_PROVIDER_AVAILABLE" or not isinstance(value,bool):
        continue
    flag=f"-D{key}={'ON' if value else 'OFF'}"
    if flag not in rules:
        raise SystemExit(f"{node}: selected profile flag missing from generated rules: {flag}")
test_command=c.get("rules_auto_test_command")
if test_command and ("\t"+test_command) not in rules:
    raise SystemExit(f"{node}: reviewed dh_auto_test command missing from generated rules")

packages=set(re.findall(r"^Package:\s*(\S+)\s*$",control,re.M))
expected=set(c.get("target_binary_packages",c.get("compatibility_binary_packages",[]))) | set(c.get("supralinux_additional_binary_packages",[]))
if packages!=expected:
    raise SystemExit(f"{node}: generated binary package set mismatch expected={sorted(expected)} actual={sorted(packages)}")
print(f"binary-package-contract PASS: {node} -> {sorted(packages)}")
print(f"generic-package-adaptation-contract PASS: {node}")
PY

if python3 - "${CONTRACTS}" "${NODE}" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
raise SystemExit(0 if d["nodes"][sys.argv[2]].get("python_module") else 1)
PY
then
    PY_MODULE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]["python_module"])' "${CONTRACTS}" "${NODE}")"
    PY_PACKAGE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]["supralinux_additional_binary_packages"][0])' "${CONTRACTS}" "${NODE}")"
    require_contains "python-binding-cmake-profile" '-DBUILD_PYTHON_BINDINGS=ON' "${SRC}/debian/rules"
    # Value is assigned by the validated Python-to-eval map above.
    # shellcheck disable=SC2153
    read -r -a shiboken_provider_packages <<< "${SHIBOKEN_PROVIDER_PACKAGES}"
    for provider_package in "${shiboken_provider_packages[@]}"; do
        require_contains "python-shiboken-clang-provider-${provider_package}" "${provider_package}" "${SRC}/debian/control"
    done
    require_contains "python-binary-package" "Package: ${PY_PACKAGE}" "${SRC}/debian/control"
    require_contains "python-install-module" "${PY_MODULE}" "${SRC}/debian/${PY_PACKAGE}.install"
    python3 - "${CONTRACTS}" "${NODE}" "${SRC}/debian/control" <<'PY'
import json,sys
contracts,node,control_path=sys.argv[1:]
d=json.load(open(contracts)); c=d["nodes"][node]; control=open(control_path).read()
runtime=c.get("python_runtime_contract",{})
providers=runtime.get("provider_packages",[])
if not providers:
    raise SystemExit(f"{node}: missing python runtime provider contract")
for package in providers:
    if package not in control:
        raise SystemExit(f"{node}: generated Python package lacks runtime provider {package}")
print(f"python-runtime-provider-contract PASS: {node} -> {providers}")
PY
fi

python3 - "${CONTRACTS}" "${NODE}" "${SRC}/debian" <<'PY'
import json,sys
from pathlib import Path
contracts,node,debian=sys.argv[1:]
c=json.load(open(contracts))["nodes"][node]
root=Path(debian)

for spec in c.get("binary_package_splits",[]):
    package=spec["package"]
    needles=spec.get("source_match_substrings")
    if needles is None:
        legacy=spec.get("source_match_substring")
        needles=[legacy] if legacy else []
    install=root/f"{package}.install"
    if not install.exists():
        raise SystemExit(f"{node}: split install file missing for {package}")
    lines=[line for line in install.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if len(lines)!=len(needles):
        raise SystemExit(f"{node}: split install payload count mismatch for {package}: expected={len(needles)} actual={lines}")
    for needle in needles:
        matching=[line for line in lines if needle in line]
        if len(matching)!=1:
            raise SystemExit(f"{node}: split install payload mismatch for {package} needle={needle!r}: {lines}")
        for other in root.glob("*.install"):
            if other==install:
                continue
            if any(needle in line for line in other.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")):
                raise SystemExit(f"{node}: split payload {needle!r} still duplicated in {other.name}")
    control=(root/"control").read_text()
    if f"Package: {package}\n" not in control:
        raise SystemExit(f"{node}: split control stanza missing for {package}")
    print(f"binary-split-contract PASS: {node} {package} -> {lines}")

for adjustment in c.get("symbols_adjustments",[]):
    path=root/adjustment["file"]
    rendered=(f" ({adjustment['tag']}){adjustment['symbol']} {adjustment['version']}"
              if adjustment.get("tag") else f" {adjustment['symbol']} {adjustment['version']}")
    lines=path.read_text().splitlines()
    if lines.count(rendered)!=1:
        raise SystemExit(f"{node}: reviewed symbols adjustment missing or duplicated: {rendered}")
    print(f"symbols-adjustment-contract PASS: {node} {rendered.strip()}")
PY

STAGE=source-package
(
  cd "${SRC}"
  dpkg-source -b .
)
cp "${BUILD}/"*.dsc "${BUILD}/"*.debian.tar.* "${PACKAGE_ORIG}" "${EVIDENCE}/source-package/"
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

echo "tree_sha256=$(cat "${EVIDENCE}/tree.sha256")"
echo "debian_tree_sha256=$(cat "${EVIDENCE}/debian-tree.sha256")"
echo "source_package_sha256:"
cat "${EVIDENCE}/source-package.sha256"
STATE=PASS
STAGE=complete
echo "KDE Tier 2 package materialization: PASS (${NODE})"
echo "package-attempted=false package-state-effect=none"
