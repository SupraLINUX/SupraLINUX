#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

campaign_fingerprint() {
  git -C "${ROOT}" show "$1:manifests/kde-tier2-package-campaign-batch3.json" |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
for key in ("state","canonical_snapshot"):
    d.pop(key,None)
for n in d.get("nodes",{}).values():
    for key in ("state","last_result","downstream_eligible","pass_evidence","last_failure_evidence"):
        n.pop(key,None)
print(hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

has_runnable() {
  git -C "${ROOT}" show "$1:manifests/kde-tier2-package-campaign-batch3.json" |
    python3 -c 'import json,sys
d=json.load(sys.stdin)
r={"prepared-pending-build","remediation-pending-build"}
raise SystemExit(0 if any(n.get("state") in r for n in d.get("nodes",{}).values()) else 1)'
}

mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    docs/*|scripts/validate_*.py|scripts/test-*.sh|manifests/kde-tier2-package-batch3-attempts.json)
      continue ;;
    manifests/kde-tier2-package-campaign-batch3.json)
      if ! git -C "${ROOT}" cat-file -e "${BEFORE}:${path}" 2>/dev/null; then
        echo "Tier 2 Batch 3 campaign is new."; exit 0
      fi
      if [[ "$(campaign_fingerprint "${BEFORE}")" != "$(campaign_fingerprint "${AFTER}")" ]]; then
        echo "Tier 2 Batch 3 semantic campaign input changed."; exit 0
      fi
      ;;
    scripts/run-kde-tier2-package-batch3.sh|scripts/plan-kde-tier2-package-batch3.py|scripts/validate-kde-tier2-batch3-retained-inputs.py|scripts/kde-tier2-package-batch3-needed.sh|.github/workflows/kde-tier2-package-batch3.yml)
      if has_runnable "${AFTER}"; then
        echo "${path}: Batch 3 implementation changed with runnable nodes."; exit 0
      fi
      ;;
    manifests/kde-tier2-package-contracts.json|manifests/kde-frameworks-tier2.json|manifests/kde-frameworks-tier2-dependencies.json|manifests/kde-frameworks-tier1.json|manifests/kde-dag.json)
      if has_runnable "${AFTER}"; then
        echo "${path}: Batch 3 consumed canonical input changed."; exit 0
      fi
      ;;
  esac
done
echo "No runnable Tier 2 Batch 3 semantic input changed."
exit 1
