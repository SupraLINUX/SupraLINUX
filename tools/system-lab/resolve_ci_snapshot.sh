#!/usr/bin/env bash
# Resolve a frozen Arch closure in a new disposable builder.
set -euo pipefail
mkdir -p evidence
python3 - <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools/system-lab')
from snapshot_lock import validate_config
cfg = validate_config(json.loads(Path('distribution/images/experimental-base.json').read_text()))
Path('evidence/build-input.txt').write_text('\n'.join([cfg['builder'],cfg['snapshot'],*cfg['packages']])+'\n')
PY
mapfile -t config < evidence/build-input.txt
docker pull --platform linux/amd64 "${config[0]}"
docker image inspect "${config[0]}" --format '{{.Id}} {{json .RepoDigests}}' > evidence/builder.txt
# Each retry has a fresh builder and evidence directory. Retry only observed
# transport errors; a metadata/closure validation failure is not retried.
attempt_dir=$(mktemp -d "$PWD/evidence/.resolve.XXXXXX")
container=
cleanup() {
    if [[ -n "$container" ]]; then docker rm -f "$container" >/dev/null 2>&1 || true; fi
    rm -rf -- "$attempt_dir"
}
trap cleanup EXIT
for attempt in 1 2 3 4; do
    mkdir "$attempt_dir/$attempt"
    log="evidence/resolver-attempt-$attempt.log"
    status=0
    container="supra-resolve-$-$attempt"
    timeout --kill-after=10 240 docker run --name "$container" --rm --platform linux/amd64 --security-opt no-new-privileges \
      --mount "type=bind,source=$PWD/tools/system-lab/resolve_snapshot.sh,target=/resolve.sh,readonly" \
      --mount "type=bind,source=$attempt_dir/$attempt,target=/out" \
      "${config[0]}" bash /resolve.sh "${config[1]}" "${config[@]:2}" 2>&1 | tee "$log" || status=$?
    if docker container inspect "$container" >/dev/null 2>&1; then
        docker rm -f "$container" >/dev/null
    fi
    container=
    if (( status == 0 )); then
        for file in pacman-version.txt transaction.txt core.db extra.db; do
            test -s "$attempt_dir/$attempt/$file"
            cp "$attempt_dir/$attempt/$file" "evidence/$file"
        done
        break
    fi
    if (( attempt == 4 )); then exit "$status"; fi
    if (( status != 124 )) && ! grep -Eqi 'connection timed out|operation timed out|operation too slow|could not resolve host|failed to connect|connection reset|HTTP.*(502|503|504)|requested URL returned error: (502|503|504)' "$log"; then
        exit "$status"
    fi
    sleep "$((attempt * 15))"
done
python3 tools/system-lab/snapshot_lock.py distribution/images/experimental-base.json evidence
