# KDE Frameworks 6.30 Tier 1 — dependency resolution

Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping validated; 18 canonical package PASS / 11 pending; newer Batch 7 PASS evidence awaits canonical promotion**

Last reviewed: **2026-09-16**

## Contract

This document separates two questions:

- **Authority:** KDE Frameworks 6.30.0 defines required dependencies, minimums, enabled/default features and build behavior.
- **Provider:** Ubuntu Resolute may provide packages that satisfy those requirements. Provider choice does not make Ubuntu authoritative over KDE.

The authoritative source inputs and KDE build metadata remain pinned in `manifests/kde-frameworks-tier1.json` and `manifests/kde-frameworks-tier1-dependencies.json`. Debian/Ubuntu packaging is a technical reference only.

The provider model distinguishes required, default-enabled, recommended, optional, runtime and required-any-of dependencies. SupraLINUX does not disable a KDE default merely because a downstream distribution chose a different profile.

## Python bindings and ECM wheel path

`kcalendarcore`, `kcoreaddons`, `kguiaddons` and `kwidgetsaddons` enable Python bindings on the selected Linux/shared-library path. The complete provider surface discovered and validated for the current ECM/Shiboken path is:

- `python3-dev`;
- `libshiboken6-dev`;
- `libpyside6-dev`;
- `python3-build`;
- `python3-setuptools`;
- `clang`;
- `libclang-dev`;
- `llvm-dev`.

`DEB_PYTHON_INSTALL_LAYOUT=deb` keeps the installed Python modules in the Debian-compatible system layout. Python bindings remain enabled; these packages are provider corrections, not feature reductions.

### Evidence chain

The initial provider revalidation run `35087361837`, job `104765243282`, artifact `10442512801`, artifact SHA-256 `49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9`, proved Resolute provides `python3-build 1.4.0-1`; `import build` reported module version `1.4.0`. PySide6/Shiboken6 remained aligned with the selected Qt provider at Qt 6.10.2. This is provider evidence only.

The first real Batch 7 package run `35102198701` then exposed a distinct clean-sbuild requirement: Shiboken/ApiExtractor could not locate Clang built-in headers or `llvm-config`. The package profiles therefore added `clang`, `libclang-dev` and `llvm-dev`. This preserved `BUILD_PYTHON_BINDINGS=ON`.

Run `35103681715` proved that correction worked: all three Batch 7 nodes passed wrapper generation and final Python-extension linking, but ECM's `python3 -m build --wheel --no-isolation` then failed because `setuptools.build_meta` was unavailable in the build environment.

Provider run `35106561251`, job `104829186807`, artifact `10450572112`, SHA-256 `488592048a0514b8f6234e8820c959817a151782fef41c138b71f7a8b7fe8fc4`, validated Resolute `python3-setuptools 78.1.1-0.1build1` and successful import of `setuptools.build_meta`. The package profiles then added `python3-setuptools` explicitly.

The final proof is the package lane itself: KCoreAddons `6.30.0-0supralinux4` is retained PASS with 34/34 tests, and KCalendarCore `6.30.0-0supralinux5` is retained PASS with 507/507 tests. KWidgetsAddons `-6` also completed Python generation, binary build and 27/27 upstream tests before failing later at a packaging-only Lintian gate. This confirms the binding provider chain without turning provider packages into KDE authority.

## X11 and Wayland

The selected Linux defaults retain X11 and Wayland wherever KDE enables them.

- `kguiaddons`: X11/XCB, Wayland client >= 1.9, Wayland Protocols >= 1.39 and Plasma Wayland Protocols >= 1.15.0; Qt 6.10 also needs the Qt Gui private surface on enabled Wayland/DBus paths.
- `kidletime`: X11/XCB Sync plus the Wayland idle path.
- `kwindowsystem`: X11/XCB plus Wayland Protocols >= 1.46 and Plasma Wayland Protocols.

The strongest selected Tier 1 Wayland Protocols floor is therefore >= 1.46. Resolute provider evidence has satisfied that floor. KWindowSystem's retained PASS also validates its X11/Wayland package path.

## Qt Designer plugins

`kitemviews`, `kplotting` and `kwidgetsaddons` retain the upstream Designer-plugin path. `qt6-tools-dev` provides the Qt `UiPlugin` development surface.

KWidgetsAddons additionally demonstrates why package splits must consume generated runtime substvars: its Designer plugin is packaged in `libkf6widgetsaddons-dev`, so `${shlibs:Depends}` must be present in that binary package's `Depends`. This is a Debian package-contract requirement caused by the shared object being shipped there, not a new KDE dependency.

## Translation tooling and locale data

ECM `ECMPoQmTools` uses Qt 6 LinguistTools; Resolute provides that surface through `qt6-tools-dev`. Missing it caused the historical KGlobalAccel and KSyntaxHighlighting `-1` package FAILs; their corrected `-2` revisions passed.

KI18n requires Python for installed tooling and relies on libc/gettext behavior on glibc systems. The source-diagnostic lane established a separate test-fixture contract for its locale-sensitive tests:

- `locales-all` for compiled locales;
- `language-pack-fr-base` for the required French iso-codes catalogs;
- `en_US.UTF-8` and `fr_CH.UTF-8` present;
- `LC_ALL` must not override the locale selections made by upstream tests.

Diagnostic run `35138333645` validates the resulting unchanged upstream KI18n suite. This evidence is non-promoting and does not replace package gates.

## Generators and language tooling

- `kholidays`: Flex and Bison >= 3.3.2.
- `solid`: Flex and Bison >= 3.0.
- `syntax-highlighting`: Perl required; XercesC remains optional validation tooling and is enabled in the selected provider profile.
- `kuserfeedback`: Flex/Bison, PHP and PHPUnit follow upstream's recommended/non-fatal profile.

## Platform/service libraries

- `kcalendarcore`: libical >= 3.0.
- `kcoreaddons`: libmount required on Linux; root-level udev discovery remains optional.
- `modemmanager-qt`: KDE probes pkg-config module `ModemManager >= 1.0`; Resolute provider is `modemmanager-dev`.
- `networkmanager-qt`: libnm >= 1.4.0 and GIO 2.0.
- `solid`: libmount and udev for the selected Linux backend set; IMobileDevice/PList remain optional.

The earlier ModemManager mapping to a related `mm-glib` development surface was corrected because it did not satisfy KDE's actual `FindModemManager.cmake` query. Targeted provider revalidation passed in run `35012023822`, job `104526071758`, artifact `10414525047`, SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`.

## Prison barcode stack

With the selected upstream defaults, Prison requires QRencode, Dmtx, ZXing, Qt Quick and Qt Multimedia. `WITH_DMTX`, `WITH_ZXING`, `WITH_QUICK` and `WITH_MULTIMEDIA` remain ON. Resolute ZXing `2.3.0-5` satisfies KDE's accepted config-package discovery path. Prison is `DIAG_PASS` in the global source lane; package PASS remains a separate gate.

## Sonnet spell backends

Sonnet discovers Aspell, HSpell, Hunspell and Voikko. Each is individually optional, but the selected non-Android build cannot proceed with no usable backend. SupraLINUX models this as required-any-of and supplies available providers. Debian/Ubuntu's HSpell development surface is provided by `hspell`; SupraLINUX does not invent a `libhspell-dev` package name.

## ABI/toolchain exports

Compiler/libstdc++ implementation exports are not treated as new KDE public APIs merely because `dpkg-gensymbols` observes them. The reviewed policy already used for BluezQt, ModemManagerQt, Solid and now KWidgetsAddons classifies `_ZSt19piecewise_construct@Base` as `(optional=toolchain)` with an upstream release minimum rather than the current Debian package revision.

Public KDE APIs are instead assigned the actual upstream introduction release after source comparison. Batch 7 applies this rule to KCoreAddons, KCalendarCore and KWidgetsAddons rather than suppressing Lintian.

## Retained package closure evidence

Batch 1 through Batch 6 are canonically closed. Representative later closures include:

- KWindowSystem `6.30.0-0supralinux4`: run `35047623320`, job `104640833059`, artifact `10428130399`, SHA-256 `9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272`, 14/14 tests PASS.
- Solid `6.30.0-0supralinux2`: run `35047623320`, job `104640833295`, artifact `10427653865`, SHA-256 `cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389`, 5/5 tests PASS.
- KCoreAddons `6.30.0-0supralinux4`: retained Batch 7 package PASS, canonical promotion pending.
- KCalendarCore `6.30.0-0supralinux5`: retained Batch 7 package PASS, canonical promotion pending.

Historical FAILs remain evidence after later PASS. BLOCKED remains distinct from FAIL.

## Current state

- upstream dependency resolution: **resolved**;
- Ubuntu Resolute package-name/provider mapping: **resolved for the current selected profiles**;
- hosted provider evidence: **PASS where recorded**;
- canonical Tier 1 package state: **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**;
- KCalendarCore and KCoreAddons: retained PASS awaiting canonical promotion;
- KWidgetsAddons: independent remediation lane;
- final Qt provider certification: **pending**.

Provider evidence alone never promotes a Framework. Only retained package PASS artifacts may become downstream predecessors.
