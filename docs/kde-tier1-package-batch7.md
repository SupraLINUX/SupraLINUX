# KDE Frameworks 6.30 Tier 1 — package Batch 7

Status: **2 retained PASS / KWidgetsAddons `-7` remediation prepared**

Canonical Tier 1 remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED** until retained package evidence is promoted into the canonical manifests. Historical FAIL attempts remain immutable evidence and are not BLOCKED.

## Selection

Batch 7 contains three independently attempted nodes:

- KCalendarCore;
- KCoreAddons;
- KWidgetsAddons.

KGuiAddons remains deferred to a local-predecessor package lane. Its public `KImageCache` development header consumes KCoreAddons, so that lane must use the retained SupraLINUX KCoreAddons PASS rather than an Ubuntu KDE package.

## Common package path

All three retain KDE Frameworks 6.30.0 source and upstream feature defaults. Python bindings and tests stay enabled; KWidgetsAddons also retains the Designer plugin. The clean build path uses retained ECM `6.30.0-0supralinux3`, Clang/LLVM for Shiboken ApiExtractor, `python3-build` plus `python3-setuptools`, strict Lintian, exact local-package installation/APT closure, Python import and C++ consumer smoke.

Ubuntu Resolute is the provider for those dependencies. KDE/ECM remains authority for the build flow and enabled features.

## KCalendarCore — retained PASS

Real attempts:

1. `-1` FAIL: Clang built-ins unavailable to Shiboken ApiExtractor.
2. `-2` FAIL: `setuptools.build_meta` unavailable to ECM's wheel build.
3. `-3` FAIL: **507/507 tests PASS**, then 18 translation catalogs were unowned by a binary package.
4. `-4` FAIL: package split succeeded, then Lintian rejected 18 new public symbols with Debian-revision minima.
5. `-5` PASS: run `35130213945`, job `104909057699`, commit `9b9e313176d5154656274976872feb7be34ab126`, artifact `10461386548`, artifact SHA-256 `6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6`, rootfs SHA-256 `eb3e6bfe65b142c1308d8a1892e00c6bd57028126147ac09376778dec60692f6`.

The retained PASS has **507/507 tests PASS**, Lintian error gate PASS, Python import PASS, APT closure PASS, consumer smoke PASS and SONAME `libKF6CalendarCore.so.6`. The reviewed ABI overlay records 10 APIs at upstream minimum 6.29.0 and 8 at 6.30.0.

## KCoreAddons — retained PASS

Real attempts:

1. `-1` FAIL: Clang built-ins unavailable.
2. `-2` FAIL: `setuptools.build_meta` unavailable.
3. `-3` FAIL: **34/34 tests PASS**, then Lintian rejected two KAboutData symbols whose generated minima included the Debian revision.
4. `-4` PASS: run `35122522242`, job `104883541991`, commit `ea465e7f78ee621f6456246e7ba76e0a89e46d78`, artifact `10457958023`, artifact SHA-256 `c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`, rootfs SHA-256 `dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794`.

The retained PASS has **34/34 tests PASS**, Lintian error gate PASS, Python import PASS, APT closure PASS, consumer smoke PASS and SONAME `libKF6CoreAddons.so.6`.

## KWidgetsAddons attempt history

1. `-1` FAIL: Clang built-ins unavailable.
2. `-2` FAIL: `setuptools.build_meta` unavailable.
3. `-3` FAIL: 25/27 tests; the two gesture suites required real window activation.
4. `-4` FAIL: Openbox fixed both gestures, but the global WM fixture changed the geometry-sensitive `KSqueezedTextLabel` result; 26/27.
5. `-5` FAIL: the 27 = 25 + 2 fixture partition was validated, but bare Xvfb was 24/25 because the font environment was no longer deterministic.
6. `-6` FAIL after **27/27 upstream tests PASS**: package/Lintian issues only.

### Revision `-6` evidence

Run `35138333353`, job `104936243365`, commit `6b3a8b9f408c5fff4bceec81ac9ffb3e47a4dbd3`:

- artifact `10464950275`;
- artifact SHA-256 `6ec80fbeeeecb7f119bea3bc2aa2ddaee665b27f52d636119260abccdcbfd883`;
- rootfs SHA-256 `08c582c7f007c64c03c476739a554527b6d8edda4905c8515f0f3224e7810ceb`;
- generic `sans-serif` resolved to **DejaVu Sans**;
- 25/25 non-gesture suites PASS under bare Xvfb;
- 2/2 gesture suites PASS under verified Openbox;
- total **27/27 tests PASS**;
- binary build completed;
- Lintian failed afterwards.

The font choice is a SupraLINUX CI fixture, not a KDE requirement. No upstream test is disabled, expected-failed or patched.

Lintian exposed two independent packaging defects:

1. `libkf6widgetsaddons-dev` contains `kwidgetsaddons6widgets.so`; `dh_shlibdeps` generated `${shlibs:Depends}`, but the package stanza did not consume it, producing a missing libc dependency.
2. Six symbols were generated with `6.30.0-0supralinux6` as minimum. Upstream comparison shows five KDE APIs are already present in Frameworks 6.29.0 but absent from 6.28.0; `_ZSt19piecewise_construct` is a libstdc++ implementation/toolchain export.

## KWidgetsAddons revision `-7`

Revision `6.30.0-0supralinux7` changes packaging only:

- retain the already-green 27-test DejaVu/Xvfb/Openbox fixture unchanged;
- add `${shlibs:Depends}` to `libkf6widgetsaddons-dev` so the Designer plugin's runtime dependency set is represented;
- append a reviewed ABI overlay before `dh_makeshlibs`;
- set the five KDE symbols to upstream minimum **6.29.0**;
- classify `_ZSt19piecewise_construct@Base` as `(optional=toolchain)` at upstream minimum **6.30.0**, matching the previously validated SupraLINUX policy for this compiler/libstdc++ export.

KDE source, Python bindings, Designer plugin, runtime functionality and upstream tests are unchanged. A package PASS is not claimed until the real `-7` run completes Lintian, Python import, exact APT closure, SONAME and consumer-smoke gates.

## CI semantics

The schema-2 Batch 7 selector ignores evidence/documentation-only changes and rebuilds only a node whose build contract changes. KCalendarCore and KCoreAddons retained PASS artifacts must remain scope-skipped while the KWidgetsAddons package tree changes.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
