#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKER="${ROOT}/scripts/check-golden-image-provenance.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
IMAGE="${TMP_DIR}/golden.qcow2"
PROVENANCE="${IMAGE}.provenance.txt"
EVIDENCE="${TMP_DIR}/verification.txt"
SOURCE_SHA="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SOURCE_COMMIT="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
CURRENT_INPUT_DIGEST="$("${ROOT}/scripts/golden-image-input-digest.sh" HEAD)"

write_image() { printf 'golden-fixture-v1\n' > "${IMAGE}"; }
write_provenance() {
    local golden_sha
    golden_sha="$(sha256sum "${IMAGE}" | awk '{print $1}')"
    cat > "${PROVENANCE}" <<EOF
created_at=2026-09-30T00:00:00Z
source_commit=${SOURCE_COMMIT}
golden_input_fingerprint_schema=1
golden_input_digest=${CURRENT_INPUT_DIGEST}
source_image=/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img
source_image_sha256=${SOURCE_SHA}
golden_image=${IMAGE}
golden_image_sha256=${golden_sha}
virt_sysprep_operations=machine-id,ssh-hostkeys,dhcp-client-state,logfiles,tmp-files
source_checkout_removed=yes
source_image_provenance_verified=yes
EOF
}
run_check() {
    SUPRALINUX_GOLDEN_PROVENANCE="${PROVENANCE}" "${CHECKER}" "${IMAGE}" "${EVIDENCE}"
}

write_image
write_provenance
run_check > "${TMP_DIR}/valid.log"
grep -Fqx 'Golden image provenance verification: PASS' "${TMP_DIR}/valid.log"
grep -Fqx 'golden_provenance_verification=PASS' "${EVIDENCE}"
grep -Fqx 'golden_input_compatibility=PASS' "${EVIDENCE}"
grep -Fqx "golden_input_digest=${CURRENT_INPUT_DIGEST}" "${EVIDENCE}"

printf 'tamper\n' >> "${IMAGE}"
if run_check >/dev/null 2>&1; then printf 'Accepted modified golden bytes.\n' >&2; exit 1; fi

write_image; write_provenance
sed -i 's/^source_image_provenance_verified=yes$/source_image_provenance_verified=no/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then printf 'Accepted missing signed-source proof.\n' >&2; exit 1; fi

write_provenance
sed -i 's/^source_checkout_removed=yes$/source_checkout_removed=no/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then printf 'Accepted missing source cleanup.\n' >&2; exit 1; fi

write_provenance
cat >> "${PROVENANCE}" <<EOF
golden_image_sha256=$(sha256sum "${IMAGE}" | awk '{print $1}')
EOF
if run_check >/dev/null 2>&1; then printf 'Accepted duplicate golden hash.\n' >&2; exit 1; fi

write_provenance
sed -i 's/^source_image_sha256=.*/source_image_sha256=invalid/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then printf 'Accepted invalid source hash.\n' >&2; exit 1; fi

write_provenance
sed -i 's/^source_commit=.*/source_commit=deadbeef/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then printf 'Accepted truncated source commit.\n' >&2; exit 1; fi

write_provenance
sed -i 's/^golden_input_fingerprint_schema=1$/golden_input_fingerprint_schema=2/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then printf 'Accepted unsupported fingerprint schema.\n' >&2; exit 1; fi

write_provenance
sed -i 's/^golden_input_digest=.*/golden_input_digest=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then printf 'Accepted stale golden inputs.\n' >&2; exit 1; fi

write_provenance
cat >> "${PROVENANCE}" <<EOF
golden_input_digest=${CURRENT_INPUT_DIGEST}
EOF
if run_check >/dev/null 2>&1; then printf 'Accepted duplicate input digest.\n' >&2; exit 1; fi

printf 'Golden image provenance functional test: PASS\n'
