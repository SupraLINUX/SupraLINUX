#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"
AFTER="$2"

for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

manifest_fingerprint() {
  git -C "${ROOT}" show "$1:manifests/kde-tier2-kmime-legacy-provider.json" 2>/dev/null |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
build_input={k:d.get(k) for k in ("source_reference","supralinux_package","adaptation")}
print(hashlib.sha256(json.dumps(build_input,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

workflow_build_fingerprint() {
  git -C "${ROOT}" show "$1:.github/workflows/kde-tier2-kmime-legacy-provider.yml" 2>/dev/null |
    python3 -c 'import hashlib,re,sys
lines=sys.stdin.read().splitlines()
wanted={"materialize","rootfs","build"}
current=None
out=[]
for line in lines:
    m=re.match(r"^  ([A-Za-z0-9_-]+):\s*$",line)
    if m:
        current=m.group(1) if m.group(1) in wanted else None
    if current:
        stripped=line.strip()
        if stripped.startswith("needs:"):
            continue
        if stripped=="if: needs.plan.outputs.run == '"'"'true'"'"'":
            continue
        out.append(line)
print(hashlib.sha256(("\n".join(out)+"\n").encode()).hexdigest())'
}

for path in \
  manifests/kde-tier2-kmime-legacy-provider.json \
  .github/workflows/kde-tier2-kmime-legacy-provider.yml
do
  git -C "${ROOT}" cat-file -e "${BEFORE}:${path}" 2>/dev/null || {
    echo "${path}: provider build input is new."
    exit 0
  }
done

if [[ "$(manifest_fingerprint "${BEFORE}")" != "$(manifest_fingerprint "${AFTER}")" ]]; then
  echo "KMime legacy-provider semantic manifest input changed."
  exit 0
fi

if [[ "$(workflow_build_fingerprint "${BEFORE}")" != "$(workflow_build_fingerprint "${AFTER}")" ]]; then
  echo "KMime legacy-provider build workflow semantics changed."
  exit 0
fi

mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/materialize-kde-tier2-kmime-legacy-provider.sh|scripts/run-kde-tier2-kmime-legacy-provider-build.sh)
      echo "${path}: provider package-consumed implementation changed."
      exit 0
      ;;
  esac
done

echo "No KMime legacy-provider package-consumed semantic input changed."
exit 1
