# KDE Tier 1 global source diagnostic lane

Date: **2026-09-16**

Status: **IMPLEMENTATION READY — first campaign pending policy gate**

## Purpose

The DAG-wide package campaign remains the only path that can promote a KDE node to package `PASS`. However, waiting for every specialized packaging lane before even compiling unrelated upstream sources delays discovery of shared provider, configure, compiler and test failures.

SupraLINUX therefore adds a second, explicitly non-promoting lane for broad failure discovery.

## Result vocabulary

This lane reports only:

- `DIAG_PASS`: exact upstream source configured, compiled, ran its unchanged test suite and installed into a staging root under the diagnostic environment;
- `DIAG_FAIL`: the real diagnostic attempt failed at provider install, configure, build, test or install staging.

These results are **not** package `PASS`, package `FAIL` or DAG `BLOCKED`.

A `DIAG_PASS` does not prove Debian package splits, ABI/symbol policy, Lintian, `.deb` runtime closure, Multi-Arch, `.changes`, `.buildinfo` or downstream eligibility. It therefore cannot change the canonical DAG state.

## Initial discovery set

The first matrix covers the seven currently topologically available Tier 1 nodes whose full package runner lanes are still being implemented:

- KConfig
- KI18n
- Sonnet
- Kirigami
- KQuickCharts
- KUserFeedback
- Prison

The jobs are independent, use `fail-fast: false`, and may run in parallel. Each job retains its own source hash, provider list, CMake cache, configure/build/test/install logs and `result.json`.

KGuiAddons is not included in this initial seven-node diagnostic set because its eventual package validation must consume the retained local KCoreAddons PASS. The diagnostic lane does not substitute Ubuntu KDE packages for that contract.

## Upstream defaults

The diagnostic runner does not disable features to obtain a green result. It asserts the selected KDE 6.30 defaults after CMake configure.

Examples enforced by the manifest include:

- KConfig: GUI, QML and Linux DBus enabled;
- KI18n: QML enabled;
- Sonnet: Widgets and QML enabled, backends required, Designer plugin enabled;
- Kirigami: shared build, Desktop style and Linux DBus enabled; examples and Ubuntu Touch remain at their upstream OFF defaults;
- KQuickCharts: examples remain at the upstream OFF default;
- KUserFeedback: survey expressions, PHP, PHPUnit and documentation enabled; console remains at the upstream OFF default;
- Prison: DMTX, ZXing, Quick and Multimedia enabled.

Sources of authority are the KDE Frameworks 6.30.0 upstream CMake files. Ubuntu Resolute supplies the required build/runtime providers but does not select these features.

## Environment

The runner uses:

- Ubuntu 26.04 hosted runner as non-authoritative diagnostic infrastructure;
- retained SupraLINUX ECM `6.30.0-0supralinux3` with exact SHA-256 verification;
- exact KDE 6.30.0 source tarball SHA-256 from the canonical Tier 1 manifest;
- provider packages declared per diagnostic node;
- serial CTest under Xvfb + Openbox with a real EWMH window-manager readiness check;
- `DESTDIR` install staging after tests.

No test exclusion is allowed by the validator.

## Relationship to package lanes

The workflow is intentionally complementary:

1. source diagnostic discovers failures broadly and early;
2. specialized package lanes produce real Debian package evidence;
3. only package `PASS` artifacts may feed downstream package nodes;
4. fixes discovered diagnostically must still pass the full package gate;
5. after remediation, the global package campaign is repeated.

This keeps the fast global discovery requested for SupraLINUX without weakening package evidence or conflating CI limitations with package results.
