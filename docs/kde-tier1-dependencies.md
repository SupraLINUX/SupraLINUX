# KDE Frameworks 6.30 Tier 1 — dependency resolution

Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping validated; canonical Tier 1 22 PASS / 7 pending after Batch 8 promotion**

Last reviewed: **2026-09-18**

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

`DEB_PYTHON_INSTALL_LAYOUT=deb` keeps installed Python modules in the Debian-compatible system layout. Python bindings remain enabled; these packages are provider corrections, not feature reductions.

### Evidence chain

Provider run `35087361837`, job `104765243282`, artifact `10442512801`, artifact SHA-256 `49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9`, proved Resolute provides `python3-build 1.4.0-1`; PySide6/Shiboken6 remained aligned with Qt 6.10.2.

The first real Batch 7 package run `35102198701` exposed the distinct clean-sbuild requirement for Clang built-ins/`llvm-config`. Adding `clang`, `libclang-dev` and `llvm-dev` preserved `BUILD_PYTHON_BINDINGS=ON`.

Run `35103681715` proved that toolchain correction worked, then exposed ECM's no-isolation wheel backend requirement. Provider run `35106561251`, job `104829186807`, artifact `10450572112`, SHA-256 `488592048a0514b8f6234e8820c959817a151782fef41c138b71f7a8b7fe8fc4`, validated Resolute `python3-setuptools 78.1.1-0.1build1` and successful import of `setuptools.build_meta`.

The package lane is final proof: KCoreAddons `6.30.0-0supralinux4`, KCalendarCore `6.30.0-0supralinux5` and KWidgetsAddons `6.30.0-0supralinux7` all retain real PASS results with Python import, Lintian and consumer-runtime closure gates. Provider packages remain providers, not KDE authority.

## X11 and Wayland

The selected Linux defaults retain X11 and Wayland wherever KDE enables them.

- `kguiaddons`: X11/XCB, Wayland client >= 1.9, Wayland Protocols >= 1.39 and Plasma Wayland Protocols >= 1.15.0; Qt 6.10 also needs the Qt Gui private surface on enabled Wayland/DBus paths.
- `kidletime`: X11/XCB Sync plus the Wayland idle path.
- `kwindowsystem`: X11/XCB plus Wayland Protocols >= 1.46 and Plasma Wayland Protocols.

The strongest selected Tier 1 Wayland Protocols floor is therefore >= 1.46. Resolute provider evidence satisfies that floor.

## Qt Designer plugins

`kitemviews`, `kplotting` and `kwidgetsaddons` retain the upstream Designer-plugin path. `qt6-tools-dev` provides the Qt `UiPlugin` development surface.

KWidgetsAddons also demonstrates why package splits must consume generated runtime substvars: its Designer plugin is packaged in `libkf6widgetsaddons-dev`, so `${shlibs:Depends}` is required in that binary package's `Depends`. This is a Debian package-contract requirement caused by the shared object being shipped there, not a new KDE dependency.

## Translation tooling and locale data

ECM `ECMPoQmTools` uses Qt 6 LinguistTools; Resolute provides that surface through `qt6-tools-dev`. Missing it caused historical KGlobalAccel and KSyntaxHighlighting package FAILs; corrected revisions passed.

KI18n requires Python for installed tooling and relies on libc/gettext behavior on glibc systems. Its source-diagnostic fixture supplies `locales-all` plus `language-pack-fr-base`, preserves `en_US.UTF-8`/`fr_CH.UTF-8`, and avoids an `LC_ALL` override. Diagnostic run `35138333645` validates the unchanged upstream suite. Diagnostic PASS remains non-promoting.

## Platform/service providers

- `kcalendarcore`: libical >= 3.0.
- `kcoreaddons`: libmount required on Linux; root-level udev discovery remains optional.
- `modemmanager-qt`: KDE probes pkg-config module `ModemManager >= 1.0`; Resolute provider is `modemmanager-dev`.
- `networkmanager-qt`: libnm >= 1.4.0 and GIO 2.0.
- `solid`: libmount and udev for the selected Linux backend set; IMobileDevice/PList remain optional.

Targeted ModemManager provider evidence passed in run `35012023822`, job `104526071758`, artifact `10414525047`, SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`.

## ABI/toolchain exports

Compiler/libstdc++ implementation exports are not treated as new KDE public APIs merely because `dpkg-gensymbols` observes them. The reviewed policy used for BluezQt, ModemManagerQt, Solid and KWidgetsAddons classifies `_ZSt19piecewise_construct@Base` as `(optional=toolchain)` with an upstream release minimum rather than the current Debian package revision.

Public KDE APIs instead use their actual upstream introduction release after source comparison. Batch 7 applies this rule to KCoreAddons, KCalendarCore and KWidgetsAddons without suppressing Lintian.

<!-- BATCH6-CANONICAL-CLOSURE -->
## Batch 6 canonical closure

KWindowSystem `6.30.0-0supralinux4` and Solid `6.30.0-0supralinux2` remain canonical hosted-clean-package-preflight PASS and downstream-eligible. Final evidence is workflow run `35047623320`: KWindowSystem job `104640833059`, artifact `10428130399`, ZIP SHA-256 `9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272`, 14/14 tests PASS; Solid job `104640833295`, artifact `10427653865`, ZIP SHA-256 `cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389`, 5/5 tests PASS. Both pass Lintian, consumer smoke, exact local-package installation and `apt-get check`. Canonical Tier 1 at the Batch 6 closure is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**.

## Batch 7 technical closure

Batch 7 is **3/3 PASS and canonically promoted**:

- KCoreAddons `6.30.0-0supralinux4`: run `35122522242`, artifact `10457958023`, SHA-256 `c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`, 34/34 tests PASS.
- KCalendarCore `6.30.0-0supralinux5`: run `35130213945`, artifact `10461386548`, SHA-256 `6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6`, 507/507 tests PASS.
- KWidgetsAddons `6.30.0-0supralinux7`: run `35145607543`, artifact `10467164025`, SHA-256 `f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e`, 27/27 tests PASS.

All three pass Lintian error gating, Python import where applicable, exact local-package APT closure and C++ consumer smoke. KWidgetsAddons preserves all upstream tests and the Designer plugin; its final remediation is packaging-only.

Historical FAIL attempts remain retained in `manifests/kde-tier1-package-batch7-attempts.json`. BLOCKED remains distinct from FAIL.

## Batch 8 technical closure

KGuiAddons `6.30.0-0supralinux2` is a retained package PASS from run `35185562846`, job `105086774400`, artifact `10482007092`, SHA-256 `71d32ecb50f6617ba198325a552e68e995c20c9050c7ae21f6a69d5b680184ca`, with `9/9 PASS`, Lintian error gate PASS, Python import PASS, exact APT closure and consumer smoke PASS.

This does not introduce a KCoreAddons build edge. KGuiAddons' KDE Framework build dependency list remains empty; `libkf6coreaddons-dev` is required by the public KImageCache development surface and is supplied from the retained SupraLINUX KCoreAddons PASS only for consumer validation.

## Current state

- upstream dependency resolution: **resolved**;
- Ubuntu Resolute package-name/provider mapping: **resolved for the current selected profiles**;
- hosted provider evidence: **PASS where recorded**;
- canonical Tier 1 package state: **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED**;
- Batch 7 retained package evidence: **3/3 PASS and canonically promoted**;
- KGuiAddons: **PASS and canonically promoted**; local-predecessor lane completed without adding a Framework build dependency;
- final Qt provider certification: **pending**.

Provider evidence alone never promotes a Framework. Only retained package PASS artifacts may feed dependents.


## Batch 9 multi-ABI readiness

KConfig, KI18n and Sonnet remain Tier 1 pending nodes with no KDE Framework build predecessor beyond retained ECM. The Batch 9 multi-ABI runner is now implemented and all three are independently runnable in parallel. Public/runtime surfaces are validated after build; they do not create undocumented Framework build edges.

KConfig preserves GUI/QML/DBus defaults and validates three runtime ABIs. KI18n preserves QML and upstream tests with the validated locale providers `iso-codes`, `language-pack-fr-base` and `locales-all`. Sonnet preserves Widgets, QML, Designer and spelling backends and validates two runtime ABIs plus a packaged backend plugin. Debian 6.28 symbol files remain hash-pinned technical baselines only and are materialized ephemerally during clean builds.

Source diagnostic run `35138333645` is non-promoting DIAG_PASS evidence. Canonical Tier 1 therefore remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until real Batch 9 package attempts pass their full gates.
