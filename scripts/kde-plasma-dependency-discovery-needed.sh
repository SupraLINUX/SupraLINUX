#!/usr/bin/env bash
set -Eeuo pipefail

[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"
AFTER="$2"

for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

if ! git cat-file -e "${AFTER}:manifests/kde-plasma.json" 2>/dev/null; then
  exit 1
fi

authorized="$(git show "${AFTER}:manifests/kde-plasma.json" | python3 -c 'import json,sys; p=json.load(sys.stdin)["planning"]; print("true" if p.get("status")=="dependency-discovery-pending" and p.get("execution_authorized") is True and p.get("package_execution_authorized") is False else "false")')"
[[ "${authorized}" == "true" ]] || exit 1

mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    manifests/kde-plasma.json|manifests/kde-plasma-dependencies.json|scripts/run-kde-plasma-dependency-discovery.py|scripts/kde-plasma-dependency-discovery-needed.sh|scripts/validate_kde_plasma.py|.github/workflows/kde-plasma-dependency-discovery.yml)
      exit 0
      ;;
  esac
done

exit 1
