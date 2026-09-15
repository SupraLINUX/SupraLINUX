# ModemManager provider correction — 2026-09-15

Status: **provider mapping correction pending CI validation**

## Authority

KDE Frameworks 6.30.0 remains the authority for the dependency requirement.

`ModemManagerQt` upstream calls `find_package(ModemManager 1.0 REQUIRED)`. Its bundled `FindModemManager.cmake` resolves the pkg-config module `ModemManager`.

Ubuntu 26.04 (Resolute) is only the provider. Resolute exposes that development surface through `modemmanager-dev`; the retained Ubuntu and Debian packaging-reference trees also use `modemmanager-dev` for KF6 ModemManagerQt.

## Correction

The previous SupraLINUX Tier 1 dependency manifest mapped the upstream `modemmanager` requirement to `libmm-glib-dev` and the hosted preflight checked the `mm-glib` pkg-config module. That checked a related ModemManager client library, but not the dependency interface requested by KDE upstream.

The provider mapping is corrected to:

- requirement: `ModemManager >= 1.0`;
- Ubuntu provider: `modemmanager-dev`;
- pkg-config probe: `ModemManager`;
- KDE authority: unchanged;
- package/DAG state effect: none.

This is a provider-metadata/preflight correction. It does not promote any KDE node and does not change the selected KDE or Qt versions.

## Gate

The correction is accepted only after the hosted Ubuntu 26.04 Tier 1 dependency preflight passes with `modemmanager-dev` installed and `pkg-config --atleast-version=1.0 ModemManager` succeeding.

Final package certification remains the real clean `sbuild` package build; hosted provider preflight is non-authoritative.
