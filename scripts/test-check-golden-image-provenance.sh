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

write_image() {
    printf 'golden-fixture-v1\n' > "${IMAGE}"
}

write_provenance() {
    local golden_sha
    golden_sha="$(sha256sum "${IMAGE}" | awk '{print $1}')"
    cat > "${PROVENANCE}" <<EOF
created_at=2026-09-11T00:00:00Z
source_commit=${SOURCE_COMMIT}
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
    SUPRALINUX_GOLDEN_PROVENANCE="${PROVENANCE}" \
        "${CHECKER}" "${IMAGE}" "${EVIDENCE}"
}

write_image
write_provenance
run_check > "${TMP_DIR}/valid.log"
grep -Fqx 'Golden image provenance verification: PASS' "${TMP_DIR}/valid.log"
grep -Fqx 'golden_provenance_verification=PASS' "${EVIDENCE}"
grep -Fqx 'source_image_provenance_verified=yes' "${EVIDENCE}"

printf 'tamper\n' >> "${IMAGE}"
if run_check >/dev/null 2>&1; then
    printf 'Golden provenance checker accepted modified golden-image bytes.\n' >&2
    exit 1
fi

write_image
write_provenance
sed -i 's/^source_image_provenance_verified=yes$/source_image_provenance_verified=no/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then
    printf 'Golden provenance checker accepted a golden image without signed source verification.\n' >&2
    exit 1
fi

write_provenance
sed -i 's/^source_checkout_removed=yes$/source_checkout_removed=no/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then
    printf 'Golden provenance checker accepted a golden image without source-checkout cleanup.\n' >&2
    exit 1
fi

write_provenance
cat >> "${PROVENANCE}" <<EOF
golden_image_sha256=$(sha256sum "${IMAGE}" | awk '{print $1}')
EOF
if run_check >/dev/null 2>&1; then
    printf 'Golden provenance checker accepted duplicate golden-image hashes.\n' >&2
    exit 1
fi

write_provenance
sed -i 's/^source_image_sha256=.*/source_image_sha256=invalid/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then
    printf 'Golden provenance checker accepted an invalid source-image hash.\n' >&2
    exit 1
fi

write_provenance
sed -i 's/^source_commit=.*/source_commit=deadbeef/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then
    printf 'Golden provenance checker accepted a truncated source commit.\n' >&2
    exit 1
fi

printf 'Golden image provenance functional test: PASS\n'
