# KDE Frameworks 6.30 Tier 1 — package Batch 7

Status: **technical closure 3/3 PASS; canonical promotion is the next atomic state update**

The canonical Tier 1 manifest still records **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED** at this commit. Batch 7 itself is now technically closed: KCalendarCore, KCoreAddons and KWidgetsAddons each have a retained real package PASS and are downstream-eligible. Historical FAIL attempts remain immutable evidence and are not BLOCKED.

## Selection

Batch 7 contains three independently attempted nodes:

- KCalendarCore;
- KCoreAddons;
- KWidgetsAddons.

KGuiAddons is the next local-predecessor lane. Its public `KImageCache` development surface consumes KCoreAddons, so that lane must use the retained SupraLINUX KCoreAddons PASS rather than an Ubuntu KDE package.

## Common package path

All three retain KDE Frameworks 6.30.0 source and upstream feature defaults. Python bindings and tests stay enabled; KWidgetsAddons also retains the Designer plugin. The clean build path uses retained ECM `6.30.0-0supralinux3`, Clang/LLVM for Shiboken ApiExtractor, `python3-build` plus `python3-setuptools`, strict Lintian, exact local-package installation/APT closure, Python import and C++ consumer smoke.

Ubuntu Resolute is provider for those dependencies. KDE/ECM remains authority for the build flow and enabled features.

## KCalendarCore `6.30.0-0supralinux5` — PASS

Real attempts:

1. `-1` FAIL: Clang built-ins unavailable to Shiboken ApiExtractor.
2. `-2` FAIL: `setuptools.build_meta` unavailable to ECM's wheel build.
3. `-3` FAIL: **507/507 tests PASS**, then 18 translation catalogs were unowned by a binary package.
4. `-4` FAIL: package split succeeded, then Lintian rejected 18 new public symbols with Debian-revision minima.
5. `-5` PASS: run `35130213945`, job `104909057699`, commit `9b9e313176d5154656274976872feb7be34ab126`, artifact `10461386548`, artifact SHA-256 `6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6`, rootfs SHA-256 `eb3e6bfe65b142c1308d8a1892e00c6bd57028126147ac09376778dec60692f6`.

Final gates: **507/507 tests PASS**, Lintian PASS, Python import PASS, APT closure PASS, consumer smoke PASS and SONAME `libKF6CalendarCore.so.6`.

## KCoreAddons `6.30.0-0supralinux4` — PASS

Real attempts:

1. `-1` FAIL: Clang built-ins unavailable.
2. `-2` FAIL: `setuptools.build_meta` unavailable.
3. `-3` FAIL: **34/34 tests PASS**, then Lintian rejected two KAboutData symbols with Debian-revision minima.
4. `-4` PASS: run `35122522242`, job `104883541991`, commit `ea465e7f78ee621f6456246e7ba76e0a89e46d78`, artifact `10457958023`, artifact SHA-256 `c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`, rootfs SHA-256 `dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794`.

Final gates: **34/34 tests PASS**, Lintian PASS, Python import PASS, APT closure PASS, consumer smoke PASS and SONAME `libKF6CoreAddons.so.6`.

## KWidgetsAddons attempt history

1. `-1` FAIL: Clang built-ins unavailable.
2. `-2` FAIL: `setuptools.build_meta` unavailable.
3. `-3` FAIL: 25/27 tests; the two gesture suites required real window activation.
4. `-4` FAIL: Openbox fixed both gestures, but the global WM fixture changed the geometry-sensitive `KSqueezedTextLabel` result; 26/27.
5. `-5` FAIL: the 27 = 25 + 2 partition was validated, but bare Xvfb was 24/25 because the font environment was not deterministic.
6. `-6` FAIL after **27/27 upstream tests PASS**: package/Lintian issues only.
7. `-7` PASS: package remediation validated without changing KDE source or dropping tests.

### Revision `-6` evidence

Run `35138333353`, job `104936243365`, commit `6b3a8b9f408c5fff4bceec81ac9ffb3e47a4dbd3`:

- artifact `10464950275`, SHA-256 `6ec80fbeeeecb7f119bea3bc2aa2ddaee665b27f52d636119260abccdcbfd883`;
- rootfs SHA-256 `08c582c7f007c64c03c476739a554527b6d8edda4905c8515f0f3224e7810ceb`;
- `sans-serif` resolved to **DejaVu Sans**;
- 25/25 non-gesture suites PASS under bare Xvfb;
- 2/2 gesture suites PASS under verified Openbox;
- **27/27 tests PASS**;
- binary build completed;
- Lintian then rejected missing `${shlibs:Depends}` on the Designer-plugin-bearing `-dev` package and six generated symbol minima.

The font choice is a SupraLINUX CI fixture, not a KDE requirement. No upstream test is disabled, expected-failed or patched.

### Revision `-7` final PASS

Run `35145607543`, job `104960718770`, commit `00be0b419b9f897cf7b7dbc8ca396e20916ead9b`:

- artifact `10467164025`;
- artifact SHA-256 `f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e`;
- rootfs SHA-256 `d381a2d238103d21dbce47af60377b48ca77b385ab8598d135d30386ac17cf12`;
- 25/25 non-gesture suites PASS under bare Xvfb;
- 2/2 gesture suites PASS under verified Openbox;
- total **27/27 upstream tests PASS**;
- `${shlibs:Depends}` consumed correctly by `libkf6widgetsaddons-dev`;
- reviewed ABI overlay applied before `dh_makeshlibs`;
- Lintian error gate PASS;
- Python module `KWidgetsAddons` import PASS;
- exact local-package APT closure and `apt-get check` PASS;
- C++ consumer smoke PASS;
- SONAME `libKF6WidgetsAddons.so.6`;
- downstream eligible.

The five KDE symbols introduced after the 6.28 baseline use upstream minimum **6.29.0**; `_ZSt19piecewise_construct@Base` remains `(optional=toolchain)` at upstream minimum **6.30.0**. No Lintian suppression was introduced.

## CI semantics

The schema-2 Batch 7 selector rebuilds only nodes whose package-consumed inputs changed. The `-7` commit rebuilt KWidgetsAddons only; KCalendarCore and KCoreAddons were scope-skipped and retained their prior PASS artifacts. The subsequent documentation-only commit scope-skipped all three nodes.

## Next state transition

Batch 7 is technically 3/3 PASS. The next commit must atomically promote the three retained PASS results into `manifests/kde-frameworks-tier1.json` and `manifests/kde-dag.json`, update canonical counts to **21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED**, and move KGuiAddons from dependency-wait to its local-predecessor lane using the retained KCoreAddons artifacts.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
