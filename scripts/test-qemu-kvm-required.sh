#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="${ROOT}/scripts/qemu-kvm-required.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
FAKE_QEMU="${TMP_DIR}/fake-qemu"

cat > "${FAKE_QEMU}" <<'FAKE'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$@"
FAKE
chmod +x "${FAKE_QEMU}"

mapfile -t ACTUAL < <(
    SUPRALINUX_QEMU_SYSTEM_X86_64="${FAKE_QEMU}" \
        "${WRAPPER}" \
        -machine q35 \
        -m 256 \
        -name 'Supra Linux Runner'
)

EXPECTED=(
    -accel
    kvm
    -machine
    q35
    -m
    256
    -name
    'Supra Linux Runner'
)

if (( ${#ACTUAL[@]} != ${#EXPECTED[@]} )); then
    printf 'Wrapper argument count mismatch: expected=%d actual=%d\n' \
        "${#EXPECTED[@]}" "${#ACTUAL[@]}" >&2
    printf 'Actual arguments:\n' >&2
    printf '  <%s>\n' "${ACTUAL[@]}" >&2
    exit 1
fi

for i in "${!EXPECTED[@]}"; do
    if [[ "${ACTUAL[$i]}" != "${EXPECTED[$i]}" ]]; then
        printf 'Wrapper argument mismatch at index %d: expected=<%s> actual=<%s>\n' \
            "${i}" "${EXPECTED[$i]}" "${ACTUAL[$i]}" >&2
        exit 1
    fi
done

set +e
SUPRALINUX_QEMU_SYSTEM_X86_64="${TMP_DIR}/missing-qemu" \
    "${WRAPPER}" -machine q35 >/dev/null 2>&1
MISSING_RC=$?
set -e

if [[ "${MISSING_RC}" -ne 127 ]]; then
    printf 'Missing QEMU executable should return 127; got %d\n' "${MISSING_RC}" >&2
    exit 1
fi

printf 'KVM-required QEMU wrapper functional test: PASS\n'
