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

# autopkgtest 5.55 x86_64 with /dev/kvm appends -enable-kvm.
mapfile -t AUTOPKGTEST_5_55_STYLE < <(
    SUPRALINUX_QEMU_SYSTEM_X86_64="${FAKE_QEMU}"         "${WRAPPER}"         -m 2048         -smp 2         -nographic         -name 'Supra Linux Runner'         -enable-kvm         -cpu host
)

EXPECTED_AUTOPKGTEST_5_55_STYLE=(
    -accel
    kvm
    -m
    2048
    -smp
    2
    -nographic
    -name
    'Supra Linux Runner'
    -cpu
    host
)

if (( ${#AUTOPKGTEST_5_55_STYLE[@]} != ${#EXPECTED_AUTOPKGTEST_5_55_STYLE[@]} )); then
    printf 'autopkgtest-5.55 argument count mismatch: expected=%d actual=%d\n'         "${#EXPECTED_AUTOPKGTEST_5_55_STYLE[@]}"         "${#AUTOPKGTEST_5_55_STYLE[@]}" >&2
    printf 'Actual arguments:\n' >&2
    printf '  <%s>\n' "${AUTOPKGTEST_5_55_STYLE[@]}" >&2
    exit 1
fi

for i in "${!EXPECTED_AUTOPKGTEST_5_55_STYLE[@]}"; do
    if [[ "${AUTOPKGTEST_5_55_STYLE[$i]}" != "${EXPECTED_AUTOPKGTEST_5_55_STYLE[$i]}" ]]; then
        printf 'autopkgtest-5.55 mismatch at index %d: expected=<%s> actual=<%s>\n'             "${i}"             "${EXPECTED_AUTOPKGTEST_5_55_STYLE[$i]}"             "${AUTOPKGTEST_5_55_STYLE[$i]}" >&2
        exit 1
    fi
done

if printf '%s\n' "${AUTOPKGTEST_5_55_STYLE[@]}" | grep -qx -- '-enable-kvm'; then
    printf 'Wrapper must remove autopkgtest -enable-kvm before emitting canonical -accel kvm.\n' >&2
    exit 1
fi

mapfile -t MACHINE_STYLE < <(
    SUPRALINUX_QEMU_SYSTEM_X86_64="${FAKE_QEMU}"         "${WRAPPER}"         -machine q35,accel=kvm:tcg         -enable-kvm         -accel tcg         -m 256         -name 'Supra Linux Runner'
)

EXPECTED_MACHINE_STYLE=(
    -machine
    'q35,accel=kvm'
    -m
    256
    -name
    'Supra Linux Runner'
)

if (( ${#MACHINE_STYLE[@]} != ${#EXPECTED_MACHINE_STYLE[@]} )); then
    printf 'machine-style argument count mismatch: expected=%d actual=%d\n'         "${#EXPECTED_MACHINE_STYLE[@]}"         "${#MACHINE_STYLE[@]}" >&2
    printf 'Actual arguments:\n' >&2
    printf '  <%s>\n' "${MACHINE_STYLE[@]}" >&2
    exit 1
fi

for i in "${!EXPECTED_MACHINE_STYLE[@]}"; do
    if [[ "${MACHINE_STYLE[$i]}" != "${EXPECTED_MACHINE_STYLE[$i]}" ]]; then
        printf 'machine-style mismatch at index %d: expected=<%s> actual=<%s>\n'             "${i}"             "${EXPECTED_MACHINE_STYLE[$i]}"             "${MACHINE_STYLE[$i]}" >&2
        exit 1
    fi
done

if printf '%s\n' "${MACHINE_STYLE[@]}" | grep -Eq '^(-accel|-enable-kvm)$'; then
    printf 'Machine-style invocation must retain only -machine accel=kvm as accelerator selector.\n' >&2
    exit 1
fi

set +e
SUPRALINUX_QEMU_SYSTEM_X86_64="${TMP_DIR}/missing-qemu"     "${WRAPPER}" -machine q35 >/dev/null 2>&1
MISSING_RC=$?
set -e

if [[ "${MISSING_RC}" -ne 127 ]]; then
    printf 'Missing QEMU executable should return 127; got %d\n' "${MISSING_RC}" >&2
    exit 1
fi

printf 'KVM-required QEMU wrapper functional test: PASS\n'
