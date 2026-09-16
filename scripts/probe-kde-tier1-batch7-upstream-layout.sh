#!/usr/bin/env bash
set -euo pipefail

WORK="${RUNNER_TEMP:-/tmp}/supralinux-batch7-upstream-probe"
OUT="$PWD/batch7-upstream-probe"
rm -rf "$WORK" "$OUT"
mkdir -p "$WORK" "$OUT"

fetch_verify() {
  local name="$1" url="$2" sha="$3"
  curl -fsSL --retry 4 --retry-delay 2 "$url" -o "$WORK/$name.tar.xz"
  printf '%s  %s\n' "$sha" "$WORK/$name.tar.xz" | sha256sum -c -
  mkdir -p "$WORK/$name"
  tar -xf "$WORK/$name.tar.xz" -C "$WORK/$name" --strip-components=1
  printf '%s\t%s\t%s\n' "$name" "$url" "$sha" >> "$OUT/sources.tsv"
}

fetch_verify "extra-cmake-modules" \
  "https://download.kde.org/stable/frameworks/6.30/extra-cmake-modules-6.30.0.tar.xz" \
  "22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e"

cmake -S "$WORK/extra-cmake-modules" -B "$WORK/ecm-build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$WORK/ecm-prefix" \
  -DBUILD_TESTING=OFF
cmake --build "$WORK/ecm-build"
cmake --install "$WORK/ecm-build"

export CMAKE_PREFIX_PATH="$WORK/ecm-prefix${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"

fetch_verify "kcalendarcore" \
  "https://download.kde.org/stable/frameworks/6.30/kcalendarcore-6.30.0.tar.xz" \
  "e8bf60e398e2f8098a4db7db44c5475d70540ad8f8948a123c8bc109dc4db776"
fetch_verify "kcoreaddons" \
  "https://download.kde.org/stable/frameworks/6.30/kcoreaddons-6.30.0.tar.xz" \
  "cc68fe15beb0fca2036cff8742f468c1345406bf99793fffacbf8f2a3f89bc4b"
fetch_verify "kguiaddons" \
  "https://download.kde.org/stable/frameworks/6.30/kguiaddons-6.30.0.tar.xz" \
  "e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d"
fetch_verify "kwidgetsaddons" \
  "https://download.kde.org/stable/frameworks/6.30/kwidgetsaddons-6.30.0.tar.xz" \
  "ab1333c258678caa7562120a1c03bb71779f7232f1a0e75b9525d921dee3e0a3"

probe_one() {
  local node="$1"
  local src="$WORK/$node"
  local build="$WORK/$node-build"
  local stage="$WORK/$node-stage"
  local log="$OUT/$node-configure.log"
  mkdir -p "$stage"

  cmake -S "$src" -B "$build" -G Ninja \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DBUILD_QCH=OFF \
    -DBUILD_TESTING=ON 2>&1 | tee "$log"

  {
    echo "# $node selected cache"
    grep -E '^(BUILD_PYTHON_BINDINGS|BUILD_DESIGNERPLUGIN|WITH_WAYLAND|BUILD_TESTING|BUILD_QCH|Python3_|Python_|Shiboken6|PySide6|Qt6.*_DIR):' "$build/CMakeCache.txt" || true
  } > "$OUT/$node-cache.txt"

  cmake --build "$build" --parallel 2 2>&1 | tee "$OUT/$node-build.log"
  DESTDIR="$stage" cmake --install "$build" 2>&1 | tee "$OUT/$node-install.log"

  find "$stage" -type f -o -type l | sed "s#^$stage##" | sort > "$OUT/$node-installed-files.txt"
  find "$stage" -type f -name '*.so*' -o -type l -name '*.so*' | sed "s#^$stage##" | sort > "$OUT/$node-shared-objects.txt"
  grep -Ei 'python|pyside|shiboken|site-packages|dist-packages' "$OUT/$node-installed-files.txt" > "$OUT/$node-python-files.txt" || true

  python3 - "$node" "$OUT/$node-shared-objects.txt" "$OUT/$node-python-files.txt" <<'PY' >> "$OUT/summary.tsv"
import sys
node, so_path, py_path = sys.argv[1:]
so = [x.strip() for x in open(so_path, encoding='utf-8') if x.strip()]
py = [x.strip() for x in open(py_path, encoding='utf-8') if x.strip()]
print(f"{node}\tshared_objects={len(so)}\tpython_paths={len(py)}")
PY
}

printf 'node\tobserved\n' > "$OUT/summary.tsv"
for node in kcalendarcore kcoreaddons kguiaddons kwidgetsaddons; do
  probe_one "$node"
done

cat "$OUT/summary.tsv"
