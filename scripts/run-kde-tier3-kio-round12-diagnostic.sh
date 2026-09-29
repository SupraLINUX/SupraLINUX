#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-tier3-kio-round12-diagnostic.json"
: "${GITHUB_TOKEN:?missing GitHub Actions token}"

WORK="${ROOT}/.work/kde-tier3-kio-round12-diagnostic"
EVIDENCE="${ROOT}/evidence/kde-tier3-kio-round12-diagnostic"
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
  "schema":1,"node":"kio","round":12,"diagnostic_result":result,
  "exit_code":int(rc),"stage":stage,"started_at":started,"finished_at":finished,
  "claim":"non-promoting-kio-icon-resolution-diagnostic",
  "package_attempted":False,"package_state_effect":"none",
  "dag_state_change":False,"downstream_eligibility_change":False
},indent=2,sort_keys=True)+"\n")
PY
}
trap write_result EXIT

download_artifact() {
  local artifact_id="$1" expected_sha="$2" dest="$3"
  mkdir -p "${dest}"
  local zip="${dest}.zip"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/${artifact_id}/zip" \
    -o "${zip}"
  printf '%s  %s\n' "${expected_sha}" "${zip}" | sha256sum --check --strict
  unzip -q "${zip}" -d "${dest}"
}

STAGE="manifest-contract"
python3 - "${MANIFEST}" <<'PY'
import json,sys
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
assert m["round"]==12
assert m["claim"]=="non-promoting-kio-icon-resolution-diagnostic"
assert m["non_promoting"] is True
assert m["package_attempted"] is False
assert m["package_state_effect"]=="none"
assert m["execution_authorized"] is False
assert m["status"]=="definition-pending-diagnostic"
PY

STAGE="host-provider"
. /etc/os-release
[[ "${ID}" == ubuntu && "${VERSION_ID}" == 26.04 ]]
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  ca-certificates cmake curl g++ qt6-base-dev qt6-qpa-plugins qt6-svg-dev qt6-svg-plugins \
  xauth xvfb unzip xz-utils
{
  cat /etc/os-release
  cmake --version
  qmake6 -query QT_VERSION 2>/dev/null || true
  dpkg-query -W -f='${Package}\t${Version}\n' qt6-base-dev qt6-qpa-plugins qt6-svg-dev qt6-svg-plugins
} > "${EVIDENCE}/host-provider.txt"

STAGE="attempt7-evidence"
download_artifact "10840963289" "32b10c0ac337040239edea709440c5b09b898d76da1ac3c8e10339bf1477d239" "${WORK}/attempt7-kio"
SBUILD_LOG="$(find "${WORK}/attempt7-kio" -type f -name sbuild.log -print -quit)"
[[ -n "${SBUILD_LOG}" && -s "${SBUILD_LOG}" ]]
python3 - "${SBUILD_LOG}" "${EVIDENCE}/attempt7-log-findings.json" <<'PY'
import json,re,sys
from pathlib import Path
text=Path(sys.argv[1]).read_text(errors="replace")
required=[
 "67% tests passed" if False else "97% tests passed, 2 tests failed out of 69",
 "50:  QT_QPA_PLATFORM=offscreen",
 "50:  QT_PLUGIN_PATH=/build/reproducible-path/kf6-kio-6.30.0/obj-x86_64-linux-gnu/bin",
 "50:  QT_QPA_PLATFORM=set:xcb",
 "50:  QT_QPA_SYSTEM_ICON_THEME=set:breeze",
 "64:  QT_QPA_PLATFORM=offscreen",
 "64:  QT_PLUGIN_PATH=/build/reproducible-path/kf6-kio-6.30.0/obj-x86_64-linux-gnu/bin",
 "64:  QT_QPA_PLATFORM=set:xcb",
 "64:  QT_QPA_SYSTEM_ICON_THEME=set:breeze",
 "breeze-icon-theme_4:6.30.0-0supralinux1",
 'Actual   (icon2.name()): ""',
 'Expected ("unknown")   : unknown',
 'Actual   (iconLabel->property("iconName").toString()): ""',
 'Expected (defaultFolderIconName)                     : "inode-directory"',
]
missing=[x for x in required if x not in text]
if missing:
    raise SystemExit("Attempt7 evidence tokens missing: "+repr(missing))
fails=re.findall(r"\t \d+ - ([^ ]+) \(Failed\)",text)
if set(fails)!={"kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"}:
    raise SystemExit(f"unexpected Attempt7 failed set: {fails}")
Path(sys.argv[2]).write_text(json.dumps({
 "workflow_run":36079116873,
 "job_id":107897110171,
 "artifact_id":10840963289,
 "tests":{"total":69,"pass":67,"fail":2},
 "failed_tests":sorted(fails),
 "ctest_environment_preserved":True,
 "breeze_installed":True,
 "kdirmodel_first_icon_name":{"actual":"","expected":"unknown"},
 "knewfilemenu_default_icon_name":{"actual":"","expected":"inode-directory"},
 "krecentdocument_failed":False,
 "package_state_effect":"none"
},indent=2,sort_keys=True)+"\n")
PY

STAGE="breeze-provider"
download_artifact "10682012012" "daaa5abda5a8f824c6fa509142d7cd9132de213d782cb32e0561873f427aa577" "${WORK}/breeze"
BREEZE_DEB="$(find "${WORK}/breeze" -type f -name 'breeze-icon-theme_6.30.0-0supralinux1_all.deb' -print -quit)"
[[ -n "${BREEZE_DEB}" && -s "${BREEZE_DEB}" ]]
printf '%s  %s\n' '308a20089ef387da2d5ba08b42be4299dd62fe5f5535786a0d8881d93b0d1e09' "${BREEZE_DEB}" | sha256sum --check --strict
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${BREEZE_DEB}"
[[ "$(dpkg-query -W -f='${Version}' breeze-icon-theme)" == '4:6.30.0-0supralinux1' ]]
for payload in \
  /usr/share/icons/breeze/index.theme \
  /usr/share/icons/breeze/mimetypes/22/unknown.svg \
  /usr/share/icons/breeze/mimetypes/16/inode-directory.svg
do
  [[ -s "${payload}" ]]
  sha256sum "${payload}"
done > "${EVIDENCE}/breeze-payload-sha256.txt"

STAGE="verified-upstream-source"
KIO_TARBALL="${WORK}/kio-6.30.0.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 \
  --output "${KIO_TARBALL}" \
  https://download.kde.org/stable/frameworks/6.30/kio-6.30.0.tar.xz
printf '%s  %s\n' 'c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2' "${KIO_TARBALL}" | sha256sum --check --strict
mkdir -p "${WORK}/kio-source"
tar -xJf "${KIO_TARBALL}" --strip-components=1 -C "${WORK}/kio-source"
python3 - "${WORK}/kio-source" "${EVIDENCE}/source-findings.json" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
dm=(root/"autotests/kdirmodeltest.cpp").read_text()
nf=(root/"autotests/knewfilemenutest.cpp").read_text()
impl=(root/"src/filewidgets/knewfilemenu.cpp").read_text()
checks={
 "kdirmodel_enables_test_mode":'QStandardPaths::setTestModeEnabled(true);' in dm,
 "kdirmodel_expects_unknown":'QCOMPARE(icon2.name(), "unknown");' in dm,
 "knewfilemenu_enables_then_disables_test_mode":nf.find('QStandardPaths::setTestModeEnabled(true);') < nf.find('QStandardPaths::setTestModeEnabled(false);'),
 "knewfilemenu_sets_fake_xdg_config_home":'qputenv("XDG_CONFIG_HOME", m_xdgConfigDir.toUtf8());' in nf,
 "knewfilemenu_expects_inode_directory":'QCOMPARE(iconLabel->property("iconName").toString(), defaultFolderIconName);' in nf,
 "knewfilemenu_uses_qicon_fromtheme":'setIcon(QIcon::fromTheme(defaultFolderIconName));' in impl,
}
if not all(checks.values()):
    raise SystemExit(f"unexpected KIO 6.30 source shape: {checks}")
default_fail=nf.find('QCOMPARE(iconLabel->property("iconName").toString(), defaultFolderIconName);')
ok_click=nf.find('okButton->click();',default_fail)
if default_fail < 0 or ok_click < 0 or default_fail >= ok_click:
    raise SystemExit("KNewFileMenu source ordering changed")
checks["default_icon_assertion_precedes_state_persisting_ok_click"]=True
Path(sys.argv[2]).write_text(json.dumps({
 "source_version":"6.30.0",
 "source_sha256":"c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2",
 "checks":checks,
 "classification":"two-primary-icon-resolution-failures-with-knewfilemenu-follow-on-state-cascade"
},indent=2,sort_keys=True)+"\n")
PY

STAGE="qt-icon-probe-build"
PROBE="${WORK}/probe"
mkdir -p "${PROBE}"
cat > "${PROBE}/CMakeLists.txt" <<'EOF_CMAKE'
cmake_minimum_required(VERSION 3.22)
project(SupraLinuxRound12IconProbe LANGUAGES CXX)
find_package(Qt6 6.9 REQUIRED COMPONENTS Widgets)
add_executable(iconprobe iconprobe.cpp)
target_link_libraries(iconprobe PRIVATE Qt6::Widgets)
EOF_CMAKE
cat > "${PROBE}/iconprobe.cpp" <<'EOF_CPP'
#include <QApplication>
#include <QIcon>
#include <QStandardPaths>
#include <QTextStream>

static void printIcon(QTextStream &out, const QString &name)
{
    const QIcon icon=QIcon::fromTheme(name);
    out << "ICON=" << name
        << " HAS=" << (QIcon::hasThemeIcon(name) ? "true" : "false")
        << " NULL=" << (icon.isNull() ? "true" : "false")
        << " NAME=" << icon.name() << "\n";
}

int main(int argc,char **argv)
{
    QApplication app(argc,argv);
    const QString mode=app.arguments().value(1,QStringLiteral("baseline"));
    QString capturedConfig;

    if (mode.startsWith(QStringLiteral("kdirmodel"))) {
        QStandardPaths::setTestModeEnabled(true);
    } else if (mode.startsWith(QStringLiteral("knewfilemenu"))) {
        QStandardPaths::setTestModeEnabled(true);
        capturedConfig=QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
        QStandardPaths::setTestModeEnabled(false);
        qputenv("XDG_CONFIG_HOME",capturedConfig.toUtf8());
    }

    if (mode.endsWith(QStringLiteral("explicit-theme"))) {
        QIcon::setThemeName(QStringLiteral("breeze"));
    }

    QTextStream out(stdout);
    out << "MODE=" << mode << "\n";
    out << "QT_VERSION=" << qVersion() << "\n";
    out << "THEME_NAME=" << QIcon::themeName() << "\n";
    out << "FALLBACK_THEME=" << QIcon::fallbackThemeName() << "\n";
    out << "CAPTURED_CONFIG=" << capturedConfig << "\n";
    for (const auto &p: QStandardPaths::standardLocations(QStandardPaths::GenericDataLocation))
        out << "GENERIC_DATA=" << p << "\n";
    for (const auto &p: QIcon::themeSearchPaths())
        out << "THEME_PATH=" << p << "\n";
    printIcon(out,QStringLiteral("unknown"));
    printIcon(out,QStringLiteral("inode-directory"));
    printIcon(out,QStringLiteral("folder-red"));
    return 0;
}
EOF_CPP
cmake -S "${PROBE}" -B "${PROBE}/build" -DCMAKE_BUILD_TYPE=Release |& tee "${EVIDENCE}/probe-configure.log"
cmake --build "${PROBE}/build" --parallel 2 |& tee "${EVIDENCE}/probe-build.log"

run_probe() {
  local mode="$1"
  mkdir -p "${WORK}/homes/${mode}"
  HOME="${WORK}/homes/${mode}" \
  QT_QPA_PLATFORM=xcb \
  QT_QPA_SYSTEM_ICON_THEME=breeze \
  xvfb-run -a -s '-screen 0 1280x1024x24' "${PROBE}/build/iconprobe" "${mode}" \
    | tee "${EVIDENCE}/probe-${mode}.txt"
}

STAGE="qt-icon-probes"
run_probe baseline
run_probe kdirmodel-testmode
run_probe kdirmodel-testmode-explicit-theme
run_probe knewfilemenu-sequence
run_probe knewfilemenu-sequence-explicit-theme

STAGE="finding-capture"
python3 - "${EVIDENCE}" <<'PY'
import json,re,sys
from pathlib import Path
ev=Path(sys.argv[1])
modes=[
 "baseline","kdirmodel-testmode","kdirmodel-testmode-explicit-theme",
 "knewfilemenu-sequence","knewfilemenu-sequence-explicit-theme"
]
def parse(mode):
    text=(ev/f"probe-{mode}.txt").read_text()
    icons={}
    for line in text.splitlines():
        if line.startswith("ICON="):
            m=re.match(r"ICON=(\S+) HAS=(true|false) NULL=(true|false) NAME=(.*)",line)
            if m:
                icons[m.group(1)]={"has":m.group(2)=="true","null":m.group(3)=="true","name":m.group(4)}
    def one(prefix):
        return next((x.split("=",1)[1] for x in text.splitlines() if x.startswith(prefix+"=")),"")
    return {
      "theme_name":one("THEME_NAME"),
      "fallback_theme":one("FALLBACK_THEME"),
      "captured_config":one("CAPTURED_CONFIG"),
      "generic_data":[x.split("=",1)[1] for x in text.splitlines() if x.startswith("GENERIC_DATA=")],
      "theme_paths":[x.split("=",1)[1] for x in text.splitlines() if x.startswith("THEME_PATH=")],
      "icons":icons
    }
results={m:parse(m) for m in modes}
for icon in ("unknown","inode-directory","folder-red"):
    b=results["baseline"]["icons"].get(icon,{})
    if not b.get("has") or b.get("null") or b.get("name")!=icon:
        raise SystemExit(f"baseline Qt/Breeze probe failed for {icon}: {b}")

def broken(mode,icon):
    x=results[mode]["icons"].get(icon,{})
    return (not x.get("has")) or x.get("null") or x.get("name")!=icon

classification={
 "kdirmodel_testmode_reproduces":broken("kdirmodel-testmode","unknown"),
 "kdirmodel_explicit_theme_recovers":not broken("kdirmodel-testmode-explicit-theme","unknown"),
 "knewfilemenu_sequence_reproduces":broken("knewfilemenu-sequence","inode-directory"),
 "knewfilemenu_explicit_theme_recovers":not broken("knewfilemenu-sequence-explicit-theme","inode-directory"),
}
if classification["kdirmodel_testmode_reproduces"] or classification["knewfilemenu_sequence_reproduces"]:
    next_scope="isolated-qt-standard-paths-theme-state-root-cause"
else:
    next_scope="kio-build-tree-process-specific-icon-resolution-diagnostic"
(ev/"findings.json").write_text(json.dumps({
 "claim":"diagnostic-only",
 "package_state_effect":"none",
 "attempt7":json.loads((ev/"attempt7-log-findings.json").read_text()),
 "source":json.loads((ev/"source-findings.json").read_text()),
 "probe_results":results,
 "classification":classification,
 "next_diagnostic_scope":next_scope
},indent=2,sort_keys=True)+"\n")
PY

STAGE="complete"
DIAG_RESULT="DIAG_COMPLETE"
echo "KIO Round 12 diagnostic evidence capture: COMPLETE (non-promoting)"
