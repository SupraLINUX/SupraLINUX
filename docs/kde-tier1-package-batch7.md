# KDE Frameworks 6.30 Tier 1 — package Batch 7

Status: **2 PASS retained / 1 remediation prepared (`KWidgetsAddons -6`)**

Canonical Tier 1 remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED** until KCalendarCore and KCoreAddons are promoted to `manifests/kde-frameworks-tier1.json`.

## Selection

Batch 7 contains three independently attempted nodes:

- KCalendarCore;
- KCoreAddons;
- KWidgetsAddons.

KGuiAddons is deferred to a local-predecessor package lane because its development surface consumes KCoreAddons. It must use the retained SupraLINUX KCoreAddons PASS rather than an Ubuntu KDE substitute.

## Common packaging path

All three preserve KDE 6.30 source and upstream feature defaults:

- `BUILD_PYTHON_BINDINGS=ON`;
- `BUILD_TESTING=ON`;
- KWidgetsAddons additionally keeps `BUILD_DESIGNERPLUGIN=ON`.

The clean build path uses retained ECM `6.30.0-0supralinux3`, the retained Tier 1 packaging reference tree, Clang/LLVM for Shiboken ApiExtractor, `python3-build` plus `python3-setuptools`, strict Lintian, local package installation/APT closure, Python import and C++ consumer smoke.

## KCalendarCore

Real attempts:

1. `-1` FAIL: Clang built-ins unavailable to ApiExtractor.
2. `-2` FAIL: `setuptools.build_meta` unavailable to ECM's isolated-disabled wheel build.
3. `-3` FAIL: 507/507 tests PASS, then `dh_missing` found 18 unowned translation catalogs.
4. `-4` FAIL: translation split and package build succeeded, but Lintian rejected 18 new public symbols with Debian-revision minima.
5. `-5` PASS: run `35130213945`, job `104909057699`, artifact `10461386548`, artifact SHA-256 `6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6`, 507/507 tests PASS, all package gates PASS.

The final ABI overlay records 10 APIs introduced in KDE 6.29.0 and 8 in KDE 6.30.0.

## KCoreAddons

Real attempts:

1. `-1` FAIL: Clang built-ins unavailable to ApiExtractor.
2. `-2` FAIL: `setuptools.build_meta` unavailable.
3. `-3` FAIL: 34/34 tests PASS, then Lintian rejected two KAboutData symbols with the current Debian revision as minimum.
4. `-4` PASS: run `35122522242`, job `104883541991`, artifact `10457958023`, artifact SHA-256 `c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`, 34/34 tests PASS, all package gates PASS.

## KWidgetsAddons

Real attempts:

1. `-1` FAIL: Clang built-ins unavailable.
2. `-2` FAIL: `setuptools.build_meta` unavailable.
3. `-3` FAIL: 25/27 tests PASS; only the two activation-dependent gesture suites failed under bare Xvfb.
4. `-4` FAIL: verified Openbox fixed the gestures, but `KSqueezedTextLabel` failed under the global WM fixture; 26/27 PASS.
5. `-5` FAIL: run `35134670336`, job `104923940192`, artifact `10462188593`, SHA-256 `f5c47f8efbf1ca2172e0578b104e472875f01966b17f33f34eeadf47daef8aa5`. The 27=25+2 partition was correct, but the bare-Xvfb partition was 24/25 because `KSqueezedTextLabel` still failed before Openbox started.

Revision `-6` keeps the 25/2 partition and adds an explicit deterministic font fixture: `fontconfig` + `fonts-dejavu-core`, with a pre-test assertion that generic sans-serif resolves to DejaVu Sans. This is a CI environment contract, not an upstream KDE requirement.

No test is omitted, disabled or patched.

## State semantics

Historical real FAIL attempts remain immutable evidence after later PASS. A retained PASS is downstream-eligible only after all package gates pass. Scope-skipped jobs do not replace retained PASS artifacts and do not create new package results.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
