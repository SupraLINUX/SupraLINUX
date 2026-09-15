# KDE Frameworks 6.30 Tier 1 — dependency resolution

Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping resolved; hosted provider preflight PASS; 16 package nodes PASS; 13 package nodes pending**
Last reviewed: **2026-09-15**

## Contract

This document separates two questions:

- **Authority:** what KDE Frameworks 6.30.0 requires or enables in its selected Linux/default build paths.
- **Provider:** which Ubuntu Resolute packages may satisfy those requirements for SupraLINUX.

The authoritative dependency inputs are the exact KDE `v6.30.0` build files recorded, with blob SHA pins, in `manifests/kde-frameworks-tier1-dependencies.json`. Ubuntu/Debian names are provider mappings and packaging references only.

The dependency manifest distinguishes `required`, `default_enabled`, `recommended`, `optional`, `runtime` and `required_any_of`. Optional features are not silently promoted to architectural requirements; conversely, default-enabled KDE features are not disabled merely because a distribution reference chose differently.

## Resolved dependency groups

### Compression and archive support

`karchive` defaults to all four support switches enabled and therefore uses zlib, bzip2, liblzma/xz, OpenSSL and libzstd/pkg-config in the selected profile. Resolute mappings are `zlib1g-dev`, `libbz2-dev`, `liblzma-dev`, `libssl-dev`, `libzstd-dev` and `pkgconf`.

### Python bindings

`kcalendarcore`, `kcoreaddons`, `kguiaddons` and `kwidgetsaddons` enable Python bindings by default on the selected Linux/shared-library paths. Their profile includes Python >= 3.9 development files, Shiboken6 and PySide6. Resolute maps these to `python3-dev`, `libshiboken6-dev` and `libpyside6-dev`.

The hosted provider PASS verifies that Shiboken6 and PySide6 normalize to the same upstream Qt patch level as the selected Ubuntu Qt candidate: **6.10.2**.

### X11 and Wayland

The selected Linux defaults retain X11 and Wayland paths where KDE enables them. Notable requirements include:

- `kguiaddons`: X11/XCB, Wayland client >= 1.9, wayland-protocols >= 1.39, plasma-wayland-protocols >= 1.15.0;
- `kidletime`: X11/XCB Sync plus a usable idle poller, Wayland client >= 1.9, wayland-protocols >= 1.27, plasma-wayland-protocols >= 1.6.0;
- `kwindowsystem`: X11/XCB components and wayland-protocols >= 1.46 plus plasma-wayland-protocols.

The strongest selected Tier 1 constraint therefore gates the provider at `wayland-protocols >= 1.46`. Hosted evidence observed Resolute `wayland-protocols 1.47-1`, `libwayland-dev 1.24.0-2` and `plasma-wayland-protocols 1.20.0-2`.

### Qt Designer plugins

`kitemviews`, `kplotting` and `kwidgetsaddons` enable Qt Designer plugins by default when not cross-compiling. Their Designer paths use ECM's Qt Designer support and require Qt `UiPlugin`; the provider mapping uses `qt6-tools-dev`.

KItemViews Batch 4 retained `BUILD_DESIGNERPLUGIN=ON` and passed as `6.30.0-0supralinux1`.

### Translation tooling and Qt LinguistTools

Batch 4 exposed a provider mapping that preparation had missed: ECM `ECMPoQmTools` uses the Qt 6 `LinguistTools` CMake component when installing translations. Resolute provides that component through `qt6-tools-dev`.

The omission caused real `-1` package FAILs for KGlobalAccel and KSyntaxHighlighting. Adding `qt6-tools-dev (>= 6.9.0~)` to their Build-Depends produced real PASS revisions `6.30.0-0supralinux2` in run `35006477086`. This is a provider/packaging correction, not a change in KDE authority or KDE requirements.

### Generators and language tooling

- `kholidays`: Flex and Bison >= 3.3.2 are required.
- `solid`: Flex and Bison >= 3.0 are required.
- `syntax-highlighting`: Perl is required. XercesC is optional compile-time validation and Python is optional generator tooling.
- `ki18n`: Python is required for installed i18n tooling. On the selected glibc platform, libintl functionality is supplied by libc.
- `kuserfeedback`: Flex/Bison, PHP and PHPUnit are upstream recommended/non-fatal dependencies.

For Batch 4, KSyntaxHighlighting deliberately includes `libxerces-c-dev` so the available upstream XML validation path is exercised, while Python remains optional and is not converted into a hard architectural dependency.

### Platform/service libraries

- `kcalendarcore`: libical >= 3.0.
- `kcoreaddons`: libmount is required on Linux; root-level udev discovery remains optional.
- `modemmanager-qt`: KDE requires `ModemManager >= 1.0` and probes pkg-config module `ModemManager`; Ubuntu Resolute provides that development surface through `modemmanager-dev`.
- `networkmanager-qt`: libnm >= 1.4.0 and GIO 2.0.
- `solid`: libmount and udev are required for the selected Linux default backend set.

The earlier `libmm-glib-dev`/`mm-glib` mapping for ModemManagerQt was incorrect because it checked a related client-library surface rather than the interface requested by KDE's `FindModemManager.cmake`. The correction is provider-only; KDE authority and its minimum requirement are unchanged.

Targeted revalidation of the corrected mapping passed in run `35012023822`, job `104526071758`, artifact `10414525047`, SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`.

Optional Solid iOS-device support (`libimobiledevice` + `libplist`) remains optional and is not a build gate merely because Resolute can provide it.

### Prison barcode stack

With upstream defaults, `prison` requires QRencode, Dmtx, ZXing, Qt Quick and Qt Multimedia. Dmtx and ZXing become mandatory in the selected profile because `WITH_DMTX` and `WITH_ZXING` default to ON; scanner support keeps `WITH_MULTIMEDIA=ON`.

Prison 6.30 probes ZXing config packages in order `3.0`, `2.0`, `1.4.0` and accepts the first one exposing `ZXing::ZXing`. Resolute ZXing `2.3.0-5` passes both the version floor and KDE discovery path.

### Sonnet spell backends

Sonnet discovers Aspell, HSpell, Hunspell and Voikko. Each backend is individually optional, but on the selected non-Android build Sonnet fails if **none** can be built. The manifest models this as `required_any_of` and the provider profile maps all available candidates. HSpell is a packaging exception: Debian/Ubuntu provides its development header/library through `hspell`; SupraLINUX must not invent `libhspell-dev`.

## Batch 4 dependency profile and closure evidence

The Batch 4 selection was `kitemviews`, `kglobalaccel` and `syntax-highlighting`.

- KItemViews requires Qt Widgets >= 6.9 and retains the default Designer plugin via `qt6-tools-dev`.
- KGlobalAccel requires Qt DBus/Gui/Widgets >= 6.9; with Qt 6.10 upstream additionally requires `Qt6GuiPrivate`; enabled tests require QtQml; ECM translation handling additionally requires `Qt6LinguistTools` supplied by `qt6-tools-dev`.
- KSyntaxHighlighting requires Qt Core/Network/Test and Perl; Gui and the QML module remain in the selected profile; XercesC validation is enabled; ECM translation handling also requires `qt6-tools-dev`.

Reference-only dependencies that cannot be traced to the selected KDE 6.30 build path, such as inherited `libxkbcommon-dev` entries in these Debian trees, are not copied into SupraLINUX packaging merely because they exist downstream.

Closure evidence:

- KItemViews PASS: run `34999449194`, artifact `10409267184`, SHA-256 `7e34fa7ede21510cf6829448e7b45a5c2832aaf9ac2719b9cb4125d23b593e55`.
- KGlobalAccel remediation PASS: run `35006477086`, artifact `10412320520`, SHA-256 `cb8143633cf15745a235937ea55ee096cb094cc96da3bd1fc39dc914f3acb3b1`.
- KSyntaxHighlighting remediation PASS: run `35006477086`, artifact `10411888269`, SHA-256 `1ec0d1e7d046b1393fbb299c9a6fec7e85ee4ac59ed5deafa0c777ead67c0b5f`.

## Batch 5 provider profile

Batch 5 selects `kidletime`, `modemmanager-qt` and `networkmanager-qt`.

- KIdleTime retains upstream X11 and Wayland defaults and their provider surface.
- ModemManagerQt uses corrected provider `modemmanager-dev` for KDE's `ModemManager >= 1.0` requirement.
- NetworkManagerQt explicitly carries both `libnm-dev` and `libglib2.0-dev` because upstream CMake directly probes `libnm>=1.4.0` and `gio-2.0`; its QML module remains enabled.

Run `35014875475` attempted all three packages. KIdleTime and NetworkManagerQt passed immediately. ModemManagerQt built and passed 11/11 tests but failed the Lintian symbols gate on `_ZSt19piecewise_construct@Base`. Its `6.30.0-0supralinux2` attempt fixed that symbols issue and again passed 11/11 tests, then failed Lintian because the Python transform invoked by `debian/rules` lacked an explicit Python build prerequisite.

Revision `6.30.0-0supralinux3` retained the same reviewed transform and added only `python3:any` to Build-Depends. Run `35021323444`, job `104557423664`, artifact `10417683848`, SHA-256 `42d4f804effc6e4b9148e8c01887bdce6f95f0554ac4d03295e844a861a54eb7`, passed 11/11 tests plus Lintian/SONAME/consumer smoke. Batch 5 is now canonically closed 3/3 PASS and all three nodes are downstream-eligible.

## Hosted provider evidence

Original broad provider-availability evidence:

- run `34700048774`;
- PR head `6ce61bc02c4aba146bcc33b16d17f56fb66f057a`;
- artifact `10299608166`;
- artifact SHA-256 `da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3`;
- result: PASS; provider evidence only.

Current targeted evidence for the corrected ModemManager provider mapping:

- run `35012023822`;
- job `104526071758`;
- commit `48fd01bfa7b254b5e5c8447b3d609f76a91f786f`;
- artifact `10414525047`;
- artifact SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`;
- result: PASS; provider-availability evidence only.

Historical runs `34699717549` and `34699889060` remain gate-implementation FAIL evidence; neither is a Framework node FAIL because no Framework was attempted.

## Package evidence status

Attica was the first real Framework package PASS against this dependency model. Batch 1 through Batch 5 evidence has now promoted sixteen Tier 1 nodes.

Current canonical state:

- upstream dependency resolution: **resolved**;
- Ubuntu package-name mapping: **resolved**;
- Ubuntu hosted provider availability/version evidence: **PASS**;
- Tier 1 package/build states: **16 PASS / 13 pending**;
- current Tier 1 FAIL: **0**;
- current Tier 1 BLOCKED: **0**;
- final Qt provider certification: **pending**.

Provider evidence alone never promotes a Framework. Each of the sixteen canonical PASS nodes has real package-attempt evidence. Batch 5 is closed 3/3 PASS; the two earlier ModemManagerQt FAIL attempts remain retained as historical evidence while its `-3` PASS is the current downstream-eligible state.
