#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GOLDEN_IMAGE="${SUPRALINUX_GOLDEN_IMAGE:-/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2}"

"${ROOT}/scripts/check-golden-image-provenance.sh" "${GOLDEN_IMAGE}"
exec "${ROOT}/scripts/run-kvm-jit-gate-core.sh" "$@"
