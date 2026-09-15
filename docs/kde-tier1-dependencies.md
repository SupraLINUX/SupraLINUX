# KDE Frameworks 6.30 Tier 1 — dependency resolution

Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping resolved; hosted provider preflight PASS; 10 package nodes PASS; 19 package nodes pending**  
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

KItemViews is selected for Batch 4 with `BUILD_DESIGNERPLUGIN=ON`, preserving that KDE default explicitly.

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
- `modemmanager-qt`: ModemManager >= 1.0.
- `networkmanager-qt`: libnm >= 1.4.0 and GIO 2.0.
- `solid`: libmount and udev are required for the selected Linux default backend set.

Optional Solid iOS-device support (`libimobiledevice` + `libplist`) remains optional and is not a build gate merely because Resolute can provide it.

### Prison barcode stack

With upstream defaults, `prison` requires QRencode, Dmtx, ZXing, Qt Quick and Qt Multimedia. Dmtx and ZXing become mandatory in the selected profile because `WITH_DMTX` and `WITH_ZXING` default to ON; scanner support keeps `WITH_MULTIMEDIA=ON`.

Prison 6.30 probes ZXing config packages in order `3.0`, `2.0`, `1.4.0` and accepts the first one exposing `ZXing::ZXing`. Resolute ZXing `2.3.0-5` passes both the version floor and KDE discovery path.

### Sonnet spell backends

Sonnet discovers Aspell, HSpell, Hunspell and Voikko. Each backend is individually optional, but on the selected non-Android build Sonnet fails if **none** can be built. The manifest models this as `required_any_of` and the provider profile maps all available candidates. HSpell is a packaging exception: Debian/Ubuntu provides its development header/library through `hspell`; SupraLINUX must not invent `libhspell-dev`.

## Batch 4 dependency profile

The Batch 4 selection is `kitemviews`, `kglobalaccel` and `syntax-highlighting`.

- KItemViews requires Qt Widgets >= 6.9. Its default Designer plugin is retained and therefore `qt6-tools-dev` is present.
- KGlobalAccel requires Qt DBus/Gui/Widgets >= 6.9; with the selected Qt 6.10 provider upstream additionally requires `Qt6GuiPrivate`. Its enabled test subdirectory requires QtQml, so `qt6-declarative-dev` is a test/build input rather than an inherited distro-only dependency.
- KSyntaxHighlighting requires Qt Core/Network/Test and Perl. Gui is retained in the selected default profile; Qt Quick is available through `qt6-declarative-dev`, so the upstream QML module is built. XercesC validation is deliberately enabled as described above.

Reference-only dependencies that cannot be traced to the selected KDE 6.30 build path, such as inherited `libxkbcommon-dev` entries in these Debian trees, are not copied into SupraLINUX packaging merely because they exist downstream.

## Hosted provider evidence

Provider availability evidence remains:

- run `34700048774`;
- PR head `6ce61bc02c4aba146bcc33b16d17f56fb66f057a`;
- artifact `10299608166`;
- artifact SHA-256 `da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3`;
- result: `status=PASS`, `provider_candidate=ubuntu-resolute`, provider evidence only.

Historical runs `34699717549` and `34699889060` remain gate-implementation FAIL evidence; neither is a Framework node FAIL because no Framework was attempted.

## Package evidence status

Attica was the first real Framework package PASS against this dependency model. Subsequent Batch 1, Batch 2 and Batch 3 package evidence has promoted ten Tier 1 nodes in total. Preparation of Batch 4 does not transfer PASS to any new revision or node.

Current canonical state:

- upstream dependency resolution: **resolved**;
- Ubuntu package-name mapping: **resolved**;
- Ubuntu hosted provider availability/version evidence: **PASS**;
- Tier 1 package/build states: **10 PASS / 19 pending**;
- current Tier 1 FAIL: **0**;
- current Tier 1 BLOCKED: **0**;
- final Qt provider certification: **pending**.

No Framework is promoted by provider evidence or packaging preparation alone. A node becomes PASS only after a real package attempt satisfies its gates.
