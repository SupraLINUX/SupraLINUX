# Qt provider certification

Status: **Ubuntu provider preflight pending; final certification pending**  
Last reviewed: **2026-09-11**

## Authority and provider

KDE upstream is the authority for the Qt version required by the desktop. Ubuntu may provide that Qt only when it satisfies the KDE-selected requirement and SupraLINUX compatibility gates.

Current KDE schedule evidence:

- Plasma 6.7 selects Qt **6.10**: <https://community.kde.org/Schedules/Plasma_6>
- Current selected Plasma: **6.7.5**.

Current Ubuntu Resolute candidate evidence includes:

- `qt6-base-dev` 6.10.2+dfsg-7: <https://packages.ubuntu.com/resolute/amd64/qt6-base-dev>
- `qt6-declarative-dev` 6.10.2+dfsg-3: <https://packages.ubuntu.com/resolute/amd64/qt6-declarative-dev>
- `qt6-declarative-private-dev` 6.10.2+dfsg-3: <https://packages.ubuntu.com/resolute/amd64/qt6-declarative-private-dev>
- `qt6-wayland-dev` 6.10.2-4: <https://packages.ubuntu.com/qt6-wayland-dev>
- `qt6-wayland-private-dev` 6.10.2-4: <https://packages.ubuntu.com/resolute/amd64/qt6-wayland-private-dev>
- `qt6-svg-dev` 6.10.2-2: <https://packages.ubuntu.com/resolute/qt6-svg-dev>
- `qt6-shadertools-dev` 6.10.2-1: <https://packages.ubuntu.com/search?keywords=qt6-shadertools-dev>
- `qt6-tools-dev` 6.10.2-1: <https://packages.ubuntu.com/resolute/qt6-tools-dev>
- `qt6-5compat-dev` 6.10.2-1: <https://packages.ubuntu.com/search?keywords=qt6-5compat-dev&suite=resolute>

Qt documents patch releases as maintenance releases and states its source/binary compatibility promises for Qt 6, subject to the documented exceptions and same-toolchain/configuration requirements: <https://doc.qt.io/qt-6.10/qt-releases.html>.

These facts make Ubuntu Qt 6.10.2 a plausible provider. They do **not** certify it.

## Provider preflight scope

The initial provider preflight deliberately targets the Qt closure needed as a baseline for Plasma/Frameworks packaging, not every optional Qt module that might appear later in KDE Gear.

Packages under the baseline gate:

- `qt6-base-dev`, `qt6-base-private-dev`;
- `qt6-declarative-dev`, `qt6-declarative-private-dev`;
- `qt6-svg-dev`;
- `qt6-wayland-dev`, `qt6-wayland-private-dev`;
- `qt6-shadertools-dev`;
- `qt6-tools-dev`, `qt6-tools-dev-tools`;
- `qt6-5compat-dev`.

`scripts/run-qt-provider-preflight.sh` requires:

1. Ubuntu 26.04 runtime;
2. manifest-required Qt series `6.10`;
3. all baseline packages installed and available from APT;
4. every baseline package resolving to one coherent upstream Qt patch release, currently expected to be 6.10.x;
5. `qtpaths6` runtime version matching that package baseline;
6. CMake discovery of public targets for Core, Gui, Widgets, DBus, Network, Concurrent, QML, Quick, QuickControls2, SVG, ShaderTools, Core5Compat and WaylandClient;
7. CMake discovery of private Gui, QML, Quick and WaylandClient targets;
8. successful compilation and execution of a probe linked against that closure;
9. retained package, CMake, runtime and result evidence.

The hosted lane is non-authoritative and its result is explicitly named **provider preflight**, not certification.

## Why Gear is not predeclared here

KDE Gear is a collection of applications with a wider and package-specific Qt dependency surface. SupraLINUX will extend the Qt module closure from the actual upstream dependency DAG for each selected application. Optional modules such as Multimedia, WebSockets, WebEngine, Positioning or Speech are added only when upstream KDE packages require them.

This preserves the project rule: KDE decides what KDE needs; Ubuntu does not define the desktop dependency set.

## Final certification requirements

Ubuntu Qt may move from `reuse-candidate`/`pending` to certified only after evidence establishes at minimum:

1. provider preflight PASS on current Ubuntu 26.04;
2. selected KDE Frameworks/Plasma sources configure and build against that provider;
3. private-API consumers required by the selected KDE stack build successfully;
4. package metadata/ABI contracts remain compatible with the SupraLINUX/Ubuntu package model;
5. KDE runtime/session smoke tests pass;
6. compatibility tests for relevant Ubuntu and third-party Qt applications pass;
7. real evidence is recorded in the manifest/status documentation.

Until then, `qt.certification.status` remains `pending`.
