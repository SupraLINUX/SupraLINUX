#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TRIGGER="${1:-${ROOT}/.github/ksq-r3-repro-input-101-trigger.env}"
BASE="${ROOT}/build/ksq-1/repro-input-101-r3"
PAYLOAD="${BASE}/payload"
PROVENANCE="${BASE}/provenance"
TMP="${RUNNER_TEMP:?RUNNER_TEMP required}/aurora-ksq-repro-input-101-r3"
REPOSITORY="${GITHUB_REPOSITORY:-SupraLINUX/SupraLINUX}"

fail() {
  echo "AURORA_KSQ_REPRO_INPUT_PREP_FAILURE: $*" >&2
  exit 1
}

[[ -f "${TRIGGER}" ]] || fail "trigger file missing"
: "${GH_TOKEN:?GH_TOKEN required}"
for command in gh curl jq unzip python3 sha256sum; do
  command -v "${command}" >/dev/null || fail "missing command ${command}"
done

# shellcheck disable=SC1090
source "${TRIGGER}"
[[ "${AURORA_KSQ_R3_REPRO_INPUT_SLICE_ID}" == "20260829T022000Z-r3" ]] || fail "slice drifted"
[[ "${AURORA_KSQ_R3_REPRO_INPUT_ACCEPTED101_RUN_ID}" == "34002503177" ]] || fail "accepted101 run drifted"
[[ "${AURORA_KSQ_R3_REPRO_INPUT_ACCEPTED101_ARTIFACT_ID}" == "9979901723" ]] || fail "accepted101 artifact drifted"
[[ "${AURORA_KSQ_R3_REPRO_INPUT_ACCEPTED101_ARTIFACT_DIGEST}" == "sha256:62b5014923d487e13e9a2377ef91dec4cc1a11a33b75acd6f58f4642b0403e83" ]] || fail "accepted101 digest drifted"
[[ "${AURORA_KSQ_R3_REPRO_INPUT_FORMAT}" == "canonical-5-range-v1" ]] || fail "format drifted"

rm -rf "${BASE}" "${TMP}"
mkdir -p "${PROVENANCE}" "${TMP}"
cp -a "${TRIGGER}" "${PROVENANCE}/trigger.env"

gh api "/repos/${REPOSITORY}/actions/runs/${AURORA_KSQ_R3_REPRO_INPUT_ACCEPTED101_RUN_ID}" > "${PROVENANCE}/accepted101-run.json"
[[ "$(jq -r '.status' "${PROVENANCE}/accepted101-run.json")" == completed ]] || fail "accepted101 run not completed"
[[ "$(jq -r '.conclusion' "${PROVENANCE}/accepted101-run.json")" == success ]] || fail "accepted101 run not successful"
[[ "$(jq -r '.head_sha' "${PROVENANCE}/accepted101-run.json")" == 8de6b08456975e391624813776866a138a8ea40e ]] || fail "accepted101 head drifted"

fetch_zip() {
  local id="$1" out="$2"
  mkdir -p "${out}"
  curl --fail --location --retry 5 --retry-all-errors \
    -H 'Accept: application/vnd.github+json' \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H 'X-GitHub-Api-Version: 2022-11-28' \
    "https://api.github.com/repos/${REPOSITORY}/actions/artifacts/${id}/zip" \
    -o "${out}.zip"
  unzip -q "${out}.zip" -d "${out}"
}

record_artifact() {
  local role="$1" id="$2" digest="$3" run="$4"
  local json="${PROVENANCE}/artifact-${id}.json"
  gh api "/repos/${REPOSITORY}/actions/artifacts/${id}" > "${json}"
  [[ "$(jq -r '.digest' "${json}")" == "${digest}" ]] || fail "${role} digest drifted"
  [[ "$(jq -r '.workflow_run.id' "${json}")" == "${run}" ]] || fail "${role} run drifted"
  [[ "$(jq -r '.expired' "${json}")" == false ]] || fail "${role} artifact expired"
  printf '%s\t%s\t%s\t%s\n' "${role}" "${id}" "${digest}" "${run}" >> "${PROVENANCE}/input-artifacts.tsv"
}

printf 'role\tartifact_id\tdigest\trun_id\n' > "${PROVENANCE}/input-artifacts.tsv"
record_artifact input-001-020 9818465016 sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba 33546093974
record_artifact input-021-040 9824689982 sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e 33561782526
record_artifact input-041-043 9892762100 sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0 33753437984
record_artifact input-044-060 9900367299 sha256:41a50bb17ea5ca4ab63c43a6aa6d6d030dae310ba716866824ac72d6c61dc4f3 33767306768
record_artifact input-061-065 9913134271 sha256:035b5930f3821d764f51f7bf4b3bd2b8e82a302539e70c2c612b93f41d3e2e65 33805321380
record_artifact accept-065 9918320108 sha256:50c33e99c7593ce6b8d4a67c8ee11c1598ad93545ed362078a57410c4a892730 33821228782
record_artifact input-066-080 9972463409 sha256:e1c9dccad9164a8e8445ff2487fc17d61c55816bfa3c22da385c336cca3feda5 33973287438
record_artifact accept-080 9972976872 sha256:ebd60471d9834efbb4fad9f5680c6a153000aa8b9393f4821a70ff148edc2511 33978315934
record_artifact input-081-090 9974023708 sha256:dfa78a851139b279f08d58bef9a0d95fc9261a26c18b6c1dc85a65afe29401ed 33978550975
record_artifact accept-090 9977725295 sha256:aa4d0499623073108161750881eee06804d1a1d20e5cd45e4a83ab4de3ad7d04 33994817042
record_artifact input-091-101 9979632407 sha256:0595106d646d61dcd0d65066b69f109823b00802b78ebc2e6547d3fa1eab9e42 33994908104
record_artifact accept-101 9979901723 sha256:62b5014923d487e13e9a2377ef91dec4cc1a11a33b75acd6f58f4642b0403e83 34002503177

fetch_zip 9918320108 "${TMP}/accepted-065"
(
  cd "${TMP}/accepted-065"
  sha256sum -c evidence.sha256
  sha256sum -c artifact-manifest.sha256
)
# shellcheck disable=SC1091
source "${TMP}/accepted-065/acceptance.env"
[[ "${AURORA_KSQ_1_ORDER65_ACCEPTANCE_STATUS}" == PASS ]] || fail "accepted065 not PASS"
[[ "${AURORA_KSQ_1_ORDER65_ACCEPTED_ACCUMULATED_DEBS}" == 295 ]] || fail "accepted065 count drifted"

fetch_zip 9972976872 "${TMP}/accepted-080"
(cd "${TMP}/accepted-080" && sha256sum -c evidence.sha256)
# shellcheck disable=SC1091
source "${TMP}/accepted-080/acceptance.env"
[[ "${AURORA_KSQ_R3_066_080_ACCEPTANCE}" == PASS ]] || fail "accepted080 not PASS"
[[ "${AURORA_KSQ_R3_066_080_ACCUMULATED_DEBS}" == 345 ]] || fail "accepted080 count drifted"
[[ "${AURORA_KSQ_R3_066_080_SOURCE_ARTIFACT_ID}" == 9972463409 ]] || fail "accepted080 source artifact drifted"

fetch_zip 9977725295 "${TMP}/accepted-090"
(cd "${TMP}/accepted-090" && sha256sum -c evidence.sha256)
# shellcheck disable=SC1091
source "${TMP}/accepted-090/acceptance.env"
[[ "${AURORA_KSQ_R3_081_090_ACCEPTANCE}" == PASS ]] || fail "accepted090 not PASS"
[[ "${AURORA_KSQ_R3_081_090_ACCUMULATED_DEBS}" == 376 ]] || fail "accepted090 count drifted"
[[ "${AURORA_KSQ_R3_081_090_PRIOR_ACCEPT_ARTIFACT_ID}" == 9972976872 ]] || fail "accepted090 prior drifted"
[[ "${AURORA_KSQ_R3_081_090_SOURCE_ARTIFACT_ID}" == 9974023708 ]] || fail "accepted090 source artifact drifted"

fetch_zip 9979901723 "${TMP}/accepted-101"
(cd "${TMP}/accepted-101" && sha256sum -c evidence.sha256)
# shellcheck disable=SC1091
source "${TMP}/accepted-101/acceptance.env"
[[ "${AURORA_KSQ_R3_091_101_ACCEPTANCE}" == PASS ]] || fail "accepted101 not PASS"
[[ "${AURORA_KSQ_R3_091_101_ACCUMULATED_DEBS}" == 424 ]] || fail "accepted101 count drifted"
[[ "${AURORA_KSQ_R3_091_101_PRIOR_ACCEPT_ARTIFACT_ID}" == 9977725295 ]] || fail "accepted101 prior drifted"
[[ "${AURORA_KSQ_R3_091_101_SOURCE_ARTIFACT_ID}" == 9979632407 ]] || fail "accepted101 source artifact drifted"

fetch_zip 9818465016 "${TMP}/input-001-020"
fetch_zip 9824689982 "${TMP}/input-021-040"
fetch_zip 9892762100 "${TMP}/input-041-043"
fetch_zip 9900367299 "${TMP}/input-044-060"
fetch_zip 9913134271 "${TMP}/input-061-065"
fetch_zip 9972463409 "${TMP}/input-066-080"
fetch_zip 9974023708 "${TMP}/input-081-090"
fetch_zip 9979632407 "${TMP}/input-091-101"

python3 "${ROOT}/scripts/ci/normalize-ksq-1-repro-input.py" \
  --chunk "1-20=${TMP}/input-001-020" \
  --chunk "21-40=${TMP}/input-021-040" \
  --chunk "41-43=${TMP}/input-041-043" \
  --chunk "44-60=${TMP}/input-044-060" \
  --chunk "61-65=${TMP}/input-061-065" \
  --chunk "66-80=${TMP}/input-066-080" \
  --chunk "81-90=${TMP}/input-081-090" \
  --chunk "91-101=${TMP}/input-091-101" \
  --output "${PAYLOAD}"

cp -a "${TMP}/accepted-101/acceptance.env" "${PROVENANCE}/accepted101.env"
cp -a "${TMP}/accepted-090/acceptance.env" "${PROVENANCE}/accepted090.env"
cp -a "${TMP}/accepted-080/acceptance.env" "${PROVENANCE}/accepted080.env"
cp -a "${TMP}/accepted-065/acceptance.env" "${PROVENANCE}/accepted065.env"

(
  cd "${PAYLOAD}"
  sha256sum -c evidence.sha256
  grep -qx 'AURORA_KSQ_1_REPRO_INPUT_STATUS=PASS' checkpoint-status.env
  grep -qx 'AURORA_KSQ_1_REPRO_INPUT_SOURCES=101' checkpoint-status.env
  grep -qx 'AURORA_KSQ_1_REPRO_INPUT_DEBS=424' checkpoint-status.env
  grep -qx 'AURORA_KSQ_1_REPRO_INPUT_CANONICAL_RANGES=5' checkpoint-status.env
)
[[ "$(find "${PAYLOAD}/debs" -maxdepth 1 -type f -name '*.deb' | wc -l)" -eq 424 ]] || fail "merged DEB count != 424"
[[ "$(find "${PAYLOAD}/chunks" -type f -name prepared-source.env | wc -l)" -eq 101 ]] || fail "prepared-source count != 101"
[[ "$(find "${PAYLOAD}/chunks" -type f -name build-status.env | wc -l)" -eq 101 ]] || fail "build-status count != 101"

(
  cd "${BASE}"
  find provenance -type f -print0 | sort -z | xargs -0 sha256sum > provenance.sha256
  sha256sum -c provenance.sha256
)

echo AURORA_KSQ_REPRO_INPUT_PREP_SUCCESS
