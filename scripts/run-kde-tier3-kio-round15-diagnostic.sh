#!/usr/bin/env bash
# shellcheck disable=SC1090,SC2034
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-kio-round15-diagnostic.json"
WORK="${ROOT}/.work/kde-tier3-kio-round15-diagnostic"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round15-diagnostic"
RESULT="${EVIDENCE}/result.json"
DIAG_RESULT=DIAG_INFRA_FAIL
STAGE=initialization
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"
rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

finish() {
  local rc="$1" finished_at
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 - "${RESULT}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json,sys
from pathlib import Path
p,result,rc,stage,started,finished=sys.argv[1:]
Path(p).write_text(json.dumps({
  "schema":1,"node":"kio","round":15,"diagnostic_result":result,
  "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
  "claim":"non-promoting-breeze-icons-init-state-diagnostic",
  "package_attempted":False,"package_state_effect":"none"
},indent=2,sort_keys=True)+"\n")
PY
}
trap 'finish "$?"' EXIT

download_artifact() {
  local id="$1" sha="$2" dest="$3"
  mkdir -p "${dest}"
  local zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${id}/zip" \
    -o "${zip}"
  printf '%s  %s\n' "${sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}

STAGE=contract
python3 scripts/validate_kde_tier3_kio_round15_diagnostic.py

STAGE=host-tools
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ca-certificates cmake curl g++ qt6-base-dev qt6-qpa-plugins qt6-svg-dev qt6-svg-plugins xauth xvfb unzip xz-utils

STAGE=round13-linkage-proof
download_artifact "10869413386" "f96d4fdfebc5fcebe63633650ebf3998a51e37e5c84c12b50bc3d745097d7cd7" "${WORK}/round13"
for trace in trace-kdirmodeltest.strace trace-knewfilemenutest.strace; do
  file="${WORK}/round13/${trace}"
  [[ -s "${file}" ]]
  grep -F '/usr/lib/x86_64-linux-gnu/libKF6IconThemes.so.6' "${file}" >/dev/null
  grep -F '/usr/lib/x86_64-linux-gnu/libKF6BreezeIcons.so.6' "${file}" >/dev/null
done
python3 - "${EVIDENCE}/round13-linkage.json" <<'PY'
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({
  "workflow_run":36146880757,"job_id":108110145068,"artifact_id":10869413386,
  "artifact_sha256":"f96d4fdfebc5fcebe63633650ebf3998a51e37e5c84c12b50bc3d745097d7cd7",
  "kdirmodel_loads_kiconthemes":True,"kdirmodel_loads_breezeicons":True,
  "knewfilemenu_loads_kiconthemes":True,"knewfilemenu_loads_breezeicons":True
},indent=2,sort_keys=True)+"\n")
PY


source "${ROOT}/scripts/run-kde-tier3-kio-round15-providers.sh"
