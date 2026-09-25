# KDE Tier 3 — KIO Round 11 diagnostic

Round 11 starts as a **non-promoting diagnostic gate**. It does not build a KIO Debian package, does not change the canonical DAG, does not authorize Level 1 or Level 2, and does not create or claim `6.30.0-0supralinux7`.

## Evidence entering Round 11

### Attempt 5

KIO `6.30.0-0supralinux5` reached **67/69 PASS** in workflow `35991007820`, job `107605066803`. The remaining failures were `kiowidgets-kdirmodeltest` and `kiofilewidgets-knewfilemenutest`.

The CTest environment on those tests still contained KDE's per-test `QT_QPA_PLATFORM=offscreen` plus the ECM-provided build-tree `QT_PLUGIN_PATH`. This proved that the outer XCB wrapper did not override the per-test platform setting.

### Attempt 6

Round 10 changed those two tests with `set_tests_properties(... ENVIRONMENT ...)`. Workflow `36035351270`, job `107754320435`, then reached **66/69 PASS**.

The targeted tests now showed only:

- `QT_QPA_PLATFORM=xcb`
- `QT_QPA_SYSTEM_ICON_THEME=breeze`

The previous `QT_PLUGIN_PATH` was absent. Therefore the Round 10 CMake edit replaced the complete CTest `ENVIRONMENT` property instead of modifying only the intended variables. The two icon failures remained, and `kiocore-krecentdocumenttest` appeared as an additional failure.

This is a real defect in the Round 10 test-fixture adaptation, not evidence that upstream KDE requires `QT_PLUGIN_PATH` to be removed.

## Breeze provider

Breeze itself is not missing. Retained support build workflow `35700002095`, job `106656021938`, artifact `10682012012` produced `breeze-icon-theme 4:6.30.0-0supralinux1` and installed the real theme tree, including `/usr/share/icons/breeze/index.theme`, `unknown.svg`, `inode-directory.svg`, and the colored folder icons.

Round 11 therefore probes Qt's actual theme resolution under Xvfb/XCB instead of changing or replacing Breeze.

## Non-destructive CTest mechanism

CMake's `ENVIRONMENT_MODIFICATION` test property is the candidate mechanism. It applies modifications after a test's existing `ENVIRONMENT`, allowing Round 11 to set:

- `QT_QPA_PLATFORM=set:xcb`
- `QT_QPA_SYSTEM_ICON_THEME=set:breeze`

while preserving KDE/ECM variables such as `QT_PLUGIN_PATH`.

The diagnostic creates a minimal CTest fixture and must prove all three effective values simultaneously before this mechanism can be accepted for KIO packaging.

## Qt/Breeze probe

Using Ubuntu Resolute Qt 6.10.2 and the exact retained SupraLINUX Breeze package, the diagnostic records:

- `QIcon::themeName()`;
- every `QIcon::themeSearchPaths()` entry;
- `QIcon::hasThemeIcon()`, null state and resolved icon name for `unknown`, `inode-directory`, and `folder-red`;
- results under default XDG paths, explicit standard XDG paths, and explicit `QIcon::setThemeName("breeze")`.

This separates a CTest environment-loss problem from a Qt theme-selection/search-path problem.

## krecentdocumenttest

The new Attempt 6 failure is handled independently. KDE KIO 6.30 writes recent-document timestamps with millisecond precision, sorts recent URLs by timestamp, and its test inserts 15 entries in a tight loop before requiring an exact last-three order.

That is evidence for a timestamp-tie race hypothesis, not permission to suppress the test. The Round 11 diagnostic verifies this exact source shape and records it separately. If later runtime evidence is required, the test remains fatal until the cause is resolved or upstream evidence justifies a stable backport.

## Gate

Current canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**. KIO remains the sole current FAIL at `6.30.0-0supralinux6`; `execution_authorized=false`.

The next step after this definition is diagnostic evidence. Only that evidence may decide whether a source-package change and revision `6.30.0-0supralinux7` are justified. Stable promotion remains separately gated by explicit user approval.

## Diagnostic result — PASS

Round 11 diagnostic workflow `36071103806` at commit `b314ad501bf5eb6213f6cf4b2562cce60804b76c` completed successfully in job `107872008601`. Evidence artifact `10837734340` has SHA-256 `d4d944ac656d755ebd8c828d1e84c1b735e076c26a17adc66da42f0464a8cedc`. The run remained non-promoting: `package_attempted=false`, no DAG state changed, and KIO stayed canonical FAIL.

The CMake fixture proved the non-destructive mechanism. The original test environment contained `QT_QPA_PLATFORM=offscreen` and `QT_PLUGIN_PATH=/probe/upstream-build-tree/bin`; applying `ENVIRONMENT_MODIFICATION` produced effective `QT_QPA_PLATFORM=xcb` and `QT_QPA_SYSTEM_ICON_THEME=breeze` while preserving `QT_PLUGIN_PATH`.

The Qt/Breeze probe also passed independently on Ubuntu Resolute with Qt 6.10.2 and the exact retained SupraLINUX Breeze package. `QIcon::themeName()` was `breeze`, the search path included `/usr/local/share/icons` and `/usr/share/icons`, and `unknown`, `inode-directory`, and `folder-red` all returned `HAS=true`, `NULL=false`, with the expected icon name in all three probe modes.

This is sufficient evidence to replace Round 10's destructive per-test `ENVIRONMENT` assignment with `ENVIRONMENT_MODIFICATION` in the Round 11 remediation definition.

`krecentdocumenttest` remains separate. Its timestamp-tie explanation is evidence-backed but not yet a focused runtime proof; therefore Round 11 does not patch, suppress, exclude, or downgrade that test. It remains fatal in the next full Level 1 attempt. If it fails again, it becomes the next independent diagnostic gate.

Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**, with `execution_authorized=false`. The next gate is `tier3-round11-kio-remediation-definition`; no `6.30.0-0supralinux7` package is claimed by this diagnostic closure.

## Closed-diagnostic CI behavior

The Round 11 diagnostic workflow is part of the pull-request diff, so GitHub can reevaluate it on later `synchronize` events even after the diagnostic gate has closed. Run `36075258421` exposed the old lifecycle assumption: its validator still required Level 1 to remain frozen at the diagnostic-stage Attempt 6 state, and the unconditional artifact upload then failed because no new diagnostic evidence had been produced.

The diagnostic validator now treats a `diagnostic-PASS` record as immutable historical evidence. Canonical lifecycle freeze checks apply only while the diagnostic is still pending. Once closed, later workflow invocations validate the recorded run/job/artifact, findings, CMake mechanism and conservative `krecentdocumenttest` policy without requiring the rest of Tier 3 to remain at the old gate.

The workflow also has explicit capture mode. It downloads Breeze, runs probes and uploads a new artifact only while `status=definition-pending-diagnostic`. With `status=diagnostic-PASS`, it reports an intentional skip after validating the historical evidence. This prevents redundant probes and false CI failures as Round 11 advances.
