#!/usr/bin/env bash
# Infrastructure-only consumer: certify cache admission + sbuild input transport.
set -Eeuo pipefail
SELECTION="$1"
WORK="$2"
EVIDENCE="$3"
shift 3
SBUILD_OPTIONS=("$@")
mkdir -p "${WORK}/source/debian/source" "${WORK}/out" "${EVIDENCE}"
mapfile -t EXTRA_PATHS < <(python3 - "${SELECTION}" <<'PY'
import json, sys
selection = json.load(open(sys.argv[1]))
assert selection["state"] == "PASS"
for item in selection["selected"]:
    print(item["path"])
PY
)
EXTRA_ARGS=()
for path in "${EXTRA_PATHS[@]}"; do EXTRA_ARGS+=("--extra-package=${path}"); done
ECM_VERSION="$(python3 - "${SELECTION}" <<'PY'
import json, sys
items = [item for item in json.load(open(sys.argv[1]))["selected"] if item["package"] == "extra-cmake-modules"]
assert len(items) == 1
print(items[0]["version"])
PY
)"
PREDECESSOR_DEPENDS="$(python3 - "${SELECTION}" "${WORK}/source/expected-predecessors.json" <<'PY'
import json, re, sys
selection = json.load(open(sys.argv[1]))['selected']
expected = [{key: item[key] for key in ['package', 'source_package', 'version', 'architecture']} for item in selection]
assert len({item['package'] for item in expected}) == len(expected)
for item in expected:
    assert re.fullmatch(r'[a-z0-9][a-z0-9+.-]+', item['package'])
    assert re.fullmatch(r'[A-Za-z0-9.+~:-]+', item['version'])
with open(sys.argv[2], 'w') as stream:
    stream.write(json.dumps(expected, indent=2) + '\n')
print(',\n               '.join(f"{item['package']} (= {item['version']})" for item in expected if item['package'] != 'extra-cmake-modules'))
PY
)"
if [[ -n "${PREDECESSOR_DEPENDS}" ]]; then PREDECESSOR_DEPENDS=", ${PREDECESSOR_DEPENDS}"; fi
cat > "${WORK}/source/debian/control" <<EOF
Source: supralinux-cache-probe
Section: devel
Priority: optional
Maintainer: SupraLINUX Project <packages@supralinux.invalid>
Build-Depends: debhelper-compat (= 13), cmake, extra-cmake-modules (= ${ECM_VERSION}), qt6-base-dev, python3${PREDECESSOR_DEPENDS}
Standards-Version: 4.7.0
Rules-Requires-Root: no

Package: supralinux-cache-probe
Architecture: any
Depends: \${shlibs:Depends}, \${misc:Depends}
Description: Infrastructure consumer for retained Frameworks input transport
 An infrastructure-only sample. Never published as a desktop package.
EOF
cat > "${WORK}/source/debian/changelog" <<'EOF'
supralinux-cache-probe (1.0) resolute; urgency=medium

  * Certify explicit retained ECM transport into a clean sbuild environment.

 -- SupraLINUX Project <packages@supralinux.invalid>  Sun, 04 Oct 2026 18:00:00 -0300
EOF
printf '3.0 (native)\n' > "${WORK}/source/debian/source/format"
printf '#!/usr/bin/make -f\n%%:\n\tdh $@\noverride_dh_auto_test:\n\t./obj-*/cache-probe\n\tpython3 verify-predecessors.py\n' > "${WORK}/source/debian/rules"
chmod +x "${WORK}/source/debian/rules"
cat > "${WORK}/source/verify-predecessors.py" <<'PY'
import json, subprocess
from pathlib import Path
expected = json.loads(Path('expected-predecessors.json').read_text())
for item in expected:
    actual = subprocess.check_output(['dpkg-query', '-W', '-f=${source:Package}\n${Version}\n${Architecture}', item['package']], text=True).splitlines()
    assert actual == [item['source_package'], item['version'], item['architecture']], (item, actual)
print(f'Reviewed predecessor versions installed in clean sbuild: PASS ({len(expected)})')
PY
cat > "${WORK}/source/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.16)
project(cache-probe LANGUAGES CXX)
find_package(ECM 6.30.0 EXACT REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})
include(KDEInstallDirs)
find_package(Qt6 6.10 REQUIRED COMPONENTS Core)
add_executable(cache-probe main.cpp)
target_link_libraries(cache-probe Qt6::Core)
install(TARGETS cache-probe DESTINATION bin)
EOF
cat > "${WORK}/source/main.cpp" <<'EOF'
#include <QCoreApplication>
#include <QString>
#include <iostream>
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const QString version = QString::fromLatin1(qVersion());
    if (!version.startsWith(QStringLiteral("6.10."))) return 1;
    std::cout << "Retained ECM 6.30.0 and Ubuntu Qt " << qVersion() << ": PASS\n";
}
EOF
(
    cd "${WORK}"
    dpkg-source -b source
)
cp "${WORK}/"*.dsc "${WORK}/"*.tar.xz "${EVIDENCE}/"
sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 \
    "${EXTRA_ARGS[@]}" "${SBUILD_OPTIONS[@]}" --build-dir="${WORK}/out" "${WORK}/supralinux-cache-probe_1.0.dsc" \
    |& tee "${EVIDENCE}/sbuild.log"
grep -Fq 'Retained ECM 6.30.0 and Ubuntu Qt 6.10.' "${EVIDENCE}/sbuild.log"
grep -Fq 'Reviewed predecessor versions installed in clean sbuild: PASS' "${EVIDENCE}/sbuild.log"
cp "${WORK}/source/expected-predecessors.json" "${EVIDENCE}/installed-predecessor-contract.json"
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${WORK}/out/"*.buildinfo > "${EVIDENCE}/predecessor-buildinfo.txt"
cp "${WORK}/out/"*.deb "${WORK}/out/"*.changes "${WORK}/out/"*.buildinfo "${EVIDENCE}/"
mapfile -t DEBUG_OUTPUTS < <(find "${WORK}/out" -maxdepth 1 -name '*.ddeb' -type f)
if (( ${#DEBUG_OUTPUTS[@]} > 0 )); then cp "${DEBUG_OUTPUTS[@]}" "${EVIDENCE}/"; fi
printf '{"state":"PASS","kind":"infrastructure-consumer-probe","canonical_package_state_effect":"none","consumes_package_attempt":false,"predecessors_installed_at_reviewed_versions":true}\n' > "${EVIDENCE}/result.json"
printf 'Frameworks retained build input probe: PASS\n'
