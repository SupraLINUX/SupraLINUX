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

mapfile -t AUTOPKGTEST_STYLE < <(
    SUPRALINUX_QEMU_SYSTEM_X86_64="${FAKE_QEMU}"         "${WRAPPER}"         -machine q35,accel=kvm:tcg         -m 256         -name 'Supra Linux Runner'
)

EXPECTED_AUTOPKGTEST_STYLE=(
    -machine
    'q35,accel=kvm'
    -m
    256
    -name
    'Supra Linux Runner'
)

if (( ${#AUTOPKGTEST_STYLE[@]} != ${#EXPECTED_AUTOPKGTEST_STYLE[@]} )); then
    printf 'Autopkgtest-style wrapper argument count mismatch: expected=%d actual=%d\n'         "${#EXPECTED_AUTOPKGTEST_STYLE[@]}" "${#AUTOPKGTEST_STYLE[@]}" >&2
    printf 'Actual arguments:\n' >&2
    printf '  <%s>\n' "${AUTOPKGTEST_STYLE[@]}" >&2
    exit 1
fi

for i in "${!EXPECTED_AUTOPKGTEST_STYLE[@]}"; do
    if [[ "${AUTOPKGTEST_STYLE[$i]}" != "${EXPECTED_AUTOPKGTEST_STYLE[$i]}" ]]; then
        printf 'Autopkgtest-style wrapper mismatch at index %d: expected=<%s> actual=<%s>\n'             "${i}" "${EXPECTED_AUTOPKGTEST_STYLE[$i]}" "${AUTOPKGTEST_STYLE[$i]}" >&2
        exit 1
    fi
done

if printf '%s\n' "${AUTOPKGTEST_STYLE[@]}" | grep -qx -- '-accel'; then
    printf 'Wrapper must not combine top-level -accel with -machine accel=.\n' >&2
    exit 1
fi

mapfile -t NO_MACHINE < <(
    SUPRALINUX_QEMU_SYSTEM_X86_64="${FAKE_QEMU}"         "${WRAPPER}"         -m 256         -name 'Supra Linux Runner'
)

EXPECTED_NO_MACHINE=(
    -accel
    kvm
    -m
    256
    -name
    'Supra Linux Runner'
)

if (( ${#NO_MACHINE[@]} != ${#EXPECTED_NO_MACHINE[@]} )); then
    printf 'No-machine wrapper argument count mismatch.\n' >&2
    exit 1
fi

for i in "${!EXPECTED_NO_MACHINE[@]}"; do
    if [[ "${NO_MACHINE[$i]}" != "${EXPECTED_NO_MACHINE[$i]}" ]]; then
        printf 'No-machine wrapper mismatch at index %d: expected=<%s> actual=<%s>\n'             "${i}" "${EXPECTED_NO_MACHINE[$i]}" "${NO_MACHINE[$i]}" >&2
        exit 1
    fi
done

set +e
SUPRALINUX_QEMU_SYSTEM_X86_64="${TMP_DIR}/missing-qemu"     "${WRAPPER}" -machine q35 >/dev/null 2>&1
MISSING_RC=$?
set -e

if [[ "${MISSING_RC}" -ne 127 ]]; then
    printf 'Missing QEMU executable should return 127; got %d\n' "${MISSING_RC}" >&2
    exit 1
fi

printf 'KVM-required QEMU wrapper functional test: PASS\n'
