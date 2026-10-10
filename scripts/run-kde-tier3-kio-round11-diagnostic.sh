#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-kio-round11-diagnostic.json"
: "${BREEZE_ARTIFACT_DIR:?BREEZE_ARTIFACT_DIR must point at the retained Breeze PASS artifact}"

WORK="${ROOT}/.work/kde-tier3-kio-round11-diagnostic"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round11-diagnostic"
RESULT="${EVIDENCE}/result.json"
DIAG_RESULT="DIAG_INFRA_FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK}" "${EVIDENCE}"
mkdir -p "${WORK}" "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/pipeline.log") 2>&1

write_result() {
    local rc=$? finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT}" "${DIAG_RESULT}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json,sys
from pathlib import Path
path,result,rc,stage,started,finished=sys.argv[1:]
Path(path).write_text(json.dumps({
  "node":"kio",
  "round":11,
  "diagnostic_result":result,
  "exit_code":int(rc),
  "stage":stage,
  "started_at":started,
  "finished_at":finished,
  "claim":"non-promoting-kio-test-environment-diagnostic",
  "package_attempted":False,
  "package_state_effect":"none",
  "dag_state_change":False,
  "downstream_eligibility_change":False
},indent=2,sort_keys=True)+"\n")
PY
}
trap write_result EXIT

STAGE="manifest-contract"
python3 - "${MANIFEST}" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
assert m["claim"]=="non-promoting-kio-test-environment-diagnostic"
assert m["non_promoting"] is True
assert m["package_attempted"] is False
assert m["package_state_effect"]=="none"
assert m["dag_state_changes_allowed"] is False
assert m["proposed_non_destructive_mechanism"]["package_revision"] is None
PY

STAGE="host-provider"
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ca-certificates cmake curl g++ qt6-base-dev qt6-qpa-plugins qt6-svg-dev qt6-svg-plugins \
  xauth xvfb xz-utils
{
  cat /etc/os-release
  cmake --version
  qmake6 -query QT_VERSION 2>/dev/null || true
  dpkg-query -W -f='${Package}\t${Version}\n' qt6-base-dev qt6-qpa-plugins qt6-svg-dev qt6-svg-plugins
} > "${EVIDENCE}/host-provider.txt"

STAGE="breeze-provider"
BREEZE_DEB="$(find "${BREEZE_ARTIFACT_DIR}" -type f -name 'breeze-icon-theme_6.30.0-0supralinux1_all.deb' -print -quit)"
[[ -n "${BREEZE_DEB}" && -s "${BREEZE_DEB}" ]]
printf '%s  %s\n' '308a20089ef387da2d5ba08b42be4299dd62fe5f5535786a0d8881d93b0d1e09' "${BREEZE_DEB}" | sha256sum --check --strict
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${BREEZE_DEB}"
[[ "$(dpkg-query -W -f='${Version}' breeze-icon-theme)" == '4:6.30.0-0supralinux1' ]]
for payload in \
  /usr/share/icons/breeze/index.theme \
  /usr/share/icons/breeze/mimetypes/22/unknown.svg \
  /usr/share/icons/breeze/mimetypes/16/inode-directory.svg \
  /usr/share/icons/breeze/places/16/folder-red.svg
do
  [[ -s "${payload}" ]]
  sha256sum "${payload}"
done > "${EVIDENCE}/breeze-payload-sha256.txt"

STAGE="cmake-environment-modification"
ENVPROBE="${WORK}/envprobe"
mkdir -p "${ENVPROBE}"
cat > "${ENVPROBE}/CMakeLists.txt" <<'EOF_CMAKE'
cmake_minimum_required(VERSION 3.22)
project(SupraLinuxRound11EnvironmentProbe NONE)
enable_testing()
add_test(NAME envprobe COMMAND "${CMAKE_COMMAND}" -E environment)
set_tests_properties(envprobe PROPERTIES
  ENVIRONMENT "QT_QPA_PLATFORM=offscreen;QT_PLUGIN_PATH=/probe/upstream-build-tree/bin")
set_property(TEST envprobe APPEND PROPERTY ENVIRONMENT_MODIFICATION
  "QT_QPA_PLATFORM=set:xcb"
  "QT_QPA_SYSTEM_ICON_THEME=set:breeze")
EOF_CMAKE
cmake -S "${ENVPROBE}" -B "${ENVPROBE}/build" |& tee "${EVIDENCE}/cmake-env-configure.log"
ctest --test-dir "${ENVPROBE}/build" -V |& tee "${EVIDENCE}/cmake-env-ctest.log"
grep -Fx '1: QT_QPA_PLATFORM=xcb' "${EVIDENCE}/cmake-env-ctest.log"
grep -Fx '1: QT_PLUGIN_PATH=/probe/upstream-build-tree/bin' "${EVIDENCE}/cmake-env-ctest.log"
grep -Fx '1: QT_QPA_SYSTEM_ICON_THEME=breeze' "${EVIDENCE}/cmake-env-ctest.log"

STAGE="qt-icon-probe-build"
ICONPROBE="${WORK}/iconprobe"
mkdir -p "${ICONPROBE}"
cat > "${ICONPROBE}/CMakeLists.txt" <<'EOF_CMAKE'
cmake_minimum_required(VERSION 3.22)
project(SupraLinuxRound11IconProbe LANGUAGES CXX)
find_package(Qt6 6.9 REQUIRED COMPONENTS Gui)
add_executable(iconprobe iconprobe.cpp)
target_link_libraries(iconprobe PRIVATE Qt6::Gui)
EOF_CMAKE
cat > "${ICONPROBE}/iconprobe.cpp" <<'EOF_CPP'
#include <QGuiApplication>
#include <QIcon>
#include <QTextStream>

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    const bool explicitTheme = app.arguments().contains(QStringLiteral("--explicit-theme"));
    if (explicitTheme) {
        QIcon::setThemeName(QStringLiteral("breeze"));
    }

    QTextStream out(stdout);
    out << "QT_VERSION=" << qVersion() << "\n";
    out << "THEME_NAME=" << QIcon::themeName() << "\n";
    const auto paths = QIcon::themeSearchPaths();
    for (const auto &path : paths) {
        out << "THEME_PATH=" << path << "\n";
    }
    const QStringList names{QStringLiteral("unknown"), QStringLiteral("inode-directory"), QStringLiteral("folder-red")};
    for (const auto &name : names) {
        const QIcon icon = QIcon::fromTheme(name);
        out << "ICON=" << name
            << " HAS=" << (QIcon::hasThemeIcon(name) ? "true" : "false")
            << " NULL=" << (icon.isNull() ? "true" : "false")
            << " NAME=" << icon.name() << "\n";
    }
    return 0;
}
EOF_CPP
cmake -S "${ICONPROBE}" -B "${ICONPROBE}/build" -DCMAKE_BUILD_TYPE=Release |& tee "${EVIDENCE}/icon-probe-configure.log"
cmake --build "${ICONPROBE}/build" --parallel 2 |& tee "${EVIDENCE}/icon-probe-build.log"

run_icon_probe() {
    local mode="$1"
    shift
    env QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze "$@" \
      xvfb-run -a -s '-screen 0 1280x1024x24' "${ICONPROBE}/build/iconprobe" \
      | tee "${EVIDENCE}/icon-${mode}.txt"
}

STAGE="qt-icon-probe-run"
run_icon_probe system-default-xdg
run_icon_probe system-explicit-xdg XDG_DATA_DIRS=/usr/local/share:/usr/share
env QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze XDG_DATA_DIRS=/usr/local/share:/usr/share \
  xvfb-run -a -s '-screen 0 1280x1024x24' "${ICONPROBE}/build/iconprobe" --explicit-theme \
  | tee "${EVIDENCE}/icon-explicit-theme.txt"

STAGE="krecentdocument-static-source"
KIO_TARBALL="${WORK}/kio-6.30.0.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 \
  --output "${KIO_TARBALL}" \
  https://download.kde.org/stable/frameworks/6.30/kio-6.30.0.tar.xz
printf '%s  %s\n' 'c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2' "${KIO_TARBALL}" | sha256sum --check --strict
mkdir -p "${WORK}/kio-source"
tar -xJf "${KIO_TARBALL}" --strip-components=1 -C "${WORK}/kio-source"
python3 - "${WORK}/kio-source" "${EVIDENCE}/krecentdocument-static.json" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
core=(root/"src/core/krecentdocument.cpp").read_text()
test=(root/"autotests/krecentdocumenttest.cpp").read_text()
checks={
  "millisecond_timestamp": 'currentDateTimeUtc().toString(Qt::ISODateWithMs)' in core,
  "timestamp_only_sort": 'documents.value(doc1) < documents.value(doc2)' in core,
  "tight_15_entry_loop": 'for (int i = 0; i < 15; ++i)' in test,
  "exact_last_three_order_assertion": 'QString::number(i + 12)' in test,
}
if not all(checks.values()):
    raise SystemExit(f"unexpected KIO 6.30 recent-document source shape: {checks}")
Path(sys.argv[2]).write_text(json.dumps({
  "source_version":"6.30.0",
  "source_sha256":"c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2",
  "checks":checks,
  "classification":"timestamp-tie-risk-present",
  "canonical_effect":"none",
  "test_suppression_authorized":False
},indent=2,sort_keys=True)+"\n")
PY

STAGE="finding-capture"
python3 - "${EVIDENCE}" <<'PY'
import json,re,sys
from pathlib import Path
ev=Path(sys.argv[1])
def parse(name):
    text=(ev/name).read_text()
    icons={}
    for line in text.splitlines():
        if line.startswith("ICON="):
            m=re.match(r"ICON=(\S+) HAS=(true|false) NULL=(true|false) NAME=(.*)",line)
            if m:
                icons[m.group(1)]={"has":m.group(2)=="true","null":m.group(3)=="true","name":m.group(4)}
    theme=next((x.split("=",1)[1] for x in text.splitlines() if x.startswith("THEME_NAME=")),"")
    paths=[x.split("=",1)[1] for x in text.splitlines() if x.startswith("THEME_PATH=")]
    return {"theme_name":theme,"theme_paths":paths,"icons":icons}
findings={
  "cmake_environment_modification":{
    "result":"PASS",
    "qt_qpa_platform":"xcb",
    "qt_qpa_system_icon_theme":"breeze",
    "qt_plugin_path_preserved":True
  },
  "icon_probes":{
    "system_default_xdg":parse("icon-system-default-xdg.txt"),
    "system_explicit_xdg":parse("icon-system-explicit-xdg.txt"),
    "explicit_theme":parse("icon-explicit-theme.txt")
  },
  "krecentdocument":json.loads((ev/"krecentdocument-static.json").read_text()),
  "claim":"diagnostic-only",
  "package_state_effect":"none"
}
(ev/"findings.json").write_text(json.dumps(findings,indent=2,sort_keys=True)+"\n")
PY

STAGE="complete"
DIAG_RESULT="DIAG_COMPLETE"
echo "KIO Round 11 diagnostic evidence capture: COMPLETE (non-promoting)"
