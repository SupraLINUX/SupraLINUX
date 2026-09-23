#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="${1:-}"
[[ -n "${NODE}" ]] || { echo "Usage: $0 <node>" >&2; exit 2; }

CAMPAIGN="${ROOT}/manifests/kde-tier3-build-level1.json"
: "${ROOTFS_ARTIFACT_DIR:?missing shared Resolute rootfs artifact}"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

WORK="${ROOT}/.work/kde-tier3-build-level1/${NODE}"
INPUTS="${WORK}/inputs"
OUT="${WORK}/out"
EVIDENCE="${ROOT}/evidence/kde-tier3-build-level1/${NODE}"
RESULT="${EVIDENCE}/result.json"
STATE=INFRA
STAGE=initialization
PACKAGE_ATTEMPTED=false
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${INPUTS}" "${OUT}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result() {
  local rc=$? finished
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT}" "${NODE}" "${STATE}" "${rc}" "${STAGE}" "${PACKAGE_ATTEMPTED}" "${STARTED_AT}" "${finished}" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); data={}
if p.exists() and p.stat().st_size:
    try: data=json.loads(p.read_text())
    except Exception: data={}
data.update({
  "schema":1,
  "node":sys.argv[2],
  "result":sys.argv[3],
  "exit_code":int(sys.argv[4]),
  "stage":sys.argv[5],
  "package_attempted":sys.argv[6].lower()=="true",
  "started_at":sys.argv[7],
  "finished_at":sys.argv[8],
  "claim":"hosted-clean-package-preflight",
  "authoritative":False,
})
p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
PY
}
trap write_result EXIT

STAGE=campaign-input-plan
python3 - "${CAMPAIGN}" "${NODE}" "${EVIDENCE}" <<'PY'
import json,shlex,sys
from pathlib import Path
campaign_path,node_id,outdir=sys.argv[1:]
c=json.load(open(campaign_path))
if c.get("execution_authorized") is not True:
    raise SystemExit("Tier3 Level1 execution is not authorized")
if node_id not in c.get("selected_nodes",[]):
    raise SystemExit(f"unknown Tier3 Level1 node: {node_id}")
n=c["nodes"][node_id]
if n.get("state") not in {"prepared-pending-build","prepared-pending-revalidation","remediation-pending-build"}:
    raise SystemExit(f"{node_id}: not runnable, state={n.get('state')}")
out=Path(outdir); specs=[]
def add_spec(input_id,cfg,kind):
    specs.append({
      "id":input_id,"kind":kind,"workflow_run":cfg.get("workflow_run"),
      "artifact_id":cfg["artifact_id"],"artifact_sha256":cfg["artifact_sha256"],
      "version":cfg["version"],"expected_binary_packages":cfg["expected_binary_packages"],
      "dev_package":cfg.get("dev_package"),
    })
add_spec("extra-cmake-modules",c["shared_predecessors"]["extra-cmake-modules"],"shared")
for input_id in n.get("retained_input_ids",[]):
    add_spec(input_id,c["retained_predecessors"][input_id],"retained")
for input_id in n.get("support_input_ids",[]):
    add_spec(input_id,c["support_predecessors"][input_id],"support")
if len({x["id"] for x in specs})!=len(specs):
    raise SystemExit(f"{node_id}: duplicate input IDs")
mat=n["materialization"]
plan={
 "node":node_id,
 "materialization":{"artifact_id":mat["artifact_id"],"artifact_sha256":mat["artifact_sha256"]},
 "inputs":specs,
 "direct_build_predecessors":n.get("direct_build_predecessors",[]),
 "buildinfo_proof_packages":n.get("buildinfo_proof_packages",[]),
 "extra_buildinfo_proof_packages":n.get("extra_buildinfo_proof_packages",[]),
}
(out/"input-plan.json").write_text(json.dumps(plan,indent=2)+"\n")
env={
 "SOURCE_PACKAGE":n["source_package"],"PACKAGE_VERSION":n["package_version"],
 "EXPECTED_BINARIES_JSON":json.dumps(n["expected_binary_packages"],separators=(",",":")),
 "PROFILE_ASSERTIONS_JSON":json.dumps(n.get("profile_assertions",{}),separators=(",",":")),
 "PYTHON_MODULE":n.get("python_module") or "",
 "QML_PACKAGES_JSON":json.dumps(n.get("qml_packages",[]),separators=(",",":")),
 "SUCCESS_TRANSITION":n.get("success_transition","PASS"),
}
(out/"input-env.sh").write_text("\n".join(f"{k}={shlex.quote(v)}" for k,v in env.items())+"\n")
PY
source "${EVIDENCE}/input-env.sh"

download_artifact() {
  local artifact_id="$1" expected_sha="$2" dest="$3"
  mkdir -p "${dest}"
  local zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2     -H "Authorization: Bearer ${GITHUB_TOKEN}"     -H "Accept: application/vnd.github+json"     -H "X-GitHub-Api-Version: 2022-11-28"     "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${artifact_id}/zip"     -o "${zip}"
  printf '%s  %s\n' "${expected_sha}" "${zip}" | sha256sum --check -
  unzip -q "${zip}" -d "${dest}"
}

STAGE=materialization-download
MAT_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["materialization"]["artifact_id"])' "${EVIDENCE}/input-plan.json")"
MAT_SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["materialization"]["artifact_sha256"])' "${EVIDENCE}/input-plan.json")"
download_artifact "${MAT_ID}" "${MAT_SHA}" "${INPUTS}/materialization"

STAGE=materialization-validation
python3 - "${INPUTS}/materialization" "${NODE}" "${PACKAGE_VERSION}" "${EVIDENCE}" <<'PY'
import hashlib,json,shlex,sys
from pathlib import Path
root=Path(sys.argv[1]); node=sys.argv[2]; version=sys.argv[3]; out=Path(sys.argv[4])
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def one(pattern):
    xs=list(root.rglob(pattern))
    if len(xs)!=1: raise SystemExit(f"{node}: expected one {pattern}, got {len(xs)}")
    return xs[0]
result=one("result.json"); r=json.loads(result.read_text())
if r.get("result")!="PASS" or r.get("package_attempted") is not False:
    raise SystemExit(f"{node}: retained materialization is not source-only PASS")
if r.get("node")!=node or r.get("package_version")!=version:
    raise SystemExit(f"{node}: materialization identity/version drift")
dsc=one("*.dsc"); debtars=list(root.rglob("*.debian.tar.*")); origs=list(root.rglob("*.orig.tar.*"))
if len(debtars)!=1 or len(origs)!=1: raise SystemExit(f"{node}: source artifact set ambiguous")
debtar,orig=debtars[0],origs[0]
for path,key in ((dsc,"dsc_sha256"),(debtar,"debian_tar_sha256"),(orig,"orig_tar_sha256")):
    expected=r.get(key)
    if not isinstance(expected,str) or len(expected)!=64 or sha(path)!=expected:
        raise SystemExit(f"{node}: materialization hash mismatch for {path.name}")
(out/"materialization-result.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
(out/"source-env.sh").write_text(f"DSC={shlex.quote(str(dsc))}\nORIG={shlex.quote(str(orig))}\nDEBIAN_TAR={shlex.quote(str(debtar))}\n")
PY
source "${EVIDENCE}/source-env.sh"

STAGE=predecessor-download
python3 - "${EVIDENCE}/input-plan.json" <<'PY' > "${EVIDENCE}/artifact-inputs.tsv"
import json,sys
p=json.load(open(sys.argv[1]))
for x in p["inputs"]: print(f"{x['id']}\t{x['artifact_id']}\t{x['artifact_sha256']}")
PY
while IFS=$'\t' read -r input_id artifact_id artifact_sha; do
  download_artifact "${artifact_id}" "${artifact_sha}" "${INPUTS}/${input_id}"
done < "${EVIDENCE}/artifact-inputs.tsv"

STAGE=predecessor-validation
python3 - "${EVIDENCE}/input-plan.json" "${INPUTS}" "${EVIDENCE}" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
plan=json.load(open(sys.argv[1])); root=Path(sys.argv[2]); out=Path(sys.argv[3])
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def meta(p):
    pkg=subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()
    ver=subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip()
    return pkg,ver
all_debs=[]; records={}; package_owner={}
for spec in plan["inputs"]:
    input_id=spec["id"]; idir=root/input_id; actual={}; paths={}
    for p in sorted(idir.rglob("*.deb")):
        pkg,ver=meta(p)
        if pkg in actual: raise SystemExit(f"{input_id}: duplicate binary {pkg}")
        if ver!=spec["version"]: raise SystemExit(f"{input_id}: {pkg} version {ver} != {spec['version']}")
        actual[pkg]=sha(p); paths[pkg]=str(p)
        if pkg in package_owner: raise SystemExit(f"duplicate package across retained artifacts: {pkg}")
        package_owner[pkg]=input_id
    if set(actual)!=set(spec["expected_binary_packages"]):
        raise SystemExit(f"{input_id}: binary set mismatch expected={sorted(spec['expected_binary_packages'])} actual={sorted(actual)}")
    if spec.get("dev_package") and spec["dev_package"] not in paths:
        raise SystemExit(f"{input_id}: declared dev package missing: {spec['dev_package']}")
    all_debs.extend(paths[p] for p in sorted(paths)); records[input_id]={**spec,"files":actual}
(out/"retained-inputs.json").write_text(json.dumps(records,indent=2,sort_keys=True)+"\n")
(out/"predecessor-debs.txt").write_text("\n".join(all_debs)+"\n")
proof=[]
for pkg in plan.get("buildinfo_proof_packages",[]):
    matches=[x for x in plan["inputs"] if x.get("dev_package")==pkg]
    if len(matches)!=1: raise SystemExit(f"buildinfo proof package {pkg}: expected one provider")
    proof.append((pkg,matches[0]["version"],matches[0]["id"]))
for pkg in plan.get("extra_buildinfo_proof_packages",[]):
    matches=[x for x in plan["inputs"] if pkg in x["expected_binary_packages"]]
    if len(matches)!=1: raise SystemExit(f"extra buildinfo proof package {pkg}: expected one provider")
    proof.append((pkg,matches[0]["version"],matches[0]["id"]))
for x in plan["inputs"]:
    if x["kind"]=="support" and x.get("dev_package"):
        proof.append((x["dev_package"],x["version"],x["id"]))
(out/"buildinfo-proof-contracts.tsv").write_text("\n".join("\t".join(x) for x in proof)+"\n")
PY
mapfile -t PREDECESSOR_DEBS < "${EVIDENCE}/predecessor-debs.txt"

STAGE=host-validation
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends   binutils cmake curl devscripts dpkg-dev g++ lintian ninja-build pkg-config python3 sbuild uidmap unzip xz-utils
if ! grep -q "^${USER}:" /etc/subuid; then sudo usermod --add-subuids 100000-165535 "${USER}"; fi
if ! grep -q "^${USER}:" /etc/subgid; then sudo usermod --add-subgids 100000-165535 "${USER}"; fi
unshare --user --map-auto true
{ cat /etc/os-release; uname -a; sbuild --version; lintian --version; } > "${EVIDENCE}/host.txt"

CHROOT_TARBALL="$(find "${ROOTFS_ARTIFACT_DIR}" -type f -name resolute-amd64.tar -print -quit)"
ROOTFS_SHA_FILE="$(find "${ROOTFS_ARTIFACT_DIR}" -type f -name rootfs.sha256 -print -quit)"
[[ -n "${CHROOT_TARBALL}" && -s "${CHROOT_TARBALL}" && -n "${ROOTFS_SHA_FILE}" ]]
expected_rootfs="$(awk '{print $1}' "${ROOTFS_SHA_FILE}")"
actual_rootfs="$(sha256sum "${CHROOT_TARBALL}" | awk '{print $1}')"
[[ "${expected_rootfs}" == "${actual_rootfs}" ]]
printf '%s\n' "${actual_rootfs}" > "${EVIDENCE}/rootfs.sha256"
SBUILD_CACHE="${HOME}/.cache/sbuild"; mkdir -p "${SBUILD_CACHE}"; ln -sfn "${CHROOT_TARBALL}" "${SBUILD_CACHE}/resolute-amd64.tar"

STAGE=sbuild
PACKAGE_ATTEMPTED=true
STATE=FAIL
EXTRA_ARGS=()
for deb in "${PREDECESSOR_DEBS[@]}"; do EXTRA_ARGS+=(--extra-package="${deb}"); done
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --arch-all   "${EXTRA_ARGS[@]}" --build-dir="${OUT}" "${DSC}" |& tee "${EVIDENCE}/sbuild.log"

grep -Eq '100% tests passed, 0 tests failed out of [1-9][0-9]*' "${EVIDENCE}/sbuild.log" || {
  echo "${NODE}: no positive non-zero upstream CTest PASS summary found" >&2; exit 1; }

STAGE=selected-profile-proof
python3 - "${PROFILE_ASSERTIONS_JSON}" "${EVIDENCE}/sbuild.log" "${EVIDENCE}/profile-proof.txt" <<'PY'
import json,sys
from pathlib import Path
profile=json.loads(sys.argv[1]); log=Path(sys.argv[2]).read_text(errors="replace"); rows=[]
for key,val in profile.items():
    token=f"-D{key}={val}"
    if token not in log: raise SystemExit(f"selected profile flag missing from build log: {token}")
    rows.append(token)
Path(sys.argv[3]).write_text("\n".join(rows)+"\n")
PY

mapfile -t DEBS < <(find "${OUT}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
(( ${#DEBS[@]} > 0 && ${#CHANGES[@]} == 1 && ${#BUILDINFO[@]} == 1 ))

STAGE=artifact-contract
python3 - "${OUT}" "${EXPECTED_BINARIES_JSON}" "${PACKAGE_VERSION}" "${EVIDENCE}" <<'PY'
import json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]); expected=set(json.loads(sys.argv[2])); version=sys.argv[3]; ev=Path(sys.argv[4]); debs={}
for p in out.glob("*.deb"):
    pkg=subprocess.check_output(["dpkg-deb","-f",str(p),"Package"],text=True).strip()
    ver=subprocess.check_output(["dpkg-deb","-f",str(p),"Version"],text=True).strip()
    if pkg in debs: raise SystemExit(f"duplicate built package: {pkg}")
    if ver!=version: raise SystemExit(f"{pkg}: version {ver} != {version}")
    debs[pkg]=str(p)
if set(debs)!=expected: raise SystemExit(f"binary set mismatch expected={sorted(expected)} actual={sorted(debs)}")
(ev/"built-debs.json").write_text(json.dumps(debs,indent=2,sort_keys=True)+"\n")
PY

STAGE=buildinfo-predecessor-proof
: > "${EVIDENCE}/buildinfo-proof.txt"
while IFS=$'\t' read -r package version provider; do
  [[ -z "${package}" ]] && continue
  grep -F "${package} (= ${version})" "${BUILDINFO[0]}" >> "${EVIDENCE}/buildinfo-proof.txt" || {
    echo "${NODE}: buildinfo does not prove ${provider}/${package}=${version}" >&2; exit 1; }
done < "${EVIDENCE}/buildinfo-proof-contracts.tsv"

STAGE=artifact-capture
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG}" "${DEBIAN_TAR}" > "${EVIDENCE}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${DSC}" "${ORIG}" "${DEBIAN_TAR}" "${EVIDENCE}/"

STAGE=lintian-source-binary
lintian --fail-on error "${DSC}" "${CHANGES[0]}" |& tee "${EVIDENCE}/lintian-source-binary.log"

STAGE=abi-contract
python3 - "${EVIDENCE}/built-debs.json" "${WORK}" "${EVIDENCE}/abi-contract.json" <<'PY'
import json,re,shutil,subprocess,sys
from pathlib import Path
built=json.load(open(sys.argv[1])); work=Path(sys.argv[2]); out=Path(sys.argv[3])
runtime=[pkg for pkg in built if re.match(r"^lib.*6$",pkg)]
if not runtime: raise SystemExit("no versioned runtime library packages found for ABI validation")
rows=[]
for index,pkg in enumerate(sorted(runtime)):
    root=work/f"abi-{index}"
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True); subprocess.check_call(["dpkg-deb","-x",built[pkg],str(root)])
    matches=[]
    for path in root.rglob("*.so*"):
        if path.is_symlink() or not path.is_file(): continue
        r=subprocess.run(["readelf","-d",str(path)],text=True,capture_output=True)
        if r.returncode or "Library soname:" not in r.stdout: continue
        for soname in re.findall(r"Library soname: \[([^\]]+)\]",r.stdout):
            if not soname.endswith(".so.6"): continue
            nm=subprocess.check_output(["nm","-D","--defined-only",str(path)],text=True)
            exports=[x for x in nm.splitlines() if x.strip()]
            if not exports: raise SystemExit(f"{pkg}: {soname} exports are empty")
            matches.append({"package":pkg,"path":str(path),"soname":soname,"exports":len(exports)})
    if not matches: raise SystemExit(f"{pkg}: no ELF SONAME ending .so.6 with non-empty exports")
    rows.extend(matches)
out.write_text(json.dumps(rows,indent=2)+"\n")
PY

STAGE=consumer-runtime-closure
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends   "${PREDECESSOR_DEBS[@]}" "${DEBS[@]}" |& tee "${EVIDENCE}/consumer-runtime-install.log"
sudo apt-get check |& tee "${EVIDENCE}/consumer-runtime-check.log"

python3 - "${EVIDENCE}/built-debs.json" "${PACKAGE_VERSION}" <<'PY'
import json,subprocess,sys
for pkg in json.load(open(sys.argv[1])):
    actual=subprocess.check_output(["dpkg-query","-W","-f=${Version}",pkg],text=True).strip()
    if actual!=sys.argv[2]: raise SystemExit(f"{pkg}: installed version {actual} != {sys.argv[2]}")
PY

STAGE=cmake-config-consumer
python3 - "${EVIDENCE}/built-debs.json" "${WORK}" "${EVIDENCE}" <<'PY'
import json,subprocess,sys
from pathlib import Path
built=json.load(open(sys.argv[1])); work=Path(sys.argv[2]); ev=Path(sys.argv[3])
dev=[pkg for pkg in built if pkg.endswith("-dev") and not pkg.endswith("-dev-bin")]
if len(dev)!=1: raise SystemExit(f"expected one built development package, got {dev}")
pkg=dev[0]; listing=subprocess.check_output(["dpkg","-L",pkg],text=True).splitlines()
configs=sorted(Path(x) for x in listing if x.endswith("Config.cmake") and "/cmake/" in x)
if not configs: raise SystemExit(f"{pkg}: no installed CMake package config")
rows=[]
for index,cfg in enumerate(configs):
    name=cfg.name[:-len("Config.cmake")]
    src=work/f"consumer-{index}"; build=src/"build"; src.mkdir(parents=True,exist_ok=True)
    (src/"CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.29)\nproject(SupraLINUXTier3Consumer LANGUAGES CXX)\n"+f"find_package({name} 6.30 REQUIRED)\n")
    r=subprocess.run(["cmake","-S",str(src),"-B",str(build),"-GNinja"],text=True,capture_output=True)
    (ev/f"consumer-{index}.log").write_text(r.stdout+r.stderr)
    if r.returncode: raise SystemExit(f"{pkg}: CMake consumer failed for {name}")
    targets=list(cfg.parent.glob("*Targets.cmake"))
    if not targets: raise SystemExit(f"{pkg}: no CMake Targets file adjacent to {cfg}")
    rows.append({"package":pkg,"cmake_package":name,"config":str(cfg),"targets":[str(x) for x in targets]})
(ev/"cmake-consumers.json").write_text(json.dumps(rows,indent=2)+"\n")
PY

if [[ "${QML_PACKAGES_JSON}" != "[]" ]]; then
  STAGE=qml-payload
  python3 - "${EVIDENCE}/built-debs.json" "${QML_PACKAGES_JSON}" "${WORK}" "${EVIDENCE}/qml-payload.json" <<'PY'
import json,shutil,subprocess,sys
from pathlib import Path
built=json.load(open(sys.argv[1])); packages=json.loads(sys.argv[2]); work=Path(sys.argv[3]); out=Path(sys.argv[4]); rows=[]
for index,pkg in enumerate(packages):
    if pkg not in built: raise SystemExit(f"declared QML package was not built: {pkg}")
    root=work/f"qml-{index}"
    if root.exists(): shutil.rmtree(root)
    root.mkdir(parents=True); subprocess.check_call(["dpkg-deb","-x",built[pkg],str(root)])
    qmldirs=sorted(root.rglob("qmldir"))
    if not qmldirs: raise SystemExit(f"{pkg}: no qmldir payload")
    rows.append({"package":pkg,"qmldir":[str(x) for x in qmldirs]})
out.write_text(json.dumps(rows,indent=2)+"\n")
PY
fi

if [[ -n "${PYTHON_MODULE}" ]]; then
  STAGE=python-import
  python3 -c "import ${PYTHON_MODULE}; print('python-import=PASS module=${PYTHON_MODULE}')" | tee "${EVIDENCE}/python-import.log"
fi

STAGE=pass-evidence
python3 - "${RESULT}" "${EVIDENCE}" "${PACKAGE_VERSION}" "${SUCCESS_TRANSITION}" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
p=Path(sys.argv[1]); ev=Path(sys.argv[2]); version=sys.argv[3]; transition=sys.argv[4]
data={}
if p.exists() and p.stat().st_size: data=json.loads(p.read_text())
log=(ev/"sbuild.log").read_text(errors="replace")
m=re.search(r"100% tests passed, 0 tests failed out of ([1-9][0-9]*)",log)
artifacts={}
for f in sorted(ev.iterdir()):
    if f.is_file() and (f.suffix in {".deb",".ddeb",".dsc"} or ".tar." in f.name or f.suffix in {".changes",".buildinfo"}):
        artifacts[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
runtime_pending=transition=="pending/runtime-validation-required"
data.update({
 "build_result":"PASS","package_version":version,
 "tests":f"{m.group(1)}/{m.group(1)} PASS" if m else "PASS",
 "lintian":"PASS-errors","apt_check":"PASS","abi_contract":"PASS","cmake_consumer":"PASS",
 "buildinfo_predecessor_proof":"PASS","selected_profile_proof":"PASS",
 "python_import":"PASS" if (ev/"python-import.log").exists() else "not-applicable",
 "qml_payload":"PASS" if (ev/"qml-payload.json").exists() else "not-applicable",
 "canonical_success_transition":transition,
 "downstream_eligible":not runtime_pending,
 "package_state_effect":"none-runtime-validation-pending" if runtime_pending else "PASS",
 "artifacts":artifacts,
})
p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
PY

if [[ "${SUCCESS_TRANSITION}" == "pending/runtime-validation-required" ]]; then STATE=RUNTIME_PENDING; else STATE=PASS; fi
STAGE=complete
echo "KDE Tier 3 Level 1 ${NODE}: build PASS; transition=${SUCCESS_TRANSITION}"
