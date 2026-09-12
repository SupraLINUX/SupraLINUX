#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECKER="${ROOT}/scripts/check-actions-runner-runtime.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT
RUNNER_DIR="${TMP_DIR}/actions-runner"
PROVENANCE="${TMP_DIR}/actions-runner.txt"
EVIDENCE="${TMP_DIR}/runtime-evidence.txt"
mkdir -p "${RUNNER_DIR}/bin"

cat > "${RUNNER_DIR}/bin/Runner.Listener" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
    --version) printf '%s\n' "${FAKE_RUNNER_VERSION:-2.337.0}" ;;
    --commit) printf '%s\n' "${FAKE_RUNNER_COMMIT:-397b032cbf865e9c3ddfab89d533ec19325e1273}" ;;
    *) exit 2 ;;
esac
EOF
chmod 0755 "${RUNNER_DIR}/bin/Runner.Listener"

write_provenance() {
    cat > "${PROVENANCE}" <<'EOF'
installed_at=2026-09-11T00:00:00Z
source_repo=actions/runner
tag=v2.337.0
asset=actions-runner-linux-x64-2.337.0.tar.gz
asset_sha256=70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613
asset_url=https://github.com/actions/runner/releases/download/v2.337.0/actions-runner-linux-x64-2.337.0.tar.gz
EOF
}

run_check() {
    SUPRALINUX_ACTIONS_RUNNER_DIR="${RUNNER_DIR}" \
    SUPRALINUX_RUNNER_PROVENANCE="${PROVENANCE}" \
        "${CHECKER}" "${EVIDENCE}"
}

write_provenance
run_check > "${TMP_DIR}/valid.log"
grep -Fqx 'Actions runner runtime provenance verification: PASS' "${TMP_DIR}/valid.log"
grep -Fqx 'runtime_matches_verified_version=yes' "${EVIDENCE}"
grep -Fqx 'runtime_version=2.337.0' "${EVIDENCE}"
grep -Fqx 'runtime_commit=397b032cbf865e9c3ddfab89d533ec19325e1273' "${EVIDENCE}"

if FAKE_RUNNER_VERSION=2.338.0 run_check >/dev/null 2>&1; then
    printf 'Runtime verifier accepted an auto-updated runner that differs from golden provenance.\n' >&2
    exit 1
fi

write_provenance
printf 'tag=v2.337.0\n' >> "${PROVENANCE}"
if run_check >/dev/null 2>&1; then
    printf 'Runtime verifier accepted ambiguous duplicate runner tags.\n' >&2
    exit 1
fi

write_provenance
sed -i 's/^asset_sha256=.*/asset_sha256=invalid/' "${PROVENANCE}"
if run_check >/dev/null 2>&1; then
    printf 'Runtime verifier accepted an invalid verified runner asset hash.\n' >&2
    exit 1
fi

write_provenance
if FAKE_RUNNER_COMMIT=not-a-commit run_check >/dev/null 2>&1; then
    printf 'Runtime verifier accepted an invalid runtime runner commit.\n' >&2
    exit 1
fi

write_provenance
if FAKE_RUNNER_COMMIT=397b032abcd1234 run_check >/dev/null 2>&1; then
    printf 'Runtime verifier accepted a truncated runtime runner commit.\n' >&2
    exit 1
fi

rm -f "${RUNNER_DIR}/bin/Runner.Listener"
if run_check >/dev/null 2>&1; then
    printf 'Runtime verifier accepted a missing Runner.Listener executable.\n' >&2
    exit 1
fi

printf 'Actions runner runtime provenance functional test: PASS\n'
