# KDE Tier 1 global source diagnostic lane

Date: **2026-09-16**

Status: **FIRST CAMPAIGN COMPLETE — 5 DIAG_PASS / 2 DIAG_FAIL; targeted remediation prepared**

## Purpose and semantics

The package DAG remains the only path that may promote a KDE node to package `PASS`. The source-diagnostic lane exists to discover provider/configure/build/test failures across independent nodes before every specialized Debian packaging lane exists.

It reports only `DIAG_PASS` and `DIAG_FAIL`. Neither value changes the canonical package DAG. In particular, `DIAG_PASS` does not prove Debian package splits, symbols/ABI policy, Lintian, Multi-Arch, `.deb` runtime closure, `.changes`, `.buildinfo` or downstream eligibility.

## First campaign

Run `35131119792` at commit `1f5fcdc68e1bbb2a7cc3f93dc20687aadc15cec0` attempted all seven nodes independently with `fail-fast: false`.

| Node | Result | Evidence / classification |
| --- | --- | --- |
| KConfig | `DIAG_FAIL` | job `104912090505`, artifact `10461886238`, SHA-256 `231cfd286876889997590b67fcfe640f34510cc46ae7fc0a3a96e72af5124142`; configure failed because `Qt6::CorePrivate` referenced a missing versioned private-header path while `qt6-base-private-dev` was absent |
| KI18n | `DIAG_FAIL` | job `104912090737`, artifact `10461686975`, SHA-256 `9edeb81c9ecdb92d07691a1b333169858c13348a25bb92c7e5a8bb3dcbec8aaf`; build completed, then 3/17 locale-data tests lacked French `iso-codes` translations |
| Sonnet | `DIAG_PASS` | job `104912091007`, artifact `10460838096`, SHA-256 `18e1c8ed50063b17d0f4063b511c4c82badf68c702768e2d01f9fb72a7b86855` |
| Kirigami | `DIAG_PASS` | job `104912090447`, artifact `10461303414`, SHA-256 `a69730c8d09d8acce2ee103c98a0d85faf819cbbe1bedb6fdac1a77364ddc7ba` |
| KQuickCharts | `DIAG_PASS` | job `104912090786`, artifact `10461177852`, SHA-256 `9db7bceb571b2595723bbe2c16ff60ea8a1fecdb0525ff53ba860231b8dd4530` |
| KUserFeedback | `DIAG_PASS` | job `104912090591`, artifact `10461537028`, SHA-256 `e91e08e4d47039274c8806db5c310bbbd31dba4bd38d4c622a67ccdd5c10d0ac` |
| Prison | `DIAG_PASS` | job `104912090832`, artifact `10460853327`, SHA-256 `a90e7fda5401670092e74d83e58bfa14c2ebd75d186a5a33a25c6328efb986c0` |

None of the five diagnostic PASS results is a package PASS.

## KConfig remediation

KConfig 6.30 configured far enough to resolve `Qt6CorePrivate`, but the imported target referenced the versioned QtCore private include surface that was not installed. The diagnostic profile had `qt6-base-dev` but not `qt6-base-private-dev`.

The next profile adds `qt6-base-private-dev`. The runner also asserts that a versioned `QtCore/.../QtCore/private` directory actually exists before CMake configure. This converts the fix from an assumption into a tested provider contract.

## KI18n remediation

KI18n compiled completely. The only failures were `kcatalogtest`, `kcountrytest` and `kcountrysubdivisiontest`, all expecting French translations from the `iso_3166-1` / `iso_3166-2` gettext domains. Examples include `New Zealand -> Nouvelle-Zélande` and `Wien -> Vienne`.

Ubuntu 26.04 supplies `iso-codes` as data and moves language-specific translation coverage through Ubuntu language packs. The next diagnostic profile therefore adds `language-pack-fr-base`. Before compiling, the runner requires actual French `iso_3166-1.mo` and `iso_3166-2.mo` catalogs under the normal or Ubuntu language-pack locale tree. The remediation is considered proven only if the next unchanged upstream tests pass.

## Upstream defaults

The diagnostic runner does not disable features to obtain a green result. It preserves and checks the selected KDE 6.30 defaults, including GUI/QML/DBus for KConfig, QML for KI18n, backends and Designer plugin for Sonnet, Desktop style and DBus for Kirigami, and the enabled multimedia/barcode paths for Prison.

## Per-node scope

The first implementation used a global semantic selector. That would rerun five already-green nodes whenever only KConfig or KI18n changed. The selector is now per-node:

- changes to one node's diagnostic profile rerun only that node;
- evidence-only `last_campaign` changes do not rerun diagnostics;
- common runner/workflow/dependency-provider changes conservatively rerun the full matrix;
- documentation-only changes do not run the diagnostic lane.

This preserves broad discovery while avoiding repeated expensive work after the common infrastructure stabilizes.

## Relationship to package lanes

1. source diagnostics discover failures broadly and early;
2. specialized package lanes produce `.deb` evidence;
3. only package `PASS` artifacts may feed downstream package nodes;
4. diagnostic fixes must still pass full package gates;
5. global package campaigns are repeated after remediation.

KGuiAddons is intentionally outside this seven-node source matrix because its package validation must consume the retained local KCoreAddons PASS rather than substitute Ubuntu KDE packages.
