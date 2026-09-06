#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

TRIGGER=.github/ksq-r3-full-validator-trigger.env
[[ -f "$TRIGGER" ]] || { echo "AURORA_KSQ_1_FULL_VALIDATOR_FAILURE: trigger missing" >&2; exit 1; }
# shellcheck disable=SC1090
source "$TRIGGER"

fail() {
  echo "AURORA_KSQ_1_FULL_VALIDATOR_FAILURE: $*" >&2
  exit 1
}

[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_SLICE_ID:-}" == 20260829T022000Z-r3 ]] || fail "slice pin mismatch"
[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_CANONICAL_RUN_ID:-}" == 34009066345 ]] || fail "canonical run pin mismatch"
[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_CANONICAL_ARTIFACT_ID:-}" == 9981890909 ]] || fail "canonical artifact pin mismatch"
[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_CANONICAL_ARTIFACT_DIGEST:-}" == sha256:96455b0b2c0ea203e67efc39fd3177da0be72543bd322f208400e90f4d7ac181 ]] || fail "canonical digest pin mismatch"
[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_CANONICAL_ARTIFACT_SIZE:-}" == 334364239 ]] || fail "canonical size pin mismatch"
[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_KWALLET_RUN_ID:-}" == 33821228782 ]] || fail "KWallet run pin mismatch"
[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_KWALLET_ARTIFACT_ID:-}" == 9918320108 ]] || fail "KWallet artifact pin mismatch"
[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_KWALLET_ARTIFACT_DIGEST:-}" == sha256:50c33e99c7593ce6b8d4a67c8ee11c1598ad93545ed362078a57410c4a892730 ]] || fail "KWallet digest pin mismatch"
[[ "${AURORA_KSQ_R3_FULL_VALIDATOR_KWALLET_ARTIFACT_SIZE:-}" == 4947 ]] || fail "KWallet size pin mismatch"

[[ -n "${GH_TOKEN:-}" ]] || fail "GH_TOKEN missing"
[[ -n "${GITHUB_REPOSITORY:-}" ]] || fail "GITHUB_REPOSITORY missing"
[[ -n "${RUNNER_TEMP:-}" ]] || fail "RUNNER_TEMP missing"

grep -Eq '^VERSION_ID="26\.04(\.1)?"$' /etc/os-release || fail "runner is not Ubuntu 26.04"
[[ "$(dpkg --print-architecture)" == amd64 ]] || fail "runner architecture is not amd64"
for command in gh curl jq unzip python3 sha256sum dpkg-deb; do
  command -v "$command" >/dev/null || fail "missing command $command"
done

base=build/ksq-1/final-build-validation-r3
rm -rf "$base"
mkdir -p "$base/provenance"
cp "$TRIGGER" "$base/provenance/trigger.env"

prove_artifact() {
  local role="$1" run="$2" head="$3" artifact="$4" name="$5" digest="$6" size="$7"
  gh api "/repos/$GITHUB_REPOSITORY/actions/runs/$run" > "$base/provenance/${role}-run.json"
  [[ "$(jq -r '.status' "$base/provenance/${role}-run.json")" == completed ]] || fail "$role run incomplete"
  [[ "$(jq -r '.conclusion' "$base/provenance/${role}-run.json")" == success ]] || fail "$role run not successful"
  [[ "$(jq -r '.head_sha' "$base/provenance/${role}-run.json")" == "$head" ]] || fail "$role run head mismatch"
  gh api "/repos/$GITHUB_REPOSITORY/actions/artifacts/$artifact" > "$base/provenance/${role}-artifact.json"
  [[ "$(jq -r '.name' "$base/provenance/${role}-artifact.json")" == "$name" ]] || fail "$role artifact name mismatch"
  [[ "$(jq -r '.digest' "$base/provenance/${role}-artifact.json")" == "$digest" ]] || fail "$role artifact digest mismatch"
  [[ "$(jq -r '.size_in_bytes' "$base/provenance/${role}-artifact.json")" == "$size" ]] || fail "$role artifact size mismatch"
  [[ "$(jq -r '.workflow_run.id' "$base/provenance/${role}-artifact.json")" == "$run" ]] || fail "$role artifact run mismatch"
  [[ "$(jq -r '.workflow_run.head_sha' "$base/provenance/${role}-artifact.json")" == "$head" ]] || fail "$role artifact head mismatch"
  [[ "$(jq -r '.expired' "$base/provenance/${role}-artifact.json")" == false ]] || fail "$role artifact expired"
}

prove_artifact canonical 34009066345 12ed5856b31ebe3870791c5e3d71ecfec70eba43 \
  9981890909 aurora-ksq-repro-input-101-r3 \
  sha256:96455b0b2c0ea203e67efc39fd3177da0be72543bd322f208400e90f4d7ac181 334364239
prove_artifact kwallet 33821228782 5b021477f00ab97e03b19e19da4e681abd7af7c0 \
  9918320108 aurora-ksq-1-accepted-through-065-kwallet-sidecar \
  sha256:50c33e99c7593ce6b8d4a67c8ee11c1598ad93545ed362078a57410c4a892730 4947

download_and_prove() {
  local artifact="$1" digest="$2" size="$3" output="$4"
  rm -rf "$output" "$output.zip"
  mkdir -p "$output"
  curl --fail --location --retry 5 --retry-all-errors \
    -H 'Accept: application/vnd.github+json' \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H 'X-GitHub-Api-Version: 2022-11-28' \
    "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$artifact/zip" \
    -o "$output.zip"
  [[ "$(stat -c '%s' "$output.zip")" == "$size" ]] || fail "artifact $artifact downloaded size mismatch"
  [[ "sha256:$(sha256sum "$output.zip" | awk '{print $1}')" == "$digest" ]] || fail "artifact $artifact downloaded digest mismatch"
  unzip -q "$output.zip" -d "$output"
}

canonical="$RUNNER_TEMP/canonical-repro-input"
kwallet="$RUNNER_TEMP/accepted-065"
download_and_prove 9981890909 "$AURORA_KSQ_R3_FULL_VALIDATOR_CANONICAL_ARTIFACT_DIGEST" "$AURORA_KSQ_R3_FULL_VALIDATOR_CANONICAL_ARTIFACT_SIZE" "$canonical"
download_and_prove 9918320108 "$AURORA_KSQ_R3_FULL_VALIDATOR_KWALLET_ARTIFACT_DIGEST" "$AURORA_KSQ_R3_FULL_VALIDATOR_KWALLET_ARTIFACT_SIZE" "$kwallet"

(
  cd "$canonical"
  sha256sum -c provenance.sha256
)
(
  cd "$canonical/payload"
  sha256sum -c evidence.sha256
)
# shellcheck disable=SC1091
source "$canonical/payload/checkpoint-status.env"
[[ "${AURORA_KSQ_1_REPRO_INPUT_STATUS:-}" == PASS ]] || fail "canonical payload not PASS"
[[ "${AURORA_KSQ_1_REPRO_INPUT_SOURCES:-}" == 101 ]] || fail "canonical source count mismatch"
[[ "${AURORA_KSQ_1_REPRO_INPUT_DEBS:-}" == 424 ]] || fail "canonical binary count mismatch"
[[ "${AURORA_KSQ_1_REPRO_INPUT_CANONICAL_RANGES:-}" == 5 ]] || fail "canonical range count mismatch"

(
  cd "$kwallet"
  sha256sum -c evidence.sha256
  sha256sum -c artifact-manifest.sha256
)
# shellcheck disable=SC1091
source "$kwallet/acceptance.env"
[[ "${AURORA_KSQ_1_ORDER65_ACCEPTANCE_STATUS:-}" == PASS ]] || fail "KWallet acceptance not PASS"
[[ "${AURORA_KSQ_1_ORDER65_ACCEPTED_ACCUMULATED_DEBS:-}" == 295 ]] || fail "KWallet acceptance count mismatch"
[[ -f "$kwallet/evidence/status.env" ]] || fail "KWallet detailed status missing"

python3 scripts/ci/generate-kde-build-closure.py
[[ "$(sha256sum build/ksq-0/build-order.tsv | awk '{print $1}')" == 9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88 ]] || fail "build-order identity mismatch"

# Stage the canonical representation without copying its 424 DEBs again.
rm -rf build/ksq-1/full
mkdir -p build/ksq-1/full/kwallet-validation
ln -s "$canonical/payload/debs" build/ksq-1/full/debs
ln -s "$canonical/payload/chunks" build/ksq-1/full/evidence-artifacts
cp -a "$kwallet/evidence/status.env" build/ksq-1/full/kwallet-validation/status.env

python3 scripts/ci/validate-ksq-1-full.py

grep -qx 'AURORA_KSQ_1_FULL_BUILD_STATUS=PASS' build/ksq-1/full/full-build-status.env || fail "full validator did not PASS"
grep -qx 'AURORA_KSQ_1_FULL_BUILD_SOURCES=101' build/ksq-1/full/full-build-status.env || fail "full validator source count mismatch"
grep -qx 'AURORA_KSQ_1_FULL_BUILD_BINARIES=424' build/ksq-1/full/full-build-status.env || fail "full validator binary count mismatch"
grep -qx 'AURORA_KSQ_1_FULL_BUILD_CHECKPOINTS=5' build/ksq-1/full/full-build-status.env || fail "full validator checkpoint count mismatch"
grep -qx 'AURORA_KSQ_1_FULL_BUILD_PACKAGING_ADAPTATIONS=2' build/ksq-1/full/full-build-status.env || fail "full validator adaptation count mismatch"
grep -qx 'AURORA_KSQ_1_FULL_BUILD_KWALLET_PAM=PASS' build/ksq-1/full/full-build-status.env || fail "full validator KWallet gate mismatch"
grep -qx 'AURORA_KSQ_1_FULL_BUILD_REPRODUCIBILITY_CERTIFIED=no' build/ksq-1/full/full-build-status.env || fail "full validator prematurely certified reproducibility"
grep -qx 'AURORA_KSQ_1_FULL_CERTIFIED=no' build/ksq-1/full/full-build-status.env || fail "full validator prematurely certified KSQ-1"

cp -a build/ksq-1/full/full-build-status.env "$base/"
cp -a build/ksq-1/full/full-build-manifest.tsv "$base/"
cp -a build/ksq-1/full/full-binary-packages.tsv "$base/"
cp -a build/ksq-1/full/full-debs.sha256 "$base/"
cp -a "$kwallet/evidence/status.env" "$base/kwallet-status.env"
cp -a "$canonical/payload/checkpoint-status.env" "$base/canonical-checkpoint-status.env"
cp -a "$canonical/payload/checkpoint-provenance.tsv" "$base/canonical-checkpoint-provenance.tsv"

[[ "$(awk 'END{print NR-1}' "$base/full-build-manifest.tsv")" == 101 ]] || fail "retained manifest row count mismatch"
[[ "$(awk 'END{print NR-1}' "$base/full-binary-packages.tsv")" == 424 ]] || fail "retained binary row count mismatch"
[[ "$(wc -l < "$base/full-debs.sha256")" == 424 ]] || fail "retained DEB hash count mismatch"

cat > "$base/status.env" <<EOF
AURORA_KSQ_R3_FULL_VALIDATOR=PASS
AURORA_KSQ_R3_FULL_VALIDATOR_SOURCES=101
AURORA_KSQ_R3_FULL_VALIDATOR_BINARIES=424
AURORA_KSQ_R3_FULL_VALIDATOR_CANONICAL_RANGES=5
AURORA_KSQ_R3_FULL_VALIDATOR_PACKAGING_ADAPTATIONS=2
AURORA_KSQ_R3_FULL_VALIDATOR_KWALLET=PASS
AURORA_KSQ_R3_FULL_VALIDATOR_CANONICAL_INPUT_ARTIFACT=9981890909
AURORA_KSQ_R3_FULL_VALIDATOR_KWALLET_ARTIFACT=9918320108
AURORA_KSQ_R3_FULL_REPRODUCIBILITY_CERTIFIED=no
AURORA_KSQ_1_FULL_CERTIFIED=no
EOF

(
  cd "$base"
  find . -type f ! -name evidence.sha256 -printf '%P\0' | sort -z | xargs -0 -r sha256sum > evidence.sha256
  sha256sum -c evidence.sha256
)

cat "$base/status.env"
echo AURORA_KSQ_R3_FULL_VALIDATOR_SUCCESS
