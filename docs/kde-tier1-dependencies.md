# KDE Frameworks 6.30 Tier 1 — dependency resolution

Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping resolved; hosted provider preflight PASS; Attica package PASS; 28 package nodes pending**  
Last reviewed: **2026-09-12**

## Contract

This document separates two questions:

- **Authority:** what KDE Frameworks 6.30.0 requires or enables in its selected Linux/default build paths.
- **Provider:** which Ubuntu Resolute packages may satisfy those requirements for SupraLINUX.

The authoritative dependency inputs are the exact KDE `v6.30.0` build files recorded, with blob SHA pins, in `manifests/kde-frameworks-tier1-dependencies.json`. Ubuntu/Debian names are provider mappings only.

The dependency manifest distinguishes `required`, `default_enabled`, `recommended`, `optional`, `runtime` and `required_any_of`. This prevents optional features from becoming accidental architecture requirements and prevents default-enabled KDE features from being silently dropped because a distro package is inconvenient.

## Resolved dependency groups

### Compression and archive support

`karchive` defaults to all four support switches enabled and therefore requires zlib, bzip2, liblzma/xz, OpenSSL and libzstd/pkg-config in the selected build profile. Resolute mappings are `zlib1g-dev`, `libbz2-dev`, `liblzma-dev`, `libssl-dev`, `libzstd-dev` and `pkgconf`.

### Python bindings

`kcalendarcore`, `kcoreaddons`, `kguiaddons` and `kwidgetsaddons` enable Python bindings by default on the selected Linux/shared-library paths. Their profile includes Python >= 3.9 development files, Shiboken6 and PySide6. Resolute maps these to `python3-dev`, `libshiboken6-dev` and `libpyside6-dev`.

The hosted PASS verifies that Shiboken6 and PySide6 normalize to the same upstream Qt patch level as the selected Ubuntu Qt candidate: **6.10.2**.

### X11 and Wayland

The selected Linux defaults retain both X11 and Wayland paths where KDE enables them.

Important requirements include:

- `kguiaddons`: X11/XCB, Wayland client >= 1.9, wayland-protocols >= 1.39, plasma-wayland-protocols >= 1.15.0;
- `kidletime`: X11/XCB Sync plus a usable idle poller, Wayland client >= 1.9, wayland-protocols >= 1.27, plasma-wayland-protocols >= 1.6.0;
- `kwindowsystem`: X11/XCB components and wayland-protocols >= 1.46 plus plasma-wayland-protocols.

The strongest selected Tier 1 constraint therefore gates the provider at `wayland-protocols >= 1.46`. The hosted PASS observed Resolute `wayland-protocols 1.47-1`, `libwayland-dev 1.24.0-2` and `plasma-wayland-protocols 1.20.0-2`.

KIdleTime records both the strongly recommended XSync path and the XScreenSaver fallback. The provider profile maps both so the eventual package build is not accidentally reduced to a weaker path.

### Qt Designer plugins

`kitemviews`, `kplotting` and `kwidgetsaddons` enable their Qt Designer plugins by default when not cross-compiling. Their designer paths use ECM's `ECMAddQtDesignerPlugin`, which requires Qt `UiPlugin`.

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

With upstream defaults, `prison` requires QRencode, Dmtx, ZXing, Qt Quick and Qt Multimedia. Dmtx and ZXing become mandatory in this selected profile because `WITH_DMTX` and `WITH_ZXING` default to ON; scanner support also keeps `WITH_MULTIMEDIA=ON`.

Prison 6.30 probes ZXing config packages in order `3.0`, `2.0`, `1.4.0` and accepts the first one exposing `ZXing::ZXing`. The preflight mirrors that strategy. Resolute ZXing `2.3.0-5` passes both the Debian-version floor and KDE's discovery path.

### Sonnet spell backends

Sonnet discovers Aspell, HSpell, Hunspell and Voikko. Each individual backend is optional, but on the selected non-Android build Sonnet fails if **none** can be built.

The manifest models this as an upstream `required_any_of` group. The provider preflight installs every mapped backend candidate Resolute exposes while gating the upstream invariant: at least one candidate must exist.

HSpell is a packaging exception: Debian/Ubuntu provides its development header/library through `hspell`; SupraLINUX must not invent `libhspell-dev`.

## Hosted provider evidence

First valid hosted provider PASS:

- run `34700048774`;
- PR head `6ce61bc02c4aba146bcc33b16d17f56fb66f057a`;
- artifact `10299608166`;
- artifact SHA-256 `da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3`;
- result: `status=PASS`, `provider_candidate=ubuntu-resolute`, provider evidence only.

Historical runs `34699717549` and `34699889060` remain gate-implementation FAIL evidence; neither is a Framework node FAIL because no Framework was attempted.

## First package evidence using this dependency model

Attica's upstream dependency surface is ECM 6.30 + Qt Core/Network >=6.9, with Qt Test/Widgets used by its enabled tests/examples. Its successful package run demonstrates that the provider/dependency model can feed a real Framework build without allowing Ubuntu's older Frameworks stack to substitute for the selected KDE stack.

Attica PASS:

- package `6.30.0-0supralinux2`;
- run `34706416753`;
- artifact `10301851297`;
- artifact SHA-256 `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`;
- tests 6/6 PASS;
- consumer PASS against Ubuntu Qt 6.10.2;
- retained ECM predecessor `6.30.0-0supralinux3`;
- current Attica state PASS/downstream eligible.

This one package PASS does not promote the remaining 28 Frameworks or constitute final Qt-provider certification.

## Qt component extensions

The existing Qt-provider preflight remains the qualification path for the selected Ubuntu Qt candidate. Tier 1 adds component-level needs on top of that baseline, notably `GuiPrivate`, `WaylandClient`, `ShaderTools`, `Multimedia` for Prison, `UiPlugin` for default Designer plugins and `Charts` as a recommended KUserFeedback feature.

The Tier 1 provider preflight proves provider availability/coherence only. It does not redefine Qt and does not constitute final Qt certification.

## Evidence state

Current state:

- upstream dependency resolution: **resolved**;
- Ubuntu package-name mapping: **resolved**;
- Ubuntu hosted provider availability/version evidence: **PASS**;
- Attica package/build state: **PASS**, downstream eligible;
- remaining Tier 1 package/build states: **28 pending**;
- current Tier 1 FAIL: **0**;
- current Tier 1 BLOCKED: **0**;
- final Qt provider certification: **pending**.

No Framework node is promoted by provider evidence alone. Attica is PASS because its package was actually attempted and passed; unattempted Frameworks remain pending.
