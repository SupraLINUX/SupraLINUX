#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 1 ]]; then
    echo "Usage: $0 <canonical-checkout>" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${SCRIPT_DIR}/promote-batch7-canonical.py"
TMP="$(mktemp)"
trap 'rm -f "${TMP}"' EXIT
cp "${SOURCE}" "${TMP}"

python3 - "${TMP}" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old = 'Batch 6 closure is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**'
new = 'Canonical Tier 1 at the Batch 6 closure is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**'
if s.count(old) != 1:
    raise SystemExit(f"expected exactly one historical-guard typo, found {s.count(old)}")
p.write_text(s.replace(old, new, 1))
PY

python3 "${TMP}" "$1"
