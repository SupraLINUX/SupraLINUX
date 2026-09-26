# KDE Tier 3 — KIO Round 16 KIconThemes/KIO library linkage diagnostic

Status: **definition pending diagnostic evidence**.

Round 15 closed with valid evidence: workflow `36208311383`, job `108309466429`, artifact `10894857677`, SHA-256 `58413dce8261e276f08b450ac6fbab494a0d691018dd0472a997b570b5e2e136`. It proved that changing the fallback to Breeze, making the Breeze resource visible, linking BreezeIcons, and calling `BreezeIcons::initIcons()` all preserve the semantic names `unknown`, `inode-directory`, and `folder-red`.

## Why Round 16

Round 13 still reproduces the two real failures in the exact KIO build tree. Its file traces prove that both failing test processes load `libKF6IconThemes.so.6` and `libKF6BreezeIcons.so.6`, plus KIO libraries from the build tree.

The exact KIO 6.30 source gives a useful dependency threshold:

- `kdirmodeltest` links `KF6::KIOCore` and `KF6::KIOWidgets`;
- `knewfilemenutest` links `KF6::KIOFileWidgets` and `KF6::KIOWidgets` plus its public test dependencies;
- `KF6::KIOWidgets` links `KF6::KIOCore` publicly and `KF6::IconThemes` privately;
- `KF6::KIOFileWidgets` links `KF6::KIOWidgets` publicly.

Therefore the next useful question is not whether Breeze initializes, but **which loaded library closure first changes QIcon identity**.

## Matrix

Round 16 rematerializes the exact KIO `6.30.0-0supralinux7` source and provider closure using the same method that reproduced the failure in Round 13. It builds only the existing support/test targets needed to obtain the real build-tree shared libraries; it does not build a Debian package.

A tiny Qt probe is linked six ways, with `--no-as-needed` and `ldd` evidence proving the intended library really remains loaded:

1. `qt-baseline`;
2. `kiconthemes-only`;
3. `kiocore-only`;
4. `kiconthemes-plus-kiocore`;
5. `kiowidgets-closure`;
6. `kiofilewidgets-closure`.

Each executable runs under the exact XCB/Breeze/KDECI/QT_PLUGIN_PATH environment and under the same three path-state sequences used in Round 15: normal, KDirModel test mode, and KNewFileMenu test-mode/config sequence.

For every run the artifact records theme, fallback, Breeze resource visibility, data/search paths, and `hasThemeIcon` / null / `QIcon::name()` for `unknown`, `inode-directory`, and `folder-red`.

The Qt baseline must preserve all three names in all three sequences. Otherwise the run is invalid.

## Interpretation

If `kiconthemes-only` reproduces, loading KIconThemes before QApplication is sufficient. If the two individual libraries pass but `kiconthemes-plus-kiocore` reproduces, their interaction is sufficient. If that passes but `kiowidgets-closure` reproduces, the first common KIOWidgets closure is isolated. A FileWidgets-only effect cannot explain the KDirModel failure by itself and will be classified accordingly. If no preload closure reproduces, the failure requires actual KIO object/path execution rather than library loading alone.

## Safety

No KIO source remediation is introduced, no test is suppressed, no Debian package is built, and no `6.30.0-0supralinux8` revision is allocated. Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED** and `execution_authorized=false`.

Next gate: `tier3-round16-kio-kiconthemes-startup-kio-library-diagnostic-evidence`.
