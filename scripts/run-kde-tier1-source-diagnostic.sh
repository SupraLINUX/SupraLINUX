#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier1-source-diagnostic.json"
NODE="${1:-}"
[[ -n "${NODE}" ]] || { echo "Usage: $0 <node>" >&2; exit 2; }
: "${ECM_ARTIFACT_DIR:?ECM_ARTIFACT_DIR must point at the retained ECM PASS artifact}"

eval "$(python3 - "${MANIFEST}" "${NODE}" <<'PY'
import json, shlex, sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
node=m.get("nodes",{}).get(sys.argv[2])
if not isinstance(node,dict): raise SystemExit(f"unknown diagnostic node: {sys.argv[2]}")
ecm=m["ecm_predecessor"]
test_env=node.get("test_environment",{})
lang=test_env.get("LANG","C.UTF-8")
lc_all=test_env.get("LC_ALL","C.UTF-8")
for k,v in {
    "SOURCE_URL":node["source_url"],
    "SOURCE_SHA256":node["source_sha256"],
    "ECM_VERSION":ecm["version"],
    "ECM_SHA256":ecm["deb_sha256"],
    "TEST_LANG":lang,
    "TEST_LC_ALL":"" if lc_all is None else lc_all,
}.items():
    print(f"{k}={shlex.quote(str(v))}")
print(f"TEST_LC_ALL_UNSET={'1' if lc_all is None else '0'}")
print("COMMON_PACKAGES=("+" ".join(shlex.quote(x) for x in m["common_build_packages"])+")")
print("NODE_PACKAGES=("+" ".join(shlex.quote(x) for x in node["provider_packages"])+")")
print("PROVIDER_ASSERTIONS=("+" ".join(shlex.quote(x) for x in node.get("provider_assertions",[]))+")")
print("REQUIRED_LOCALES=("+" ".join(shlex.quote(x) for x in node.get("required_locales",[]))+")")
PY
)"

WORK_DIR="${ROOT}/.work/kde-tier1-source-diagnostic/${NODE}"
SOURCE_DIR="${WORK_DIR}/source"
BUILD_DIR="${WORK_DIR}/build"
INSTALL_ROOT="${WORK_DIR}/install-root"
EVIDENCE_DIR="${ROOT}/evidence/kde-tier1-source-diagnostic/${NODE}"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
DIAG_RESULT="DIAG_FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${WORK_DIR}" "${EVIDENCE_DIR}"

write_result() {
    local rc=$? finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT_JSON}" "${NODE}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json,sys
from pathlib import Path
p,node,result,rc,stage,started,finished=sys.argv[1:]
Path(p).write_text(json.dumps({
    "node":node,"diagnostic_result":result,"exit_code":int(rc),"stage":stage,
    "started_at":started,"finished_at":finished,
    "claim":"non-promoting-source-diagnostic","authoritative":False,
    "package_gate":False,"dag_state_change":False,"downstream_eligible_claimed":False,
    "runner_class":"github-hosted-ubuntu-26.04"
},indent=2)+"\n")
PY
}
trap write_result EXIT
exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "=== SupraLINUX KDE Tier 1 source diagnostic: ${NODE} ==="

STAGE="manifest-validation"
python3 - "${MANIFEST}" "${NODE}" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text()); node=sys.argv[2]
if m.get("claim")!="non-promoting-source-diagnostic" or m.get("non_promoting") is not True: raise SystemExit("diagnostic manifest lost non-promoting contract")
if m.get("dag_state_changes_allowed") is not False: raise SystemExit("diagnostic must not change DAG state")
if node not in m.get("nodes",{}): raise SystemExit(f"unknown node {node}")
PY

STAGE="host-validation"
. /etc/os-release
[[ "${ID}" == "ubuntu" && "${VERSION_ID}" == "26.04" ]] || { echo "Expected Ubuntu 26.04, got ${PRETTY_NAME}" >&2; exit 1; }
{ cat /etc/os-release; uname -a; cmake --version 2>/dev/null || true; python3 --version; } > "${EVIDENCE_DIR}/host.txt"

STAGE="provider-install"
sudo apt-get update
mapfile -t PACKAGES < <(printf '%s\n' "${COMMON_PACKAGES[@]}" "${NODE_PACKAGES[@]}" | awk 'NF' | sort -u)
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${PACKAGES[@]}" |& tee "${EVIDENCE_DIR}/apt-install.log"
printf '%s\n' "${PACKAGES[@]}" > "${EVIDENCE_DIR}/requested-provider-packages.txt"
dpkg-query -W -f='${Package}\t${Version}\n' "${PACKAGES[@]}" 2>/dev/null | sort > "${EVIDENCE_DIR}/installed-provider-packages.txt"

STAGE="provider-surface-validation"
for assertion in "${PROVIDER_ASSERTIONS[@]}"; do
    case "${assertion}" in
        qt-core-private-versioned-includes)
            compgen -G '/usr/include/*/qt6/QtCore/*/QtCore/private' >/dev/null || { echo "qt6-base-private-dev installed but versioned QtCore private include surface is absent" >&2; exit 1; }
            ;;
        iso-3166-french-catalogs)
            ISO1="$(find /usr/share/locale /usr/share/locale-langpack -type f -path '*/fr/LC_MESSAGES/iso_3166-1.mo' -print -quit 2>/dev/null || true)"
            ISO2="$(find /usr/share/locale /usr/share/locale-langpack -type f -path '*/fr/LC_MESSAGES/iso_3166-2.mo' -print -quit 2>/dev/null || true)"
            [[ -n "${ISO1}" && -s "${ISO1}" && -n "${ISO2}" && -s "${ISO2}" ]] || { echo "French iso-codes catalogs are absent after provider installation" >&2; exit 1; }
            printf '%s\n%s\n' "${ISO1}" "${ISO2}" > "${EVIDENCE_DIR}/iso-codes-french-catalogs.txt"
            ;;
        *) echo "Unknown provider assertion: ${assertion}" >&2; exit 2 ;;
    esac
done

locale_exists() {
    local wanted="${1,,}" have
    wanted="${wanted/utf-8/utf8}"
    while IFS= read -r have; do
        have="${have,,}"
        have="${have/utf-8/utf8}"
        [[ "${have}" == "${wanted}" ]] && return 0
    done < <(locale -a)
    return 1
}
if ((${#REQUIRED_LOCALES[@]})); then
    : > "${EVIDENCE_DIR}/required-locales.txt"
    for required_locale in "${REQUIRED_LOCALES[@]}"; do
        locale_exists "${required_locale}" || { echo "Required locale is unavailable: ${required_locale}" >&2; locale -a >&2; exit 1; }
        printf '%s\n' "${required_locale}" >> "${EVIDENCE_DIR}/required-locales.txt"
    done
fi

ECM_DEB="$(find "${ECM_ARTIFACT_DIR}" -maxdepth 2 -type f -name "extra-cmake-modules_${ECM_VERSION}_all.deb" -print -quit)"
[[ -n "${ECM_DEB}" && -s "${ECM_DEB}" ]] || { echo "Retained ECM PASS .deb missing" >&2; exit 1; }
printf '%s  %s\n' "${ECM_SHA256}" "${ECM_DEB}" | sha256sum --check --strict
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${ECM_DEB}" |& tee "${EVIDENCE_DIR}/ecm-install.log"
[[ "$(dpkg-query -W -f='${Version}' extra-cmake-modules)" == "${ECM_VERSION}" ]]
sha256sum "${ECM_DEB}" > "${EVIDENCE_DIR}/ecm-predecessor-sha256.txt"

STAGE="upstream-source"
TARBALL="${WORK_DIR}/${NODE}-6.30.0.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 --output "${TARBALL}" "${SOURCE_URL}"
printf '%s  %s\n' "${SOURCE_SHA256}" "${TARBALL}" | sha256sum --check --strict
sha256sum "${TARBALL}" > "${EVIDENCE_DIR}/source-sha256.txt"
mkdir -p "${SOURCE_DIR}"
tar -xJf "${TARBALL}" --strip-components=1 -C "${SOURCE_DIR}"

STAGE="configure"
cmake -S "${SOURCE_DIR}" -B "${BUILD_DIR}" -GNinja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_INSTALL_PREFIX=/usr -DBUILD_TESTING=ON |& tee "${EVIDENCE_DIR}/configure.log"
cp "${BUILD_DIR}/CMakeCache.txt" "${EVIDENCE_DIR}/CMakeCache.txt"

STAGE="upstream-default-validation"
python3 - "${MANIFEST}" "${NODE}" "${BUILD_DIR}/CMakeCache.txt" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text()); node=sys.argv[2]
cache={}
for line in Path(sys.argv[3]).read_text(errors="replace").splitlines():
    if not line or line.startswith(('#','//')) or '=' not in line or ':' not in line.split('=',1)[0]: continue
    left,value=line.split('=',1); cache[left.split(':',1)[0]]=value
for key,expected in m['nodes'][node].get('cmake_defaults',{}).items():
    got=cache.get(key)
    if got != expected: raise SystemExit(f"{node}: upstream default {key}={got!r}, expected {expected!r}")
print(f"{node}: upstream default assertions PASS")
PY

STAGE="build"
cmake --build "${BUILD_DIR}" --parallel 2 |& tee "${EVIDENCE_DIR}/build.log"

STAGE="tests"
TEST_WRAPPER="${WORK_DIR}/run-tests-under-x.sh"
cat > "${TEST_WRAPPER}" <<'EOF2'
#!/usr/bin/env bash
set -Eeuo pipefail
: "${BUILD_DIR:?}"; : "${EVIDENCE_DIR:?}"; : "${TEST_LANG:?}"; : "${TEST_LC_ALL_UNSET:?}"
openbox >"${EVIDENCE_DIR}/openbox.log" 2>&1 &
wm_pid=$!
cleanup() { kill "${wm_pid}" 2>/dev/null || true; wait "${wm_pid}" 2>/dev/null || true; }
trap cleanup EXIT
ready=false
for _ in $(seq 1 100); do
    if xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -Eq 'window id # 0x[0-9a-fA-F]+'; then ready=true; break; fi
    sleep 0.1
done
[[ "${ready}" == true ]] || { echo "Openbox did not publish a real EWMH supporting-WM window" >&2; exit 1; }
export QT_QPA_PLATFORM=xcb
export LANG="${TEST_LANG}"
if [[ "${TEST_LC_ALL_UNSET}" == 1 ]]; then unset LC_ALL; else export LC_ALL="${TEST_LC_ALL}"; fi
{
    printf 'LANG=%s\n' "${LANG}"
    if [[ -v LC_ALL ]]; then printf 'LC_ALL=%s\n' "${LC_ALL}"; else printf 'LC_ALL=<unset>\n'; fi
    printf 'LANGUAGE=%s\n' "${LANGUAGE-<unset>}"
    locale
} > "${EVIDENCE_DIR}/test-environment.txt"
ctest --test-dir "${BUILD_DIR}" --output-on-failure -j1 |& tee "${EVIDENCE_DIR}/tests.log"
EOF2
chmod +x "${TEST_WRAPPER}"
export BUILD_DIR EVIDENCE_DIR TEST_LANG TEST_LC_ALL TEST_LC_ALL_UNSET
dbus-run-session -- xvfb-run -a -s '-screen 0 1920x1080x24' "${TEST_WRAPPER}"

STAGE="install-staging"
mkdir -p "${INSTALL_ROOT}"
DESTDIR="${INSTALL_ROOT}" cmake --install "${BUILD_DIR}" |& tee "${EVIDENCE_DIR}/install.log"
find "${INSTALL_ROOT}" -type f -o -type l | sed "s#^${INSTALL_ROOT}##" | sort > "${EVIDENCE_DIR}/installed-files.txt"
test -s "${EVIDENCE_DIR}/installed-files.txt"

STAGE="complete"
DIAG_RESULT="DIAG_PASS"
printf '%s\n' "node=${NODE}" "diagnostic_result=DIAG_PASS" "claim=non-promoting-source-diagnostic" "package_gate=false" "dag_state_change=false" "source_sha256=${SOURCE_SHA256}" "ecm_version=${ECM_VERSION}" > "${EVIDENCE_DIR}/summary.txt"
echo "KDE Tier 1 source diagnostic ${NODE}: DIAG_PASS (non-promoting)"
