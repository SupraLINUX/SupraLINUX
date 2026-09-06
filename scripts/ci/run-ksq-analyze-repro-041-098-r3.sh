#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
TRIGGER=.github/ksq-r3-repro-041-098-analyze-trigger.env
[[ -f "$TRIGGER" ]] || { echo "AURORA_KSQ_R3_REPRO_041_098_FAILURE: trigger missing" >&2; exit 1; }
# shellcheck disable=SC1090
source "$TRIGGER"

fail() { echo "AURORA_KSQ_R3_REPRO_041_098_FAILURE: $*" >&2; exit 1; }

[[ "${AURORA_KSQ_R3_REPRO_041_098_FIRST_ORDER:-}" == 41 ]] || fail "first order mismatch"
[[ "${AURORA_KSQ_R3_REPRO_041_098_LAST_ORDER:-}" == 98 ]] || fail "last order mismatch"
[[ "${AURORA_KSQ_R3_REPRO_041_098_CANONICAL_RUN_ID:-}" == 34009066345 ]] || fail "canonical run mismatch"
[[ "${AURORA_KSQ_R3_REPRO_041_098_CANONICAL_ARTIFACT_ID:-}" == 9981890909 ]] || fail "canonical artifact mismatch"
[[ "${AURORA_KSQ_R3_REPRO_041_098_REFERENCE_RUN_ID:-}" == 33281736655 ]] || fail "reference run mismatch"
[[ -n "${GH_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" && -n "${RUNNER_TEMP:-}" ]] || fail "required Actions environment missing"

grep -Eq '^VERSION_ID="26\.04(\.1)?"$' /etc/os-release || fail "runner is not Ubuntu 26.04"
[[ "$(dpkg --print-architecture)" == amd64 ]] || fail "runner architecture is not amd64"

base=build/ksq-1/repro-reusable-041-098-r3
rm -rf "$base"
mkdir -p "$base/provenance"
cp "$TRIGGER" "$base/provenance/trigger.env"

# Candidate is the sealed canonical 101-source input.
gh api "/repos/$GITHUB_REPOSITORY/actions/runs/$AURORA_KSQ_R3_REPRO_041_098_CANONICAL_RUN_ID" > "$base/provenance/candidate-run.json"
[[ "$(jq -r '.status' "$base/provenance/candidate-run.json")" == completed ]] || fail "candidate run incomplete"
[[ "$(jq -r '.conclusion' "$base/provenance/candidate-run.json")" == success ]] || fail "candidate run not successful"
[[ "$(jq -r '.head_sha' "$base/provenance/candidate-run.json")" == 12ed5856b31ebe3870791c5e3d71ecfec70eba43 ]] || fail "candidate head mismatch"

# Historical run was globally cancelled only after the relevant range artifacts were preserved.
gh api "/repos/$GITHUB_REPOSITORY/actions/runs/$AURORA_KSQ_R3_REPRO_041_098_REFERENCE_RUN_ID" > "$base/provenance/reference-run.json"
[[ "$(jq -r '.status' "$base/provenance/reference-run.json")" == completed ]] || fail "reference run incomplete"
[[ "$(jq -r '.conclusion' "$base/provenance/reference-run.json")" == cancelled ]] || fail "reference run conclusion drifted"
[[ "$(jq -r '.head_sha' "$base/provenance/reference-run.json")" == 90fd5d3119ebfaab42f721d3bdd977a3472da498 ]] || fail "reference head mismatch"

prove_job() {
  local id="$1" expected_conclusion="$2" build_conclusion="$3"
  gh api "/repos/$GITHUB_REPOSITORY/actions/jobs/$id" > "$base/provenance/reference-job-$id.json"
  [[ "$(jq -r '.run_id' "$base/provenance/reference-job-$id.json")" == "$AURORA_KSQ_R3_REPRO_041_098_REFERENCE_RUN_ID" ]] || fail "reference job $id run mismatch"
  [[ "$(jq -r '.status' "$base/provenance/reference-job-$id.json")" == completed ]] || fail "reference job $id incomplete"
  [[ "$(jq -r '.conclusion' "$base/provenance/reference-job-$id.json")" == "$expected_conclusion" ]] || fail "reference job $id conclusion mismatch"
  [[ "$(jq -r '.steps[] | select(.name | startswith("Build sources")) | .conclusion' "$base/provenance/reference-job-$id.json")" == "$build_conclusion" ]] || fail "reference job $id build-step conclusion mismatch"
  [[ "$(jq -r '.steps[] | select(.name | startswith("Preserve binary checkpoint")) | .conclusion' "$base/provenance/reference-job-$id.json")" == success ]] || fail "reference job $id binary preservation failed"
  [[ "$(jq -r '.steps[] | select(.name | startswith("Preserve build evidence")) | .conclusion' "$base/provenance/reference-job-$id.json")" == success ]] || fail "reference job $id evidence preservation failed"
}
prove_job 99197674603 success success
prove_job 99206441749 success success
prove_job 99217598358 cancelled cancelled

prove_artifact() {
  local role="$1" id="$2" name="$3" digest="$4" size="$5" run="$6" head="$7"
  gh api "/repos/$GITHUB_REPOSITORY/actions/artifacts/$id" > "$base/provenance/$role-artifact.json"
  [[ "$(jq -r '.name' "$base/provenance/$role-artifact.json")" == "$name" ]] || fail "$role name mismatch"
  [[ "$(jq -r '.digest' "$base/provenance/$role-artifact.json")" == "$digest" ]] || fail "$role digest mismatch"
  [[ "$(jq -r '.size_in_bytes' "$base/provenance/$role-artifact.json")" == "$size" ]] || fail "$role size mismatch"
  [[ "$(jq -r '.workflow_run.id' "$base/provenance/$role-artifact.json")" == "$run" ]] || fail "$role run mismatch"
  [[ "$(jq -r '.workflow_run.head_sha' "$base/provenance/$role-artifact.json")" == "$head" ]] || fail "$role head mismatch"
  [[ "$(jq -r '.expired' "$base/provenance/$role-artifact.json")" == false ]] || fail "$role artifact expired"
}
prove_artifact candidate 9981890909 aurora-ksq-repro-input-101-r3 sha256:96455b0b2c0ea203e67efc39fd3177da0be72543bd322f208400e90f4d7ac181 334364239 34009066345 12ed5856b31ebe3870791c5e3d71ecfec70eba43
prove_artifact ref-ev-041-060 9726386379 aurora-ksq-1-evidence-041-060 sha256:6591dc3fe32bced541bf6c46fbaa03534ebe7de54203f4e59d0034fec73f02e5 2002788 33281736655 90fd5d3119ebfaab42f721d3bdd977a3472da498
prove_artifact ref-deb-041-060 9726385927 aurora-ksq-1-debs-041-060 sha256:f410e5185956a11b337809f1651ce8d93b6f9a2747492c7f0e5829abe4598191 5202947 33281736655 90fd5d3119ebfaab42f721d3bdd977a3472da498
prove_artifact ref-ev-061-080 9727641609 aurora-ksq-1-evidence-061-080 sha256:aaa709fe81e46d4c7c885b513ef97703fb559194ced6d111e0ace71ba8746b80 2396824 33281736655 90fd5d3119ebfaab42f721d3bdd977a3472da498
prove_artifact ref-deb-061-080 9727641105 aurora-ksq-1-debs-061-080 sha256:5fb1005caefbccc64ba86c09acbd3b56f55fd9a44c5f13307380a32b30da40c8 11468089 33281736655 90fd5d3119ebfaab42f721d3bdd977a3472da498
prove_artifact ref-ev-081-101 9729820568 aurora-ksq-1-evidence-081-101 sha256:5a2c05498f5346a1c72a25c59d9a7d3bd55788d0cce6896d9fde14726f20a6c5 2826876 33281736655 90fd5d3119ebfaab42f721d3bdd977a3472da498
prove_artifact ref-deb-081-101 9729819980 aurora-ksq-1-debs-081-101 sha256:ced4f26dd7c00c45967d3458e3f18dabab0049edcb8b03f9e8bd3fcd56c9866a 70080482 33281736655 90fd5d3119ebfaab42f721d3bdd977a3472da498

download_artifact() {
  local id="$1" digest="$2" size="$3" out="$4"
  rm -rf "$out" "$out.zip"; mkdir -p "$out"
  curl --fail --location --retry 5 --retry-all-errors \
    -H 'Accept: application/vnd.github+json' -H "Authorization: Bearer ${GH_TOKEN}" -H 'X-GitHub-Api-Version: 2022-11-28' \
    "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$id/zip" -o "$out.zip"
  [[ "$(stat -c '%s' "$out.zip")" == "$size" ]] || fail "artifact $id downloaded size mismatch"
  [[ "sha256:$(sha256sum "$out.zip" | awk '{print $1}')" == "$digest" ]] || fail "artifact $id downloaded digest mismatch"
  unzip -q "$out.zip" -d "$out"
}

candidate="$RUNNER_TEMP/candidate-canonical"
refev41="$RUNNER_TEMP/refev-041-060"; refdeb41="$RUNNER_TEMP/refdeb-041-060"
refev61="$RUNNER_TEMP/refev-061-080"; refdeb61="$RUNNER_TEMP/refdeb-061-080"
refev81="$RUNNER_TEMP/refev-081-101"; refdeb81="$RUNNER_TEMP/refdeb-081-101"
download_artifact 9981890909 sha256:96455b0b2c0ea203e67efc39fd3177da0be72543bd322f208400e90f4d7ac181 334364239 "$candidate"
download_artifact 9726386379 sha256:6591dc3fe32bced541bf6c46fbaa03534ebe7de54203f4e59d0034fec73f02e5 2002788 "$refev41"
download_artifact 9726385927 sha256:f410e5185956a11b337809f1651ce8d93b6f9a2747492c7f0e5829abe4598191 5202947 "$refdeb41"
download_artifact 9727641609 sha256:aaa709fe81e46d4c7c885b513ef97703fb559194ced6d111e0ace71ba8746b80 2396824 "$refev61"
download_artifact 9727641105 sha256:5fb1005caefbccc64ba86c09acbd3b56f55fd9a44c5f13307380a32b30da40c8 11468089 "$refdeb61"
download_artifact 9729820568 sha256:5a2c05498f5346a1c72a25c59d9a7d3bd55788d0cce6896d9fde14726f20a6c5 2826876 "$refev81"
download_artifact 9729819980 sha256:ced4f26dd7c00c45967d3458e3f18dabab0049edcb8b03f9e8bd3fcd56c9866a 70080482 "$refdeb81"

(cd "$candidate" && sha256sum -c provenance.sha256)
(cd "$candidate/payload" && sha256sum -c evidence.sha256)
source "$candidate/payload/checkpoint-status.env"
[[ "$AURORA_KSQ_1_REPRO_INPUT_STATUS" == PASS && "$AURORA_KSQ_1_REPRO_INPUT_SOURCES" == 101 && "$AURORA_KSQ_1_REPRO_INPUT_DEBS" == 424 ]] || fail "canonical payload contract mismatch"

python3 scripts/ci/analyze-ksq-repro-reference-range.py \
  --first 41 --last 98 \
  --candidate-evidence "$candidate/payload/chunks" \
  --candidate-debs "$candidate/payload/debs" \
  --reference-evidence "$refev41" --reference-debs "$refdeb41" \
  --reference-evidence "$refev61" --reference-debs "$refdeb61" \
  --reference-evidence "$refev81" --reference-debs "$refdeb81" \
  --output "$base/proof"

grep -qx 'AURORA_KSQ_1_REPRO_RANGE_STATUS=PASS' "$base/proof/status.env" || fail "range proof not PASS"
grep -qx 'AURORA_KSQ_1_REPRO_RANGE_FIRST_ORDER=41' "$base/proof/status.env" || fail "range first mismatch"
grep -qx 'AURORA_KSQ_1_REPRO_RANGE_LAST_ORDER=98' "$base/proof/status.env" || fail "range last mismatch"
grep -qx 'AURORA_KSQ_1_REPRO_RANGE_SOURCES=58' "$base/proof/status.env" || fail "range source count mismatch"
[[ "$(awk 'END{print NR-1}' "$base/proof/source-proof.tsv")" == 58 ]] || fail "source proof row count mismatch"
binaries="$(awk 'END{print NR-1}' "$base/proof/binary-proof.tsv")"
[[ "$binaries" -gt 0 ]] || fail "binary proof empty"
grep -qx "AURORA_KSQ_1_REPRO_RANGE_BINARIES=$binaries" "$base/proof/status.env" || fail "binary proof count mismatch"

cat > "$base/audit.env" <<EOF
AURORA_KSQ_R3_REPRO_041_098=PASS
AURORA_KSQ_R3_REPRO_041_098_SOURCES=58
AURORA_KSQ_R3_REPRO_041_098_BINARIES=$binaries
AURORA_KSQ_R3_REPRO_041_098_SOURCE_IDENTITY=PASS
AURORA_KSQ_R3_REPRO_041_098_BINARY_IDENTITY=PASS
AURORA_KSQ_R3_REPRO_041_098_REFERENCE_RUN=33281736655
AURORA_KSQ_R3_REPRO_041_098_REFERENCE_BUILD_JOBS=99197674603,99206441749,99217598358
AURORA_KSQ_1_FULL_CERTIFIED=no
EOF

(
  cd "$base"
  find . -type f ! -name evidence.sha256 -printf '%P\0' | sort -z | xargs -0 -r sha256sum > evidence.sha256
  sha256sum -c evidence.sha256
)
cat "$base/audit.env"
echo AURORA_KSQ_R3_REPRO_041_098_SUCCESS
