#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="${ROOT}/scripts/qemu-kvm-required.sh"
AUTOPKGTEST_QEMU_LIB="/usr/share/autopkgtest/lib/autopkgtest_qemu.py"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

if ! dpkg-query -W -f='${Version}\n' autopkgtest >/dev/null 2>&1; then
    printf 'autopkgtest must be installed for the QEMU argv lifecycle preflight.\n' >&2
    exit 1
fi

AUTOPKGTEST_VERSION="$(dpkg-query -W -f='${Version}' autopkgtest)"

if [[ ! -r "${AUTOPKGTEST_QEMU_LIB}" ]]; then
    printf 'Missing installed autopkgtest QEMU implementation: %s\n' "${AUTOPKGTEST_QEMU_LIB}" >&2
    exit 1
fi

if ! grep -Fq 'argv.append("-enable-kvm")' "${AUTOPKGTEST_QEMU_LIB}"; then
    printf 'Installed autopkgtest no longer exposes the expected -enable-kvm KVM contract; review provider semantics before retry.\n' >&2
    exit 1
fi

FAKE_QEMU="${TMP_DIR}/fake-qemu"
cat > "${FAKE_QEMU}" <<'FAKE'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$@"
FAKE
chmod +x "${FAKE_QEMU}"

mapfile -t ACTUAL < <(
    SUPRALINUX_QEMU_SYSTEM_X86_64="${FAKE_QEMU}"         "${WRAPPER}"         -m 2048         -smp 2         -nographic         -enable-kvm         -cpu host         -name 'Supra Linux Runner'
)

EXPECTED=(
    -accel
    kvm
    -m
    2048
    -smp
    2
    -nographic
    -cpu
    host
    -name
    'Supra Linux Runner'
)

if (( ${#ACTUAL[@]} != ${#EXPECTED[@]} )); then
    printf 'Synthetic autopkgtest QEMU argv count mismatch: expected=%d actual=%d\n'         "${#EXPECTED[@]}" "${#ACTUAL[@]}" >&2
    printf 'Actual arguments:\n' >&2
    printf '  <%s>\n' "${ACTUAL[@]}" >&2
    exit 1
fi

for i in "${!EXPECTED[@]}"; do
    if [[ "${ACTUAL[$i]}" != "${EXPECTED[$i]}" ]]; then
        printf 'Synthetic autopkgtest QEMU argv mismatch at index %d: expected=<%s> actual=<%s>\n'             "${i}" "${EXPECTED[$i]}" "${ACTUAL[$i]}" >&2
        exit 1
    fi
done

if printf '%s\n' "${ACTUAL[@]}" | grep -qx -- '-enable-kvm'; then
    printf 'Synthetic preflight retained conflicting -enable-kvm.\n' >&2
    exit 1
fi

if [[ "$(printf '%s\n' "${ACTUAL[@]}" | grep -cx -- '-accel')" -ne 1 ]]; then
    printf 'Synthetic preflight must emit exactly one top-level -accel selector.\n' >&2
    exit 1
fi

printf 'autopkgtest_version=%s\n' "${AUTOPKGTEST_VERSION}"
printf 'provider_contract=-enable-kvm\n'
printf 'normalized_acceleration=-accel kvm\n'
printf 'Synthetic autopkgtest QEMU argv lifecycle preflight: PASS\n'
