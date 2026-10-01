#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SUPRALINUX_JIT_STARTUP_PREFLIGHT=1
exec "${ROOT}/scripts/run-kvm-jit-gate.sh" runner-contract
