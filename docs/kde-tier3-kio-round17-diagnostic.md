# KDE Tier 3 — KIO Round 17 root-cause environment diagnostic

Status: **definition pending diagnostic evidence**.

Round 16 closed with workflow `36209833629`, job `108313880904`, artifact `10894374901`, SHA-256 `8cda50173446df052b21e5ca4fe89129af65e1c1e1ff13ac137953b5a9508cf6`. It proved that simply loading KIconThemes, KIOCore, KIOWidgets or KIOFileWidgets — including a verified KIconThemes startup — does not reproduce the empty `QIcon::name()` failures.

## Why Round 17

The exact KIO 6.30 source shows two concrete production paths that Round 16 did not execute.

For `KDirModelTest::testIcon`, `KDirModel::data(Qt::DecorationRole)` creates the `unknown` fallback, tries the invalid absolute icon path through `QIcon::fromTheme(iconName, fallbackIcon)`, then returns `KIconUtils::addOverlays(icon, item.overlays())`.

For `KNewFileMenuTest::testFolderIconCollection`, the test constructs `KNewFileMenu`, calls `checkUpToDate()`, opens the Folder dialog, then `showNewDirNameDlg()` creates `QIcon::fromTheme("inode-directory")` and passes it through `setIcon()`, which stores `icon.name()` in the label property.

These are now the shortest known paths between the successful Round 16 probes and the failing real assertions.

## Current method — Attempt 4

Round 17 now uses an environment-only A/B/A experiment. KIO source and compiled binaries remain unchanged while only the installed state of `qt6-svg-plugins` changes:

1. **present-initial** — the exact original tests run with the SVG plugin installed;
2. **absent** — `qt6-svg-plugins` is removed and the same binaries run again;
3. **reinstalled** — the plugin is installed again and the same binaries run a third time.

Every phase uses a fresh HOME and the same XCB/Breeze/KDECI/QT_PLUGIN_PATH environment. Evidence records dpkg state, package versions, apt policy/dependency metadata, SVG plugin files on disk, test exit codes, and exact historical failure signatures.

The controlling A/B/A result is:

`PASS with plugin → both historical empty-name FAILs without plugin → PASS after reinstall`.

If confirmed, Round 17 establishes the missing Qt SVG plugin as the environmental root cause controlling both failures. It does **not** yet assign packaging ownership. The following gate must decide whether the required contract belongs to Breeze icon-theme packaging, the KIO build/test closure, or another shared Qt SVG provider rule.

## Safety

This is not a remediation and not a package attempt. Attempt 4 patches no source, changes no expected result, builds no Debian package, and allocates no KIO revision. KIO remains `6.30.0-0supralinux7` FAIL/downstream-ineligible until an actual package attempt passes. Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.

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

## Invalid Attempt 2 — conditional source still changed the baseline

Attempt 2 at commit `4c5c4bcb9c3cf420d02b7d9a406159ef62e4535c` also cannot be used as causal evidence. Workflow `36214198192`, job `108326788757`, produced artifact `10896848386` with SHA-256 `5b4c14d52b858a2455b7a9ee395db305360c8a386993fad37e92f7620fdb4002`.

The no-touch baseline unexpectedly passed both tests. Although `SUPRALINUX_R17_TOUCH` was unset, the instrumented source still changed C++ object shape: KDirModel stored the overlay result in a local `QIcon` before returning it, and KNewFileMenu stored the default themed icon in a named local before passing it to `setIcon()`. Therefore the baseline was not semantically identical at the object-lifetime/codegen level.

Repository Policy `36214198247` also stopped at ShellCheck SC2100 on an unquoted diagnostic stage label. That lint issue is independent of the diagnostic result and is corrected in Attempt 3.

Attempt 2 is recorded as `DIAG_INVALID / conditional-instrumentation-still-perturbs-baseline`, with no canonical effect.

## Attempt 3 — exact original baseline, then structural A/B

Attempt 3 builds and executes the exact unmodified `6.30.0-0supralinux7` source first. Both original failures must reproduce before any source delta is applied.

Only after that gate passes:

1. KDirModel changes exactly one expression: the direct return of `KIconUtils::addOverlays(...)` is stored in a local `QIcon` and then returned.
2. The original KDirModel source is restored byte-for-byte, rebuilt, and must fail again.
3. KNewFileMenu changes exactly one expression: `QIcon::fromTheme(defaultFolderIconName)` is stored in a named local `QIcon` before `setIcon()`.
4. The original KNewFileMenu source is restored byte-for-byte, rebuilt, and must fail again.

This directly tests whether the temporary/copy/move lifetime shape that appeared accidentally in Attempts 1–2 is sufficient to heal each failure. If both variants heal while both restored baselines fail, the next gate is a focused confirmation of temporary lifetime/copy-move semantics versus LTO/code generation.

No package is built and no KIO revision is allocated.

## Invalid Attempt 3 — exact source, wrong environment fixture

Attempt 3 at commit `287c4e09d259af0d7f05c70ba856f81a75fac0b3` used the exact unmodified KIO source, but the supposedly historical baseline still passed both tests. Workflow `36215721289`, job `108331181346`, produced artifact `10897152304` with SHA-256 `dfe1356e3e10e4e12894627cab203c96ba9d842f11825ccb405b211da329b8f6`. Repository Policy `36215721283` passed.

The artifact proves:

- `KDirModelTest::testIcon`: 3 passed / 0 failed;
- `KNewFileMenuTest::testFolderIconCollection(default)`: 3 passed / 0 failed.

The important difference is environmental, not source-level. Round 17 inherited the Round 16 host-tools fixture, which explicitly installs both `qt6-svg-dev` and `qt6-svg-plugins`. Round 13 — the build-tree reproduction matching Attempt 7 — did not explicitly install those SVG packages. This also aligns with the earlier Round 15 invalid baseline where Breeze SVG icons became null/unnamed without the SVG plugin.

Attempt 3 is therefore recorded as `DIAG_INVALID / original-baseline-passed-due-to-environment-fixture-drift`, with no canonical effect. The temporary-lifetime hypothesis is not promoted from this attempt.

## Attempt 4 — Qt SVG plugin A/B/A, no source changes

Attempt 4 leaves KIO source and binaries unchanged and varies only the installed state of `qt6-svg-plugins`:

1. **present-initial** — exact original tests run with the plugin installed;
2. **absent** — remove only `qt6-svg-plugins` and rerun the same binaries;
3. **reinstalled** — reinstall `qt6-svg-plugins` and rerun again.

Each phase uses a fresh HOME and the same XCB/Breeze/KDECI/QT_PLUGIN_PATH environment. Evidence records package versions, apt policy/dependency metadata, the SVG plugin files on disk, test exit codes, and the exact historical failure signatures.

The strongest confirmation is:

`PASS with plugin → both historical empty-name FAILs without plugin → PASS after reinstall`.

That would establish `qt6-svg-plugins` presence as the controlling environmental variable for both KIO failures. Only after that result will the next gate decide the correct packaging owner/provider contract — for example whether the dependency belongs in the Breeze icon-theme contract, KIO build/test closure, or another shared Qt SVG provider rule. No ownership decision is assumed in Round 17.

No package is built, no source is patched, and no KIO revision is allocated.

