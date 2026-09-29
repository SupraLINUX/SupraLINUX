#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFIER="${ROOT}/scripts/verify-ubuntu-cloud-image-provenance.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
GNUPGHOME="${TMP_DIR}/gnupg"
IMAGE_NAME="ubuntu-26.04-server-cloudimg-amd64.img"
IMAGE="${TMP_DIR}/${IMAGE_NAME}"
PROVENANCE="${IMAGE}.provenance.txt"
SUMS="${TMP_DIR}/SHA256SUMS"
SIGNATURE="${TMP_DIR}/SHA256SUMS.gpg"
KEYRING="${TMP_DIR}/test-keyring.gpg"

mkdir -m 0700 "${GNUPGHOME}"

gpg --batch --homedir "${GNUPGHOME}" --passphrase '' \
    --quick-generate-key 'SupraLINUX CI Source Image Test <ci@supralinux.invalid>' rsa2048 sign 0 \
    >/dev/null 2>&1
gpg --batch --homedir "${GNUPGHOME}" --export > "${KEYRING}"

write_image() {
    printf 'SupraLINUX Ubuntu source image fixture\n' > "${IMAGE}"
}

write_signed_metadata() {
    local hash
    hash="$(sha256sum "${IMAGE}" | awk '{print $1}')"
    printf '%s *%s\n' "${hash}" "${IMAGE_NAME}" > "${SUMS}"
    gpg --batch --yes --homedir "${GNUPGHOME}" \
        --output "${SIGNATURE}" --detach-sign "${SUMS}"
}

write_provenance() {
    local hash
    hash="$(sha256sum "${IMAGE}" | awk '{print $1}')"
    cat > "${PROVENANCE}" <<EOF
fetched_at=2026-09-11T00:00:00Z
release=resolute
architecture=amd64
source=https://cloud-images.ubuntu.com/releases/resolute/release/${IMAGE_NAME}
sha256=${hash}
signature=verified-with-gpgv
keyring=${KEYRING}
EOF
}

verify_fixture() {
    SUPRALINUX_CLOUD_IMAGE_SUMS="${SUMS}" \
    SUPRALINUX_CLOUD_IMAGE_SIGNATURE="${SIGNATURE}" \
    SUPRALINUX_CLOUD_IMAGE_KEYRING="${KEYRING}" \
        "${VERIFIER}" "${IMAGE}" "${PROVENANCE}"
}

write_image
write_signed_metadata
write_provenance
verify_fixture > "${TMP_DIR}/valid.log" 2>&1
grep -Fqx 'Ubuntu source-image provenance verification: PASS' "${TMP_DIR}/valid.log"
grep -Fqx 'signed_metadata_verification=PASS' "${TMP_DIR}/valid.log"

printf 'tampered-image\n' >> "${IMAGE}"
if verify_fixture >/dev/null 2>&1; then
    printf 'Verifier accepted source-image bytes that differ from signed metadata.\n' >&2
    exit 1
fi

write_image
write_signed_metadata
write_provenance
printf '# unsigned tamper\n' >> "${SUMS}"
if verify_fixture >/dev/null 2>&1; then
    printf 'Verifier accepted checksum metadata modified after signing.\n' >&2
    exit 1
fi

write_image
write_signed_metadata
write_provenance
sed -i 's/^signature=.*/signature=unverified/' "${PROVENANCE}"
if verify_fixture >/dev/null 2>&1; then
    printf 'Verifier accepted provenance without the verified-with-gpgv marker.\n' >&2
    exit 1
fi

write_image
write_signed_metadata
write_provenance
HASH="$(sha256sum "${IMAGE}" | awk '{print $1}')"
printf 'sha256=%s\n' "${HASH}" >> "${PROVENANCE}"
if verify_fixture >/dev/null 2>&1; then
    printf 'Verifier accepted ambiguous provenance with duplicate sha256 fields.\n' >&2
    exit 1
fi

write_image
write_signed_metadata
write_provenance
printf 'forged-image\n' > "${IMAGE}"
FORGED_HASH="$(sha256sum "${IMAGE}" | awk '{print $1}')"
sed -i "s/^sha256=.*/sha256=${FORGED_HASH}/" "${PROVENANCE}"
if verify_fixture >/dev/null 2>&1; then
    printf 'Verifier accepted jointly modified image/provenance without matching signed metadata.\n' >&2
    exit 1
fi

printf 'Ubuntu source-image provenance functional test: PASS (signed metadata reverified)\n'
