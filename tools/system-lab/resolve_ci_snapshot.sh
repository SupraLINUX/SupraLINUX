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
docker run --rm --platform linux/amd64 --security-opt no-new-privileges \
  --mount "type=bind,source=$PWD/tools/system-lab/resolve_snapshot.sh,target=/resolve.sh,readonly" \
  --mount "type=bind,source=$PWD/evidence,target=/out" \
  "${config[0]}" bash /resolve.sh "${config[1]}" "${config[@]:2}"
python3 tools/system-lab/snapshot_lock.py distribution/images/experimental-base.json evidence
