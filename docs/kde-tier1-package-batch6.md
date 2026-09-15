# KDE Frameworks 6.30 Tier 1 — package Batch 6

Status: **remediation prepared — second builds pending**
Last reviewed: **2026-09-15**

## Selection

Batch 6 contains **KWindowSystem** and **Solid**. Both are independent Tier 1 frameworks whose only KDE predecessor is the retained Extra CMake Modules PASS and each has one primary shared-library ABI/symbols baseline, so the existing runner can validate them without a multi-library architecture change.

Canonical Tier 1 remains **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** until real package attempts pass and a separate closure commit promotes them.

## KDE authority and Linux defaults

KDE Frameworks 6.30.0 remains authority. Ubuntu Resolute supplies providers only.

KWindowSystem 6.30.0 keeps upstream Linux defaults enabled: QML bindings, X11 and Wayland. Its package profile therefore includes Qt GuiPrivate for the selected Qt 6.10 series, Qt QML, Qt Wayland Client, X11/XCB, Wayland Protocols >= 1.46 and Plasma Wayland Protocols. The test package inputs include Xvfb and Weston so the X11 and headless-Wayland upstream tests can execute rather than disabling the suite.

Solid 6.30.0 keeps DBus, udev, libmount and the standard Linux backends enabled. Flex and Bison are required. IMobileDevice and PList are upstream-optional; the Ubuntu providers are included so the optional iOS backend is built when upstream detection succeeds. No `UDEV_DISABLED` or distro-only HAL override is introduced.

The established common Frameworks profile still builds with `BUILD_QCH=OFF`; Debian-family `-doc` binary names are retained as compatibility stubs and no QCH payload is claimed.

## Provenance

Official KDE source hashes:

- KWindowSystem: `639a501b877446b19905399d27e2be2b6ebb0bb481abe3209dc4d535a12e12ca`; root CMake blob `e8317948e1df27330ceddf45bf418aa2a02bde5b`.
- Solid: `bdbfdc9f26b87e12b951097825af2956f2dee3f14c701d780277b69701f2c74e`; root CMake blob `65681c1db745cd52a547659f1b778fa42bb3cb52`.

Retained Debian 6.28 packaging references remain technical references only: run `34708030450`, artifact `10301938362`. The per-node keyring bundles differ byte-for-byte but both contain the Frameworks 6.30 signer fingerprint `90A968ACA84537CC27B99EAF2C8DF587A6D4AAC1`; the campaign records each bundle hash separately rather than pretending they are identical.

Dependency-provider preflight remains run `35012023822`, job `104526071758`, artifact `10414525047`, SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`. This is provider-availability evidence only and is not package PASS evidence.

## Initial real attempt and remediation

Run `35034742520` attempted both nodes from preparation commit `74fe53f698ad108958b9409029e8d51cc61c0956`. Both are real package FAIL results in the Batch 6 attempt ledger; neither is BLOCKED. Canonical Tier 1 remains unpromoted at **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED**.

- KWindowSystem `6.30.0-0supralinux1`: job `104601176595`, artifact `10422598658`, artifact SHA-256 `cc38c90312b6e73b2dc338712c391af96664cdd2a342d16f2a163bce67c1be1b`. CMake configured and compilation started, then `src/kx11extras.cpp` failed on missing `xcb/xfixes.h`. The retained Debian 6.28 and Ubuntu 6.24 packaging trees both declare `libxcb-xfixes0-dev`; SupraLINUX had omitted it. Revision `-2` adds only that Build-Depends and leaves KDE source plus X11/Wayland/QML defaults unchanged.
- Solid `6.30.0-0supralinux1`: job `104601176254`, artifact `10422873422`, artifact SHA-256 `135a63a6855bed690e6bbdbf67dc924b5dbd8bd304f0a78c84920927772e15a0`. The package built and passed `5/5` tests. Lintian then rejected `_ZSt19piecewise_construct@Base` because `dpkg-gensymbols` assigned the current Debian revision as its minimum version. The retained Ubuntu symbols reference already records this libstdc++/toolchain export at `6.4.0` on `!armhf !riscv64`. Revision `-2` keeps the Debian 6.28 public ABI baseline and applies one hash-locked optional-toolchain delta: `(optional=toolchain|arch=!armhf !riscv64)_ZSt19piecewise_construct@Base 6.4.0`. `python3:any` is declared because `debian/rules` executes the transform.

The Solid transform SHA-256 is `35fff06320bf6a5ec8db8ba5f4e062e2242f692446f3d19304602ba7147c0b70`; the reviewed transformed symbols SHA-256 is `8614c45e8a902f3c3011b8cec65680ab5152314c798a71ebec108fc50fb547d0`. Neither remediation changes KDE source, Qt selection, authority boundaries or the canonical DAG.

## Deferred surfaces

KConfig, KI18n and Sonnet remain deferred because the present package runner assumes one primary ABI symbols file. KCoreAddons, KGuiAddons, KWidgetsAddons and KCalendarCore are not made easier by silently switching off upstream Python bindings. Kirigami/KQuickCharts and other multi-library/QML-heavy surfaces stay outside this lane until their packaging contracts are explicitly designed.

## Promotion rule

Preparation is not PASS. Neither node is downstream-eligible yet. A node becomes PASS only after a real clean Resolute sbuild, tests, Lintian error gate, binary/package contracts, SONAME check and consumer smoke all pass and evidence is retained. Canonical Tier1/DAG state changes only in a subsequent closure commit.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
