#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$#" -eq 3 ]] || { echo "Usage: $0 <before-sha> <after-sha> <node>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"; NODE="$3"
case "${NODE}" in
  kconfig|ki18n|sonnet|kirigami|kquickcharts|kuserfeedback|prison) ;;
  *) echo "Unsupported diagnostic node: ${NODE}" >&2; exit 2 ;;
esac
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    manifests/kde-frameworks-tier1-dependencies.json|\
    scripts/run-kde-tier1-source-diagnostic.sh|\
    scripts/kde-tier1-source-diagnostic-needed.sh|\
    .github/workflows/kde-tier1-source-diagnostic.yml)
      exit 0 ;;
  esac
done

MANIFEST="manifests/kde-tier1-source-diagnostic.json"
if printf '%s\n' "${changed[@]}" | grep -Fxq "${MANIFEST}"; then
  git cat-file -e "${BEFORE}:${MANIFEST}" 2>/dev/null || exit 0
  if ! python3 - "${BEFORE}" "${AFTER}" "${NODE}" <<'PY'
import json, subprocess, sys
before, after, node = sys.argv[1:]
path = "manifests/kde-tier1-source-diagnostic.json"
def load(ref):
    return json.loads(subprocess.check_output(["git","show",f"{ref}:{path}"], text=True))
def common(data):
    return {k:v for k,v in data.items() if k not in {"nodes","last_campaign"}}
b=load(before); a=load(after)
if common(b) != common(a):
    raise SystemExit(1)
if b.get("nodes",{}).get(node) != a.get("nodes",{}).get(node):
    raise SystemExit(1)
raise SystemExit(0)
PY
  then
    exit 0
  fi
fi

# Evidence-only last_campaign updates and documentation do not alter a node's
# diagnostic execution contract.
exit 1
