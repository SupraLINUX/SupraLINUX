#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ACCEPT="${1:?order65 acceptance artifact root required}"
P1="${2:?001-020 artifact root required}"
P2="${3:?021-040 artifact root required}"
P3="${4:?041-043 artifact root required}"
P4="${5:?044-060 artifact root required}"
P5="${6:?061-065 artifact root required}"
OUT="${7:-${ROOT}/build/ksq-1/accepted-through-065-restore}"
TARGET="${ROOT}/build/ksq-1/full/debs"

fail() {
    echo "AURORA_KSQ_1_ACCEPTED_065_RESTORE_FAILURE: $*" >&2
    exit 1
}

[[ -f "${ACCEPT}/acceptance.env" ]] || fail "acceptance.env missing"
grep -qx 'AURORA_KSQ_1_ORDER65_ACCEPTANCE_STATUS=PASS' "${ACCEPT}/acceptance.env" || fail "order65 acceptance not PASS"
grep -qx 'AURORA_KSQ_1_ORDER65_ACCEPTED_THROUGH_ORDER=65' "${ACCEPT}/acceptance.env" || fail "accepted order drifted"
grep -qx 'AURORA_KSQ_1_ORDER65_ACCEPTED_ACCUMULATED_DEBS=295' "${ACCEPT}/acceptance.env" || fail "accepted DEB count drifted"
grep -qx 'AURORA_KSQ_1_ORDER65_ACCEPTED_SOLVER_PACKAGES=375' "${ACCEPT}/acceptance.env" || fail "solver selection drifted"
grep -qx 'AURORA_KSQ_1_ORDER65_ACCEPTED_INSTALLED_SELECTION=375' "${ACCEPT}/acceptance.env" || fail "installed selection drifted"
grep -qx 'AURORA_KSQ_1_ORDER65_ACCEPTED_BOOTSTRAP_VARIANT=apt' "${ACCEPT}/acceptance.env" || fail "bootstrap variant drifted"
grep -qx 'AURORA_KSQ_1_ORDER65_ACCEPTED_INSTALL_RECOMMENDS=true' "${ACCEPT}/acceptance.env" || fail "Recommends policy drifted"
grep -qx 'AURORA_KSQ_1_ORDER65_ACCEPTED_RUNTIME_AUTO_UNLOCK_CERTIFIED=no' "${ACCEPT}/acceptance.env" || fail "auto-unlock scope drifted"
(
    cd "${ACCEPT}"
    sha256sum -c evidence.sha256
    sha256sum -c artifact-manifest.sha256
) || fail "order65 acceptance hashes failed"

pick_root() {
    local download="$1" chunk="$2"
    local -a found=()
    [[ -d "${download}/ksq-1/full/${chunk}" ]] && found+=("${download}")
    [[ -d "${download}/build/ksq-1/full/${chunk}" ]] && found+=("${download}/build")
    [[ "${#found[@]}" -eq 1 ]] || fail "ambiguous checkpoint root download=${download} chunk=${chunk} matches=${#found[@]}"
    printf '%s\n' "${found[0]}"
}

r1="$(pick_root "${P1}" chunk-001-020)"
r2="$(pick_root "${P2}" chunk-021-040)"
r3="$(pick_root "${P3}" chunk-041-043)"
r4="$(pick_root "${P4}" chunk-044-060)"
r5="$(pick_root "${P5}" chunk-061-065)"

rm -rf "${OUT}"
mkdir -p "${OUT}"
cat > "${OUT}/checkpoint-spec.json" <<EOF_JSON
[
  {"root":"$r1","first_order":1,"last_order":20,"run_id":33546093974,"artifact_id":9818465016,"artifact_digest":"sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba","new_debs":103,"accumulated_debs":103,"new_debs_manifest_sha256":"b0be04014893808a79aaea514e2a5c4bc968b5c9c9769d8d7ea6cae7992b01f9","build_manifest_sha256":"ff87f96c85bc4ba1553f16b3700cf701eca04e9b749a1c739bb1088cceb3485b"},
  {"root":"$r2","first_order":21,"last_order":40,"run_id":33561782526,"artifact_id":9824689982,"artifact_digest":"sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e","new_debs":89,"accumulated_debs":192,"new_debs_manifest_sha256":"3924d0151581a53f505ca8cd0a615b4ffee9c246afeabec003633905db159bfa","build_manifest_sha256":"6e121efdeb62b8c0c6c48ae14f60e41e452e16fe177f03536f1c2677848b111a"},
  {"root":"$r3","first_order":41,"last_order":43,"run_id":33753437984,"artifact_id":9892762100,"artifact_digest":"sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0","new_debs":13,"accumulated_debs":205,"new_debs_manifest_sha256":"d5e6cbd51cac0ac2d2dca953722ccbd1a43beb3c981766f683ae69ace539105c","build_manifest_sha256":"e4311aeba5c7856ac2c0ff803c9adc2fdcb63adb104d1a8f2707a1fc45696ab1"},
  {"root":"$r4","first_order":44,"last_order":60,"run_id":33767306768,"artifact_id":9900367299,"artifact_digest":"sha256:41a50bb17ea5ca4ab63c43a6aa6d6d030dae310ba716866824ac72d6c61dc4f3","new_debs":70,"accumulated_debs":275,"new_debs_manifest_sha256":"a712b2f8d67d2bbb8aea4f3ccc6f7af930e4cfc3974f5562c923b12ea23267a5","build_manifest_sha256":"4ac871dc0865bb10b27f0b23db8b8969e595c67ab4faa75dd295b0877ccaf709"},
  {"root":"$r5","first_order":61,"last_order":65,"run_id":33805321380,"artifact_id":9913134271,"artifact_digest":"sha256:035b5930f3821d764f51f7bf4b3bd2b8e82a302539e70c2c612b93f41d3e2e65","new_debs":20,"accumulated_debs":295,"new_debs_manifest_sha256":"4a3384fa85ebe543c79a4c6e67341ab526ec1b4a010e137da3e39b24a4d94960","build_manifest_sha256":"2e983b7549d24ddf8af0fd4235224b05ba78f91d8422f8f9189ef9bf156b7c13"}
]
EOF_JSON

python3 "${ROOT}/scripts/ci/restore-ksq-1-checkpoint-chain.py" \
    --spec "${OUT}/checkpoint-spec.json" \
    --target "${TARGET}" \
    --evidence "${OUT}/checkpoint-evidence"

status="${OUT}/checkpoint-evidence/checkpoint-status.env"
grep -qx 'AURORA_KSQ_1_CHECKPOINT_CHAIN=PASS' "${status}" || fail "checkpoint chain not PASS"
grep -qx 'AURORA_KSQ_1_CHECKPOINT_RANGES=5' "${status}" || fail "checkpoint range count drifted"
grep -qx 'AURORA_KSQ_1_CHECKPOINT_LAST_ORDER=65' "${status}" || fail "checkpoint last order drifted"
grep -qx 'AURORA_KSQ_1_CHECKPOINT_DEBS=295' "${status}" || fail "checkpoint DEB count drifted"
grep -qx 'AURORA_KSQ_1_CHECKPOINT_OVERLAP=none' "${status}" || fail "checkpoint overlap detected"
[[ "$(find "${TARGET}" -maxdepth 1 -type f -name '*.deb' | wc -l)" -eq 295 ]] || fail "restored target does not contain exactly 295 DEBs"

(
    cd "${TARGET}"
    find . -maxdepth 1 -type f -name '*.deb' -printf '%f\0' | sort -z | xargs -0 sha256sum
) > "${OUT}/accepted-065-debs.sha256"
cp -a "${ACCEPT}" "${OUT}/order65-acceptance-evidence"

{
    echo 'AURORA_KSQ_1_ACCEPTED_065_RESTORE_STATUS=PASS'
    echo 'AURORA_KSQ_1_ACCEPTED_065_LAST_ORDER=65'
    echo 'AURORA_KSQ_1_ACCEPTED_065_DEBS=295'
    echo 'AURORA_KSQ_1_ACCEPTED_065_CHECKPOINT_RANGES=5'
    echo 'AURORA_KSQ_1_ACCEPTED_065_ORDER65_ACCEPTANCE=independently-validated'
} > "${OUT}/status.env"
cat "${OUT}/status.env"
echo AURORA_KSQ_1_ACCEPTED_065_RESTORE_SUCCESS
