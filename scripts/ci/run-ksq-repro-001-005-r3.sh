#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

TRIGGER=.github/ksq-r3-repro-001-005-trigger.env
[[ -f "$TRIGGER" ]] || { echo "AURORA_KSQ_R3_REPRO_001_005_FAILURE: trigger missing" >&2; exit 1; }
# shellcheck disable=SC1090
source "$TRIGGER"

fail() {
  echo "AURORA_KSQ_R3_REPRO_001_005_FAILURE: $*" >&2
  exit 1
}

[[ "${AURORA_KSQ_R3_REPRO_001_005_SLICE_ID:-}" == 20260829T022000Z-r3 ]] || fail "slice pin mismatch"
[[ "${AURORA_KSQ_R3_REPRO_001_005_FIRST_ORDER:-}" == 1 ]] || fail "first-order pin mismatch"
[[ "${AURORA_KSQ_R3_REPRO_001_005_LAST_ORDER:-}" == 5 ]] || fail "last-order pin mismatch"
[[ "${AURORA_KSQ_R3_REPRO_001_005_SOURCE_PREP_UMASK:-}" == 0002 ]] || fail "source-prep umask pin mismatch"
[[ "${AURORA_KSQ_R3_REPRO_001_005_CANONICAL_RUN_ID:-}" == 34009066345 ]] || fail "canonical run pin mismatch"
[[ "${AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_ID:-}" == 9981890909 ]] || fail "canonical artifact pin mismatch"
[[ "${AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_DIGEST:-}" == sha256:96455b0b2c0ea203e67efc39fd3177da0be72543bd322f208400e90f4d7ac181 ]] || fail "canonical digest pin mismatch"
[[ "${AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_SIZE:-}" == 334364239 ]] || fail "canonical size pin mismatch"

[[ -n "${GH_TOKEN:-}" ]] || fail "GH_TOKEN missing"
[[ -n "${GITHUB_REPOSITORY:-}" ]] || fail "GITHUB_REPOSITORY missing"
[[ -n "${RUNNER_TEMP:-}" ]] || fail "RUNNER_TEMP missing"

grep -Eq '^VERSION_ID="26\.04(\.1)?"$' /etc/os-release || fail "runner is not Ubuntu 26.04"
[[ "$(dpkg --print-architecture)" == amd64 ]] || fail "runner architecture is not amd64"

base=build/ksq-1/repro-001-005-r3
rm -rf "$base"
mkdir -p "$base/host-evidence" "$base/provenance" "$base/reference"
date --iso-8601=seconds > "$base/host-evidence/start-time.txt"
cp "$TRIGGER" "$base/provenance/trigger.env"

# Prove the canonical candidate input before consuming it.
gh api "/repos/$GITHUB_REPOSITORY/actions/runs/$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_RUN_ID" > "$base/provenance/canonical-run.json"
[[ "$(jq -r '.status' "$base/provenance/canonical-run.json")" == completed ]] || fail "canonical run incomplete"
[[ "$(jq -r '.conclusion' "$base/provenance/canonical-run.json")" == success ]] || fail "canonical run not successful"
[[ "$(jq -r '.head_sha' "$base/provenance/canonical-run.json")" == 12ed5856b31ebe3870791c5e3d71ecfec70eba43 ]] || fail "canonical run head mismatch"

gh api "/repos/$GITHUB_REPOSITORY/actions/artifacts/$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_ID" > "$base/provenance/canonical-artifact.json"
[[ "$(jq -r '.name' "$base/provenance/canonical-artifact.json")" == aurora-ksq-repro-input-101-r3 ]] || fail "canonical artifact name mismatch"
[[ "$(jq -r '.digest' "$base/provenance/canonical-artifact.json")" == "$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_DIGEST" ]] || fail "canonical artifact digest mismatch"
[[ "$(jq -r '.size_in_bytes' "$base/provenance/canonical-artifact.json")" == "$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_SIZE" ]] || fail "canonical artifact size mismatch"
[[ "$(jq -r '.workflow_run.id' "$base/provenance/canonical-artifact.json")" == "$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_RUN_ID" ]] || fail "canonical artifact run mismatch"
[[ "$(jq -r '.workflow_run.head_sha' "$base/provenance/canonical-artifact.json")" == 12ed5856b31ebe3870791c5e3d71ecfec70eba43 ]] || fail "canonical artifact head mismatch"
[[ "$(jq -r '.expired' "$base/provenance/canonical-artifact.json")" == false ]] || fail "canonical artifact expired"

canonical="$RUNNER_TEMP/canonical-repro-input"
rm -rf "$canonical" "$canonical.zip"
mkdir -p "$canonical"
curl --fail --location --retry 5 --retry-all-errors \
  -H 'Accept: application/vnd.github+json' \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_ID/zip" \
  -o "$canonical.zip"
[[ "$(stat -c '%s' "$canonical.zip")" == "$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_SIZE" ]] || fail "downloaded canonical size mismatch"
[[ "sha256:$(sha256sum "$canonical.zip" | awk '{print $1}')" == "$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_DIGEST" ]] || fail "downloaded canonical digest mismatch"
unzip -q "$canonical.zip" -d "$canonical"
(
  cd "$canonical"
  sha256sum -c provenance.sha256
)
(
  cd "$canonical/payload"
  sha256sum -c evidence.sha256
)
# shellcheck disable=SC1090
source "$canonical/payload/checkpoint-status.env"
[[ "${AURORA_KSQ_1_REPRO_INPUT_STATUS:-}" == PASS ]] || fail "canonical payload status is not PASS"
[[ "${AURORA_KSQ_1_REPRO_INPUT_SOURCES:-}" == 101 ]] || fail "canonical source count mismatch"
[[ "${AURORA_KSQ_1_REPRO_INPUT_DEBS:-}" == 424 ]] || fail "canonical DEB count mismatch"
[[ "${AURORA_KSQ_1_REPRO_INPUT_CANONICAL_RANGES:-}" == 5 ]] || fail "canonical range count mismatch"
[[ -d "$canonical/payload/chunks/chunk-001-020" ]] || fail "canonical 001-020 range missing"

# Prepare only the supported stable Ubuntu 26.04 toolchain used by the accepted native builder.
sudo apt-get -o Acquire::Retries=5 -o APT::Update::Error-Mode=any update
sudo apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
  ca-certificates curl python3 ubuntu-keyring gpgv jq unzip \
  sbuild mmdebstrap uidmap zstd devscripts dpkg-dev apt-utils \
  gzip xz-utils diffutils build-essential apparmor apparmor-utils libcap2-bin

dpkg-query -W -f='${Package}\t${Version}\n' sbuild libsbuild-perl mmdebstrap uidmap util-linux apparmor | sort | tee "$base/host-evidence/toolchain.tsv"
grep -q $'^sbuild\t0.91.2ubuntu3$' "$base/host-evidence/toolchain.tsv" || fail "unexpected sbuild version"
grep -q $'^libsbuild-perl\t0.91.2ubuntu3$' "$base/host-evidence/toolchain.tsv" || fail "unexpected libsbuild-perl version"
grep -q $'^mmdebstrap\t1.5.7-3$' "$base/host-evidence/toolchain.tsv" || fail "unexpected mmdebstrap version"
[[ "$(stat -c '%a' /usr/bin/newuidmap)" == 4755 ]] || fail "newuidmap is not stock setuid"
[[ "$(stat -c '%a' /usr/bin/newgidmap)" == 4755 ]] || fail "newgidmap is not stock setuid"
[[ -z "$(getcap /usr/bin/newuidmap /usr/bin/newgidmap || true)" ]] || fail "uidmap file capabilities unexpectedly present"

# Reuse the independently validated immutable r3 publication; certified build I/O is local-only after this point.
r3v="$RUNNER_TEMP/r3-validation"
rm -rf "$r3v" "$r3v.zip"
mkdir -p "$r3v"
curl --fail --location --retry 5 --retry-all-errors \
  -H 'Accept: application/vnd.github+json' \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/9969086882/zip" \
  -o "$r3v.zip"
unzip -q "$r3v.zip" -d "$r3v"
(
  cd "$r3v"
  sha256sum -c evidence.sha256
)
# shellcheck disable=SC1090
source "$r3v/acceptance.env"
[[ "${AURORA_KSQ_SNAPSHOT_R3_INDEPENDENT_VALIDATION:-}" == PASS ]] || fail "r3 independent validation is not PASS"
# shellcheck disable=SC1090
source "$r3v/publication.env"
[[ "${AURORA_KSQ_SNAPSHOT_R3_RELEASE_ASSET_SHA256:-}" == cb904b478afe186b96823b1b2872d5937517e3de10c6d2dd3170ec29fea09bc6 ]] || fail "r3 release digest pin mismatch"

release="$RUNNER_TEMP/r3-release"
rm -rf "$release"
mkdir -p "$release"
gh release download "$AURORA_KSQ_SNAPSHOT_R3_RELEASE_TAG" -R "$GITHUB_REPOSITORY" \
  -p "$AURORA_KSQ_SNAPSHOT_R3_RELEASE_ASSET" \
  -p "$AURORA_KSQ_SNAPSHOT_R3_RELEASE_MANIFEST" \
  -D "$release"
[[ "$(sha256sum "$release/$AURORA_KSQ_SNAPSHOT_R3_RELEASE_ASSET" | awk '{print $1}')" == "$AURORA_KSQ_SNAPSHOT_R3_RELEASE_ASSET_SHA256" ]] || fail "r3 release archive digest mismatch"

sudo install -d -o "$(id -u)" -g "$(id -g)" -m 0755 /opt/supralinux/archive
tar -xf "$release/$AURORA_KSQ_SNAPSHOT_R3_RELEASE_ASSET" -C /opt/supralinux/archive
python3 scripts/ci/ksq-snapshot-slice-r3.py validate --slice-root /opt/supralinux/archive/20260829T022000Z-r3

slice=/opt/supralinux/archive/20260829T022000Z-r3
AURORA_KSQ_LOCAL_SLICE_ROOT="$slice" bash scripts/ci/prepare-ksq-1-local-apt-metadata.sh 2>&1 | tee "$base/local-apt-metadata.log"
grep -q '^AURORA_KSQ_1_LOCAL_APT_HOST_FRAGMENTS=disabled$' "$base/local-apt-metadata.log" || fail "host apt fragments not disabled"
grep -q '^AURORA_KSQ_1_LOCAL_APT_SUCCESS$' "$base/local-apt-metadata.log" || fail "local apt preparation failed"
! grep -Eq 'c-n-f|/cnf/|Components' "$base/local-apt-metadata.log" || fail "unexpected command-not-found metadata"
! grep -Eq '^(Get|Hit|Ign|Err):[0-9]+ https?://' "$base/local-apt-metadata.log" || fail "remote APT transport in local metadata step"

python3 scripts/ci/generate-kde-build-closure.py
[[ "$(sha256sum build/ksq-0/build-order.tsv | awk '{print $1}')" == 9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88 ]] || fail "build-order identity mismatch"

AURORA_KSQ_LOCAL_SLICE_ROOT="$slice" bash scripts/ci/prepare-ksq-1-local-build-environment.sh 2>&1 | tee "$base/mmdebstrap-buildd.log"
grep -q '^AURORA_KSQ_1_LOCAL_BUILD_ENV_SUCCESS$' "$base/mmdebstrap-buildd.log" || fail "local build environment failed"
! grep -Eq '^(Get|Hit|Ign|Err):[0-9]+ https?://' "$base/mmdebstrap-buildd.log" || fail "remote APT transport while building chroot"

bash scripts/ci/configure-ksq-1-native-sbuild-network-proof.sh 2>&1 | tee "$base/network-proof-config.log"
grep -qx 'AURORA_KSQ_1_NATIVE_NETWORK_PROOF=PASS' build/ksq-1/environment/native-sbuild-network-proof.env || fail "native network proof missing"

# Orders 001-005 were prepared in the accepted checkpoint under umask 0002. Reproduce that exact source identity.
rm -rf build/ksq-1/full
mkdir -p build/ksq-1/full/debs
umask "$AURORA_KSQ_R3_REPRO_001_005_SOURCE_PREP_UMASK"
[[ "$(umask)" == 0002 ]] || fail "effective source-prep umask mismatch"
printf 'AURORA_KSQ_1_REPRO_SOURCE_PREP_UMASK=%s\n' "$(umask)" | tee "$base/source-preparation.env"
# shellcheck disable=SC1091
source build/ksq-1/environment/build-environment.env
export SBUILD_CONFIG="$AURORA_KSQ_1_SBUILD_CONFIG"

bash scripts/ci/build-ksq-1-range.sh 1 5 2>&1 | tee "$base/range.log"
chunk=build/ksq-1/full/chunk-001-005
[[ -d "$chunk" ]] || fail "rebuilt 001-005 chunk missing"
grep -qx 'AURORA_KSQ_1_RANGE_STATUS=PASS' "$chunk/evidence/range-status.env" || fail "rebuilt range status is not PASS"
grep -qx 'AURORA_KSQ_1_RANGE_FIRST_ORDER=1' "$chunk/evidence/range-status.env" || fail "rebuilt first order mismatch"
grep -qx 'AURORA_KSQ_1_RANGE_LAST_ORDER=5' "$chunk/evidence/range-status.env" || fail "rebuilt last order mismatch"
[[ "$(find "$chunk/new-debs" -maxdepth 1 -type f -name '*.deb' | wc -l)" == 12 ]] || fail "rebuilt 001-005 DEB count mismatch"
(
  cd "$chunk/new-debs"
  sha256sum -c ../evidence/new-debs.sha256
)

python3 scripts/ci/validate-ksq-1-repro-range.py \
  --first 1 \
  --last 5 \
  --candidate-root-range "1-20=$canonical/payload/chunks/chunk-001-020" \
  --rebuilt-root "$chunk" \
  --output "$base/analysis"
grep -qx 'AURORA_KSQ_1_REPRO_RANGE_STATUS=PASS' "$base/analysis/status.env" || fail "001-005 reproducibility analysis not PASS"
grep -qx 'AURORA_KSQ_1_REPRO_RANGE_FIRST_ORDER=1' "$base/analysis/status.env" || fail "analysis first order mismatch"
grep -qx 'AURORA_KSQ_1_REPRO_RANGE_LAST_ORDER=5' "$base/analysis/status.env" || fail "analysis last order mismatch"
grep -qx 'AURORA_KSQ_1_REPRO_RANGE_SOURCES=5' "$base/analysis/status.env" || fail "analysis source count mismatch"
grep -qx 'AURORA_KSQ_1_REPRO_RANGE_BINARIES=12' "$base/analysis/status.env" || fail "analysis binary count mismatch"

# Preserve a compact reusable reference root for the final 95+6 proof.
cp -a "$chunk/evidence" "$base/reference/evidence"
mkdir -p "$base/reference/debs"
cp -a "$chunk/new-debs/"*.deb "$base/reference/debs/"
[[ "$(find "$base/reference/debs" -maxdepth 1 -type f -name '*.deb' | wc -l)" == 12 ]] || fail "preserved reference DEB count mismatch"

start="$(cat "$base/host-evidence/start-time.txt")"
sudo journalctl -k --since "$start" --no-pager 2>/dev/null | grep 'apparmor="DENIED"' > "$base/host-evidence/apparmor-denied-all.log" || true
grep -Ei 'profile="[^\"]*(sbuild|mmdebstrap|unprivileged_userns)[^\"]*"|comm="(sbuild|mmdebstrap|unshare|mount|newuidmap|newgidmap)"' \
  "$base/host-evidence/apparmor-denied-all.log" > "$base/host-evidence/apparmor-denied-relevant.log" || true
denials="$(wc -l < "$base/host-evidence/apparmor-denied-relevant.log")"
[[ "$denials" == 0 ]] || fail "relevant AppArmor denials observed: $denials"

cat > "$base/audit.env" <<EOF
AURORA_KSQ_R3_REPRO_001_005=PASS
AURORA_KSQ_R3_REPRO_001_005_SOURCES=5
AURORA_KSQ_R3_REPRO_001_005_BINARIES=12
AURORA_KSQ_R3_REPRO_001_005_SOURCE_IDENTITY=PASS
AURORA_KSQ_R3_REPRO_001_005_BINARY_IDENTITY=PASS
AURORA_KSQ_R3_REPRO_001_005_SOURCE_PREP_UMASK=0002
AURORA_KSQ_R3_REPRO_001_005_APPARMOR_DENIALS=0
AURORA_KSQ_R3_REPRO_001_005_DOCKER_USED=0
AURORA_KSQ_R3_REPRO_001_005_CUSTOM_APPARMOR_USED=0
AURORA_KSQ_R3_REPRO_001_005_UIDMAP_FILECAP_PATCH_USED=0
AURORA_KSQ_R3_REPRO_001_005_CANONICAL_INPUT_RUN=$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_RUN_ID
AURORA_KSQ_R3_REPRO_001_005_CANONICAL_INPUT_ARTIFACT=$AURORA_KSQ_R3_REPRO_001_005_CANONICAL_ARTIFACT_ID
AURORA_KSQ_1_FULL_CERTIFIED=no
EOF

# Self-contained integrity manifest for everything retained by this run.
(
  cd "$base"
  find . -type f ! -name evidence.sha256 -printf '%P\0' | sort -z | xargs -0 -r sha256sum > evidence.sha256
  sha256sum -c evidence.sha256
)

cat "$base/audit.env"
echo AURORA_KSQ_R3_REPRO_001_005_SUCCESS
