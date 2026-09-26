# KDE Tier 3 — KIO Round 15 BreezeIcons init-state diagnostic

Status: **definition pending diagnostic evidence**.

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
