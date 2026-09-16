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

## Batch 6 selection

KWindowSystem and Solid are the next package candidates. This does not change authority: KDE upstream 6.30.0 defines requirements; Ubuntu Resolute is only a provider. KWindowSystem retains QML, X11 and Wayland with Wayland Protocols >= 1.46 and Plasma Wayland Protocols. Solid retains DBus, udev and libmount; IMobileDevice/PList remain upstream-optional and their Ubuntu providers are supplied rather than disabled. Canonical Tier 1 remains **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** until real package evidence is promoted.

## Batch 6 provider correction evidence

Initial run `35034742520` proved the selected KDE 6.30 source reaches real package compilation on Resolute. KWindowSystem exposed one packaging omission: upstream source includes `xcb/xfixes.h`, while the SupraLINUX Build-Depends lacked `libxcb-xfixes0-dev`. Both retained Debian 6.28 and Ubuntu 6.24 packaging trees include that provider, so revision `-2` adds it without changing KDE's X11/Wayland/QML feature selection.

Solid completed its build and `5/5` tests. Its failure was not a missing provider: Lintian rejected the toolchain-exported `_ZSt19piecewise_construct@Base`. Ubuntu's retained symbols baseline records this export at minimum `6.4.0` on architectures other than armhf/riscv64. SupraLINUX keeps the Debian 6.28 public ABI baseline and marks only that export `optional=toolchain` with the retained Ubuntu architecture/minimum-version evidence.

## Batch 6 second-attempt evidence

Run `35038057329` confirms the Solid provider/ABI remediation: Solid `6.30.0-0supralinux2` passed `5/5` tests, Lintian, SONAME and consumer smoke (artifact `10423914110`, SHA-256 `7cc2b15e2fa627e3cd280395e0ac48bd3658c7328d194958b872713738b97fc0`).

KWindowSystem `-2` also confirms `libxcb-xfixes0-dev` was the correct missing build provider: compilation now succeeds. The remaining failure is test-fixture-only. Upstream KDE's v6.30.0 tests require a NETWM-compliant X11 window manager and explicitly mention OpenBox on build.kde.org. Revision `-3` therefore adds `openbox <!nocheck>` plus `x11-utils <!nocheck>` and waits for `_NET_SUPPORTING_WM_CHECK` inside Xvfb; these are test providers and do not alter the runtime dependency contract.

## Batch 6 third-attempt test-fixture evidence

Run `35040999577` confirms that the OpenBox test provider and readiness check are correct: KWindowSystem `6.30.0-0supralinux3` compiles, OpenBox publishes `_NET_SUPPORTING_WM_CHECK`, the Wayland suite passes and CTest advances to `12/14` suites PASS. The retained FAIL evidence is job `104620609155`, artifact `10425162919`, SHA-256 `58481311a264849cbe78c166fcfd2e174d95bc56e04e32be9cab7efed3a2b9dc`.

The remaining failures are not unresolved providers. They occur because stateful X11 test executables share one Xvfb/OpenBox display while `dh_auto_test` inherits parallel test execution. One suite owns the global compositor selection and root-window effect properties; another expects the active-window signal count from a clean initial X11 state. KDE's own `kwindowsystemx11test.cpp` explicitly warns that `testActiveWindowChanged()` must be the first test because later X11 state would make it fail.

Revision `-4` keeps all dependency mappings and the same nocheck-only Xvfb/OpenBox test providers. It serializes only the `dh_auto_test` phase with `--no-parallel`, preserving normal build parallelism and every upstream X11/Wayland test. This is test-fixture execution policy, not a new runtime/provider contract and not a change in KDE authority.

## Batch 6 fourth-attempt runtime-closure evidence

Run `35046462679` proves the `-4` X11 execution policy: KWindowSystem passes **14/14 CTest suites**, `sbuild` completes and the Lintian error gate passes. The remaining FAIL is later at `consumer-smoke` (job `104637230834`, artifact `10426857754`, artifact ZIP SHA-256 `ec2af4fb475bfc11f91592d2f18190f39175334b21356b179fc8fd4e60e19ac2`).

This failure does **not** add a KDE runtime requirement and does not change the provider mapping. The built `libkf6windowsystem6` package already declares `libxcb-res0 (>= 1.10)`, while `readelf` correctly records `libxcb-res.so.0` as a needed library. The defect is in the hosted consumer-smoke runner: it extracted the locally built `.deb` set but did not materialize external runtime `Depends`, so the result leaked the host's preinstalled-library set.

The shared runner remediation installs the exact locally built `.deb` set through APT with `--no-install-recommends`, lets Ubuntu Resolute satisfy only external `Depends`, runs `apt-get check`, verifies exact installed SupraLINUX revisions, and still compiles/runs against the extracted built artifacts. This preserves the authority/provider boundary: KDE/package metadata decides the dependency contract; Ubuntu merely provides dependencies matching that contract.

Because this changes a shared Batch 6 build input, both KWindowSystem and the retained-PASS Solid node must revalidate. No package revision is bumped for this runner-only correction. Canonical Tier 1 remains **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** until the corrected lane passes and closure promotes the nodes.

<!-- BATCH6-CANONICAL-CLOSURE -->
## Batch 6 canonical closure

KWindowSystem `6.30.0-0supralinux4` and Solid `6.30.0-0supralinux2` are canonical hosted-clean-package-preflight PASS and downstream-eligible. Final evidence is workflow run `35047623320`: KWindowSystem job `104640833059`, artifact `10428130399`, ZIP SHA-256 `9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272`, 14/14 tests PASS; Solid job `104640833295`, artifact `10427653865`, ZIP SHA-256 `cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389`, 5/5 tests PASS. Both pass Lintian error gating, consumer smoke, exact local-package installation and `apt-get check`. The shared consumer-runtime closure remediation is therefore validated. Canonical Tier 1 is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. Historical FAIL attempts remain retained as evidence; BLOCKED remains distinct from FAIL.
