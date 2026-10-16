#!/usr/bin/env bash
# shellcheck disable=SC1090,SC2034,SC2154

STAGE=source-link-contract
python3 - "${SRC}" "${EVIDENCE}/source-link-contract.json" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
auto=(root/"autotests/CMakeLists.txt").read_text()
widgets=(root/"src/widgets/CMakeLists.txt").read_text()
filewidgets=(root/"src/filewidgets/CMakeLists.txt").read_text()
checks={
 "kdirmodel_links_kiocore": "kdirmodeltest.cpp" in auto and "LINK_LIBRARIES KF6::KIOCore KF6::KIOWidgets Qt6::Test" in auto,
 "knewfilemenu_in_filewidgets_group": "knewfilemenutest.cpp" in auto and "LINK_LIBRARIES KF6::KIOFileWidgets KF6::KIOWidgets KF6::Bookmarks Qt6::Test KF6::I18n KF6::WindowSystem" in auto,
 "kiowidgets_public_kiocore": "KF6::KIOCore" in widgets,
 "kiowidgets_private_iconthemes": "KF6::IconThemes   # KIconLoader" in widgets,
 "kiofilewidgets_public_kiowidgets": "KF6::KIOWidgets" in filewidgets,
}
if not all(checks.values()):
    raise SystemExit(f"unexpected KIO 6.30 linkage contract: {checks}")
Path(sys.argv[2]).write_text(json.dumps({"source_version":"6.30.0","checks":checks},indent=2,sort_keys=True)+"\n")
PY

STAGE=probe-link-inputs
KIO_BIN="${OBJ}/bin"
KICONTHEMES_LIB=/usr/lib/x86_64-linux-gnu/libKF6IconThemes.so.6
KIOCORE_LIB="${KIO_BIN}/libKF6KIOCore.so.6"
KIOWIDGETS_LIB="${KIO_BIN}/libKF6KIOWidgets.so.6"
KIOFILEWIDGETS_LIB="${KIO_BIN}/libKF6KIOFileWidgets.so.6"
for f in "${KICONTHEMES_LIB}" "${KIOCORE_LIB}" "${KIOWIDGETS_LIB}" "${KIOFILEWIDGETS_LIB}"; do [[ -e "${f}" ]]; done
[[ "$(dpkg-query -W -f='${Version}' libkf6iconthemes6)" == "6.30.0-0supralinux3" ]]
dpkg-query -W -f='${Package}\t${Version}\n' libkf6iconthemes6 libkf6breezeicons6 qt6-svg-plugins > "${EVIDENCE}/installed-link-providers.tsv"

STAGE=probe-build
PROBE="${WORK}/link-probe"
mkdir -p "${PROBE}"
cat > "${PROBE}/CMakeLists.txt" <<'EOF_CMAKE'
cmake_minimum_required(VERSION 3.22)
project(SupraLinuxRound16LinkProbe LANGUAGES CXX)
find_package(Qt6 6.9 REQUIRED COMPONENTS Widgets)
set(KICONTHEMES_LIB "" CACHE FILEPATH "")
set(KIOCORE_LIB "" CACHE FILEPATH "")
set(KIOWIDGETS_LIB "" CACHE FILEPATH "")
set(KIOFILEWIDGETS_LIB "" CACHE FILEPATH "")
set(KIO_BIN "" CACHE PATH "")
function(add_link_probe name)
  add_executable(${name} probe.cpp)
  target_link_libraries(${name} PRIVATE Qt6::Widgets)
  if(ARGN)
    target_link_options(${name} PRIVATE "LINKER:--no-as-needed")
    target_link_libraries(${name} PRIVATE ${ARGN})
  endif()
  set_target_properties(${name} PROPERTIES BUILD_RPATH "${KIO_BIN}")
endfunction()
add_link_probe(qtprobe)
add_link_probe(kiconthemesprobe "${KICONTHEMES_LIB}")
add_link_probe(kiocoreprobe "${KIOCORE_LIB}")
add_link_probe(kiconthemeskiocoreprobe "${KICONTHEMES_LIB}" "${KIOCORE_LIB}")
add_link_probe(kiowidgetsprobe "${KIOWIDGETS_LIB}")
add_link_probe(kiofilewidgetsprobe "${KIOFILEWIDGETS_LIB}")
EOF_CMAKE
cat > "${PROBE}/probe.cpp" <<'EOF_CPP'
#include <QApplication>
#include <QCoreApplication>
#include <QFile>
#include <QIcon>
#include <QStandardPaths>
#include <QTextStream>
static void printIcon(QTextStream &out,const QString &name)
{
    const QIcon icon=QIcon::fromTheme(name);
    out << "ICON=" << name
        << " HAS=" << (QIcon::hasThemeIcon(name) ? "true" : "false")
        << " NULL=" << (icon.isNull() ? "true" : "false")
        << " NAME=" << icon.name() << "\n";
}
static void state(QTextStream &out,const QString &phase)
{
    out << phase << "_THEME=" << QIcon::themeName() << "\n";
    out << phase << "_FALLBACK=" << QIcon::fallbackThemeName() << "\n";
    out << phase << "_RESOURCE=" << (QFile::exists(QStringLiteral(":/icons/breeze/index.theme")) ? "true" : "false") << "\n";
}
int main(int argc,char **argv)
{
    QApplication app(argc,argv);
    const QString sequence=app.arguments().value(1,QStringLiteral("normal"));
    const QString mode=app.arguments().value(2,QStringLiteral("unknown"));
    QTextStream out(stdout);
    out << "QT_VERSION=" << qVersion() << "\nMODE=" << mode << "\nSEQUENCE=" << sequence << "\n";
    state(out,QStringLiteral("PRE"));
    QString captured;
    if (sequence == QLatin1String("kdirmodel-testmode")) {
        QStandardPaths::setTestModeEnabled(true);
    } else if (sequence == QLatin1String("knewfilemenu-sequence")) {
        QStandardPaths::setTestModeEnabled(true);
        captured=QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
        QStandardPaths::setTestModeEnabled(false);
        qputenv("XDG_CONFIG_HOME",captured.toUtf8());
    }
    state(out,QStringLiteral("POST"));
    out << "CAPTURED_CONFIG=" << captured << "\n";
    for (const auto &p: QCoreApplication::libraryPaths()) out << "LIBRARY_PATH=" << p << "\n";
    for (const auto &p: QStandardPaths::standardLocations(QStandardPaths::GenericDataLocation)) out << "GENERIC_DATA=" << p << "\n";
    for (const auto &p: QIcon::themeSearchPaths()) out << "THEME_PATH=" << p << "\n";
    printIcon(out,QStringLiteral("unknown"));
    printIcon(out,QStringLiteral("inode-directory"));
    printIcon(out,QStringLiteral("folder-red"));
    return 0;
}
EOF_CPP
cmake -S "${PROBE}" -B "${PROBE}/build" -DCMAKE_BUILD_TYPE=Release \
  -DKICONTHEMES_LIB="${KICONTHEMES_LIB}" -DKIOCORE_LIB="${KIOCORE_LIB}" \
  -DKIOWIDGETS_LIB="${KIOWIDGETS_LIB}" -DKIOFILEWIDGETS_LIB="${KIOFILEWIDGETS_LIB}" -DKIO_BIN="${KIO_BIN}" \
  |& tee "${EVIDENCE}/probe-configure.log"
cmake --build "${PROBE}/build" --parallel 2 |& tee "${EVIDENCE}/probe-build.log"

STAGE=linkage-proof
for bin in qtprobe kiconthemesprobe kiocoreprobe kiconthemeskiocoreprobe kiowidgetsprobe kiofilewidgetsprobe; do
  LD_LIBRARY_PATH="${KIO_BIN}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" ldd "${PROBE}/build/${bin}" > "${EVIDENCE}/${bin}-ldd.txt"
done
if grep -Eq 'libKF6(IconThemes|KIO)' "${EVIDENCE}/qtprobe-ldd.txt"; then echo "Qt baseline linkage contaminated" >&2; exit 2; fi
grep -F 'libKF6IconThemes.so.6' "${EVIDENCE}/kiconthemesprobe-ldd.txt" >/dev/null
grep -F 'libKF6KIOCore.so.6' "${EVIDENCE}/kiocoreprobe-ldd.txt" >/dev/null
grep -F 'libKF6IconThemes.so.6' "${EVIDENCE}/kiconthemeskiocoreprobe-ldd.txt" >/dev/null
grep -F 'libKF6KIOCore.so.6' "${EVIDENCE}/kiconthemeskiocoreprobe-ldd.txt" >/dev/null
grep -F 'libKF6KIOWidgets.so.6' "${EVIDENCE}/kiowidgetsprobe-ldd.txt" >/dev/null
grep -F 'libKF6IconThemes.so.6' "${EVIDENCE}/kiowidgetsprobe-ldd.txt" >/dev/null
grep -F 'libKF6KIOFileWidgets.so.6' "${EVIDENCE}/kiofilewidgetsprobe-ldd.txt" >/dev/null
grep -F 'libKF6KIOWidgets.so.6' "${EVIDENCE}/kiofilewidgetsprobe-ldd.txt" >/dev/null

source "${ROOT}/scripts/run-kde-tier3-kio-round16-probe-matrix.sh"
