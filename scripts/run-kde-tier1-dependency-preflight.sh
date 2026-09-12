#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT}/manifests/kde-frameworks-tier1-dependencies.json"
EVIDENCE="${ROOT}/evidence/kde-tier1-dependency-preflight"

rm -rf "${EVIDENCE}"
mkdir -p "${EVIDENCE}"
exec > >(tee "${EVIDENCE}/preflight.log") 2>&1

echo "KDE Frameworks Tier 1 dependency provider preflight"
echo "Hosted Ubuntu checks are non-authoritative; real package builds remain required."

. /etc/os-release
if [[ "${VERSION_ID}" != "26.04" ]]; then
    echo "Expected Ubuntu 26.04, got ${PRETTY_NAME}" >&2
    exit 1
fi

{
    printf 'PRETTY_NAME=%s\n' "${PRETTY_NAME}"
    printf 'VERSION_ID=%s\n' "${VERSION_ID}"
    uname -a
} > "${EVIDENCE}/host.txt"
sha256sum "${MANIFEST}" > "${EVIDENCE}/manifest.sha256"

python3 - "${MANIFEST}" "${EVIDENCE}" <<'PY'
import json
import pathlib
import sys

m = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
out = pathlib.Path(sys.argv[2])
registry = m["requirements"]
qt_map = m["qt_provider_packages"]

mandatory = {"cmake", "g++", "ninja-build", "pkgconf", "python3"}
recommended = set()
optional = set()
alternatives = []

def add(target, packages):
    target.update(p for p in packages if p)

for node_id, node in m["nodes"].items():
    qt = node.get("qt", {})
    for category in ("required", "default_enabled", "provider_implied"):
        for component in qt.get(category, []):
            add(mandatory, qt_map[component])
    for component in qt.get("recommended", []):
        add(recommended, qt_map[component])
    for category in ("optional", "test"):
        for component in qt.get(category, []):
            add(optional, qt_map[component])

    ext = node.get("external", {})
    for category in ("required", "default_enabled", "runtime"):
        for key in ext.get(category, []):
            add(mandatory, registry[key]["packages"])
    for key in ext.get("recommended", []):
        add(recommended, registry[key]["packages"])
    for key in ext.get("optional", []):
        add(optional, registry[key]["packages"])
    for group in ext.get("required_any_of", []):
        for key in group["choices"]:
            for package in registry[key]["packages"]:
                alternatives.append((f"{node_id}:{group['name']}", key, package))

recommended -= mandatory
optional -= mandatory
optional -= recommended

(out / "mandatory-packages.txt").write_text("".join(f"{p}\n" for p in sorted(mandatory)), encoding="utf-8")
(out / "recommended-packages.txt").write_text("".join(f"{p}\n" for p in sorted(recommended)), encoding="utf-8")
(out / "optional-packages.txt").write_text("".join(f"{p}\n" for p in sorted(optional)), encoding="utf-8")
(out / "alternative-packages.tsv").write_text(
    "".join(f"{group}\t{key}\t{package}\n" for group, key, package in sorted(alternatives)),
    encoding="utf-8",
)
PY

sudo apt-get update

candidate_for() {
    local package="$1"
    apt-cache policy "${package}" | awk '/Candidate:/ {print $2; exit}'
}

: > "${EVIDENCE}/apt-candidates.tsv"
declare -a mandatory_packages=()
while IFS= read -r package; do
    [[ -n "${package}" ]] || continue
    candidate="$(candidate_for "${package}")"
    printf 'mandatory\t%s\t%s\n' "${package}" "${candidate:-<missing>}" | tee -a "${EVIDENCE}/apt-candidates.tsv"
    if [[ -z "${candidate}" || "${candidate}" == "(none)" ]]; then
        echo "Mandatory provider package has no Resolute candidate: ${package}" >&2
        exit 1
    fi
    mandatory_packages+=("${package}")
done < "${EVIDENCE}/mandatory-packages.txt"

declare -a recommended_available=()
while IFS= read -r package; do
    [[ -n "${package}" ]] || continue
    candidate="$(candidate_for "${package}")"
    printf 'recommended\t%s\t%s\n' "${package}" "${candidate:-<missing>}" | tee -a "${EVIDENCE}/apt-candidates.tsv"
    if [[ -n "${candidate}" && "${candidate}" != "(none)" ]]; then
        recommended_available+=("${package}")
    fi
done < "${EVIDENCE}/recommended-packages.txt"

while IFS= read -r package; do
    [[ -n "${package}" ]] || continue
    candidate="$(candidate_for "${package}")"
    printf 'optional\t%s\t%s\n' "${package}" "${candidate:-<missing>}" | tee -a "${EVIDENCE}/apt-candidates.tsv"
done < "${EVIDENCE}/optional-packages.txt"

declare -A alternative_group_has_candidate=()
declare -a alternative_available=()
while IFS=$'\t' read -r group key package; do
    [[ -n "${package}" ]] || continue
    candidate="$(candidate_for "${package}")"
    printf 'alternative:%s:%s\t%s\t%s\n' "${group}" "${key}" "${package}" "${candidate:-<missing>}" | tee -a "${EVIDENCE}/apt-candidates.tsv"
    if [[ -n "${candidate}" && "${candidate}" != "(none)" ]]; then
        alternative_group_has_candidate["${group}"]=1
        alternative_available+=("${package}")
    fi
done < "${EVIDENCE}/alternative-packages.tsv"

while IFS= read -r group; do
    [[ -n "${group}" ]] || continue
    if [[ -z "${alternative_group_has_candidate[$group]:-}" ]]; then
        echo "No Resolute candidate satisfies required alternative group: ${group}" >&2
        exit 1
    fi
done < <(cut -f1 "${EVIDENCE}/alternative-packages.tsv" | sort -u)

mapfile -t install_packages < <(
    printf '%s\n' \
        "${mandatory_packages[@]}" \
        "${recommended_available[@]}" \
        "${alternative_available[@]}" |
        sed '/^$/d' |
        sort -u
)

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${install_packages[@]}"

{
    printf 'package\tinstalled-version\n'
    for package in "${install_packages[@]}"; do
        printf '%s\t%s\n' "${package}" "$(dpkg-query -W -f='${Version}' "${package}")"
    done
} > "${EVIDENCE}/installed-versions.tsv"

check_pkg_min() {
    local package="$1"
    local minimum="$2"
    local version
    version="$(dpkg-query -W -f='${Version}' "${package}")"
    if ! dpkg --compare-versions "${version}" ge "${minimum}"; then
        echo "${package} ${version} does not satisfy >= ${minimum}" >&2
        return 1
    fi
    printf '%s\t%s\t>=\t%s\tPASS\n' "${package}" "${version}" "${minimum}" >> "${EVIDENCE}/version-checks.tsv"
}

: > "${EVIDENCE}/version-checks.tsv"
check_pkg_min bison 3.3.2
check_pkg_min python3-dev 3.9
check_pkg_min libical-dev 3.0
check_pkg_min libwayland-dev 1.9
check_pkg_min wayland-protocols 1.46
check_pkg_min plasma-wayland-protocols 1.15.0
check_pkg_min libmm-glib-dev 1.0
check_pkg_min libnm-dev 1.4.0
check_pkg_min libzxing-dev 1.4.0

upstream_numeric_version() {
    local package="$1"
    dpkg-query -W -f='${Version}' "${package}" |
        sed -E 's/^[0-9]+://' |
        grep -oE '[0-9]+\.[0-9]+\.[0-9]+' |
        head -1
}

qt_base_upstream="$(upstream_numeric_version qt6-base-dev)"
if [[ "${qt_base_upstream}" != "6.10.2" ]]; then
    echo "Expected selected Ubuntu Qt provider upstream version 6.10.2, got ${qt_base_upstream}" >&2
    exit 1
fi
printf 'qt6-base-dev\t%s\t==\t6.10.2\tPASS\n' "${qt_base_upstream}" >> "${EVIDENCE}/version-checks.tsv"

for package in qt6-base-private-dev qt6-declarative-dev qt6-svg-dev qt6-wayland-dev qt6-shadertools-dev qt6-multimedia-dev qt6-tools-dev libshiboken6-dev libpyside6-dev; do
    if dpkg-query -W -f='${Status}' "${package}" 2>/dev/null | grep -q 'ok installed'; then
        upstream="$(upstream_numeric_version "${package}")"
        if [[ "${upstream}" != "${qt_base_upstream}" ]]; then
            echo "Qt/PySide provider skew: ${package}=${upstream}, qt6-base-dev=${qt_base_upstream}" >&2
            exit 1
        fi
        printf '%s\t%s\t==\t%s\tPASS\n' "${package}" "${upstream}" "${qt_base_upstream}" >> "${EVIDENCE}/version-checks.tsv"
    fi
done

: > "${EVIDENCE}/pkg-config-versions.tsv"
for module in libical libnm gio-2.0 libzstd wayland-client mm-glib; do
    version="$(pkg-config --modversion "${module}")"
    printf '%s\t%s\n' "${module}" "${version}" >> "${EVIDENCE}/pkg-config-versions.tsv"
done

if dpkg-query -W -f='${Status}' hspell 2>/dev/null | grep -q 'ok installed'; then
    test -f /usr/include/hspell.h
    if ! find /usr/lib -type f \( -name 'libhspell.a' -o -name 'libhspell.so' -o -name 'libhspell.so.*' \) -print -quit | grep -q .; then
        echo "hspell is installed but no libhspell library was found" >&2
        exit 1
    fi
    {
        echo "/usr/include/hspell.h"
        find /usr/lib -type f \( -name 'libhspell.a' -o -name 'libhspell.so' -o -name 'libhspell.so.*' \) -print
    } > "${EVIDENCE}/hspell-development-surface.txt"
fi

probe_dir="$(mktemp -d)"
trap 'rm -rf "${probe_dir}"' EXIT
cat > "${probe_dir}/CMakeLists.txt" <<'CMAKE'
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXTier1DependencyProbe LANGUAGES CXX)
find_package(Qt6 6.9 REQUIRED COMPONENTS Core Gui Qml Quick Multimedia)
find_package(Qt6GuiPrivate 6.9 REQUIRED NO_MODULE)
find_package(Qt6WaylandClient 6.9 REQUIRED CONFIG)
find_package(Qt6UiPlugin REQUIRED CONFIG)
find_package(Shiboken6 REQUIRED CONFIG)
find_package(PySide6 REQUIRED CONFIG)
find_package(ZXing 1.4.0 REQUIRED CONFIG)
find_package(PlasmaWaylandProtocols 1.15.0 REQUIRED CONFIG)
CMAKE

cmake -S "${probe_dir}" -B "${probe_dir}/build" -GNinja -DCMAKE_BUILD_TYPE=Release \
    2>&1 | tee "${EVIDENCE}/cmake-sensitive-provider-probe.log"

{
    echo "status=PASS"
    echo "authority=kde-upstream"
    echo "provider_candidate=ubuntu-resolute"
    echo "provider_check=hosted-non-authoritative"
    echo "ubuntu_version=${VERSION_ID}"
    echo "qt_upstream=${qt_base_upstream}"
    echo "framework_package_build_certification=pending"
} > "${EVIDENCE}/summary.env"

echo "KDE Frameworks Tier 1 dependency provider preflight: PASS"
