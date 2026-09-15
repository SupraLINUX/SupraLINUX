# ModemManager provider correction — 2026-09-15

Status: **validated**

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

## Validation

Hosted Ubuntu 26.04 dependency-preflight evidence:

- run `35012023822`;
- job `104526071758`;
- commit `48fd01bfa7b254b5e5c8447b3d609f76a91f786f`;
- artifact `10414525047`;
- artifact SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`;
- result: PASS.

The run installed `modemmanager-dev`, checked its minimum provider version and required `pkg-config --atleast-version=1.0 ModemManager` to succeed.

This is provider-availability evidence only. It does not promote ModemManagerQt. Final package evidence still requires the clean Batch 5 `sbuild` attempt.
