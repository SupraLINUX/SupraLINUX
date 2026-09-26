#!/usr/bin/env bash
set -Eeuo pipefail

[[ "$#" -eq 1 ]] || { echo "Usage: $0 <kuserfeedback|prison>" >&2; exit 2; }
NODE="$1"
case "${NODE}" in
  kuserfeedback|prison) ;;
  *) echo "Unsupported Batch 11 node: ${NODE}" >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAMPAIGN="${ROOT}/manifests/kde-tier1-package-campaign-batch11.json"

eval "$(python3 - "${CAMPAIGN}" "${NODE}" <<'PY'
import json, shlex, sys
d=json.load(open(sys.argv[1]))
n=d["nodes"][sys.argv[2]]
s=d["shared_predecessors"]
vals={
 "UPSTREAM_VERSION":n["upstream_version"],
 "SOURCE_PACKAGE":n["source_package"],
 "DEBIAN_VERSION":n["package_version"],
 "UPSTREAM_URL":n["source_url"],
 "UPSTREAM_SHA256":n["source_sha256"],
 "SIGNING_KEY_SHA256":n["signing_key"]["sha256"],
 "EXPECTED_TEST_COUNT":n["expected_test_count"],
 "ECM_VERSION":s["extra_cmake_modules"]["version"],
 "ECM_DEB_SHA256":s["extra_cmake_modules"]["deb_sha256"],
 "REFERENCE_SNAPSHOT_SHA256":s["packaging_trees"]["snapshot_json_sha256"],
 "TREE_HASHES_SHA256":s["packaging_trees"]["tree_hashes_tsv_sha256"],
}
for k,v in vals.items():
    print(f"{k}={shlex.quote(str(v))}")
PY
)"

PACKAGE_META="${ROOT}/packages/kde/${NODE}/debian"
CONSUMER_META="${ROOT}/packages/kde/${NODE}/consumer"
WORK_DIR="${ROOT}/.work/kde-tier1-package-batch11/${NODE}"
SOURCE_WORK="${WORK_DIR}/source"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-package-batch11/${NODE}"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar"
MIRROR="${SBUILD_MIRROR:-http://azure.archive.ubuntu.com/ubuntu}"

: "${ECM_ARTIFACT_DIR:?ECM_ARTIFACT_DIR must point at retained ECM PASS artifact}"
: "${TIER1_REFERENCE_DIR:?TIER1_REFERENCE_DIR must point at retained Tier 1 packaging-tree artifact}"

STATE=FAIL
STAGE='initialization'
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${SOURCE_WORK}" "${OUT_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"

write_result() {
  local rc="$?" finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT_JSON}" "${NODE}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished}" "${UPSTREAM_VERSION}" "${DEBIAN_VERSION}" <<'PY'
import json, sys
from pathlib import Path
p,node,state,rc,stage,started,finished,version,debver=sys.argv[1:]
Path(p).write_text(json.dumps({
 "node":node,
 "state":state,
 "exit_code":int(rc),
 "stage":stage,
 "started_at":started,
 "finished_at":finished,
 "authoritative":False,
 "runner_class":"github-hosted-ubuntu-26.04",
 "upstream_authority":"kde-upstream",
 "upstream_version":version,
 "debian_version":debver,
 "ecm_predecessor":"6.30.0-0supralinux3",
 "claim":"hosted-clean-package-preflight",
 "lane":"multi-surface-optional",
 "lintian_gate":"sbuild-summary-plus-dsc-plus-changes",
 "downstream_eligible":state=="PASS",
},indent=2)+"\n")
PY
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "=== SupraLINUX KDE Tier 1 Batch 11: ${NODE} ${UPSTREAM_VERSION} (${DEBIAN_VERSION}) ==="

STAGE='campaign-validation'
python3 - "${CAMPAIGN}" "${NODE}" "${PACKAGE_META}/rules" "${PACKAGE_META}/control" <<'PY'
import json,re,sys
from pathlib import Path
d=json.load(open(sys.argv[1]))
node=sys.argv[2]
n=d["nodes"][node]
rules=Path(sys.argv[3]).read_text()
control=Path(sys.argv[4]).read_text()
if d.get("schema") != 2 or d.get("batch") != "tier1-batch-11" or d.get("lane") != "multi-surface-optional":
    raise SystemExit("Batch 11 campaign mismatch")
if d.get("selected_nodes") != ["kuserfeedback","prison"]:
    raise SystemExit("Batch 11 selected node set changed")
if n.get("state") not in {"prepared-pending-build","remediation-pending-build","FAIL","PASS"}:
    raise SystemExit(f"{node}: state is not attemptable")
if n.get("kde_framework_build_dependencies") != []:
    raise SystemExit(f"{node}: must remain Tier 1")
for key,value in n.get("cmake_required_options",{}).items():
    token=f"-D{key}={value}"
    if token not in rules:
        raise SystemExit(f"{node}: debian/rules missing {token}")
m=re.search(r"Build-Depends:\s*(.*?)(?:\n\S|\Z)",control,re.S)
if not m:
    raise SystemExit("Build-Depends missing")
field=" ".join(x.strip() for x in m.group(1).splitlines())
for package in n.get("feature_required_build_providers",[]):
    if not re.search(rf"(?<![A-Za-z0-9+.-]){re.escape(package)}(?=\s|\(|,|$)",field):
        raise SystemExit(f"{node}: feature provider {package} missing from Build-Depends")
PY

for f in control rules changelog README.source copyright.reference upstream/signing-key.asc source/format; do
  test -s "${PACKAGE_META}/${f}"
done
test -s "${CONSUMER_META}/CMakeLists.txt"
test -s "${CONSUMER_META}/main.cpp"
printf '%s  %s\n' "${SIGNING_KEY_SHA256}" "${PACKAGE_META}/upstream/signing-key.asc" | sha256sum --check --strict

STAGE='retained-input-validation'
ECM_DEB="$(find "${ECM_ARTIFACT_DIR}" -maxdepth 2 -type f -name "extra-cmake-modules_${ECM_VERSION}_all.deb" -print -quit)"
[[ -n "${ECM_DEB}" && -s "${ECM_DEB}" ]] || { echo "Retained ECM PASS .deb missing" >&2; exit 1; }
printf '%s  %s\n' "${ECM_DEB_SHA256}" "${ECM_DEB}" | sha256sum --check --strict
[[ "$(dpkg-deb -f "${ECM_DEB}" Package)" == extra-cmake-modules ]]
[[ "$(dpkg-deb -f "${ECM_DEB}" Version)" == "${ECM_VERSION}" ]]
sha256sum "${ECM_DEB}" > "${EVIDENCE_DIR}/ecm-predecessor-sha256.txt"

REFERENCE_SNAPSHOT="${TIER1_REFERENCE_DIR}/snapshot.json"
TREE_HASHES="${TIER1_REFERENCE_DIR}/tree-hashes.tsv"
test -s "${REFERENCE_SNAPSHOT}"
test -s "${TREE_HASHES}"
printf '%s  %s\n' "${REFERENCE_SNAPSHOT_SHA256}" "${REFERENCE_SNAPSHOT}" | sha256sum --check --strict
printf '%s  %s\n' "${TREE_HASHES_SHA256}" "${TREE_HASHES}" | sha256sum --check --strict

TREE_ROOT="${TIER1_REFERENCE_DIR}/trees/debian/${NODE}"
test -s "${TREE_ROOT}/tree-files.sha256"
EXPECTED_TREE_MANIFEST_SHA="$(awk -F '\t' -v node="${NODE}" '$1=="debian" && $2==node {print $6}' "${TREE_HASHES}")"
[[ "${EXPECTED_TREE_MANIFEST_SHA}" =~ ^[0-9a-f]{64}$ ]] || { echo "No retained Debian tree manifest hash for ${NODE}" >&2; exit 1; }
printf '%s  %s\n' "${EXPECTED_TREE_MANIFEST_SHA}" "${TREE_ROOT}/tree-files.sha256" | sha256sum --check --strict
(cd "${TREE_ROOT}" && sha256sum --check --strict tree-files.sha256)
printf '%s\n' "${EXPECTED_TREE_MANIFEST_SHA}" > "${EVIDENCE_DIR}/retained-tree-manifest-sha256.txt"

STAGE='host-validation'
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends   binutils ca-certificates cmake curl dbus-daemon devscripts dpkg-dev g++ lintian   mmdebstrap ninja-build pkg-config python3 sbuild uidmap ubuntu-keyring xz-utils   qt6-declarative-dev-tools
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true
{ cat /etc/os-release; uname -a; python3 --version; sbuild --version; mmdebstrap --version; lintian --version; } > "${EVIDENCE_DIR}/host.txt"

STAGE='upstream-source'
ORIG_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 --output "${ORIG_TARBALL}" "${UPSTREAM_URL}"
printf '%s  %s\n' "${UPSTREAM_SHA256}" "${ORIG_TARBALL}" | sha256sum --check --strict
SRCNAME="${SOURCE_PACKAGE#kf6-}"
tar -xJf "${ORIG_TARBALL}" -C "${SOURCE_WORK}"
EXTRACTED="${SOURCE_WORK}/${SRCNAME}-${UPSTREAM_VERSION}"
SOURCE_DIR="${SOURCE_WORK}/${SOURCE_PACKAGE}-${UPSTREAM_VERSION}"
test -d "${EXTRACTED}"
mv "${EXTRACTED}" "${SOURCE_DIR}"
cp -a "${PACKAGE_META}" "${SOURCE_DIR}/debian"
cp -a "${TREE_ROOT}/debian/copyright" "${SOURCE_DIR}/debian/copyright"

python3 - "${SOURCE_DIR}/debian/copyright" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1])
lines=p.read_text().splitlines()
start=next((i for i,x in enumerate(lines) if x.strip()=="Files: debian/*"),None)
if start is None:
    raise SystemExit("reference copyright lacks Files: debian/* stanza")
lic=next((i for i in range(start+1,len(lines)) if lines[i].startswith("License:")),None)
if lic is None:
    raise SystemExit("reference debian stanza lacks License")
if not any("SupraLINUX Project" in x for x in lines[start:lic]):
    lines.insert(lic,"           2026, SupraLINUX Project")
p.write_text("\n".join(lines)+"\n")
PY

python3 - "${CAMPAIGN}" "${NODE}" "${SOURCE_DIR}/debian" "${TREE_ROOT}" "${EVIDENCE_DIR}" <<'PY'
import json,shutil,sys
from pathlib import Path
n=json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]
deb=Path(sys.argv[3]); tree=Path(sys.argv[4]); evidence=Path(sys.argv[5])
def classify(line,arch="amd64"):
    s=line.strip()
    if "@Base" not in s:
        return None
    tags=s[1:s.index(")")].split("|") if s.startswith("(") else []
    if any(t.startswith("optional=") for t in tags):
        return "optional"
    applicable=True
    for t in tags:
        if not t.startswith("arch="):
            continue
        values=t[5:].split()
        positive=[v for v in values if not v.startswith("!")]
        negative=[v[1:] for v in values if v.startswith("!")]
        if arch in negative or (positive and arch not in positive):
            applicable=False
    return "required" if applicable else "nonoptional-inapplicable"
rows=[]
for abi in n["abi_contracts"]:
    src=tree/"debian"/abi["symbols_file"]
    if not src.is_file():
        raise SystemExit(f"missing retained symbols reference {src}")
    shutil.copy2(src,deb/abi["symbols_file"])
    counts={"total":0,"optional":0,"nonoptional-inapplicable":0,"required":0}
    for line in src.read_text(errors="replace").splitlines():
        kind=classify(line)
        if kind:
            counts["total"]+=1
            counts[kind]+=1
    if counts["required"] <= 0:
        raise SystemExit(f"{abi['surface']}: no required amd64 exports")
    rows.append(f"{abi['surface']} total={counts['total']} optional={counts['optional']} nonoptional_inapplicable_amd64={counts['nonoptional-inapplicable']} required_amd64={counts['required']}")
(evidence/"abi-reference-counts.txt").write_text("\n".join(rows)+"\n")
PY
chmod +x "${SOURCE_DIR}/debian/rules"
if [[ -e "${SOURCE_DIR}/debian/run-tests-under-x.sh" ]]; then chmod +x "${SOURCE_DIR}/debian/run-tests-under-x.sh"; fi

STAGE='source-development-contract'
python3 "${ROOT}/scripts/audit-kde-development-contract.py" source   --node "${NODE}" --campaign "${CAMPAIGN}" --source-dir "${SOURCE_DIR}"   --control "${SOURCE_DIR}/debian/control"   --output "${EVIDENCE_DIR}/source-development-contract.json"

STAGE='source-package'
pushd "${SOURCE_WORK}" >/dev/null
dpkg-source -b "$(basename "${SOURCE_DIR}")"
popd >/dev/null
DSC="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.dsc"
DEBIAN_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.debian.tar.xz"
test -s "${DSC}"
test -s "${DEBIAN_TARBALL}"
sha256sum "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/source-package-sha256.txt"

STAGE='sbuild-rootfs'
rm -f "${CHROOT_TARBALL}"
mmdebstrap --mode=unshare --variant=buildd --architectures=amd64 --components=main,universe   --skip=output/mknod --format=tar resolute "${CHROOT_TARBALL}" "${MIRROR}" |& tee "${EVIDENCE_DIR}/rootfs.log"
test -s "${CHROOT_TARBALL}"
sha256sum "${CHROOT_TARBALL}" > "${EVIDENCE_DIR}/rootfs-sha256.txt"

STAGE='sbuild'
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --arch-all   --extra-package="${ECM_DEB}" --build-dir="${OUT_DIR}" "${DSC}" |& tee "${EVIDENCE_DIR}/sbuild.log"
if grep -Eq '^Lintian:[[:space:]]+fail[[:space:]]*$' "${EVIDENCE_DIR}/sbuild.log"; then
  echo "sbuild reported Lintian failure" >&2
  exit 1
fi
grep -Eq "100% tests passed, 0 tests failed out of ${EXPECTED_TEST_COUNT}" "${EVIDENCE_DIR}/sbuild.log" || {
  echo "Expected exact CTest PASS count ${EXPECTED_TEST_COUNT} not found" >&2
  exit 1
}

mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
mapfile -t EXPECTED_PACKAGES < <(python3 - "${CAMPAIGN}" "${NODE}" <<'PY'
import json,sys
for x in json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]["binary_contracts"]:
    print(x["name"])
PY
)
(( ${#DEBS[@]} == ${#EXPECTED_PACKAGES[@]} && ${#DDEBS[@]} > 0 && ${#CHANGES[@]} == 1 && ${#BUILDINFO[@]} == 1 )) || {
  echo "Unexpected artifact counts deb=${#DEBS[@]} expected=${#EXPECTED_PACKAGES[@]} ddeb=${#DDEBS[@]} changes=${#CHANGES[@]} buildinfo=${#BUILDINFO[@]}" >&2
  exit 1
}
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/ecm-buildinfo-proof.txt"

python3 - "${CAMPAIGN}" "${NODE}" "${BUILDINFO[0]}" "${EVIDENCE_DIR}/feature-providers.txt" <<'PY'
import json,re,sys
n=json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]
text=open(sys.argv[3]).read()
out=[]
for package in n.get("feature_required_build_providers",[]):
    if not re.search(rf"(?<![A-Za-z0-9+.-]){re.escape(package)} \(=",text):
        raise SystemExit(f"buildinfo missing feature provider {package}")
    out.append(package)
open(sys.argv[4],"w").write("\n".join(out)+"\n")
PY

STAGE='artifact-contract'
declare -A DEB_BY_PACKAGE=()
for deb in "${DEBS[@]}"; do
  p="$(dpkg-deb -f "${deb}" Package)"
  DEB_BY_PACKAGE["${p}"]="${deb}"
  [[ "$(dpkg-deb -f "${deb}" Version)" == "${DEBIAN_VERSION}" ]]
done
for p in "${EXPECTED_PACKAGES[@]}"; do
  [[ -n "${DEB_BY_PACKAGE[$p]:-}" ]] || { echo "Expected binary missing: ${p}" >&2; exit 1; }
done

python3 - "${CAMPAIGN}" "${NODE}" "${OUT_DIR}" <<'PY'
import json,subprocess,sys
from pathlib import Path
n=json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]
out=Path(sys.argv[3])
debs={}
for p in out.glob("*.deb"):
    debs[subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()]=p
def field(p,name):
    r=subprocess.run(["dpkg-deb","-f",str(p),name],text=True,capture_output=True)
    return r.stdout.strip() if r.returncode==0 else ""
for c in n["binary_contracts"]:
    p=debs[c["name"]]
    ma=field(p,"Multi-Arch") or None
    if field(p,"Architecture") != c["architecture"]:
        raise SystemExit(f"{c['name']}: Architecture mismatch")
    if ma != c["multi_arch"]:
        raise SystemExit(f"{c['name']}: Multi-Arch mismatch")
PY

: > "${EVIDENCE_DIR}/dbgsym-contracts.txt"
for ddeb in "${DDEBS[@]}"; do
  dbgpkg="$(dpkg-deb -f "${ddeb}" Package)"
  dbgver="$(dpkg-deb -f "${ddeb}" Version)"
  dbgdep="$(dpkg-deb -f "${ddeb}" Depends)"
  [[ "${dbgpkg}" == *-dbgsym && "${dbgver}" == "${DEBIAN_VERSION}" ]]
  basepkg="${dbgpkg%-dbgsym}"
  [[ -n "${DEB_BY_PACKAGE[$basepkg]:-}" ]] || { echo "dbgsym without local base package: ${dbgpkg}" >&2; exit 1; }
  [[ "${dbgdep}" == *"${basepkg} (= ${DEBIAN_VERSION})"* ]] || { echo "dbgsym dependency mismatch: ${dbgpkg}" >&2; exit 1; }
  printf '%s %s Depends: %s\n' "${dbgpkg}" "${dbgver}" "${dbgdep}" >> "${EVIDENCE_DIR}/dbgsym-contracts.txt"
done

STAGE='abi-contract'
python3 - "${CAMPAIGN}" "${NODE}" "${OUT_DIR}" "${EVIDENCE_DIR}/abi-reference-counts.txt" "${EVIDENCE_DIR}/abi-generated-counts.txt" <<'PY'
import json,re,subprocess,sys,tempfile
from pathlib import Path
n=json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]
out=Path(sys.argv[3]); refs=Path(sys.argv[4]).read_text(); ev=Path(sys.argv[5])
debs={}
for p in out.glob("*.deb"):
    debs[subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()]=p
required={}
for line in refs.splitlines():
    m=re.match(r"(\S+).* required_amd64=(\d+)$",line)
    if m:
        required[m.group(1)]=int(m.group(2))
rows=[]
for abi in n["abi_contracts"]:
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        p=debs[abi["runtime_package"]]
        subprocess.run(["dpkg-deb","-x",str(p),str(root/"data")],check=True)
        subprocess.run(["dpkg-deb","-e",str(p),str(root/"control")],check=True)
        libs=list((root/"data").rglob(abi["soname"]))
        if not libs:
            raise SystemExit(f"{abi['surface']}: SONAME payload missing")
        dyn=subprocess.check_output(["readelf","-d",str(libs[0])],text=True)
        if f"Library soname: [{abi['soname']}]" not in dyn:
            raise SystemExit(f"{abi['surface']}: SONAME mismatch")
        symbols=root/"control"/"symbols"
        if not symbols.is_file():
            raise SystemExit(f"{abi['surface']}: symbols metadata missing")
        generated=sum(1 for line in symbols.read_text(errors="replace").splitlines() if "@Base" in line)
        floor=required.get(abi["surface"],0)
        if generated < floor:
            raise SystemExit(f"{abi['surface']}: exports {generated} below required floor {floor}")
        rows.append(f"{abi['surface']} generated={generated} required_floor={floor} soname={abi['soname']}")
ev.write_text("\n".join(rows)+"\n")
PY

STAGE='qml-contract'
python3 - "${CAMPAIGN}" "${NODE}" "${OUT_DIR}" "${EVIDENCE_DIR}/qml-contracts.txt" <<'PY'
import json,subprocess,sys,tempfile
from pathlib import Path
n=json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]
out=Path(sys.argv[3]); evidence=Path(sys.argv[4])
bypkg={}
for p in out.glob("*.deb"):
    bypkg[subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()]=p
seen=[]
for c in n.get("qml_contracts",[]):
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        subprocess.run(["dpkg-deb","-x",str(bypkg[c["package"]]),str(root)],check=True)
        modules=[]
        for q in root.rglob("qmldir"):
            for line in q.read_text(errors="replace").splitlines():
                line=line.strip()
                if line.startswith("module "):
                    modules.append(line.split(None,1)[1])
        if c["required_root_module"] not in modules:
            raise SystemExit(f"{c['package']}: missing {c['required_root_module']}; got {sorted(set(modules))}")
    seen.append((c["required_root_module"],c["package"]))
evidence.write_text("\n".join(f"{m}\t{p}" for m,p in seen)+"\n")
PY

STAGE='development-contract'
python3 "${ROOT}/scripts/audit-kde-development-contract.py" artifact   --node "${NODE}" --campaign "${CAMPAIGN}" --debs-dir "${OUT_DIR}"   --consumer-cmake "${CONSUMER_META}/CMakeLists.txt"   --output "${EVIDENCE_DIR}/development-contract.json"

STAGE='artifact-capture'
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" "${EVIDENCE_DIR}/"

STAGE='lintian-source-binary'
lintian --fail-on error "${DSC}" "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian-source-binary.log"

STAGE='consumer-runtime-closure'
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${DEBS[@]}" |& tee "${EVIDENCE_DIR}/consumer-runtime-install.log"
sudo apt-get check |& tee "${EVIDENCE_DIR}/consumer-runtime-check.log"
: > "${EVIDENCE_DIR}/consumer-runtime-packages.txt"
for p in "${EXPECTED_PACKAGES[@]}"; do
  v="$(dpkg-query -W -f='${Version}' "${p}")"
  [[ "${v}" == "${DEBIAN_VERSION}" ]]
  printf '%s=%s\n' "${p}" "${v}" >> "${EVIDENCE_DIR}/consumer-runtime-packages.txt"
done

STAGE='qml-import-smoke'
QML_ROOT="${WORK_DIR}/qml-smoke"
mkdir -p "${QML_ROOT}"
idx=0
while IFS=$'\t' read -r module _package; do
  qml="${QML_ROOT}/smoke-${idx}.qml"
  out="${EVIDENCE_DIR}/smoke-${idx}.qml.imports.json"
  printf 'import QtQml\nimport %s\nQtObject {}\n' "${module}" > "${qml}"
  /usr/lib/qt6/libexec/qmlimportscanner -rootPath "${QML_ROOT}" -importPath /usr/lib/"$(dpkg-architecture -qDEB_HOST_MULTIARCH)"/qt6/qml > "${out}"
  python3 - "${out}" "${module}" <<'PY'
import json,sys
items=json.load(open(sys.argv[1]))
expected=sys.argv[2]
if not any(x.get("name")==expected for x in items):
    raise SystemExit(f"QML import scanner did not resolve {expected}")
PY
  idx=$((idx+1))
done < "${EVIDENCE_DIR}/qml-contracts.txt"
(( idx > 0 ))

STAGE='consumer-smoke'
CONSUMER_BUILD="${WORK_DIR}/consumer-build"
cmake -S "${CONSUMER_META}" -B "${CONSUMER_BUILD}" -GNinja -DCMAKE_BUILD_TYPE=Release |& tee "${EVIDENCE_DIR}/consumer-configure.log"
cmake --build "${CONSUMER_BUILD}" --verbose |& tee "${EVIDENCE_DIR}/consumer-build.log"
QT_QPA_PLATFORM=offscreen "${CONSUMER_BUILD}/${NODE}-consumer" |& tee "${EVIDENCE_DIR}/consumer-run.log"

STAGE='dag-pass-evidence'
python3 - "${CAMPAIGN}" "${NODE}" "${EVIDENCE_DIR}/dag-node.txt" <<'PY'
import json,sys
from pathlib import Path
n=json.load(open(sys.argv[1]))["nodes"][sys.argv[2]]
lines=[
 f"node={sys.argv[2]}",
 "state=PASS",
 f"upstream_version={n['upstream_version']}",
 f"debian_version={n['package_version']}",
 "ecm_predecessor=6.30.0-0supralinux3",
 "tests=PASS-exact-count",
 "lintian=PASS-source-and-binary",
 "apt_check=PASS",
 "consumer_smoke=PASS",
 "qml_import_smoke=PASS",
 "development_contract=PASS",
 "downstream_eligible=yes",
]
for abi in n["abi_contracts"]:
    lines.append(f"abi={abi['surface']}:{abi['soname']}")
for provider in n.get("feature_required_build_providers",[]):
    lines.append(f"feature_provider={provider}")
Path(sys.argv[3]).write_text("\n".join(lines)+"\n")
PY

STATE=PASS
STAGE='complete'
echo "KDE Tier 1 Batch 11 node ${NODE}: PASS"
