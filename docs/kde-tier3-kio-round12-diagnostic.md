# KDE Tier 3 — KIO Round 12 icon-resolution diagnostic

Status: **definition pending diagnostic evidence**.

Round 12 begins only after the canonical Attempt 7 closure was validated by Repository Policy `36081396544` on commit `8f79504c8bce450ffc3b2ecdd7da388e5f62103b`. It is a non-promoting diagnostic gate: no Debian package is built, no source package is changed, no test is suppressed, and no DAG state changes.

## Evidence entering Round 12

Level 1 Attempt 7 ran in workflow `36079116873` at commit `ef6262ac9018df2c0d111d97f99919d8acdeb215`.

KIO `6.30.0-0supralinux7` reached **67/69** upstream tests. Only these two targets failed:

- `kiowidgets-kdirmodeltest`;
- `kiofilewidgets-knewfilemenutest`.

`kiocore-krecentdocumenttest` passed in Attempt 7, so the Round 11 timestamp issue is no longer part of the current failing set.

The KIO failure evidence is job `107897110171`, artifact `10840963289`, SHA-256 `32b10c0ac337040239edea709440c5b09b898d76da1ac3c8e10339bf1477d239`.

## What Round 11 already proved

Round 12 does not repeat the Round 11 question.

CTest showed for both failing targets that the original environment still contained:

- `QT_QPA_PLATFORM=offscreen`;
- `QT_PLUGIN_PATH=<KIO build tree>/bin`.

It then applied:

- `QT_QPA_PLATFORM=set:xcb`;
- `QT_QPA_SYSTEM_ICON_THEME=set:breeze`.

Therefore `ENVIRONMENT_MODIFICATION` preserved `QT_PLUGIN_PATH` exactly as intended.

Breeze was also genuinely installed inside the Attempt 7 sbuild chroot as `breeze-icon-theme 4:6.30.0-0supralinux1`. The retained Breeze artifact is `10682012012`, and the exact `breeze-icon-theme` Debian package has SHA-256 `308a20089ef387da2d5ba08b42be4299dd62fe5f5535786a0d8881d93b0d1e09`.

The remaining failure therefore cannot be classified as “Breeze package missing” or “QT_PLUGIN_PATH destroyed”.

## Primary failure class

Both remaining targets first fail on themed icon identity.

`KDirModelTest::testIcon()` receives an icon whose `QIcon::name()` is empty where upstream expects `unknown`.

`KNewFileMenuTest::testFolderIconCollection(default)` receives an empty `iconName` where upstream expects `inode-directory`.

The later 19 `KNewFileMenuTest` rows fail on `chooseIconBox->isExpanded()`. Those are follow-on failures: the default row aborts at the icon assertion before it reaches the later OK-button path that creates the directory and persists the expanded-state setting.

This reduces Round 12 to an icon-resolution investigation rather than two unrelated failures.

## Diagnostic probes

The diagnostic verifies the exact KIO 6.30.0 tarball by SHA-256 and checks the upstream source shape before executing probes.

It then runs a Qt Widgets probe under Ubuntu 26.04, Qt 6.10.2, XCB/Xvfb and the exact retained Breeze package. The probe exercises:

1. normal baseline icon resolution;
2. the `KDirModelTest` sequence with `QStandardPaths::setTestModeEnabled(true)`;
3. the same sequence with explicit `QIcon::setThemeName("breeze")`;
4. the `KNewFileMenuTest` sequence: enable test mode, obtain the test config path, disable test mode, set fake `XDG_CONFIG_HOME`;
5. that sequence with explicit Breeze theme selection.

For every mode it records:

- `QIcon::themeName()` and fallback theme;
- `QStandardPaths::GenericDataLocation`;
- every `QIcon::themeSearchPaths()` entry;
- `QIcon::hasThemeIcon()`, null state and icon name for `unknown`, `inode-directory`, and `folder-red`.

The baseline must resolve all three icons. The other modes are diagnostic outcomes, not preselected answers.

If either real-test sequence reproduces the empty icon, Round 12 will have isolated the root cause to Qt standard-path/theme state. If neither reproduces it, the evidence narrows the next diagnostic to KIO's build-tree/process context instead of changing packaging blindly.

## Safety

No package revision is allocated. In particular, Round 12 does **not** claim `6.30.0-0supralinux8`.

Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**:

- KIO remains current FAIL at `6.30.0-0supralinux7`;
- KXMLGui remains PASS at `6.30.0-0supralinux5`;
- `execution_authorized=false`;
- Level 2 remains unauthorized;
- stable promotion still requires explicit user approval.

Next diagnostic gate: `tier3-round12-kio-diagnostic-evidence`.

## Diagnostic result — PASS, no isolated reproduction

Round 12 completed in workflow `36082312546` at commit `91b57e78d5d74ed6ad7c87313086d1476bf60ba6`, job `107906716315`. Evidence artifact `10842450967` has SHA-256 `5b34f0a73e1e0f9b32e0c88d6c5bc90d3463d4b4854931eecda66244a9c52df6`. Repository Policy `36082312426` also passed for the definition commit.

The result is intentionally diagnostic rather than a package PASS. No package was built, no package revision changed, and canonical KIO remains FAIL at `6.30.0-0supralinux7`.

All five Qt/Breeze probe modes resolved `unknown`, `inode-directory`, and `folder-red` correctly. In particular:

- baseline: Breeze selected and all three icons resolved;
- `KDirModelTest` test-mode sequence: all three icons still resolved, with `.qttest/share` added ahead of the normal system data locations;
- explicit Breeze after KDirModel test mode: still resolved;
- `KNewFileMenuTest` enable-test-mode → capture `.qttest/config` → disable-test-mode → fake `XDG_CONFIG_HOME` sequence: all three icons still resolved;
- explicit Breeze after the KNewFileMenu sequence: still resolved.

Therefore neither `QStandardPaths::setTestModeEnabled(true)` nor the KNewFileMenu `XDG_CONFIG_HOME` sequence is sufficient to reproduce Attempt 7. Qt 6.10.2, XCB/Xvfb and the exact retained Breeze package also work together in isolation.

This narrows the unresolved delta to the real **KIO build-tree/test-process context**: something present only when the actual KIO test binaries run from the build tree causes the themed icon name to become empty.

Round 12 is closed. No remediation is justified yet and no `6.30.0-0supralinux8` revision is allocated. Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**, with `execution_authorized=false`.

Next gate: **`tier3-round13-kio-build-tree-diagnostic-definition`**.

### Historical versus current next-gate validation

Attempt 7's immutable campaign ledger continues to record `tier3-round12-kio-diagnostic-definition` as the gate that followed that attempt. Closing Round 12 must not rewrite that historical edge.

The live Tier 3, Level 1, package-contract and materialization manifests may advance to `tier3-round13-kio-build-tree-diagnostic-definition` only when the recorded Round 12 diagnostic is `diagnostic-PASS` with workflow `36082312546`, job `107906716315`, artifact `10842450967` and SHA-256 `5b34f0a73e1e0f9b32e0c88d6c5bc90d3463d4b4854931eecda66244a9c52df6`.

This distinction preserves historical evidence while allowing the current lifecycle to advance. It does not authorize Level 1 execution, alter the canonical package states, or allocate a new KIO revision.
