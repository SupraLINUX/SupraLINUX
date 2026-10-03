#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUDIT="${ROOT}/scripts/audit-kde-development-contract.py"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/source/src" "${TMP}/debs" "${TMP}/pkg-dev/DEBIAN" "${TMP}/pkg-dev/usr/lib/x86_64-linux-gnu/cmake/KF6Foo" "${TMP}/pkg-qml/DEBIAN" "${TMP}/pkg-qml/usr/lib/x86_64-linux-gnu/qt6/qml/org/kde/foo" "${TMP}/out"
cat > "${TMP}/campaign.json" <<'JSON'
{"nodes":{"foo":{"package_validation_dependencies":[{"required_during_dh_qmldeps":true,"required_local_packages":["qml6-module-org-kde-kirigami"]}],"qml_contracts":[{"package":"qml6-module-org-kde-foo","required_root_module":"org.kde.foo"}]}}}
JSON
cat > "${TMP}/control" <<'EOF'
Source: kf6-foo
Build-Depends: extra-cmake-modules, qml6-module-org-kde-kirigami

Package: libfoo-dev
Architecture: any
Depends: extra-cmake-modules (>= 6.30.0), ${misc:Depends}
Description: foo dev
EOF
cat > "${TMP}/source/src/KF6FooConfig.cmake.in" <<'EOF'
include(CMakeFindDependencyMacro)
find_dependency(ECM 6.30.0)
EOF
python3 "${AUDIT}" source --node foo --campaign "${TMP}/campaign.json" --source-dir "${TMP}/source" --control "${TMP}/control" --output "${TMP}/out/source.json"
grep -q '"result": "PASS"' "${TMP}/out/source.json"
cp "${TMP}/control" "${TMP}/control.bad"; sed -i '/Package: libfoo-dev/,$ s/extra-cmake-modules (>= 6.30.0), //' "${TMP}/control.bad"
if python3 "${AUDIT}" source --node foo --campaign "${TMP}/campaign.json" --source-dir "${TMP}/source" --control "${TMP}/control.bad" --output "${TMP}/out/source-bad.json"; then echo "source audit accepted missing ECM development dependency" >&2; exit 1; fi
cat > "${TMP}/pkg-dev/DEBIAN/control" <<'EOF'
Package: libfoo-dev
Version: 6.30.0-0supralinux1
Section: libdevel
Priority: optional
Architecture: amd64
Maintainer: Test <test@example.invalid>
Depends: extra-cmake-modules (>= 6.30.0)
Description: test dev
EOF
cat > "${TMP}/pkg-dev/usr/lib/x86_64-linux-gnu/cmake/KF6Foo/KF6FooConfig.cmake" <<'EOF'
include(CMakeFindDependencyMacro)
find_dependency(ECM 6.30.0)
include(${CMAKE_CURRENT_LIST_DIR}/KF6FooTarget.cmake)
EOF
cat > "${TMP}/pkg-dev/usr/lib/x86_64-linux-gnu/cmake/KF6Foo/KF6FooTarget.cmake" <<'EOF'
add_library(KF6::Foo SHARED IMPORTED)
EOF
cat > "${TMP}/pkg-qml/DEBIAN/control" <<'EOF'
Package: qml6-module-org-kde-foo
Version: 6.30.0-0supralinux1
Section: libs
Priority: optional
Architecture: amd64
Maintainer: Test <test@example.invalid>
Description: test qml
EOF
echo 'module org.kde.foo' > "${TMP}/pkg-qml/usr/lib/x86_64-linux-gnu/qt6/qml/org/kde/foo/qmldir"
dpkg-deb --build "${TMP}/pkg-dev" "${TMP}/debs/libfoo-dev.deb" >/dev/null
dpkg-deb --build "${TMP}/pkg-qml" "${TMP}/debs/qml.deb" >/dev/null
cat > "${TMP}/consumer.cmake" <<'EOF'
find_package(KF6Foo 6.30 REQUIRED CONFIG)
if(NOT TARGET KF6::Foo)
 message(FATAL_ERROR "missing")
endif()
target_link_libraries(consumer PRIVATE KF6::Foo)
EOF
python3 "${AUDIT}" artifact --node foo --campaign "${TMP}/campaign.json" --debs-dir "${TMP}/debs" --consumer-cmake "${TMP}/consumer.cmake" --output "${TMP}/out/artifact.json"
grep -q '"result": "PASS"' "${TMP}/out/artifact.json"
sed 's/KF6::Foo/KF6::Missing/g' "${TMP}/consumer.cmake" > "${TMP}/consumer.bad.cmake"
if python3 "${AUDIT}" artifact --node foo --campaign "${TMP}/campaign.json" --debs-dir "${TMP}/debs" --consumer-cmake "${TMP}/consumer.bad.cmake" --output "${TMP}/out/artifact-bad.json"; then echo "artifact audit accepted nonexistent CMake target" >&2; exit 1; fi
echo "KDE development contract audit: PASS"
