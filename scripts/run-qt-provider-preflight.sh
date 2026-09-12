#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="${ROOT}/evidence/qt-provider-preflight"
WORK_DIR="${ROOT}/.work/qt-provider-preflight"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
MANIFEST="${ROOT}/manifests/desktop-stack.json"
STATE="FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

PACKAGES=(
    qt6-base-dev
    qt6-base-private-dev
    qt6-declarative-dev
    qt6-declarative-private-dev
    qt6-svg-dev
    qt6-wayland-dev
    qt6-wayland-private-dev
    qt6-shadertools-dev
    qt6-tools-dev
    qt6-tools-dev-tools
    qt6-5compat-dev
)

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${WORK_DIR}" "${EVIDENCE_DIR}"

write_result() {
    local rc="$?"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT_JSON}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json
import sys
from pathlib import Path

path, state, rc, stage, started, finished = sys.argv[1:]
Path(path).write_text(json.dumps({
    "node": "qt-provider-preflight",
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": False,
    "claim": "ubuntu-qt-provider-preflight-only",
    "platform": "ubuntu-26.04",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT

exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

for command_name in apt-cache cmake c++ dpkg-query ninja python3 qtpaths6; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi

REQUIRED_SERIES="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["qt"]["required_series"])' "${MANIFEST}")"
if [[ ! "${REQUIRED_SERIES}" =~ ^[0-9]+\.[0-9]+$ ]]; then
    printf 'Invalid Qt required_series in manifest: %s\n' "${REQUIRED_SERIES}" >&2
    exit 1
fi

normalize_upstream_version() {
    local deb_version="$1"
    if [[ "${deb_version}" =~ ^([0-9]+\.[0-9]+\.[0-9]+) ]]; then
        printf '%s' "${BASH_REMATCH[1]}"
    else
        return 1
    fi
}

STAGE="package-coherence"
printf 'Checking Ubuntu Qt provider package closure...\n'
printf 'package\tinstalled\tcandidate\tupstream\n' > "${EVIDENCE_DIR}/packages.tsv"
BASE_UPSTREAM=""
for package in "${PACKAGES[@]}"; do
    installed="$(dpkg-query -W -f='${Version}' "${package}" 2>/dev/null || true)"
    candidate="$(apt-cache policy "${package}" | awk '/Candidate:/ {print $2}')"
    if [[ -z "${installed}" || -z "${candidate}" || "${candidate}" == "(none)" ]]; then
        printf 'Qt provider package missing installed/candidate version: %s installed=%s candidate=%s\n' \
            "${package}" "${installed:-missing}" "${candidate:-missing}" >&2
        exit 1
    fi
    upstream="$(normalize_upstream_version "${installed}")" || {
        printf 'Cannot normalize Qt upstream version for %s: %s\n' "${package}" "${installed}" >&2
        exit 1
    }
    if [[ "${upstream}" != "${REQUIRED_SERIES}."* ]]; then
        printf 'Package %s provides Qt %s but KDE requires Qt %s.x.\n' "${package}" "${upstream}" "${REQUIRED_SERIES}" >&2
        exit 1
    fi
    if [[ -z "${BASE_UPSTREAM}" ]]; then
        BASE_UPSTREAM="${upstream}"
    elif [[ "${upstream}" != "${BASE_UPSTREAM}" ]]; then
        printf 'Mixed Qt upstream patch releases are not accepted by provider preflight: %s=%s baseline=%s\n' \
            "${package}" "${upstream}" "${BASE_UPSTREAM}" >&2
        exit 1
    fi
    printf '%s\t%s\t%s\t%s\n' "${package}" "${installed}" "${candidate}" "${upstream}" \
        >> "${EVIDENCE_DIR}/packages.tsv"
done

QT_PATHS_VERSION="$(qtpaths6 --qt-version | tr -d '\r[:space:]')"
if [[ "${QT_PATHS_VERSION}" != "${BASE_UPSTREAM}" ]]; then
    printf 'qtpaths6 reports %s but provider package baseline is %s.\n' "${QT_PATHS_VERSION}" "${BASE_UPSTREAM}" >&2
    exit 1
fi

{
    printf 'checked_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'platform=%s\n' "${PRETTY_NAME}"
    printf 'required_series=%s\n' "${REQUIRED_SERIES}"
    printf 'resolved_upstream_version=%s\n' "${BASE_UPSTREAM}"
    printf 'qtpaths_version=%s\n' "${QT_PATHS_VERSION}"
    printf 'provider=ubuntu\n'
    printf 'provider_series=resolute\n'
    printf 'claim=preflight-only\n'
    printf '\nqtpaths:\n'
    qtpaths6 --query
} > "${EVIDENCE_DIR}/environment.txt"

dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' 'libqt6*' 'qt6-*' 'qml6-*' 2>/dev/null \
    | sort -u > "${EVIDENCE_DIR}/installed-qt-packages.tsv" || true

STAGE="cmake-configure"
mkdir -p "${WORK_DIR}/src"
cat > "${WORK_DIR}/src/CMakeLists.txt" <<EOF_CMAKE
cmake_minimum_required(VERSION 3.24)
project(SupraLinuxQtProviderProbe LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 ${REQUIRED_SERIES} REQUIRED COMPONENTS
    Core Gui Widgets DBus Network Concurrent
    Qml Quick QuickControls2
    Svg ShaderTools Core5Compat WaylandClient
)
find_package(Qt6GuiPrivate ${REQUIRED_SERIES} REQUIRED)
find_package(Qt6QmlPrivate ${REQUIRED_SERIES} REQUIRED)
find_package(Qt6QuickPrivate ${REQUIRED_SERIES} REQUIRED)
find_package(Qt6WaylandClientPrivate ${REQUIRED_SERIES} REQUIRED)

set(required_targets
    Qt6::Core Qt6::Gui Qt6::Widgets Qt6::DBus Qt6::Network Qt6::Concurrent
    Qt6::Qml Qt6::Quick Qt6::QuickControls2 Qt6::Svg Qt6::ShaderTools
    Qt6::Core5Compat Qt6::WaylandClient
    Qt6::GuiPrivate Qt6::QmlPrivate Qt6::QuickPrivate Qt6::WaylandClientPrivate
)
foreach(target IN LISTS required_targets)
    if(NOT TARGET "\${target}")
        message(FATAL_ERROR "Required Qt provider target is missing: \${target}")
    endif()
endforeach()

add_executable(qt-provider-probe main.cpp)
target_link_libraries(qt-provider-probe PRIVATE \${required_targets})
EOF_CMAKE

cat > "${WORK_DIR}/src/main.cpp" <<'EOF_CPP'
#include <QCoreApplication>
#include <QTextCodec>
#include <QVersionNumber>
#include <QQmlEngine>
#include <QSvgRenderer>
#include <iostream>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const auto version = QVersionNumber::fromString(qVersion());
    if (version.majorVersion() != 6 || version.minorVersion() != 10) {
        std::cerr << "unexpected Qt runtime version: " << qVersion() << '\n';
        return 10;
    }
    QQmlEngine engine;
    QSvgRenderer renderer;
    if (QTextCodec::codecForName("UTF-8") == nullptr) {
        std::cerr << "Qt Core5Compat codec lookup failed\n";
        return 11;
    }
    std::cout << "qt_runtime_version=" << qVersion() << '\n';
    std::cout << "qml_engine=PASS\n";
    std::cout << "svg_module=PASS\n";
    std::cout << "core5compat=PASS\n";
    return 0;
}
EOF_CPP

cmake -S "${WORK_DIR}/src" -B "${WORK_DIR}/build" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release |& tee "${EVIDENCE_DIR}/cmake-configure.log"

STAGE="cmake-build"
cmake --build "${WORK_DIR}/build" --verbose |& tee "${EVIDENCE_DIR}/cmake-build.log"

STAGE="runtime-probe"
"${WORK_DIR}/build/qt-provider-probe" |& tee "${EVIDENCE_DIR}/runtime-probe.txt"
grep -Fqx "qt_runtime_version=${BASE_UPSTREAM}" "${EVIDENCE_DIR}/runtime-probe.txt"
grep -Fqx 'qml_engine=PASS' "${EVIDENCE_DIR}/runtime-probe.txt"
grep -Fqx 'svg_module=PASS' "${EVIDENCE_DIR}/runtime-probe.txt"
grep -Fqx 'core5compat=PASS' "${EVIDENCE_DIR}/runtime-probe.txt"

STATE="PASS"
STAGE="complete"
printf 'Ubuntu Qt provider preflight: PASS (Qt %s for required series %s)\n' "${BASE_UPSTREAM}" "${REQUIRED_SERIES}"
printf 'This is provider preflight evidence only; KDE build/DAG compatibility certification remains separate.\n'
