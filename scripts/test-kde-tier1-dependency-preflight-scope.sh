#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/scripts" "$TMP/manifests" "$TMP/docs" "$TMP/.github/workflows"
cp "$ROOT/scripts/kde-tier1-dependency-preflight-needed.sh" "$TMP/scripts/"
cp "$ROOT/scripts/kde-tier1-dependency-contract-fingerprint.py" "$TMP/scripts/"
cp "$ROOT/manifests/kde-frameworks-tier1-dependencies.json" "$TMP/manifests/"
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/scripts/run-kde-tier1-dependency-preflight.sh"
printf 'name: test\n' > "$TMP/.github/workflows/kde-tier1-dependency-preflight.yml"
printf 'baseline\n' > "$TMP/docs/kde-tier1-dependencies.md"
chmod +x "$TMP/scripts/"*.sh "$TMP/scripts/"*.py

git -C "$TMP" init -q
git -C "$TMP" config user.name 'SupraLINUX scope test'
git -C "$TMP" config user.email 'scope-test@supralinux.invalid'
git -C "$TMP" add .
git -C "$TMP" commit -q -m base
BASE="$(git -C "$TMP" rev-parse HEAD)"

expect_rc() {
    local expected="$1" before="$2" after="$3" label="$4" rc
    set +e
    "$TMP/scripts/kde-tier1-dependency-preflight-needed.sh" "$before" "$after" >"$TMP/$label.log" 2>&1
    rc=$?
    set -e
    if [[ "$rc" -ne "$expected" ]]; then
        cat "$TMP/$label.log" >&2
        printf '%s: expected rc=%s, got rc=%s\n' "$label" "$expected" "$rc" >&2
        exit 1
    fi
    printf '%s: PASS (rc=%s)\n' "$label" "$rc"
}

python3 - "$TMP/manifests/kde-frameworks-tier1-dependencies.json" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1]); d=json.loads(p.read_text())
d['provider_candidate']['status']='hosted-preflight-pass'
d['provider_candidate']['evidence']={'workflow_run':123,'artifact_id':456}
p.write_text(json.dumps(d,separators=(',',':'))+'\n')
PY
git -C "$TMP" add manifests/kde-frameworks-tier1-dependencies.json
git -C "$TMP" commit -q -m evidence-only
EVIDENCE="$(git -C "$TMP" rev-parse HEAD)"
expect_rc 1 "$BASE" "$EVIDENCE" evidence_only

python3 - "$TMP/manifests/kde-frameworks-tier1-dependencies.json" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1]); d=json.loads(p.read_text())
d['requirements']['python-build']['packages']=['python3-build','synthetic-provider-change']
p.write_text(json.dumps(d,separators=(',',':'))+'\n')
PY
git -C "$TMP" add manifests/kde-frameworks-tier1-dependencies.json
git -C "$TMP" commit -q -m contract-change
CONTRACT="$(git -C "$TMP" rev-parse HEAD)"
expect_rc 0 "$EVIDENCE" "$CONTRACT" contract_change

printf 'documentation only\n' >> "$TMP/docs/kde-tier1-dependencies.md"
git -C "$TMP" add docs/kde-tier1-dependencies.md
git -C "$TMP" commit -q -m docs-only
DOCS="$(git -C "$TMP" rev-parse HEAD)"
expect_rc 1 "$CONTRACT" "$DOCS" docs_only

printf '# execution input changed\n' >> "$TMP/scripts/run-kde-tier1-dependency-preflight.sh"
git -C "$TMP" add scripts/run-kde-tier1-dependency-preflight.sh
git -C "$TMP" commit -q -m runner-change
RUNNER="$(git -C "$TMP" rev-parse HEAD)"
expect_rc 0 "$DOCS" "$RUNNER" runner_change

printf 'KDE Tier 1 dependency preflight semantic-scope tests: PASS\n'
