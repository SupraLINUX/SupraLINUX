# KDE Frameworks 6.30 Tier 1 — dependency resolution

Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping resolved; hosted provider preflight pending**  
Last reviewed: **2026-09-12**

## Contract

This document separates two questions:

- **Authority:** what KDE Frameworks 6.30.0 requires or enables in its selected Linux/default build paths.
- **Provider:** which Ubuntu Resolute packages may satisfy those requirements for SupraLINUX.

The authoritative dependency inputs are the exact KDE `v6.30.0` `CMakeLists.txt` files recorded, with blob SHA pins, in `manifests/kde-frameworks-tier1-dependencies.json`. Ubuntu/Debian names are provider mappings only.

The dependency manifest deliberately distinguishes `required`, `default_enabled`, `recommended`, `optional`, `runtime` and `required_any_of`. This prevents an optional feature from being silently promoted to a hard architecture dependency, and prevents a default-enabled feature from being silently dropped merely because a distro package is inconvenient.

## Resolved dependency groups

### Compression and archive support

`karchive` defaults to all four support switches enabled and therefore requires zlib, bzip2, liblzma/xz, OpenSSL and libzstd/pkg-config in the selected build profile. Resolute mappings are `zlib1g-dev`, `libbz2-dev`, `liblzma-dev`, `libssl-dev`, `libzstd-dev` and `pkgconf`.

### Python bindings

`kcalendarcore`, `kcoreaddons`, `kguiaddons` and `kwidgetsaddons` enable Python bindings by default on the selected Linux/shared-library build paths. Their profile therefore includes Python >= 3.9 development files, Shiboken6 and PySide6. Resolute mappings are `python3-dev`, `libshiboken6-dev` and `libpyside6-dev`.

The provider preflight must verify that Shiboken/PySide are coherent with the selected Qt 6.10.2 candidate rather than merely checking package names.

### X11 and Wayland

The selected Linux defaults keep both X11 and Wayland paths enabled where KDE enables them.

Important requirements include:

- `kguiaddons`: X11/XCB, Wayland client >= 1.9, wayland-protocols >= 1.39, plasma-wayland-protocols >= 1.15.0;
- `kidletime`: X11/XCB Sync plus a usable idle poller, Wayland client >= 1.9, wayland-protocols >= 1.27, plasma-wayland-protocols >= 1.6.0;
- `kwindowsystem`: X11/XCB components and wayland-protocols >= 1.46 plus plasma-wayland-protocols.

The strongest selected Tier 1 constraint therefore gates the provider at `wayland-protocols >= 1.46`.

KIdleTime records both the strongly recommended XSync path and the XScreenSaver fallback. The provider profile maps both so the eventual package build is not accidentally reduced to a weaker path.

### Qt Designer plugins

`kitemviews`, `kplotting` and `kwidgetsaddons` enable their Qt Designer plugins by default when not cross-compiling. Their designer subdirectories use ECM's `ECMAddQtDesignerPlugin`; that path requires Qt `UiPlugin`.

The provider mapping therefore includes `qt6-tools-dev`. This is classified as a default-enabled Qt component, not as a new KDE Framework dependency.

### Generators and language tooling

- `kholidays`: Flex and Bison >= 3.3.2 are required.
- `solid`: Flex and Bison >= 3.0 are required.
- `syntax-highlighting`: Perl is required; XercesC and Python remain optional tooling/features.
- `ki18n`: Python is required for installed i18n tooling. On the selected glibc platform, libintl functionality is supplied by libc rather than a separate provider package.
- `kuserfeedback`: Flex/Bison, PHP and PHPUnit are upstream recommended/non-fatal dependencies and remain classified that way.

### Platform/service libraries

- `kcalendarcore`: libical >= 3.0.
- `kcoreaddons`: libmount is required on Linux; root-level udev discovery remains optional.
- `modemmanager-qt`: ModemManager >= 1.0.
- `networkmanager-qt`: libnm >= 1.4.0 and GIO 2.0.
- `solid`: libmount and udev are required for the selected Linux default backend set.

Optional Solid iOS-device support (`libimobiledevice` + `libplist`) remains optional and is not a build gate merely because Resolute can provide it.

### Prison barcode stack

With upstream defaults, `prison` requires QRencode, Dmtx, ZXing, Qt Quick and Qt Multimedia. Dmtx and ZXing become mandatory in this selected profile because `WITH_DMTX` and `WITH_ZXING` default to ON; scanner support also keeps the default `WITH_MULTIMEDIA=ON` path.

### Sonnet spell backends

Sonnet discovers Aspell, HSpell, Hunspell and Voikko. Each individual backend is optional, but on the selected non-Android build Sonnet fails if **none** can be built.

The manifest therefore models an upstream `required_any_of` group. The provider preflight installs every mapped backend candidate that Resolute actually exposes while gating only the upstream invariant: at least one candidate must exist.

HSpell is a packaging exception worth recording explicitly: the Debian/Ubuntu development surface is mapped through the `hspell` package. SupraLINUX must not invent a `libhspell-dev` package. The hosted preflight also checks for the actual HSpell header/library when that candidate is installed.

## Qt component extensions

The existing Qt-provider preflight remains the qualification path for the selected Ubuntu Qt candidate. Tier 1 adds component-level needs on top of that baseline, notably `GuiPrivate`, `WaylandClient`, `ShaderTools`, `Multimedia` for Prison, `UiPlugin` for default Designer plugins, and `Charts` as a recommended KUserFeedback feature.

The Tier 1 dependency preflight checks provider coherence; it does not redefine the Qt version and does not constitute final Qt certification.

## Evidence semantics

Before the hosted workflow runs:

- upstream dependency resolution: **resolved**;
- Ubuntu package-name mapping: **resolved**;
- Ubuntu provider availability/version evidence: **pending**;
- Tier 1 packaging: **pending**;
- Tier 1 build state: **pending**.

A successful `.github/workflows/kde-tier1-dependency-preflight.yml` run may promote only the provider-availability claim. It must not mark any Framework node PASS.

The real package-build campaign remains the proof for package correctness and is where PASS/FAIL/BLOCKED begins to apply.
