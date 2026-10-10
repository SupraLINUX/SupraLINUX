#!/usr/bin/env bash
set -Eeuo pipefail

[[ "$#" -eq 1 ]] || { echo "Usage: $0 <kirigami|kquickcharts>" >&2; exit 2; }
NODE="$1"
case "${NODE}" in kirigami|kquickcharts) ;; *) echo "Unsupported Batch 10 node: ${NODE}" >&2; exit 2 ;; esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAMPAIGN="${ROOT}/manifests/kde-tier1-package-campaign-batch10.json"

eval "$(python3 - "${CAMPAIGN}" "${NODE}" <<'PY2'
import json,shlex,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text()); n=d['nodes'][sys.argv[2]]; s=d['shared_predecessors']
vals={
'UPSTREAM_VERSION':n['upstream_version'],'SOURCE_PACKAGE':n['source_package'],'DEBIAN_VERSION':n['package_version'],
'UPSTREAM_URL':n['source_url'],'UPSTREAM_SHA256':n['source_sha256'],'SIGNING_KEY_SHA256':n['signing_key']['sha256'],
'COPYRIGHT_REFERENCE_SHA256':n['copyright']['reference_sha256'],'EXPECTED_TEST_COUNT':n['expected_test_count'],'ECM_VERSION':s['extra_cmake_modules']['version'],
'ECM_DEB_SHA256':s['extra_cmake_modules']['deb_sha256'],'REFERENCE_SNAPSHOT_SHA256':s['packaging_trees']['snapshot_json_sha256'],
'BINARY_CONTRACTS_JSON_SHA256':s['binary_contracts']['contracts_json_sha256']}
for k,v in vals.items(): print(f'{k}={shlex.quote(str(v))}')
PY2
)"

PACKAGE_META="${ROOT}/packages/kde/${NODE}/debian"
CONSUMER_META="${ROOT}/packages/kde/${NODE}/consumer"
WORK_DIR="${ROOT}/.work/kde-tier1-package-batch10/${NODE}"
SOURCE_WORK="${WORK_DIR}/source"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-package-batch10/${NODE}"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar"
MIRROR="${SBUILD_MIRROR:-http://azure.archive.ubuntu.com/ubuntu}"
: "${ECM_ARTIFACT_DIR:?ECM_ARTIFACT_DIR must point at retained ECM PASS artifact}"
: "${TIER1_REFERENCE_DIR:?TIER1_REFERENCE_DIR must point at retained Tier 1 packaging-tree artifact}"
: "${BINARY_CONTRACT_DIR:?BINARY_CONTRACT_DIR must point at retained binary-contract artifact}"
if [[ "${NODE}" == kquickcharts ]]; then : "${KIRIGAMI_ARTIFACT_DIR:?KIRIGAMI_ARTIFACT_DIR must point at a retained/current SupraLINUX Kirigami PASS artifact}"; fi

STATE=FAIL; STAGE=initialization; STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${SOURCE_WORK}" "${OUT_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"
write_result() {
  local rc="$?" finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT_JSON}" "${NODE}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished}" "${UPSTREAM_VERSION}" "${DEBIAN_VERSION}" <<'PY2'
import json,sys
from pathlib import Path
p,node,state,rc,stage,started,finished,version,debver=sys.argv[1:]
Path(p).write_text(json.dumps({'node':node,'state':state,'exit_code':int(rc),'stage':stage,'started_at':started,'finished_at':finished,'authoritative':False,'runner_class':'github-hosted-ubuntu-26.04','upstream_authority':'kde-upstream','upstream_version':version,'debian_version':debver,'ecm_predecessor':'6.30.0-0supralinux3','claim':'hosted-clean-package-preflight','lane':'qml-multisurface','lintian_gate':'sbuild-summary-plus-dsc-plus-changes','downstream_eligible':state=='PASS'},indent=2)+'\n')
PY2
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "=== SupraLINUX KDE Tier 1 Batch 10: ${NODE} ${UPSTREAM_VERSION} (${DEBIAN_VERSION}) ==="

STAGE=campaign-validation
python3 - "${CAMPAIGN}" "${NODE}" <<'PY2'
import json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text()); node=sys.argv[2]; n=d['nodes'][node]
if d.get('schema')!=2 or d.get('batch')!='tier1-batch-10' or d.get('lane')!='qml-multisurface': raise SystemExit('Batch 10 campaign mismatch')
if d.get('selected_nodes')!=['kirigami','kquickcharts']: raise SystemExit('Batch 10 selected node set changed')
if n.get('state') not in {'prepared-pending-build','remediation-pending-build','PASS'}: raise SystemExit(f'{node}: state is not attemptable')
if n.get('kde_framework_build_dependencies')!=[]: raise SystemExit(f'{node}: must remain Tier 1')
if n.get('upstream_defaults',{}).get('BUILD_TESTING')!='ON': raise SystemExit(f'{node}: tests must remain ON')
if len(n.get('abi_contracts',[]))<2: raise SystemExit(f'{node}: multi-surface ABI contract missing')
if node=='kquickcharts':
 p=n.get('package_validation_dependencies',[])
 if len(p)!=1 or p[0].get('node')!='kirigami' or p[0].get('not_kde_framework_build_dependency') is not True:
  raise SystemExit('QuickCharts Kirigami package-validation dependency contract changed')
PY2
for f in control rules changelog README.source copyright.reference upstream/signing-key.asc source/format run-tests-under-x.sh; do test -s "${PACKAGE_META}/${f}"; done
test -s "${CONSUMER_META}/CMakeLists.txt"; test -s "${CONSUMER_META}/main.cpp"
grep -Fq -- '-DBUILD_TESTING=ON' "${PACKAGE_META}/rules"
if grep -Eq 'QT_QML_NO_CACHEGEN=ON|BUILD_QCH=ON' "${PACKAGE_META}/rules"; then echo "Forbidden downstream feature override present in debian/rules" >&2; exit 1; fi
if grep -Eq 'dh_auto_test.*\|\|[[:space:]]*true' "${PACKAGE_META}/rules" "${PACKAGE_META}/run-tests-under-x.sh"; then echo "Forbidden downstream test suppression present" >&2; exit 1; fi
printf '%s  %s\n' "${SIGNING_KEY_SHA256}" "${PACKAGE_META}/upstream/signing-key.asc" | sha256sum --check --strict

STAGE=retained-input-validation
ECM_DEB="$(find "${ECM_ARTIFACT_DIR}" -maxdepth 2 -type f -name "extra-cmake-modules_${ECM_VERSION}_all.deb" -print -quit)"
[[ -n "${ECM_DEB}" && -s "${ECM_DEB}" ]] || { echo "Retained ECM PASS .deb missing" >&2; exit 1; }
printf '%s  %s\n' "${ECM_DEB_SHA256}" "${ECM_DEB}" | sha256sum --check --strict
[[ "$(dpkg-deb -f "${ECM_DEB}" Package)" == extra-cmake-modules && "$(dpkg-deb -f "${ECM_DEB}" Version)" == "${ECM_VERSION}" ]]
sha256sum "${ECM_DEB}" > "${EVIDENCE_DIR}/ecm-predecessor-sha256.txt"
REFERENCE_SNAPSHOT="${TIER1_REFERENCE_DIR}/snapshot.json"; test -s "${REFERENCE_SNAPSHOT}"
printf '%s  %s\n' "${REFERENCE_SNAPSHOT_SHA256}" "${REFERENCE_SNAPSHOT}" | sha256sum --check --strict
BINARY_CONTRACTS_JSON="${BINARY_CONTRACT_DIR}/binary-contracts.json"; test -s "${BINARY_CONTRACTS_JSON}"
printf '%s  %s\n' "${BINARY_CONTRACTS_JSON_SHA256}" "${BINARY_CONTRACTS_JSON}" | sha256sum --check --strict
python3 - "${CAMPAIGN}" "${NODE}" "${TIER1_REFERENCE_DIR}" "${EVIDENCE_DIR}" <<'PY2'
import hashlib,json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text()); node=sys.argv[2]; tree=Path(sys.argv[3]); evidence=Path(sys.argv[4]); n=d['nodes'][node]

def classify_export(line, arch='amd64'):
    s=line.strip()
    if '@Base' not in s:
        return None
    tags=[]
    if s.startswith('('):
        try:
            tags=s[1:s.index(')')].split('|')
        except ValueError as exc:
            raise SystemExit(f'{node}: malformed symbols tag line: {line}') from exc
    if any(tag.startswith('optional=') for tag in tags):
        return 'optional'
    applicable=True
    for tag in tags:
        if not tag.startswith('arch='):
            continue
        values=tag[5:].split()
        positive=[value for value in values if not value.startswith('!')]
        negative=[value[1:] for value in values if value.startswith('!')]
        if arch in negative or (positive and arch not in positive):
            applicable=False
    return 'required' if applicable else 'nonoptional-inapplicable'

summary=[]
for abi in n['abi_contracts']:
    retained=tree/'trees'/abi['reference_provider']/node/'debian'/abi['symbols_file']
    if not retained.is_file(): raise SystemExit(f'missing retained symbols reference {retained}')
    got=hashlib.sha256(retained.read_bytes()).hexdigest()
    if got!=abi['reference_sha256']: raise SystemExit(f'{retained}: symbols SHA mismatch {got}')
    counts={'total':0,'optional':0,'nonoptional-inapplicable':0,'required':0}
    for line in retained.read_text(errors='replace').splitlines():
        kind=classify_export(line)
        if kind is None:
            continue
        counts['total']+=1
        counts[kind]+=1
    expected={
        'total':abi['reference_export_count'],
        'optional':abi['reference_optional_export_count'],
        'nonoptional-inapplicable':abi['reference_nonoptional_inapplicable_amd64_count'],
        'required':abi['reference_required_export_count_amd64'],
    }
    if counts!=expected:
        raise SystemExit(f"{node}/{abi['surface']}: retained symbols classification {counts} != {expected}")
    if counts['total'] != counts['optional'] + counts['nonoptional-inapplicable'] + counts['required']:
        raise SystemExit(f"{node}/{abi['surface']}: retained symbols classification does not partition total")
    summary.append(
        f"{abi['surface']} total={counts['total']} optional={counts['optional']} "
        f"nonoptional_inapplicable_amd64={counts['nonoptional-inapplicable']} required_amd64={counts['required']}"
    )
(evidence/'abi-reference-counts.txt').write_text('\n'.join(summary)+'\n')
copyright=tree/'trees'/'debian'/node/'debian'/'copyright'
if hashlib.sha256(copyright.read_bytes()).hexdigest()!=n['copyright']['reference_sha256']: raise SystemExit('copyright reference SHA mismatch')
PY2

KIRIGAMI_DEBS=()
if [[ "${NODE}" == kquickcharts ]]; then
  STAGE=kirigami-validation-predecessor
  mapfile -t KIRIGAMI_DEBS < <(find "${KIRIGAMI_ARTIFACT_DIR}" -type f -name '*.deb' -print | sort)
  (( ${#KIRIGAMI_DEBS[@]} >= 18 )) || { echo "Kirigami PASS artifact has too few .deb files: ${#KIRIGAMI_DEBS[@]}" >&2; exit 1; }
  python3 - "${CAMPAIGN}" "${KIRIGAMI_ARTIFACT_DIR}" "${EVIDENCE_DIR}/kirigami-predecessor.txt" <<'PY2'
import json,subprocess,sys
from pathlib import Path
d=json.load(open(sys.argv[1])); root=Path(sys.argv[2]); out=Path(sys.argv[3]); k=d['nodes']['kirigami']; expected=k['package_version']; seen={}; rows=[]
for p in root.rglob('*.deb'):
 pkg=subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip()
 ver=subprocess.check_output(['dpkg-deb','-f',str(p),'Version'],text=True).strip()
 seen[pkg]=ver; rows.append(f'{pkg}={ver}')
for c in k['binary_contracts']:
 if seen.get(c['name'])!=expected: raise SystemExit(f"Kirigami predecessor {c['name']}={seen.get(c['name'])}, expected {expected}")
if seen.get('qml6-module-org-kde-kirigami')!=expected: raise SystemExit('local Kirigami QML predecessor missing')
out.write_text('\n'.join(sorted(rows))+'\n')
PY2
fi

STAGE=host-validation
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]] || { echo "Expected Ubuntu 26.04" >&2; exit 1; }
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends binutils ca-certificates cmake curl dbus-daemon devscripts dpkg-dev g++ lintian mmdebstrap ninja-build pkg-config python3 sbuild uidmap ubuntu-keyring xz-utils qt6-declarative-dev-tools
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true
{ cat /etc/os-release; uname -a; python3 --version; sbuild --version; mmdebstrap --version; lintian --version; } > "${EVIDENCE_DIR}/host.txt"

STAGE=upstream-source
ORIG_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 --output "${ORIG_TARBALL}" "${UPSTREAM_URL}"
printf '%s  %s\n' "${UPSTREAM_SHA256}" "${ORIG_TARBALL}" | sha256sum --check --strict
SRCNAME="${SOURCE_PACKAGE#kf6-}"
tar -xJf "${ORIG_TARBALL}" -C "${SOURCE_WORK}"
EXTRACTED="${SOURCE_WORK}/${SRCNAME}-${UPSTREAM_VERSION}"; SOURCE_DIR="${SOURCE_WORK}/${SOURCE_PACKAGE}-${UPSTREAM_VERSION}"
test -d "${EXTRACTED}"; mv "${EXTRACTED}" "${SOURCE_DIR}"
cp -a "${PACKAGE_META}" "${SOURCE_DIR}/debian"
COPYRIGHT_REFERENCE="${TIER1_REFERENCE_DIR}/trees/debian/${NODE}/debian/copyright"
cp -a "${COPYRIGHT_REFERENCE}" "${SOURCE_DIR}/debian/copyright"
python3 - "${SOURCE_DIR}/debian/copyright" <<'PY2'
import sys
from pathlib import Path
p=Path(sys.argv[1]); lines=p.read_text().splitlines(); start=next((i for i,x in enumerate(lines) if x.strip()=='Files: debian/*'),None)
if start is None: raise SystemExit('reference copyright lacks Files: debian/* stanza')
lic=next((i for i in range(start+1,len(lines)) if lines[i].startswith('License:')),None)
if lic is None: raise SystemExit('reference debian stanza lacks License')
if not any('SupraLINUX Project' in x for x in lines[start:lic]): lines.insert(lic,'           2026, SupraLINUX Project')
p.write_text('\n'.join(lines)+'\n')
PY2
python3 - "${CAMPAIGN}" "${NODE}" "${SOURCE_DIR}/debian" "${TIER1_REFERENCE_DIR}" <<'PY2'
import json,shutil,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text()); node=sys.argv[2]; deb=Path(sys.argv[3]); tree=Path(sys.argv[4]); n=d['nodes'][node]
for abi in n['abi_contracts']:
    shutil.copy2(tree/'trees'/abi['reference_provider']/node/'debian'/abi['symbols_file'], deb/abi['symbols_file'])
PY2
chmod +x "${SOURCE_DIR}/debian/rules" "${SOURCE_DIR}/debian/run-tests-under-x.sh"

STAGE=source-development-contract
python3 "${ROOT}/scripts/audit-kde-development-contract.py" source \
  --node "${NODE}" --campaign "${CAMPAIGN}" --source-dir "${SOURCE_DIR}" \
  --control "${SOURCE_DIR}/debian/control" \
  --output "${EVIDENCE_DIR}/source-development-contract.json"

STAGE=source-package
pushd "${SOURCE_WORK}" >/dev/null; dpkg-source -b "$(basename "${SOURCE_DIR}")"; popd >/dev/null
DSC="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.dsc"; DEBIAN_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.debian.tar.xz"
test -s "${DSC}"; test -s "${DEBIAN_TARBALL}"; sha256sum "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/source-package-sha256.txt"

STAGE=sbuild-rootfs
rm -f "${CHROOT_TARBALL}"
mmdebstrap --mode=unshare --variant=buildd --architectures=amd64 --components=main,universe --skip=output/mknod --format=tar resolute "${CHROOT_TARBALL}" "${MIRROR}" |& tee "${EVIDENCE_DIR}/rootfs.log"
test -s "${CHROOT_TARBALL}"; sha256sum "${CHROOT_TARBALL}" > "${EVIDENCE_DIR}/rootfs-sha256.txt"

STAGE=sbuild
SBUILD_EXTRA=("--extra-package=${ECM_DEB}")
if [[ "${NODE}" == kquickcharts ]]; then for p in "${KIRIGAMI_DEBS[@]}"; do SBUILD_EXTRA+=("--extra-package=${p}"); done; fi
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --arch-all "${SBUILD_EXTRA[@]}" --build-dir="${OUT_DIR}" "${DSC}" |& tee "${EVIDENCE_DIR}/sbuild.log"
if grep -Eq '^Lintian:[[:space:]]+fail[[:space:]]*$' "${EVIDENCE_DIR}/sbuild.log"; then echo "sbuild reported Lintian failure" >&2; exit 1; fi
grep -Eq "100% tests passed, 0 tests failed out of ${EXPECTED_TEST_COUNT}" "${EVIDENCE_DIR}/sbuild.log" || { echo "Expected exact CTest PASS count ${EXPECTED_TEST_COUNT} not found" >&2; exit 1; }
mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
mapfile -t EXPECTED_PACKAGES < <(python3 - "${CAMPAIGN}" "${NODE}" <<'PY2'
import json,sys
from pathlib import Path
for x in json.loads(Path(sys.argv[1]).read_text())['nodes'][sys.argv[2]]['binary_contracts']: print(x['name'])
PY2
)
(( ${#DEBS[@]} == ${#EXPECTED_PACKAGES[@]} && ${#DDEBS[@]} > 0 && ${#CHANGES[@]} == 1 && ${#BUILDINFO[@]} == 1 )) || { echo "Unexpected artifact counts deb=${#DEBS[@]} expected=${#EXPECTED_PACKAGES[@]} ddeb=${#DDEBS[@]} changes=${#CHANGES[@]} buildinfo=${#BUILDINFO[@]}" >&2; exit 1; }
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/ecm-buildinfo-proof.txt"

STAGE=artifact-contract
declare -A DEB_BY_PACKAGE=()
for deb in "${DEBS[@]}"; do p="$(dpkg-deb -f "${deb}" Package)"; DEB_BY_PACKAGE["${p}"]="${deb}"; [[ "$(dpkg-deb -f "${deb}" Version)" == "${DEBIAN_VERSION}" ]]; done
for p in "${EXPECTED_PACKAGES[@]}"; do [[ -n "${DEB_BY_PACKAGE[$p]:-}" ]] || { echo "Expected binary missing: ${p}" >&2; exit 1; }; done
python3 - "${CAMPAIGN}" "${NODE}" "${OUT_DIR}" <<'PY2'
import json,subprocess,sys
from pathlib import Path
n=json.loads(Path(sys.argv[1]).read_text())['nodes'][sys.argv[2]]; out=Path(sys.argv[3]); debs={}
for p in out.glob('*.deb'): debs[subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip()]=p
def field(p,n):
 r=subprocess.run(['dpkg-deb','-f',str(p),n],text=True,capture_output=True); return r.stdout.strip() if r.returncode==0 else ''
def ma(p):
 v=field(p,'Multi-Arch'); return None if v in {'','no'} else v
for c in n['binary_contracts']:
 p=debs[c['name']]
 if field(p,'Architecture')!=c['architecture']: raise SystemExit(f"{c['name']}: Architecture mismatch")
 if ma(p)!=c['multi_arch']: raise SystemExit(f"{c['name']}: Multi-Arch mismatch")
PY2
: > "${EVIDENCE_DIR}/dbgsym-contracts.txt"
for ddeb in "${DDEBS[@]}"; do
  dbgpkg="$(dpkg-deb -f "${ddeb}" Package)"; dbgver="$(dpkg-deb -f "${ddeb}" Version)"; dbgdep="$(dpkg-deb -f "${ddeb}" Depends)"
  [[ "${dbgpkg}" == *-dbgsym && "${dbgver}" == "${DEBIAN_VERSION}" ]]
  basepkg="${dbgpkg%-dbgsym}"
  [[ -n "${DEB_BY_PACKAGE[$basepkg]:-}" ]] || { echo "dbgsym has no matching local binary package: ${dbgpkg}" >&2; exit 1; }
  [[ "${dbgdep}" == *"${basepkg} (= ${DEBIAN_VERSION})"* ]] || { echo "dbgsym exact dependency mismatch: ${dbgpkg}: ${dbgdep}" >&2; exit 1; }
  printf '%s %s Depends: %s\n' "${dbgpkg}" "${dbgver}" "${dbgdep}" >> "${EVIDENCE_DIR}/dbgsym-contracts.txt"
done

STAGE=abi-contract
python3 - "${CAMPAIGN}" "${NODE}" "${OUT_DIR}" "${EVIDENCE_DIR}" <<'PY2'
import json,subprocess,sys,tempfile
from pathlib import Path
n=json.loads(Path(sys.argv[1]).read_text())['nodes'][sys.argv[2]]; out=Path(sys.argv[3]); evidence=Path(sys.argv[4]); debs={}
for p in out.glob('*.deb'): debs[subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip()]=p
summary=[]
for abi in n['abi_contracts']:
 p=debs[abi['runtime_package']]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); subprocess.run(['dpkg-deb','-x',str(p),str(root/'data')],check=True); subprocess.run(['dpkg-deb','-e',str(p),str(root/'control')],check=True)
  libs=list((root/'data').rglob(abi['soname']))
  if not libs: raise SystemExit(f"{abi['surface']}: {abi['soname']} payload missing")
  dyn=subprocess.check_output(['readelf','-d',str(libs[0])],text=True)
  if f'Library soname: [{abi["soname"]}]' not in dyn: raise SystemExit(f"{abi['surface']}: SONAME mismatch")
  sym=root/'control'/'symbols'
  if not sym.is_file(): raise SystemExit(f"{abi['surface']}: binary control symbols missing")
  txt=sym.read_text(errors='replace')
  if abi['soname'] not in txt: raise SystemExit(f"{abi['surface']}: symbols header lacks SONAME")
  if '0supralinux' in txt: raise SystemExit(f"{abi['surface']}: symbols acquired Debian-revision minimum; requires reviewed overlay")
  exports=sum('@Base' in x for x in txt.splitlines())
  required=abi.get('effective_required_export_count_amd64',abi['reference_required_export_count_amd64'])
  if exports < required: raise SystemExit(f"{abi['surface']}: export count {exports} below required amd64 baseline {required}")
  (evidence/f"symbols-{abi['surface']}.txt").write_text(txt)
  summary.append(
      f"{abi['surface']} soname={abi['soname']} exports={exports} "
      f"baseline_total={abi['reference_export_count']} "
      f"reference_required_amd64={abi['reference_required_export_count_amd64']} "
      f"effective_required_amd64={required}"
  )
(evidence/'abi-contracts.txt').write_text('\n'.join(summary)+'\n')
PY2

STAGE='qml-package-contract'
python3 - "${CAMPAIGN}" "${NODE}" "${OUT_DIR}" "${EVIDENCE_DIR}" <<'PY2'
import json,subprocess,sys,tempfile
from pathlib import Path
n=json.load(open(sys.argv[1]))['nodes'][sys.argv[2]]; out=Path(sys.argv[3]); evidence=Path(sys.argv[4]); debs={}
for p in out.glob('*.deb'): debs[subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip()]=p
mods=[]
for q in n['qml_contracts']:
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); subprocess.run(['dpkg-deb','-x',str(debs[q['package']]),str(root)],check=True)
  declared=[]
  for f in root.rglob('qmldir'):
   for line in f.read_text(errors='replace').splitlines():
    if line.startswith('module '): declared.append((line.split(None,1)[1].strip(),str(f.relative_to(root))))
  if not any(m==q['required_root_module'] for m,_ in declared): raise SystemExit(f"{q['package']}: required root module {q['required_root_module']} missing")
  mods.extend(declared)
if not mods: raise SystemExit('no QML module declarations found')
seen=[]
for m,p in mods:
 if m not in [x[0] for x in seen]: seen.append((m,p))
(evidence/'qml-contracts.txt').write_text('\n'.join(f'{m}\t{p}' for m,p in seen)+'\n')
PY2

STAGE=development-contract
python3 "${ROOT}/scripts/audit-kde-development-contract.py" artifact \
  --node "${NODE}" --campaign "${CAMPAIGN}" --debs-dir "${OUT_DIR}" \
  --consumer-cmake "${CONSUMER_META}/CMakeLists.txt" \
  --output "${EVIDENCE_DIR}/development-contract.json"

STAGE=artifact-capture
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" "${EVIDENCE_DIR}/"

STAGE=lintian-source-binary
lintian --fail-on error "${DSC}" "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian-source-binary.log"

STAGE=consumer-runtime-closure
INSTALL_DEBS=("${DEBS[@]}")
if [[ "${NODE}" == kquickcharts ]]; then INSTALL_DEBS+=("${KIRIGAMI_DEBS[@]}" "${ECM_DEB}"); fi
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${INSTALL_DEBS[@]}" |& tee "${EVIDENCE_DIR}/consumer-runtime-install.log"
sudo apt-get check |& tee "${EVIDENCE_DIR}/consumer-runtime-check.log"
: > "${EVIDENCE_DIR}/consumer-runtime-packages.txt"
for p in "${EXPECTED_PACKAGES[@]}"; do v="$(dpkg-query -W -f='${Version}' "${p}")"; [[ "${v}" == "${DEBIAN_VERSION}" ]]; printf '%s=%s\n' "${p}" "${v}" >> "${EVIDENCE_DIR}/consumer-runtime-packages.txt"; done
if [[ "${NODE}" == kquickcharts ]]; then
  KIRIGAMI_VERSION="$(python3 - "${CAMPAIGN}" <<'PY2'
import json,sys
print(json.load(open(sys.argv[1]))['nodes']['kirigami']['package_version'])
PY2
)"
  [[ "$(dpkg-query -W -f='${Version}' qml6-module-org-kde-kirigami)" == "${KIRIGAMI_VERSION}" ]] || { echo "QuickCharts resolved non-SupraLINUX Kirigami QML runtime" >&2; exit 1; }
  [[ "$(dpkg-query -W -f='${Version}' extra-cmake-modules)" == "${ECM_VERSION}" ]] || { echo "QuickCharts resolved non-SupraLINUX ECM development provider" >&2; exit 1; }
  printf 'qml6-module-org-kde-kirigami=%s\n' "${KIRIGAMI_VERSION}" >> "${EVIDENCE_DIR}/consumer-runtime-packages.txt"
  printf 'extra-cmake-modules=%s\n' "${ECM_VERSION}" >> "${EVIDENCE_DIR}/consumer-runtime-packages.txt"
fi

STAGE='qml-import-smoke'
QML_ROOT="${WORK_DIR}/qml-smoke"; mkdir -p "${QML_ROOT}"
idx=0
while IFS=$'\t' read -r module _path; do
  qml="${QML_ROOT}/smoke-${idx}.qml"; out="${EVIDENCE_DIR}/smoke-${idx}.qml.imports.json"
  printf 'import QtQml\nimport %s\nQtObject {}\n' "${module}" > "${qml}"
  /usr/lib/qt6/libexec/qmlimportscanner -rootPath "${QML_ROOT}" -importPath /usr/lib/"$(dpkg-architecture -qDEB_HOST_MULTIARCH)"/qt6/qml > "${out}"
  python3 - "${out}" "${module}" <<'PY2'
import json,sys
items=json.load(open(sys.argv[1])); expected=sys.argv[2]
if not any(x.get('name')==expected for x in items): raise SystemExit(f'QML import scanner did not resolve {expected}')
PY2
  idx=$((idx+1))
done < "${EVIDENCE_DIR}/qml-contracts.txt"
(( idx > 0 ))

STAGE=consumer-smoke
CONSUMER_BUILD="${WORK_DIR}/consumer-build"
cmake -S "${CONSUMER_META}" -B "${CONSUMER_BUILD}" -GNinja -DCMAKE_BUILD_TYPE=Release |& tee "${EVIDENCE_DIR}/consumer-configure.log"
cmake --build "${CONSUMER_BUILD}" --verbose |& tee "${EVIDENCE_DIR}/consumer-build.log"
QT_QPA_PLATFORM=offscreen "${CONSUMER_BUILD}/${NODE}-consumer" |& tee "${EVIDENCE_DIR}/consumer-run.log"

STAGE=dag-pass-evidence
python3 - "${CAMPAIGN}" "${NODE}" "${EVIDENCE_DIR}/dag-node.txt" <<'PY2'
import json,sys
from pathlib import Path
n=json.loads(Path(sys.argv[1]).read_text())['nodes'][sys.argv[2]]
lines=[f'node={sys.argv[2]}','state=PASS',f'upstream_version={n["upstream_version"]}',f'debian_version={n["package_version"]}','ecm_predecessor=6.30.0-0supralinux3','tests=PASS-via-sbuild-nonzero-ctest','lintian=PASS-source-and-binary','apt_check=PASS','consumer_smoke=PASS','qml_import_smoke=PASS','downstream_eligible=yes']
for a in n['abi_contracts']: lines.append(f"abi={a['surface']}:{a['soname']}")
for p in n.get('package_validation_dependencies',[]): lines.append(f"package_validation_dependency={p['node']}:{p['kind']}")
Path(sys.argv[3]).write_text('\n'.join(lines)+'\n')
PY2
STATE=PASS; STAGE=complete
echo "KDE Tier 1 Batch 10 node ${NODE}: PASS"
