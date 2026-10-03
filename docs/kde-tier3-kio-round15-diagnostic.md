# KDE Tier 3 — KIO Round 15 BreezeIcons init-state diagnostic

Status: **diagnostic PASS — closed**.

Round 14 rejected the simple provider-presence hypothesis: installing the exact retained `libkf6iconthemes-bin 6.30.0-0supralinux3` package did not recover either KIO icon-name failure, and `KIconEnginePlugin.so` was not loaded. KIO remains `6.30.0-0supralinux7` FAIL/downstream-ineligible.

## Why this gate exists

Round 12 established a clean isolated reference under Ubuntu 26.04 / Qt 6.10.2 / XCB / Breeze: `QIcon::themeName()` was `breeze`, `QIcon::fallbackThemeName()` was `hicolor`, and `unknown`, `inode-directory` and `folder-red` all preserved their names.

Round 13 provides an additional fact that was not yet isolated experimentally: both real failing KIO processes load `/usr/lib/x86_64-linux-gnu/libKF6IconThemes.so.6` and `/usr/lib/x86_64-linux-gnu/libKF6BreezeIcons.so.6`.

The exact KDE 6.30 sources explain why that matters:

- `KF6IconThemes` registers `initThemeHelper` with `Q_COREAPP_STARTUP_FUNCTION`;
- `initThemeHelper` calls `BreezeIcons::initIcons()` before the `!initThemeUsed` early return;
- `BreezeIcons::initIcons()` registers the Breeze icon resource and changes an empty or `hicolor` fallback theme to `breeze`.

Therefore Round 15 isolates that state transition instead of changing packaging again.

## Matrix

No KIO source is compiled in this gate. Two tiny probes are built against the exact retained BreezeIcons artifact:

1. `qtprobe`, linked only to Qt Widgets;
2. `breezeprobe`, linked to Qt Widgets plus `KF6::BreezeIcons`.

Each is exercised under the normal sequence, the `KDirModelTest` test-mode sequence and the `KNewFileMenuTest` test-mode/config sequence. Four modes are compared:

- `qt-baseline`: the Round 12-style Qt/Breeze reference;
- `qt-fallback-breeze`: changes only `QIcon::fallbackThemeName()` to `breeze`;
- `breeze-linked-no-init`: links BreezeIcons but does not call `initIcons()`;
- `breeze-init`: calls `BreezeIcons::initIcons()` before the KIO-like path sequence.

For every run the evidence records theme, fallback, Breeze resource visibility, generic data paths, icon search paths and the `hasThemeIcon` / null / `QIcon::name()` state of `unknown`, `inode-directory` and `folder-red`.

The baseline must resolve all three icons with their names intact in all three sequences. Otherwise the diagnostic is invalid due to environment drift.

If fallback-only reproduces the empty-name failure, the fallback transition is sufficient. If it does not but linking BreezeIcons without `initIcons()` reproduces, linkage/resource state is sufficient. If only `breeze-init` reproduces, `BreezeIcons::initIcons()` is the isolated causal transition. If none reproduce, Round 15 rejects Breeze initialization as sufficient and the next scope becomes the broader `KF6IconThemes` startup/KIO-library interaction.

## Evidence and safety

The runner reuses only retained, hash-verified evidence:

- Round 13 artifact `10869413386`, SHA-256 `f96d4fdfebc5fcebe63633650ebf3998a51e37e5c84c12b50bc3d745097d7cd7`;
- Breeze Icons artifact `10682012012`, SHA-256 `daaa5abda5a8f824c6fa509142d7cd9132de213d782cb32e0561873f427aa577`;
- KIconThemes artifact `10731249726`, SHA-256 `5b06a92638fb67409710b140f3ebc597400d0d739db497e3d570fbe42cfa5206`.

No Debian package is built, no KIO revision is allocated, no source is patched and no test is suppressed. Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**. Stable promotion still requires explicit user approval.

Next gate: `tier3-round15-kio-breeze-icons-init-state-diagnostic-evidence`.

## Invalid Attempt 1 — fixture drift

The first Round 15 execution at commit `d4a220f95b742b1125fad564b2729358ebfd941d` reached the matrix but is **not diagnostic evidence about BreezeIcons behavior**. Workflow `36207971890`, job `108308432777`, produced artifact `10894787434` with SHA-256 `7ac10f5ee01a1a28240db7391d748cbd292abaed923c155845d560307710f598`.

Every mode, including `qt-baseline`, returned null/unnamed icons. Comparison with the validated Round 12 fixture found the drift: Round 12 explicitly installed `qt6-svg-dev` and `qt6-svg-plugins`, while the initial Round 15 runner omitted them. Breeze's filesystem theme payload is SVG, so this invalidated the baseline before any BreezeIcons causal comparison.

Attempt 1 is therefore recorded as `DIAG_INVALID / baseline-drift-invalid`, with **no canonical state effect**. The definition is corrected by restoring the exact Qt SVG fixture and by making invalid-baseline result reporting explicit. The same matrix will be rerun; no package or KIO revision changes.

## Diagnostic result — PASS, Breeze initialization is not sufficient

The corrected Round 15 execution completed in workflow `36208311383`, job `108309466429`, at commit `594b86b3e5ca78a8b936350d037c3877743ac273`. Evidence artifact `10894857677` has SHA-256 `58413dce8261e276f08b450ac6fbab494a0d691018dd0472a997b570b5e2e136`. Repository Policy `36208311436` passed on the same commit.

The baseline is valid. Across all three path sequences — normal, `KDirModelTest` test mode, and the `KNewFileMenuTest` test-mode/config sequence — all four modes preserve the semantic names `unknown`, `inode-directory`, and `folder-red`.

The state transitions were observed exactly:

- Qt baseline: fallback remains `hicolor`, Breeze resource is not visible, icon names remain intact.
- fallback-only: fallback becomes `breeze`, resource remains absent, icon names remain intact.
- BreezeIcons linked without explicit init: `:/icons/breeze` is visible while fallback remains `hicolor`; icon names remain intact.
- explicit `BreezeIcons::initIcons()`: resource is visible and fallback changes `hicolor → breeze`; icon names remain intact.

Therefore neither the fallback change, Breeze resource visibility, BreezeIcons linkage, nor `BreezeIcons::initIcons()` is sufficient to reproduce the KIO icon-name loss.

Round 15 remains non-promoting. KIO stays `6.30.0-0supralinux7` FAIL/downstream-ineligible, no `-8` exists, and canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.

Next gate: **`tier3-round16-kio-kiconthemes-startup-kio-library-diagnostic-definition`**.
