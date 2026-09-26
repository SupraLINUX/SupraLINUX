# KDE Tier 3 — KIO Round 18 Qt SVG provider contract audit

Status: **definition pending audit**.

Round 17 proved a reversible environmental cause: with `qt6-svg-plugins 6.10.2-2` installed both historical KIO icon tests pass, removing only that package restores both empty-`QIcon::name()` failures, and reinstalling it restores PASS. Round 18 assigns the dependency to the correct contract before any KIO `-8` package is created.

## Authority and provider

KDE remains authority over the desktop dependency model. Qt defines the SVG icon engine mechanism. Ubuntu Resolute is the provider for the selected Qt 6.10.2 packages.

KIO 6.30 itself does not directly request Qt6Svg in its top-level CMake contract; it consumes KF6IconThemes. KIconThemes 6.30 explicitly requires Qt6Svg and links `Qt6::Svg` privately. Breeze Icons supplies the SVG icon payload but does not own the Qt plugin loading contract.

Qt documents that QIcon uses icon engines and that QtSvg provides the vector/SVG icon engine. The Qt plugin documentation classifies QIconEnginePlugin under `iconengines`.

Upstream references:
- https://github.com/KDE/kio/tree/v6.30.0
- https://github.com/KDE/kiconthemes/tree/v6.30.0
- https://github.com/KDE/breeze-icons/tree/v6.30.0
- https://doc.qt.io/qt-6/qicon.html
- https://doc.qt.io/qt-6/plugins-howto.html

## Resolute contract to verify

The audit runs on Ubuntu 26.04 and records current APT metadata plus the downloaded `qt6-svg-plugins` payload.

Required facts:

1. `qt6-svg-plugins` is the package containing `libqsvgicon.so` and `libqsvg.so`.
2. `qt6-svg-dev` provides the development contract and does **not** hard-depend on `qt6-svg-plugins`.
3. `libqt6gui6` recommends `qt6-svg-plugins`, making the SVG engine part of the normal Qt GUI runtime recommendation rather than a KIO-specific runtime dependency.
4. `libkf6iconthemes6` depends on `libqt6svg6` but does not hard-depend on the plugin package.
5. `kf6-breeze-icon-theme` does not own the Qt SVG plugin dependency.

This preserves Ubuntu application compatibility instead of adding a new hard runtime edge to KIO, KIconThemes or Breeze.

## SupraLINUX precedent and expected decision

SupraLINUX already uses `qt6-svg-plugins <!nocheck>` for the KIconThemes upstream test environment because Resolute splits the QtSvg plugin payload from `qt6-svg-dev`.

If the Round 18 audit confirms the expected Resolute metadata, KIO adopts the same class of contract:

`Build-Depends: qt6-svg-plugins <!nocheck>`

Classification: `upstream-test-environment-provider`.

The relation belongs only to the KIO build/test closure. No new runtime binary dependency is added.

## Safety

This definition is non-promoting. It does not modify KIO source, does not change the canonical DAG, does not allocate `6.30.0-0supralinux8`, and does not build a Debian package.

Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**. KIO remains `6.30.0-0supralinux7` FAIL and downstream-ineligible.

Next gate: `tier3-round18-kio-qt-svg-provider-contract-audit-evidence`.
