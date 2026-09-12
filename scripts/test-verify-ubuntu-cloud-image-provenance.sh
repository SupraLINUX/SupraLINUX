#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFIER="${ROOT}/scripts/verify-ubuntu-cloud-image-provenance.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
IMAGE="${TMP_DIR}/ubuntu-26.04-server-cloudimg-amd64.img"
PROVENANCE="${IMAGE}.provenance.txt"

write_valid_fixture() {
    printf 'SupraLINUX Ubuntu source image fixture\n' > "${IMAGE}"
    local hash
    hash="$(sha256sum "${IMAGE}" | awk '{print $1}')"
    cat > "${PROVENANCE}" <<EOF
fetched_at=2026-09-11T00:00:00Z
release=resolute
architecture=amd64
source=https://cloud-images.ubuntu.com/releases/resolute/release/ubuntu-26.04-server-cloudimg-amd64.img
sha256=${hash}
signature=verified-with-gpgv
keyring=/usr/share/keyrings/ubuntu-cloudimage-keyring.gpg
EOF
}

write_valid_fixture
"${VERIFIER}" "${IMAGE}" "${PROVENANCE}" > "${TMP_DIR}/valid.log"
grep -Fqx 'Ubuntu source-image provenance verification: PASS' "${TMP_DIR}/valid.log"

printf 'tampered\n' >> "${IMAGE}"
if "${VERIFIER}" "${IMAGE}" "${PROVENANCE}" >/dev/null 2>&1; then
    printf 'Verifier accepted a source image whose bytes no longer match provenance.\n' >&2
    exit 1
fi

write_valid_fixture
sed -i 's/^signature=.*/signature=unverified/' "${PROVENANCE}"
if "${VERIFIER}" "${IMAGE}" "${PROVENANCE}" >/dev/null 2>&1; then
    printf 'Verifier accepted provenance without the verified-with-gpgv marker.\n' >&2
    exit 1
fi

write_valid_fixture
HASH="$(awk -F= '$1 == "sha256" {print $2}' "${PROVENANCE}")"
printf 'sha256=%s\n' "${HASH}" >> "${PROVENANCE}"
if "${VERIFIER}" "${IMAGE}" "${PROVENANCE}" >/dev/null 2>&1; then
    printf 'Verifier accepted ambiguous provenance with duplicate sha256 fields.\n' >&2
    exit 1
fi

printf 'Ubuntu source-image provenance functional test: PASS\n'
