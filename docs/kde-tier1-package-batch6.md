# KDE Frameworks 6.30 Tier 1 — package Batch 6

Status: **Solid PASS — KWindowSystem fourth build pending**
Last reviewed: **2026-09-15**

## Selection

Batch 6 contains **KWindowSystem** and **Solid**. Both are independent Tier 1 frameworks whose only KDE predecessor is the retained Extra CMake Modules PASS and each has one primary shared-library ABI/symbols baseline, so the existing runner can validate them without a multi-library architecture change.

Canonical Tier 1 remains **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** until real package attempts pass and a separate closure commit promotes them.

## KDE authority and Linux defaults

KDE Frameworks 6.30.0 remains authority. Ubuntu Resolute supplies providers only.

KWindowSystem 6.30.0 keeps upstream Linux defaults enabled: QML bindings, X11 and Wayland. Its package profile therefore includes Qt GuiPrivate for the selected Qt 6.10 series, Qt QML, Qt Wayland Client, X11/XCB, Wayland Protocols >= 1.46 and Plasma Wayland Protocols. The test package inputs include Xvfb, OpenBox, x11-utils and Weston so the X11 and headless-Wayland upstream tests can execute rather than disabling the suite. OpenBox is a nocheck-only fixture, not a runtime dependency.

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

## Second real attempt and KWindowSystem test-fixture remediation

Run `35038057329` tested revision `6.30.0-0supralinux2` from commit `ce2853eff3546bb7ad07bf28eedc3b2cab5aed2f`. Repository Policy `35038057338` passed.

- **Solid `-2`: PASS.** Job `104611513122`, artifact `10423914110`, artifact SHA-256 `7cc2b15e2fa627e3cd280395e0ac48bd3658c7328d194958b872713738b97fc0`. All `5/5` upstream CTest suites passed, Lintian's error gate passed, SONAME is `libKF6Solid.so.6`, and the consumer smoke test passed. Solid is eligible for canonical promotion at Batch 6 closure, but the canonical Tier 1 manifest remains unchanged while the batch is open.
- **KWindowSystem `-2`: FAIL.** Job `104611513304`, artifact `10424431374`, artifact SHA-256 `7b47be8422970fd10c1f67ef450f05bcff9f6086f7f188cd5f91bfcf3c082904`. The missing-header problem was resolved and compilation completed. CTest then reported `11/14` suites passing; the failing suites were `kwindowinfox11test`, `kwindowsystemx11test` and `kwindowsystem_threadtest`, all of which exercise window-manager-managed X11 state.

This second KWindowSystem failure is an incomplete test fixture, not a KDE source failure. KDE upstream `v6.30.0` explicitly documents in `autotests/kwindowinfox11test.cpp` that `build.kde.org` uses **OpenBox**, and `kwindowsystemx11test.cpp` states that multiple tests require a running NETWM-compliant window manager. Bare Xvfb supplies an X server but no window manager.

Revision `6.30.0-0supralinux3` therefore kept every upstream test enabled and changed only the test environment: `openbox <!nocheck>` and `x11-utils <!nocheck>` were added, `Xvfb` starts OpenBox, the fixture waits until `_NET_SUPPORTING_WM_CHECK` contains a real window id, and only then runs `dh_auto_test`. No KDE source, production dependency, X11/Wayland/QML feature, Qt choice or canonical DAG state changed.

## Third real attempt and X11 test-serialization remediation

Run `35040999577` tested KWindowSystem `6.30.0-0supralinux3` from commit `0da3238a528893a28e624d89014dc82dea3d8e9d`. Repository Policy `35040999426` passed. Solid correctly scope-skipped because its retained `-2` PASS inputs did not change.

KWindowSystem `-3` is a real FAIL: job `104620609155`, artifact `10425162919`, artifact SHA-256 `58481311a264849cbe78c166fcfd2e174d95bc56e04e32be9cab7efed3a2b9dc`. Compilation completed, OpenBox became ready, the Wayland suite passed, and CTest reached **12/14 suites PASS**. The two remaining failures were:

- `kwindoweffectstest`: `testEffectAvailable(BackgroundContrast)` observed `compositingChangedSpy.count() == 0` instead of `1` while faking the global `_NET_WM_CM_S0` compositor selection.
- `kwindowsystemx11test`: `testActiveWindowChanged()` observed two `activeWindowChanged` signals instead of the single signal upstream expects for its first X11 case.

The build log shows `dh_auto_test` inherited `parallel=4`, so independent CTest executables ran concurrently against the same Xvfb/OpenBox root-window and NETWM state. Upstream `autotests/CMakeLists.txt` does not give each suite a separate X server or mark these X11 suites as isolated, and `kwindowsystemx11test.cpp` explicitly requires `testActiveWindowChanged()` to be the first case because later X11 state would invalidate it. This is a test-fixture concurrency defect in the package execution environment, not evidence for changing KDE source.

Revision `6.30.0-0supralinux4` therefore preserves the same Xvfb/OpenBox fixture and all upstream tests, but invokes only `dh_auto_test` with debhelper's supported `--no-parallel` control. Compilation remains free to use normal parallelism. No tests are excluded and no production feature or runtime dependency changes.

## Deferred surfaces

KConfig, KI18n and Sonnet remain deferred because the present package runner assumes one primary ABI symbols file. KCoreAddons, KGuiAddons, KWidgetsAddons and KCalendarCore are not made easier by silently switching off upstream Python bindings. Kirigami/KQuickCharts and other multi-library/QML-heavy surfaces stay outside this lane until their packaging contracts are explicitly designed.

## Promotion rule

The open batch is not canonically closed. Solid has real PASS evidence and is package-attempt downstream-eligible; KWindowSystem remains remediation-pending-build. Canonical Tier1/DAG remains unchanged until a separate closure commit. A node becomes PASS only after a real clean Resolute sbuild, tests, Lintian error gate, binary/package contracts, SONAME check and consumer smoke all pass and evidence is retained. Canonical Tier1/DAG state changes only in a subsequent closure commit.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
