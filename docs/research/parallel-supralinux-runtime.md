# Research note: parallel SupraLINUX desktop runtime

Status: **exploratory / not adopted**  
Date: **2026-09-26**  
Decision effect: **none**. This document records a possible future architecture. It does not change the current SupraLINUX packaging model, canonical KDE/Qt policy, active KIO work, or release plan.

## Why this exists

SupraLINUX currently has a favorable alignment:

- Ubuntu 26.04 provides Qt 6.10.
- Plasma 6.7.x can use Qt 6.10.
- SupraLINUX can therefore keep Ubuntu's public Qt runtime while packaging the KDE stack independently.

The risk appears when a future stable KDE release requires a newer Qt than Ubuntu 26.04 provides. Plasma 6.8 is expected to require the Qt 6.11 line, while the Ubuntu 26.04 base is currently on Qt 6.10. Replacing Ubuntu's Qt globally would increase compatibility risk for Ubuntu and third-party applications.

The explored alternative is to preserve Ubuntu's public runtime and give the SupraLINUX desktop its own private runtime.

## Core idea

Use **two process-local desktop runtimes**, not two operating systems and not a translation layer.

```text
Ubuntu applications                     SupraLINUX desktop/apps
        |                                        |
        v                                        v
Ubuntu public runtime                    Supra private runtime
Qt from Ubuntu                           Qt required by KDE
Ubuntu-compatible KF6                    Supra KDE Frameworks
Ubuntu Qt/KDE plugins                    Supra Qt/KDE plugins
        |                                        |
        +--------------------+-------------------+
                             v
                        Ubuntu 26.04
        kernel / glibc / Mesa / systemd / drivers /
             PipeWire / D-Bus / Wayland / APT/dpkg
```

Each process must use exactly one coherent Qt/KF runtime. The design must prevent accidental in-process mixing.

## Important refinement

Isolating **only Qt** is insufficient.

If SupraLINUX installed a new Qt privately but exposed newer KDE Frameworks globally in the normal Ubuntu library paths, Ubuntu KDE applications could still resolve against the Supra libraries and indirectly enter the Supra Qt runtime.

A robust implementation would therefore isolate the stack from Qt upward:

- Qt required by KDE;
- KDE Frameworks built against that Qt;
- Qt plugins;
- KDE plugins;
- QML modules;
- Plasma;
- KWin;
- SupraLINUX KDE applications that are part of the desktop stack.

Ubuntu keeps its public Qt/KF packages available for Ubuntu applications.

## Possible filesystem model

Exact paths are not decided. A candidate layout is:

```text
/usr/lib/x86_64-linux-gnu/
    Ubuntu Qt/KF public ABI

/usr/lib/supralinux/runtime/
    lib/
    plugins/
    qml/
    libexec/
    translations/
```

Supra executables would locate their private libraries through per-binary mechanisms such as ELF RUNPATH/RPATH and Qt runtime configuration. Global `LD_LIBRARY_PATH`, `QT_PLUGIN_PATH`, or global QML path overrides must be avoided because applications launched from Plasma could inherit them and load the wrong runtime.

## Why it is technically possible

The investigated components support the necessary primitives:

1. **ELF dynamic loader** resolves shared libraries per process and supports RUNPATH/RPATH-based lookup.
2. **Qt** supports installation under arbitrary prefixes and `qt.conf` can redirect Libraries, Plugins, QmlImports, LibraryExecutables and related paths.
3. Qt explicitly warns against globally exporting `QT_PLUGIN_PATH` when multiple Qt installations coexist.
4. **CMake** supports installation RPATH configuration.
5. **KDE development tooling** routinely builds Frameworks/Plasma into a separate prefix and can run a complete Plasma session from that prefix.
6. Debian packaging policy allows private shared objects under package/private subdirectories of `/usr/lib`.
7. Flatpak's KDE runtime is not the same architecture, but it demonstrates the broader model of Qt + KDE Frameworks runtimes coexisting with the host.

There is therefore no fundamental technical barrier to parallel runtimes.

## Packaging model under this option

The important APT rule would be:

> The private Supra runtime must not pretend to satisfy Ubuntu's public Qt/KF dependencies.

Conceptually:

```text
libqt6core6t64                  -> Ubuntu
libkf6coreaddons6               -> Ubuntu

supralinux-qt6-core             -> Supra private runtime
supralinux-kf6-coreaddons       -> Supra private runtime
supralinux-plasma-workspace     -> depends on Supra private runtime
```

A private `supralinux-qt6-core` should not simply `Provides: libqt6core6t64` if it is not intended to satisfy Ubuntu applications.

This preserves normal APT resolution:

```text
apt install ubuntu-application
  -> Ubuntu Qt/KF dependencies

install Supra desktop
  -> Supra private Qt/KF dependencies
```

## Strict plugin and QML separation

Plugins are one of the highest-risk areas.

Qt platform plugins, image/icon plugins, styles, QML binary modules and other in-process components must match the Qt runtime of the process.

Required rule:

```text
Ubuntu Qt -> Ubuntu-compatible plugins/QML
Supra Qt  -> Supra-built plugins/QML
```

No global plugin path may cause cross-loading.

This is especially important for QPA/Wayland integration and Plasma, where QML and binary plugins are pervasive.

## Compatibility bridge

A private desktop runtime still has to make Ubuntu Qt applications look and behave native under Plasma.

A future compatibility bridge may need Ubuntu-runtime builds of selected integration components, for example:

- Breeze Qt style;
- Plasma/Qt platform theme integration;
- file-dialog/platform integration where applicable;
- portals and settings propagation;
- icon/theme discovery;
- desktop settings over D-Bus/XDG interfaces.

Some integration components might need to be built twice:

```text
component
  |- build for Ubuntu Qt
  `- build for Supra Qt
```

The exact set is unknown and requires a PoC.

## Compatibility boundary

The intended compatibility promise would be primarily **application/process level**.

Separate Ubuntu applications can coexist with a Supra Plasma session because communication normally occurs through stable process boundaries such as:

- Wayland;
- D-Bus;
- PipeWire;
- XDG Desktop Portals;
- sockets/IPC.

Binary plugins loaded **inside** Plasma/KWin/Supra applications are different: they belong to the Supra runtime and must be built for it. An Ubuntu binary plugin cannot be assumed compatible in-process merely because the host is Ubuntu.

## Resource cost

Parallel runtimes do increase resource usage.

### RAM

Two different Qt/KF builds cannot share all of the same read-only library pages. If both runtimes are actively used, both sets of libraries can reside in memory.

However, libraries are still shared between processes using the **same** runtime. Five Supra applications do not imply five private copies of Qt's code pages.

The cost must be evaluated for generic low-end hardware, not around a developer workstation. The minimum evaluation should explicitly include **4 GiB RAM** systems.

Required measurements:

- idle Plasma Supra;
- Plasma + one Supra Qt/KDE application;
- Plasma + one Ubuntu Qt application;
- Plasma + one Ubuntu KDE application;
- mixed multi-application workload;
- PSS, RSS, private/shared pages and page cache.

No fixed RAM overhead is accepted yet; earlier conversational estimates were only rough hypotheses and must not become design evidence.

### CPU

There is no translation layer. Each process executes directly against its selected runtime, so sustained CPU overhead should be small. Possible differences are mainly startup/library loading, plugin initialization and separate caches. This must still be measured.

### Disk

Disk usage will increase because portions of Qt, Frameworks, plugins and QML are duplicated. This is expected to be a more visible cost than CPU overhead.

## Complexity assessment

Qualitative estimate, to be replaced by measured engineering evidence:

| Architecture | Initial complexity | Ubuntu compatibility risk |
| --- | --- | --- |
| Reuse Ubuntu Qt while sufficient | low | low |
| Replace Ubuntu Qt globally | medium | medium/high |
| Private Qt but public Supra KF | high | high/structurally incomplete |
| Private Qt + KF + Plasma runtime | high | low/medium if isolation holds |
| Private runtime + complete compatibility bridge | very high | potentially lowest |

The parallel-runtime option has substantial initial engineering cost. Its value is that the cost becomes a controlled platform boundary rather than repeatedly replacing Ubuntu's public Qt each time KDE raises its requirement.

## Main risks

1. Accidental library/plugin/QML cross-loading.
2. Incorrect RUNPATH or runtime discovery.
3. Ubuntu KDE applications resolving Supra libraries.
4. Duplicate integration components and maintenance burden.
5. Security maintenance for the private Qt line.
6. Increased build/CI time and artifact storage.
7. Increased RAM/disk usage on low-end hardware.
8. Third-party in-process Plasma/KWin plugins requiring Supra-specific builds.
9. Packaging complexity and possible file collisions.
10. Need to keep runtime boundaries correct across every KDE/Qt update.

## Potential advantages

1. KDE stable can move independently of Ubuntu's Qt cadence.
2. Ubuntu's public Qt remains untouched for Ubuntu applications.
3. Ubuntu security updates to its Qt do not mutate the Supra desktop runtime.
4. Supra Qt updates do not automatically replace libraries used by Ubuntu applications.
5. The compatibility boundary is explicit and testable.
6. Future Qt transitions become repeatable runtime upgrades rather than global ABI replacements.

## Proposed PoC before any adoption

Do **not** change the canonical distro architecture yet.

Build an isolated PoC on Ubuntu 26.04:

### Stage 1 — library isolation

- keep Ubuntu Qt 6.10 intact;
- install/build a newer Qt in a private Supra prefix;
- build 2–3 representative KDE Frameworks against it;
- build one small Supra Qt/KDE application;
- prove with `ldd`/`readelf` that the Ubuntu app resolves Ubuntu Qt while the Supra app resolves Supra Qt.

### Stage 2 — runtime paths

Validate:

- ELF RUNPATH;
- Qt plugin paths;
- QML import paths;
- QPA/Wayland plugin isolation;
- no global `LD_LIBRARY_PATH`;
- no global `QT_PLUGIN_PATH`.

### Stage 3 — desktop integration

Test:

- Wayland;
- D-Bus;
- XDG portals;
- Breeze/style integration;
- file dialogs;
- icon themes;
- settings propagation.

### Stage 4 — larger KDE sample

Add representative Frameworks and applications, then KWin and Plasma only after the runtime boundary is proven.

### Stage 5 — Ubuntu compatibility matrix

Test representative packages from Ubuntu:

- GTK applications;
- pure Qt applications;
- KDE applications using Ubuntu Frameworks;
- Electron applications;
- third-party `.deb` software.

Verify both APT installability and runtime behavior.

### Stage 6 — low-end performance

At minimum evaluate a 4 GiB RAM profile:

- boot/idle;
- mixed Ubuntu/Supra applications;
- PSS/RSS/private/shared memory;
- cold/warm startup;
- CPU;
- disk footprint.

## Adoption gate

This architecture should be considered only if the PoC proves all of the following:

1. Ubuntu Qt/KF remain installable and operational without replacement.
2. Supra desktop processes consistently resolve only the private runtime.
3. No global environment variable contaminates child Ubuntu applications.
4. Plugin/QML separation is deterministic.
5. Ubuntu application compatibility is materially better than a global Qt replacement.
6. Low-end RAM/CPU/disk impact is acceptable.
7. The packaging/CI burden is sustainable.
8. Security updates for private Qt can be handled reliably.

If those conditions are not met, the option remains rejected or experimental.

## Current decision

**No architecture change.**

The canonical SupraLINUX project continues with the current model and current KIO work. This note exists so that the Qt 6.11+ problem is not rediscovered later and so that a future architectural decision can start from documented evidence rather than memory.

## References consulted during discussion

- Qt: Building Qt from source / installation prefix: https://doc.qt.io/qt-6/linux-building.html
- Qt: Configure options: https://doc.qt.io/qt-6/configure-options.html
- Qt: Using `qt.conf`: https://doc.qt.io/qt-6/qt-conf.html
- Qt: Plugin deployment and version/path rules: https://doc.qt.io/qt-6/deployment-plugins.html
- Qt: QML import paths: https://doc.qt.io/qt-6/qtqml-syntax-imports.html
- Qt: QPA: https://doc.qt.io/qt-6/qpa.html
- CMake: `INSTALL_RPATH`: https://cmake.org/cmake/help/latest/prop_tgt/INSTALL_RPATH.html
- KDE developer documentation: building with KDE Builder / separate prefixes: https://develop.kde.org/docs/getting-started/building/
- KDE Frameworks policies: https://community.kde.org/Frameworks/Policies
- Debian Policy, shared libraries/private objects: https://www.debian.org/doc/debian-policy/ch-sharedlibs.html
- Flatpak available runtimes: https://docs.flatpak.org/en/latest/available-runtimes.html
- KDE neon FAQ: https://neon.kde.org/faq
