# KDE Frameworks 6.30 Tier 1 — package batch 1

Status: **prepared; actual package attempts pending CI**  
Last reviewed: **2026-09-12**

## Scope

The first generalized package batch contains three independent KDE Frameworks 6.30 Tier 1 nodes:

- `kcodecs`;
- `kdbusaddons`;
- `threadweaver`.

All three depend on the retained Extra CMake Modules PASS root and do not depend on another KDE Framework. They can therefore be attempted independently and in parallel. Their source-manifest/DAG states remain `pending` until the real builds run.

## Authority and provider split

KDE upstream `v6.30.0` defines the sources, CMake requirements, Qt minimums, defaults and test structure. Ubuntu Resolute supplies compatible Qt/general build dependencies and is the application/package compatibility target. Ubuntu/Debian `debian/` trees are reference inputs only.

The batch consumes two retained PASS inputs:

- ECM `6.30.0-0supralinux3`: run `34694951158`, artifact `10298635300`, `.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- generic Tier 1 packaging trees: run `34708030450`, artifact `10301938362`, artifact SHA-256 `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`.

## KCodecs

KDE 6.30 root CMake blob `a4844477467d5c7b47875f837fa6db0b22550397` requires ECM 6.30 and Qt Core >=6.9. `ECMPoQmTools` is active for the shipped translations and resolves Qt6 LinguistTools, so Resolute `qt6-tools-dev` is retained for that actual upstream path.

Historical distro Build-Depends `gperf`, Doxygen and `libxkbcommon-dev` are not copied because they are not requirements of the selected KDE 6.30 build/default path.

Source SHA-256: `a42c79ff3237b73789d1c63cdfd848c0d59671ce5e93723a2efa128f00cb3450`.

Ubuntu compatibility symbols baseline: `libkf6codecs6.symbols`, SHA-256 `8dfcf6c469195a45e5f1d038a42cf1f223fe12d00c3ee1e3aa5125142935e1a3`.

The established binary split is retained: data, runtime, development and documentation compatibility packages.

## KDBusAddons

KDE 6.30 root CMake blob `26cde2148db4d86adeea0f4bda597f0f9e610816` requires Qt DBus >=6.9. With the selected Qt 6.10 provider and upstream `WITH_X11=ON`, KDE explicitly requires `Qt6GuiPrivate`; Resolute therefore supplies `qt6-base-private-dev`. Translation processing uses Qt LinguistTools, supplied through `qt6-tools-dev`.

Tests are executed in a private D-Bus session with `dbus-run-session`. No Xvfb wrapper is introduced because the selected upstream tests are D-Bus/QCore based. Doxygen and `libxkbcommon-dev` are not copied merely from distro reference packaging.

Source SHA-256: `063ef80460f76d86dc4b033ef04b65b69ba82ee0de410440fe609465e7f5a997`.

Ubuntu compatibility symbols baseline: `libkf6dbusaddons6.symbols`, SHA-256 `03b48faa6b7c5b400f3a165c38c4c5e7e7fc454a0b099ef1ad776b3809851683`.

The established binary split is retained: command-line tool, data, runtime, development and documentation compatibility packages.

## ThreadWeaver

KDE 6.30 root CMake blob `309efd1d962d925a71610ea65fed2a1007ef055d` requires Qt Core >=6.9. The always-built examples additionally request Qt Widgets/Test; these are part of Qt Base. No translation-tools, Doxygen or `libxkbcommon-dev` dependency is added.

Source SHA-256: `e5400968a41820393e76190ab5dbb276c09513263d1b185d64b40f82dcd9b457`.

Ubuntu and Debian currently share the same retained symbols file for `libkf6threadweaver6`; the Ubuntu-targeted baseline SHA-256 is `a7403ee234e24d20f20502ed4a07b13ef265ec285cd5fb2b44709dfea39907b7`.

The established binary split is retained: runtime, development and documentation compatibility packages.

## Shared package gate

`scripts/run-kde-tier1-package-preflight.sh` is the generalized hosted preflight. Per matrix node it:

1. validates campaign state and retained ECM/reference inputs;
2. downloads and verifies the exact KDE 6.30 source;
3. injects the exact retained Ubuntu symbols baseline;
4. assembles a `3.0 (quilt)` source package with `dpkg-source -b`, without running package build helpers on the host;
5. creates a fresh Resolute buildd root and runs `sbuild --chroot-mode=unshare`;
6. proves ECM `6.30.0-0supralinux3` in `.buildinfo`;
7. injects the retained Debian sid copyright metadata as a packaging baseline, adds SupraLINUX's packaging attribution, and runs `reuse lint` against upstream SPDX/REUSE metadata during package tests;
8. validates the expected Debian binary split, Architecture/Multi-Arch and absence of unreviewed Provides/Breaks/Replaces/Conflicts;
9. verifies library SONAME;
10. retains `.deb`, `.changes`, `.buildinfo`, `.dsc`, source/rootfs hashes and logs;
11. runs `lintian --fail-on error`;
12. builds and executes a package-specific downstream CMake consumer.

KDBusAddons' consumer also runs inside `dbus-run-session`.

## QDoc boundary

All three upstream trees use `ECMGenerateQDoc`. QDoc generation is exposed through explicit targets rather than the normal default build. The historical distro `BUILD_QCH=ON` switch is therefore not copied. Existing `*-doc` names are retained as compatibility packages, matching the policy already proven with Attica, until a common Frameworks QDoc policy is selected.

## CI/DAG semantics

The workflow uses a three-node matrix with `fail-fast: false` and `max-parallel: 3`. A failure in one node must not prevent independent nodes from being attempted.

Event-delta scope is evaluated per node. A change to one package directory rebuilds only that node; changes to shared campaign/runner/workflow inputs rebuild all three. Documentation and later evidence/state-only manifest changes do not rebuild package artifacts.

Before the workflow actually runs:

- `kcodecs`: `prepared-pending-build`;
- `kdbusaddons`: `prepared-pending-build`;
- `threadweaver`: `prepared-pending-build`.

These are preparation states, not PASS. After the real CI attempts, each node will independently become PASS or FAIL based on its own evidence. No node is BLOCKED because their only KDE predecessor, ECM, is PASS.
