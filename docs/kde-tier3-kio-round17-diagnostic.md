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

## Invalid Attempt 1 — observation changed behavior

The first Round 17 execution at commit `9d0286656b81152d76e96e9ec7fb776e0fd233ab` is **not valid causal evidence**. Workflow `36213295538`, job `108324143779`, produced artifact `10896761982` with SHA-256 `5247d6b2f9f80c15cb04c63c4687d37b707421e3a1f91f0e8f9e2d3360c01084`.

Both instrumented tests unexpectedly passed. The common perturbation was the diagnostic itself: the inserted checkpoints repeatedly called `QIcon::name()` before the original assertions. In the KDirModel path, the invalid-path fallback held `unknown` through `QIcon::fromTheme(..., fallback)` and `KIconUtils::addOverlays()`; in KNewFileMenu every inserted early `inode-directory` read returned the expected name. Because those reads changed the final behavior, Attempt 1 is recorded as `DIAG_INVALID / instrumentation-perturbed-original-failure` with no canonical effect.

This is still a useful design clue: reading `QIcon::name()` may materialize or stabilize lazy icon-engine state. The corrected Attempt 2 tests that hypothesis deliberately instead of pretending to observe passively.

## Corrected Attempt 2 strategy

The transient source delta now contains conditional touch points controlled by `SUPRALINUX_R17_TOUCH`.

First, both tests run with **no touch variable at all**. That baseline must reproduce the original empty-name failures; otherwise Attempt 2 is invalid.

Then every variant runs in a fresh process and activates exactly one controlled `QIcon::name()` read site. KDirModel variants cover the fallback icon, absolute invalid icon, post-`fromTheme`, pre-overlay and post-overlay states. KNewFileMenu variants cover constructor, `checkUpToDate()` entry/exit, dialog entry/post-`initDialog()`, default icon creation and `setIcon()` input.

The diagnostic classifies the earliest single read that changes each original FAIL into PASS. This turns the perturbation into the measured variable while retaining an untouched-behavior baseline.

No package is built, no canonical source is changed, and no KIO revision is allocated.

