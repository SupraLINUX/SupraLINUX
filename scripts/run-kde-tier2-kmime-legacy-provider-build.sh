#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/manifests/kde-tier2-kmime-legacy-provider.json"
WORK="$ROOT/.work/kde-tier2-kmime-legacy-provider-build"
OUT="$WORK/out"
EVIDENCE="$ROOT/evidence/kde-tier2-kmime-legacy-provider-build"

MATERIALIZATION_DIR="${MATERIALIZATION_DIR:-}"
ROOTFS_ARTIFACT_DIR="${ROOTFS_ARTIFACT_DIR:-}"
ECM_ARTIFACT_DIR="${ECM_ARTIFACT_DIR:-}"
KCODECS_ARTIFACT_DIR="${KCODECS_ARTIFACT_DIR:-}"
FRAMEWORK_ARTIFACT_DIR="${FRAMEWORK_ARTIFACT_DIR:-}"

STATE=FAIL
STAGE=initialization
PACKAGE_ATTEMPTED=false

rm -rf "$WORK" "$EVIDENCE"
mkdir -p "$OUT" "$EVIDENCE"
exec > >(tee "$EVIDENCE/pipeline.log") 2>&1

write_result(){
  local rc=$?
  python3 - "$EVIDENCE/result.json" "$STATE" "$rc" "$STAGE" "$PACKAGE_ATTEMPTED" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
d={}
if p.exists():
    try:
        d=json.loads(p.read_text())
    except Exception:
        d={}
d.update({
    "result":sys.argv[2],
    "exit_code":int(sys.argv[3]),
    "stage":sys.argv[4],
    "package_attempted":sys.argv[5]=="true",
    "package_state_effect":"none" if sys.argv[2]!="PASS" else "PASS-candidate-only",
})
p.write_text(json.dumps(d,indent=2)+"\n")
PY
}
trap write_result EXIT

for dir in "$MATERIALIZATION_DIR" "$ROOTFS_ARTIFACT_DIR" "$ECM_ARTIFACT_DIR" "$KCODECS_ARTIFACT_DIR" "$FRAMEWORK_ARTIFACT_DIR"; do
  [[ -d "$dir" ]] || { echo "missing input directory: $dir" >&2; exit 1; }
done

readarray -t cfg < <(python3 - "$MANIFEST" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
p=m["supralinux_package"]
a=m["adaptation"]
for value in (
    p["package_version"],
    p["runtime_package"],
    p["runtime_soname"],
    p["versioned_provides"],
    p["development_package"],
    p["development_cmake_package"],
    p["development_cmake_target"],
    a["new_dependency"],
):
    print(value)
PY
)

PACKAGE_VERSION="${cfg[0]}"
RUNTIME_PACKAGE="${cfg[1]}"
RUNTIME_SONAME="${cfg[2]}"
DEV_PACKAGE="${cfg[4]}"
DEV_CMAKE_PACKAGE="${cfg[5]}"
DEV_CMAKE_TARGET="${cfg[6]}"
DATA_DEP="${cfg[7]}"

DSC="$(find "$MATERIALIZATION_DIR" -type f -name "kmime_${PACKAGE_VERSION}.dsc" -print -quit)"
ORIG="$(find "$MATERIALIZATION_DIR" -type f -name 'kmime_25.12.3.orig.tar.*' ! -name '*.asc' -print -quit)"
DEBIAN_TAR="$(find "$MATERIALIZATION_DIR" -type f -name "kmime_${PACKAGE_VERSION}.debian.tar.*" -print -quit)"
[[ -n "$DSC" && -s "$DSC" && -n "$ORIG" && -n "$DEBIAN_TAR" ]]

. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 26.04 ]]

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  binutils cmake devscripts dpkg-dev g++ lintian ninja-build pkg-config python3 sbuild uidmap xz-utils

if ! grep -q "^$USER:" /etc/subuid; then
  sudo usermod --add-subuids 100000-165535 "$USER"
fi
if ! grep -q "^$USER:" /etc/subgid; then
  sudo usermod --add-subgids 100000-165535 "$USER"
fi
unshare --user --map-auto true

CHROOT_TARBALL="$(find "$ROOTFS_ARTIFACT_DIR" -type f -name resolute-amd64.tar -print -quit)"
ROOTFS_SHA_FILE="$(find "$ROOTFS_ARTIFACT_DIR" -type f -name rootfs.sha256 -print -quit)"
[[ -n "$CHROOT_TARBALL" && -n "$ROOTFS_SHA_FILE" ]]

expected_rootfs="$(awk '{print $1}' "$ROOTFS_SHA_FILE")"
actual_rootfs="$(sha256sum "$CHROOT_TARBALL" | awk '{print $1}')"
[[ "$expected_rootfs" == "$actual_rootfs" ]]
printf '%s\n' "$actual_rootfs" > "$EVIDENCE/rootfs.sha256"

mkdir -p "$HOME/.cache/sbuild"
ln -sfn "$CHROOT_TARBALL" "$HOME/.cache/sbuild/resolute-amd64.tar"

mapfile -t ECM_DEBS < <(find "$ECM_ARTIFACT_DIR" -type f -name '*.deb' -print | sort)
mapfile -t KCODECS_DEBS < <(find "$KCODECS_ARTIFACT_DIR" -type f -name '*.deb' -print | sort)
mapfile -t FRAMEWORK_DEBS < <(find "$FRAMEWORK_ARTIFACT_DIR" -type f -name 'libkf6mime*.deb' -print | sort)

(( ${#ECM_DEBS[@]} > 0 ))
(( ${#KCODECS_DEBS[@]} > 0 ))
(( ${#FRAMEWORK_DEBS[@]} == 3 ))

STAGE=sbuild
PACKAGE_ATTEMPTED=true
extra=()
for deb in "${ECM_DEBS[@]}" "${KCODECS_DEBS[@]}"; do
  extra+=(--extra-package="$deb")
done

sbuild --verbose --chroot-mode=unshare --dist=resolute --arch=amd64 --no-arch-all \
  "${extra[@]}" --build-dir="$OUT" "$DSC" |& tee "$EVIDENCE/sbuild.log"

mapfile -t DEBS < <(find "$OUT" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "$OUT" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "$OUT" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "$OUT" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)

(( ${#DEBS[@]} == 2 ))
(( ${#CHANGES[@]} == 1 ))
(( ${#BUILDINFO[@]} == 1 ))

STAGE=artifact-contract
python3 - "$MANIFEST" "$OUT" "$EVIDENCE" <<'PY'
import json,subprocess,sys
from pathlib import Path

m=json.load(open(sys.argv[1]))
out=Path(sys.argv[2])
ev=Path(sys.argv[3])
p=m["supralinux_package"]
a=m["adaptation"]

built={}
for deb in out.glob("*.deb"):
    pkg=subprocess.check_output(["dpkg-deb","-f",str(deb),"Package"],text=True).strip()
    ver=subprocess.check_output(["dpkg-deb","-f",str(deb),"Version"],text=True).strip()
    if ver!=p["package_version"]:
        raise SystemExit(f"{pkg}: version {ver} != {p['package_version']}")
    if pkg in built:
        raise SystemExit(f"duplicate package {pkg}")
    built[pkg]=str(deb)

if set(built)!=set(p["expected_binary_packages"]):
    raise SystemExit(f"binary set mismatch: expected={p['expected_binary_packages']} actual={sorted(built)}")
if "libkmime-data" in built:
    raise SystemExit("legacy data package must not be produced in arch-any provider build")

runtime=built[p["runtime_package"]]
depends=subprocess.check_output(["dpkg-deb","-f",runtime,"Depends"],text=True).strip()
provides=subprocess.check_output(["dpkg-deb","-f",runtime,"Provides"],text=True).strip()
multi=subprocess.check_output(["dpkg-deb","-f",runtime,"Multi-Arch"],text=True).strip()

if a["new_dependency"] not in depends:
    raise SystemExit(f"runtime data alternative missing: {depends}")
if p["versioned_provides"] not in provides:
    raise SystemExit(f"versioned Provides missing: {provides}")
if multi!=p["multi_arch"]:
    raise SystemExit(f"Multi-Arch mismatch: {multi}")

(ev/"built-debs.json").write_text(json.dumps(built,indent=2)+"\n")
(ev/"runtime-control.json").write_text(json.dumps({
    "Depends":depends,
    "Provides":provides,
    "Multi-Arch":multi,
},indent=2)+"\n")
print("legacy provider binary/control contract: PASS")
PY

RUNTIME_DEB="$(python3 - "$EVIDENCE/built-debs.json" "$RUNTIME_PACKAGE" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))[sys.argv[2]])
PY
)"

RUNTIME_ROOT="$WORK/runtime-root"
mkdir -p "$RUNTIME_ROOT"
dpkg-deb -x "$RUNTIME_DEB" "$RUNTIME_ROOT"
LIB="$(find "$RUNTIME_ROOT" -type f -name "$RUNTIME_SONAME.*" -print -quit)"
[[ -n "$LIB" ]]
readelf -d "$LIB" | tee "$EVIDENCE/runtime-readelf.txt"
readelf -d "$LIB" | grep -F "Library soname: [$RUNTIME_SONAME]"

STAGE=artifact-capture
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "$DSC" "$ORIG" "$DEBIAN_TAR" > "$EVIDENCE/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "$DSC" "$ORIG" "$DEBIAN_TAR" "$EVIDENCE/"

STAGE=lintian
lintian --fail-on error "$DSC" "${CHANGES[0]}" |& tee "$EVIDENCE/lintian.log"

STAGE=coinstallation
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  "${KCODECS_DEBS[@]}" "${FRAMEWORK_DEBS[@]}" "${DEBS[@]}" |& tee "$EVIDENCE/coinstall.log"
sudo apt-get check |& tee "$EVIDENCE/apt-check.log"

if dpkg-query -W -f='${Status}\n' libkmime-data 2>/dev/null | grep -q 'install ok installed'; then
  echo "stock legacy libkmime-data must not be installed" >&2
  exit 1
fi

[[ "$(dpkg-query -W -f='${Version}' "$RUNTIME_PACKAGE")" == "$PACKAGE_VERSION" ]]
[[ "$(dpkg-query -W -f='${Version}' "$DEV_PACKAGE")" == "$PACKAGE_VERSION" ]]
[[ "$(dpkg-query -W -f='${Version}' libkf6mime6)" == "6.30.0-0supralinux1" ]]

dpkg -L "$RUNTIME_PACKAGE" | grep -E '/libKPim6Mime\.so\.6($|\.)' | tee "$EVIDENCE/legacy-runtime-paths.txt"
dpkg -L libkf6mime6 | grep -E '/libKF6Mime\.so\.6($|\.)' | tee "$EVIDENCE/framework-runtime-paths.txt"

STAGE=dual-consumer-smoke
for family in legacy framework; do
  dir="$WORK/consumer-$family"
  mkdir -p "$dir"
  cat > "$dir/main.cpp" <<'CPP'
#include <KMime/Message>
int main() {
    KMime::Message message;
    (void)message;
    return 0;
}
CPP
done

cat > "$WORK/consumer-legacy/CMakeLists.txt" <<EOF
cmake_minimum_required(VERSION 3.29)
project(LegacyMimeConsumer LANGUAGES CXX)
find_package($DEV_CMAKE_PACKAGE REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE $DEV_CMAKE_TARGET)
EOF

cat > "$WORK/consumer-framework/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.29)
project(FrameworkMimeConsumer LANGUAGES CXX)
find_package(KF6Mime 6.30 REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE KF6::Mime)
EOF

for family in legacy framework; do
  dir="$WORK/consumer-$family"
  cmake -S "$dir" -B "$dir/build" -GNinja -DCMAKE_BUILD_TYPE=Release |& tee "$EVIDENCE/$family-consumer-configure.log"
  cmake --build "$dir/build" --verbose |& tee "$EVIDENCE/$family-consumer-build.log"
  "$dir/build/consumer"
  readelf -d "$dir/build/consumer" > "$EVIDENCE/$family-consumer-readelf.txt"
done

grep -F 'Shared library: [libKPim6Mime.so.6]' "$EVIDENCE/legacy-consumer-readelf.txt"
grep -F 'Shared library: [libKF6Mime.so.6]' "$EVIDENCE/framework-consumer-readelf.txt"

STAGE=pass-evidence
python3 - "$EVIDENCE/result.json" "$PACKAGE_VERSION" "$RUNTIME_SONAME" "$DATA_DEP" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
d={
    "result":"PASS",
    "package_attempted":True,
    "package_state_effect":"PASS-candidate-only",
    "package_version":sys.argv[2],
    "runtime_soname":sys.argv[3],
    "data_dependency":sys.argv[4],
    "clean_sbuild":"PASS",
    "lintian_errors":"PASS",
    "coinstallation":"PASS",
    "apt_check":"PASS",
    "legacy_consumer":"PASS",
    "framework_consumer":"PASS",
    "legacy_data_installed":False,
}
p.write_text(json.dumps(d,indent=2)+"\n")
print(json.dumps(d,indent=2))
PY

STATE=PASS
STAGE=complete
echo "KMime legacy compatibility-provider clean build: PASS"
