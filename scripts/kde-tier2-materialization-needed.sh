#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

contract_fingerprint() {
  git -C "${ROOT}" show "$1:manifests/kde-tier2-package-contracts.json" |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
d.pop("state",None)
d.pop("reference_evidence",None)
m=d.get("materialization",{})
m.pop("status",None)
m.pop("evidence",None)
print(hashlib.sha256(json.dumps(d,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    manifests/kde-tier2-package-contracts.json)
      if ! git -C "${ROOT}" cat-file -e "${BEFORE}:${path}" 2>/dev/null; then
        echo "Tier 2 contract manifest is new."; exit 0
      fi
      if [[ "$(contract_fingerprint "${BEFORE}")" != "$(contract_fingerprint "${AFTER}")" ]]; then
        echo "Tier 2 materialization inputs changed."; exit 0
      fi
      ;;
    scripts/materialize_kde_tier2_package.py|scripts/run-kde-tier2-package-materialization.sh|scripts/kde-tier2-materialization-needed.sh|.github/workflows/kde-tier2-package-materialization.yml)
      echo "${path}: materializer implementation changed."; exit 0 ;;
  esac
done
echo "No Tier 2 package-materialization input changed."
exit 1
