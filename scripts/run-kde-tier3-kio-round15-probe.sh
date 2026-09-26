# shellcheck disable=SC2154
STAGE=probe-build
PROBE="${WORK}/probe"
mkdir -p "${PROBE}"
cat > "${PROBE}/CMakeLists.txt" <<'EOF_CMAKE'
cmake_minimum_required(VERSION 3.22)
project(SupraLinuxRound15BreezeProbe LANGUAGES CXX)
find_package(Qt6 6.9 REQUIRED COMPONENTS Widgets)
find_package(KF6BreezeIcons 6.30.0 REQUIRED)
add_executable(qtprobe probe.cpp)
target_link_libraries(qtprobe PRIVATE Qt6::Widgets)
add_executable(breezeprobe probe.cpp)
target_compile_definitions(breezeprobe PRIVATE WITH_BREEZE_ICONS=1)
target_link_libraries(breezeprobe PRIVATE Qt6::Widgets KF6::BreezeIcons)
EOF_CMAKE
cat > "${PROBE}/probe.cpp" <<'EOF_CPP'
#include <QApplication>
#include <QFile>
#include <QIcon>
#include <QStandardPaths>
#include <QTextStream>
#ifdef WITH_BREEZE_ICONS
#include <BreezeIcons>
#endif
static void printIcon(QTextStream &out, const QString &name)
{
    const QIcon icon=QIcon::fromTheme(name);
    out << "ICON=" << name
        << " HAS=" << (QIcon::hasThemeIcon(name) ? "true" : "false")
        << " NULL=" << (icon.isNull() ? "true" : "false")
        << " NAME=" << icon.name() << "\n";
}
static void printState(QTextStream &out, const QString &phase)
{
    out << phase << "_THEME=" << QIcon::themeName() << "\n";
    out << phase << "_FALLBACK=" << QIcon::fallbackThemeName() << "\n";
    out << phase << "_RESOURCE=" << (QFile::exists(QStringLiteral(":/icons/breeze/index.theme")) ? "true" : "false") << "\n";
}
int main(int argc,char **argv)
{
    QApplication app(argc,argv);
    const QString sequence=app.arguments().value(1,QStringLiteral("normal"));
    const QString mode=app.arguments().value(2,QStringLiteral("baseline"));
    QTextStream out(stdout);
    out << "QT_VERSION=" << qVersion() << "\nSEQUENCE=" << sequence << "\nMODE=" << mode << "\n";
    printState(out,QStringLiteral("PRE"));
    if (mode == QLatin1String("fallback-breeze")) {
        QIcon::setFallbackThemeName(QStringLiteral("breeze"));
    }
#ifdef WITH_BREEZE_ICONS
    else if (mode == QLatin1String("init")) {
        BreezeIcons::initIcons();
    }
#endif
    QString capturedConfig;
    if (sequence == QLatin1String("kdirmodel-testmode")) {
        QStandardPaths::setTestModeEnabled(true);
    } else if (sequence == QLatin1String("knewfilemenu-sequence")) {
        QStandardPaths::setTestModeEnabled(true);
        capturedConfig=QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
        QStandardPaths::setTestModeEnabled(false);
        qputenv("XDG_CONFIG_HOME",capturedConfig.toUtf8());
    }
    printState(out,QStringLiteral("POST"));
    out << "CAPTURED_CONFIG=" << capturedConfig << "\n";
    for (const auto &p: QStandardPaths::standardLocations(QStandardPaths::GenericDataLocation)) out << "GENERIC_DATA=" << p << "\n";
    for (const auto &p: QIcon::themeSearchPaths()) out << "THEME_PATH=" << p << "\n";
    printIcon(out,QStringLiteral("unknown"));
    printIcon(out,QStringLiteral("inode-directory"));
    printIcon(out,QStringLiteral("folder-red"));
    return 0;
}
EOF_CPP
cmake -S "${PROBE}" -B "${PROBE}/build" -DCMAKE_BUILD_TYPE=Release |& tee "${EVIDENCE}/probe-configure.log"
cmake --build "${PROBE}/build" --parallel 2 |& tee "${EVIDENCE}/probe-build.log"
ldd "${PROBE}/build/qtprobe" > "${EVIDENCE}/qtprobe-ldd.txt"
ldd "${PROBE}/build/breezeprobe" > "${EVIDENCE}/breezeprobe-ldd.txt"
if grep -F 'libKF6BreezeIcons' "${EVIDENCE}/qtprobe-ldd.txt"; then echo 'qtprobe unexpectedly links BreezeIcons' >&2; exit 2; fi
grep -F 'libKF6BreezeIcons.so.6' "${EVIDENCE}/breezeprobe-ldd.txt" >/dev/null

run_probe() {
  local binary="$1" sequence="$2" mode="$3" label="$4"
  local home="${WORK}/homes/${label}"
  mkdir -p "${home}"
  HOME="${home}" QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze \
    xvfb-run -a -s '-screen 0 1280x1024x24' "${PROBE}/build/${binary}" "${sequence}" "${mode}" \
    > "${EVIDENCE}/${label}.txt"
}

STAGE=probe-matrix
for sequence in normal kdirmodel-testmode knewfilemenu-sequence; do
  run_probe qtprobe "${sequence}" baseline "${sequence}--qt-baseline"
  run_probe qtprobe "${sequence}" fallback-breeze "${sequence}--qt-fallback-breeze"
  run_probe breezeprobe "${sequence}" no-init "${sequence}--breeze-linked-no-init"
  run_probe breezeprobe "${sequence}" init "${sequence}--breeze-init"
done


source "${ROOT}/scripts/run-kde-tier3-kio-round15-classify.sh"
