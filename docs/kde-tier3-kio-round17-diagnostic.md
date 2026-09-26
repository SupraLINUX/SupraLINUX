# KDE Tier 3 — KIO Round 17 actual object-path state-transition diagnostic

Status: **definition pending diagnostic evidence**.

Round 16 closed with workflow `36209833629`, job `108313880904`, artifact `10894374901`, SHA-256 `8cda50173446df052b21e5ca4fe89129af65e1c1e1ff13ac137953b5a9508cf6`. It proved that simply loading KIconThemes, KIOCore, KIOWidgets or KIOFileWidgets — including a verified KIconThemes startup — does not reproduce the empty `QIcon::name()` failures.

## Why Round 17

The exact KIO 6.30 source shows two concrete production paths that Round 16 did not execute.

For `KDirModelTest::testIcon`, `KDirModel::data(Qt::DecorationRole)` creates the `unknown` fallback, tries the invalid absolute icon path through `QIcon::fromTheme(iconName, fallbackIcon)`, then returns `KIconUtils::addOverlays(icon, item.overlays())`.

For `KNewFileMenuTest::testFolderIconCollection`, the test constructs `KNewFileMenu`, calls `checkUpToDate()`, opens the Folder dialog, then `showNewDirNameDlg()` creates `QIcon::fromTheme("inode-directory")` and passes it through `setIcon()`, which stores `icon.name()` in the label property.

These are now the shortest known paths between the successful Round 16 probes and the failing real assertions.

## Method

Round 17 rematerializes the exact retained KIO `6.30.0-0supralinux7` source and exact provider closure. It then applies a **transient diagnostic-only instrumentation patch** to two files:

- `src/widgets/kdirmodel.cpp`;
- `src/filewidgets/knewfilemenu.cpp`.

The patch adds only `qInfo()` observations prefixed with `R17|`; it does not change conditions, return values, icon names, package metadata, tests, or expected results. The exact patch diff is retained in the evidence artifact.

The instrumented build must still reproduce both original failures. If either test unexpectedly passes, the diagnostic is invalid because the instrumentation perturbed behavior.

### KDirModel checkpoints

For the invalid absolute icon entry, evidence records the icon name/null state at:

1. direct `unknown` fallback creation;
2. direct absolute-path `QIcon` construction;
3. after `QIcon::fromTheme(invalidName, fallbackIcon)`;
4. before `KIconUtils::addOverlays()`;
5. after `KIconUtils::addOverlays()`.

This distinguishes Qt fallback semantics from KGuiAddons overlay processing and later KDirModel transport.

### KNewFileMenu checkpoints

Evidence probes `inode-directory` at:

1. constructor body;
2. `checkUpToDate()` entry and exit;
3. `showNewDirNameDlg()` entry;
4. after `initDialog()`;
5. actual default icon construction;
6. `setIcon()` input;
7. after writing the `iconName` property and after pixmap rendering.

The first checkpoint where the semantic name becomes empty identifies the smallest object-path interval requiring the next investigation.

## Safety

This is not a remediation and not a package attempt. The diagnostic patch never enters Debian source artifacts, no KIO revision is allocated, no expected result is changed, and no test is suppressed. KIO remains `6.30.0-0supralinux7` FAIL/downstream-ineligible and canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.

Next gate: `tier3-round17-kio-object-path-state-transition-diagnostic-evidence`.
