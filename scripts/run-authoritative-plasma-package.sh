#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Shared engine; defaults preserve the original Plasma lane.
CAMPAIGN="${SUPRALINUX_PACKAGE_CAMPAIGN:-manifests/kde-plasma-package-build.json}"
EVIDENCE_NAME="${SUPRALINUX_PACKAGE_EVIDENCE:-authoritative-plasma-package}"
[[ "${EVIDENCE_NAME}" == authoritative-plasma-package || "${EVIDENCE_NAME}" == authoritative-package-revalidation ]]
WORK="${ROOT}/.work/${EVIDENCE_NAME}"
EVIDENCE="${ROOT}/evidence/${EVIDENCE_NAME}"
MIRROR="${SBUILD_MIRROR:-http://archive.ubuntu.com/ubuntu}"
TEST_IMAGE="${AUTOPKGTEST_QEMU_IMAGE:-/var/lib/supralinux/autopkgtest/resolute-amd64.img}"
CHROOT="${HOME}/.cache/sbuild/resolute-amd64.tar"
STATE="INFRA_INVALID"
STAGE="initialization"
ATTEMPT=false
BUILD_RESULT="not-run"
TEST_RESULT="not-run"
LINTIAN_RESULT="not-run"
STARTED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
NODE=""
PACKAGE_VERSION=""
rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}/out" "${EVIDENCE}/packages" "$(dirname "${CHROOT}")"

finish() {
    local rc=$?
    trap - EXIT
    python3 - "${EVIDENCE}" "${STATE}" "${STAGE}" "${ATTEMPT}" "${BUILD_RESULT}" \
        "${TEST_RESULT}" "${LINTIAN_RESULT}" "${STARTED}" "${NODE}" "${PACKAGE_VERSION}" "${rc}" <<'PY'
import datetime, hashlib, json, os, subprocess, sys
from pathlib import Path
path, state, stage, attempt, build, tests, lintian, started, node, version, rc = sys.argv[1:]
root = Path(path)
payload = {
    "schema": 1, "node": node, "version": version, "state": state,
    "stage": stage, "exit_code": int(rc), "started_at": started,
    "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "workflow_run_id": os.environ.get("GITHUB_RUN_ID"), "workflow_job": os.environ.get("GITHUB_JOB"),
    "authoritative": True, "runner_class": "supralinux-kvm-ubuntu-26.04-ephemeral",
    "package_attempt_consumed": attempt == "true", "sbuild_result": build,
    "lintian_result": lintian, "autopkgtest_result": tests,
    "sbuild_backend": "unshare", "system_test_backend": "autopkgtest-qemu",
    "system_test_acceleration": "kvm-required", "release_publication": False,
    "files_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(root.rglob("*")) if p.is_file() and str(p.relative_to(root)) not in {"result.json", "pipeline.log"}},
}
(root / "result.json").write_text(json.dumps(payload, indent=2) + "\n")
PY
    exit "${rc}"
}
trap finish EXIT
exec > >(tee -a "${EVIDENCE}/pipeline.log") 2>&1

STAGE="authorization"
if [[ "${CAMPAIGN}" == manifests/package-revalidation.json ]]; then
    python3 "${ROOT}/scripts/validate_package_revalidation.py"
else
    python3 "${ROOT}/scripts/validate_plasma_package_build.py"
fi
mapfile -t AUTHORIZED < <(python3 - "${ROOT}" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from importlib.machinery import SourceFileLoader
module = SourceFileLoader("prepare", str(Path(sys.argv[1]) / "scripts/prepare-plasma-package.py")).load_module()
manifest = module.load_campaign()
assert not manifest.get("dependency_hold"), "Known predecessor upgrade conflict requires revalidation"
assert manifest["package_execution_authorized"] is True and manifest["state"] == "execution-authorized"
assert len(manifest["authorized_nodes"]) == 1, "One current node per disposable runner"
node = manifest["authorized_nodes"][0]
_, record = module.contract(node)
print(node)
print(record["version"])
print(record["upstream_url"])
print(record["upstream_sha256"])
print(record["signature_sha256"])
PY
)
[[ ${#AUTHORIZED[@]} == 5 ]] || { printf 'Invalid reviewed package authorization.\n' >&2; exit 1; }
NODE="${AUTHORIZED[0]}"
PACKAGE_VERSION="${AUTHORIZED[1]}"
SOURCE_URL="${AUTHORIZED[2]}"
SOURCE_HASH="${AUTHORIZED[3]}"
SIGNATURE_HASH="${AUTHORIZED[4]}"
python3 "${ROOT}/scripts/freeze-reviewed-package-contract.py" "${NODE}" --output "${EVIDENCE}/build-contract.json"
EXECUTION_CHECKPOINT="$(python3 - "${EVIDENCE}/build-contract.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1])).get("execution_checkpoint", "none"))
PY
)"
EXTRA_ARGS=()
EXTRA_PATHS=()

STAGE="runner-contract"
"${ROOT}/scripts/check-actions-runner-runtime.sh" "${EVIDENCE}/actions-runner-runtime.txt"
# shellcheck disable=SC1091
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
[[ "$(systemd-detect-virt --vm)" == kvm ]]
[[ -r /dev/kvm && -w /dev/kvm && -f "${TEST_IMAGE}" ]]
"${ROOT}/scripts/check-nested-kvm-runtime.sh" "${EVIDENCE}/nested-kvm-runtime.txt"
for command_name in autopkgtest curl dpkg-source gpg gpgv lintian mmdebstrap sbuild unshare; do
    command -v "${command_name}" >/dev/null
done
unshare --user --map-auto true
{
    cat /etc/os-release
    uname -a
    dpkg-query -W -f='${Package}\t${Version}\n' autopkgtest dpkg-dev lintian mmdebstrap sbuild ubuntu-keyring
    printf 'mirror=%s\nsuites=resolute,resolute-updates,resolute-security\n' "${MIRROR}"
    printf 'rootfs_created_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${EVIDENCE}/environment.txt"
sha256sum "${TEST_IMAGE}" > "${EVIDENCE}/test-image-sha256.txt"

STAGE="reviewed-ubuntu-baseline-preflight"
set +e
python3 "${ROOT}/scripts/probe-reviewed-ubuntu-baseline.py"
BASELINE_RC=$?
set -e
BASELINE_EVIDENCE="${ROOT}/evidence/runner-contract/reviewed-ubuntu-baseline"
if [[ -d "${BASELINE_EVIDENCE}" ]]; then
    mv "${BASELINE_EVIDENCE}" "${EVIDENCE}/ubuntu-baseline-preflight"
fi
[[ ${BASELINE_RC} == 0 ]] || exit "${BASELINE_RC}"

if [[ "${EXECUTION_CHECKPOINT}" != "none" ]]; then
    STAGE="predecessor-cache-admission"
    python3 "${ROOT}/scripts/admit-frameworks-cache.py" "${NODE}" \
        --output "${EVIDENCE}/predecessor-inputs.json"
    mapfile -t EXTRA_PATHS < <(python3 - "${EVIDENCE}/predecessor-inputs.json" <<'PY'
import json, sys
for item in json.load(open(sys.argv[1]))["selected"]:
    print(item["path"])
PY
)
    for path in "${EXTRA_PATHS[@]}"; do EXTRA_ARGS+=("--extra-package=${path}"); done
fi

STAGE="verified-source"
TARBALL="${WORK}/upstream.tar.xz"
curl --fail --location --retry 3 --connect-timeout 20 --max-time 180 --output "${TARBALL}" "${SOURCE_URL}"
curl --fail --location --retry 3 --connect-timeout 20 --max-time 180 --output "${TARBALL}.sig" "${SOURCE_URL}.sig"
printf '%s  %s\n%s  %s\n' "${SOURCE_HASH}" "${TARBALL}" "${SIGNATURE_HASH}" "${TARBALL}.sig" | sha256sum --check --strict
python3 - "${ROOT}" "${EVIDENCE}/build-contract.json" "${NODE}" "${WORK}" "${TARBALL}" "${EVIDENCE}" <<'PY'
import hashlib, json, re, subprocess, sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
root, contract, work, tarball, evidence = [Path(sys.argv[i]) for i in [1, 2, 4, 5, 6]]
record = json.loads(contract.read_text())['nodes'][sys.argv[3]]
if record.get('signing_key_path'):
    key = root/record['signing_key_path']
    relative = str(key.relative_to(root/record['packaging_path']))
    assert hashlib.sha256(key.read_bytes()).hexdigest() == record['packaging_sha256'][relative]
    fingerprint = record['signing_fingerprint']
else:
    subprocess.run(['python3', str(root/'scripts/run-kde-plasma-level0-materialization.py'), '--check-signing-key'], check=True)
    module = SourceFileLoader('materialize', str(root/'scripts/run-kde-plasma-level0-materialization.py')).load_module()
    key, fingerprint = root/'keys/kde-plasma-release.asc', None
subprocess.run(['gpg','--batch','--yes','--dearmor','--output',str(work/'release-keyring.gpg'),str(key)],check=True)
result = subprocess.run(['gpgv','--status-fd','1','--keyring',str(work/'release-keyring.gpg'),str(tarball)+'.sig',str(tarball)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
(evidence/'signature.log').write_text(result.stdout)
print(result.stdout)
assert result.returncode == 0
if fingerprint:
    matches = re.findall(r'^\[GNUPG:\] VALIDSIG (.*)$',result.stdout,re.M)
    assert len(matches) == 1 and matches[0].split()[-1] == fingerprint
    assert not re.search(r'\[GNUPG:\] (?:EXPKEYSIG|EXPSIG|REVKEYSIG|BADSIG|ERRSIG|KEYEXPIRED)\b',result.stdout)
else:
    assert module.valid_release_signature(result.stdout), 'Wrong KDE signature authority'
PY

STAGE="source-package"
python3 "${ROOT}/scripts/prepare-plasma-package.py" "${NODE}" --upstream "${TARBALL}" --output "${WORK}/source" |& tee "${EVIDENCE}/source-package.log"
mapfile -t DSCS < <(find "${WORK}/source" -maxdepth 1 -name '*.dsc' -type f)
[[ ${#DSCS[@]} == 1 ]]
cp "${WORK}/source/"*.dsc "${WORK}/source/"*.tar.xz "${EVIDENCE}/packages/"
cp "${TARBALL}.sig" "${EVIDENCE}/upstream.tar.xz.sig"

STAGE="sbuild-rootfs"
rm -f "${CHROOT}"
ROOTFS_POLICY="$(python3 - "${EVIDENCE}/build-contract.json" "${NODE}" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))['nodes'][sys.argv[2]].get('sbuild_rootfs_policy',{}).get('kind','fresh-buildd'))
PY
)"
if [[ "${ROOTFS_POLICY}" == "immutable-bare-milestone" ]]; then
    python3 "${ROOT}/scripts/prepare-milestone-sbuild-rootfs.py" "${NODE}" --output "${CHROOT}" \
        --evidence "${EVIDENCE}/rootfs-admission.json" --mirror "${MIRROR}" |& tee "${EVIDENCE}/rootfs.log"
    EXTRA_ARGS+=(--apt-update --apt-distupgrade)
else
    [[ "${ROOTFS_POLICY}" == "fresh-buildd" ]]
    mmdebstrap --mode=unshare --variant=buildd --architectures=amd64 --components=main,universe \
        --skip=output/mknod --format=tar resolute "${CHROOT}" \
        "deb ${MIRROR} resolute main universe" \
        "deb ${MIRROR} resolute-updates main universe" \
        "deb ${MIRROR} resolute-security main universe" |& tee "${EVIDENCE}/rootfs.log"
fi
sha256sum "${CHROOT}" > "${EVIDENCE}/rootfs-sha256.txt"

if [[ "${EXECUTION_CHECKPOINT}" != "none" ]]; then
    STAGE="predecessor-transport-probe"
    "${ROOT}/scripts/probe-frameworks-build-inputs.sh" "${EVIDENCE}/predecessor-inputs.json" \
        "${WORK}/cache-probe" "${EVIDENCE}/cache-probe" --apt-update --apt-distupgrade
fi

if [[ "${CAMPAIGN}" == manifests/package-revalidation.json ]]; then
    STAGE="retained-upgrade-inputs"
    python3 "${ROOT}/scripts/prepare-retained-package-inputs.py" "${NODE}" --output "${WORK}/retained-upgrade" \
        --evidence "${EVIDENCE}/retained-upgrade-inputs.json"
fi
MODE="$(python3 - "${EVIDENCE}/build-contract.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1])).get('execution_mode', 'build'))
PY
)"
if [[ "${MODE}" == preflight ]]; then
    STATE="PASS"
    STAGE="reviewed-package-preflight-complete"
    printf 'Reviewed package infrastructure preflight: PASS; no package Attempt consumed\n'
    exit 0
fi
[[ "${MODE}" == build ]]

STAGE="sbuild"
STATE="FAIL"
ATTEMPT=true
BUILD_RESULT="FAIL"
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --arch-all \
    "${EXTRA_ARGS[@]}" --build-dir="${WORK}/out" "${DSCS[0]}" |& tee "${EVIDENCE}/sbuild.log"
BUILD_RESULT="PASS"
STAGE="artifact-capture"
mapfile -t DEBS < <(find "${WORK}/out" -maxdepth 1 -name '*.deb' -type f | sort)
mapfile -t CHANGES < <(find "${WORK}/out" -maxdepth 1 -name '*.changes' -type f)
[[ ${#DEBS[@]} -gt 0 && ${#CHANGES[@]} == 1 ]]
cp "${WORK}/out/"*.deb "${WORK}/out/"*.changes "${WORK}/out/"*.buildinfo "${EVIDENCE}/packages/"
mapfile -t DDEBS < <(find "${WORK}/out" -maxdepth 1 -name '*.ddeb' -type f | sort)
if (( ${#DDEBS[@]} > 0 )); then cp "${DDEBS[@]}" "${EVIDENCE}/packages/"; fi
python3 - "${ROOT}" "${NODE}" "${WORK}/out" <<'PY'
import json, subprocess, sys
from pathlib import Path
from importlib.machinery import SourceFileLoader
prepare = SourceFileLoader("prepare", str(Path(sys.argv[1])/"scripts/prepare-plasma-package.py")).load_module()
record = prepare.load_campaign()["nodes"][sys.argv[2]]
actual = {}
for deb in Path(sys.argv[3]).glob("*.deb"):
    package, version, architecture = [subprocess.check_output(["dpkg-deb", "-f", str(deb), field], text=True).strip()
                                      for field in ["Package", "Version", "Architecture"]]
    assert version == record["version"], "Built version differs from reviewed contract"
    actual[package] = architecture
assert actual == record["binary_packages"], f"Binary identity mismatch: {actual}"
for deb in Path(sys.argv[3]).glob("*.ddeb"):
    fields = {name: subprocess.check_output(["dpkg-deb", "-f", str(deb), name], text=True).strip()
              for name in ["Package", "Source", "Version", "Architecture"]}
    assert fields["Package"].endswith("-dbgsym") and fields["Source"].split(" ")[0] == record["source_package"]
    assert fields["Version"] == record["version"] and fields["Architecture"] == "amd64"
buildinfo = next(Path(sys.argv[3]).glob("*.buildinfo")).read_text()
for predecessor in record.get("frameworks_predecessors", {}).values():
    for binary in predecessor["binaries"]:
        assert f"{binary['package']} (= {predecessor['version']})" in buildinfo, "Wrong build predecessor version"
PY

STAGE="upstream-package-tests"
python3 "${ROOT}/scripts/plasma-package-testing.py" upstream-tests "${NODE}" \
    --build-log "${EVIDENCE}/sbuild.log" --output "${EVIDENCE}/upstream-tests.json"

STAGE="lintian"
LINTIAN_RESULT="FAIL"
lintian --fail-on error "${DSCS[0]}" "${CHANGES[0]}" |& tee "${EVIDENCE}/lintian.log"
LINTIAN_RESULT="PASS"

STAGE="autopkgtest-qemu"
STATE="INFRA_INVALID"
SETUP="$(python3 "${ROOT}/scripts/plasma-package-testing.py" setup "${NODE}")"
TEST_ARGS=()
if [[ "${CAMPAIGN}" == manifests/package-revalidation.json ]]; then
    TEST_ARGS+=(--test-name=ubuntu-abi-client --test-name=consumer)
fi
set +e
autopkgtest "${DSCS[0]}" "${DEBS[@]}" "${EXTRA_PATHS[@]}" "${TEST_ARGS[@]}" --setup-commands="${SETUP}" --output-dir="${EVIDENCE}/autopkgtest" -- \
    qemu --qemu-command="${ROOT}/scripts/qemu-kvm-required.sh" --qemu-architecture=x86_64 \
    --cpus=2 --ram-size=2048 "${TEST_IMAGE}" |& tee "${EVIDENCE}/autopkgtest.log"
PIPELINE_RC=("${PIPESTATUS[@]}")
set -e
[[ ${PIPELINE_RC[1]} == 0 ]] || { TEST_RESULT="evidence-transport-failure"; exit 1; }
case "${PIPELINE_RC[0]}" in
    0) TEST_RESULT="PASS" ;;
    8|16|20) TEST_RESULT="INFRA_INVALID"; exit "${PIPELINE_RC[0]}" ;;
    *) STATE="FAIL"; TEST_RESULT="FAIL"; exit "${PIPELINE_RC[0]}" ;;
esac
if [[ "${CAMPAIGN}" == manifests/package-revalidation.json ]]; then
    STAGE="retained-package-upgrade"
    set +e
    autopkgtest "${DSCS[0]}" --no-built-binaries --test-name=retained-upgrade \
        --copy="${WORK}/retained-upgrade:/var/tmp/supralinux-retained-packages" \
        --copy="${WORK}/out:/var/tmp/supralinux-candidate-packages" \
        --setup-commands="${SETUP}" --output-dir="${EVIDENCE}/retained-upgrade" -- \
        qemu --qemu-command="${ROOT}/scripts/qemu-kvm-required.sh" --qemu-architecture=x86_64 \
        --cpus=2 --ram-size=2048 "${TEST_IMAGE}" |& tee "${EVIDENCE}/retained-upgrade.log"
    PIPELINE_RC=("${PIPESTATUS[@]}")
    set -e
    [[ ${PIPELINE_RC[1]} == 0 ]] || { TEST_RESULT="evidence-transport-failure"; exit 1; }
    case "${PIPELINE_RC[0]}" in
        0) TEST_RESULT="PASS" ;;
        8|16|20) TEST_RESULT="INFRA_INVALID"; exit "${PIPELINE_RC[0]}" ;;
        *) STATE="FAIL"; TEST_RESULT="FAIL"; exit "${PIPELINE_RC[0]}" ;;
    esac
fi
STAGE="evidence-deduplication"
python3 "${ROOT}/scripts/prune-duplicate-package-evidence.py" "${EVIDENCE}"
STATE="PASS"
STAGE="complete"
printf 'Authoritative Plasma package: PASS (%s %s)\n' "${NODE}" "${PACKAGE_VERSION}"
