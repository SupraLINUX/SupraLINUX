# KDE Frameworks 6.30 Tier 1 — dependency resolution

Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping validated; canonical Tier 1 25 PASS / 4 pending after Batch 9 promotion**

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
- canonical Tier 1 package state: **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**;
- Batch 7 retained package evidence: **3/3 PASS and canonically promoted**;
- KGuiAddons: **PASS and canonically promoted**; local-predecessor lane completed without adding a Framework build dependency;
- final Qt provider certification: **pending**.

Provider evidence alone never promotes a Framework. Only retained package PASS artifacts may feed dependents.


## Batch 9 multi-ABI closure

KConfig, KI18n and Sonnet are canonical Tier 1 PASS nodes with no KDE Framework build predecessor beyond retained ECM. The Batch 9 multi-ABI runner validated their public/runtime surfaces without introducing undocumented Framework build edges.

KConfig preserves GUI/QML/DBus defaults and validates three runtime ABIs. KI18n preserves QML and upstream tests with the validated locale providers `iso-codes`, `language-pack-fr-base` and `locales-all`. Sonnet preserves Widgets, QML, Designer and spelling backends and validates two runtime ABIs plus a packaged backend plugin. Debian 6.28 symbol files remain hash-pinned technical baselines only and were materialized ephemerally during clean builds.

Source diagnostic run `35138333645` remains non-promoting DIAG_PASS evidence; canonical promotion is based on retained real package PASS artifacts. Final promotion precheck Repository Policy run `35365719747` passed and all three package jobs scope-skipped. Canonical Tier 1 is **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**.


## Batch 9 KConfig exported Qt QML development contract

KConfig 6.30's selected GUI/QML surface exports `KF6ConfigConfig.cmake`, which directly executes `find_dependency(Qt6Qml "6.9.0")`. That consumer requirement is defined by the KDE/Qt build metadata; Ubuntu does not define whether the dependency exists.

Validation cycle 4 (run `35358920602`, KConfig job `105645094816`) proved that the package itself builds, passes `90/90` upstream tests, Lintian, architecture-aware ABI checks, exact local-package APT closure and QML import scanning, but a clean external CMake consumer cannot configure when only the previous `libkf6config-dev` dependency set is installed.

Ubuntu 26.04 Resolute provides the needed development CMake/QML surface through `qt6-declarative-dev 6.10.2+dfsg-3`. SupraLINUX therefore adds `qt6-declarative-dev (>= 6.9.0~)` to the binary `libkf6config-dev` Depends in revision `6.30.0-0supralinux4`. This is provider mapping for a KDE-exported requirement, not an Ubuntu-authored KDE dependency or a change to upstream defaults.


Final proof: KConfig `6.30.0-0supralinux4` passed run `35360530830`, job `105650448776`, artifact `10554715051` after the binary development dependency was added. The clean external consumer configure/build/run gate passed, so the `Qt6Qml >= 6.9.0` provider mapping is validated rather than merely inferred.


## Batch 9 technical closure

The multi-ABI lane is complete and canonically promoted:

- KConfig `6.30.0-0supralinux4`: run `35360530830`, job `105650448776`, artifact `10554715051`, SHA-256 `bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e`, `90/90 PASS`;
- KI18n `6.30.0-0supralinux1`: run `35358920602`, job `105645094825`, artifact `10553916882`, SHA-256 `2a0d66f2760c49ba1128b8b51c741173a72e6f3ab51f3eb17c3584896d30a678`, `17/17 PASS`;
- Sonnet `6.30.0-0supralinux3`: run `35358920602`, job `105645094787`, artifact `10554216487`, SHA-256 `ae5a33cf8699b96b7b7b8c1a83bc4d37a484878029818c1885b4f4f44f15b431`, `8/8 PASS`.

All three pass Lintian, exact local-package APT closure, QML import scanning and C++ consumer validation. The remaining provider work belongs to the four unpromoted Tier 1 nodes; provider availability does not alter KDE authority.


## Batch 10 Kirigami / KQuickCharts package-validation ordering

Kirigami and KQuickCharts remain Tier 1 at the KDE Framework build-DAG level: both have `kde_framework_build_dependencies=[]`, and the retained 6.30 source diagnostic compiled KQuickCharts with its Qt provider set without introducing a Kirigami build edge.

The packaged KQuickCharts QML surface is different: `qml6-module-org-kde-quickcharts` requires the `org.kde.kirigami` QML runtime surface. SupraLINUX therefore models Kirigami as a **package-validation predecessor** only. KQuickCharts full APT/QML/consumer validation consumes a retained SupraLINUX Kirigami PASS artifact and verifies the installed Kirigami QML package at the exact campaign version. Ubuntu's KDE package must not silently satisfy that closure.

### Batch 10 cycle 1 evidence

PR CI `35389030840` exercised the package-validation edge exactly as designed: Kirigami was attempted and failed its own Lintian symbols contract; KQuickCharts was not attempted and was recorded BLOCKED by Kirigami. This remains a package-validation ordering relation only and does not create a `KQuickCharts -> Kirigami` KDE Framework build dependency.

### Batch 10 cycle 2 consumer-package contract

The built Kirigami development package proves the consumer-facing CMake contract directly: it installs `KF6KirigamiPlatformConfig.cmake`, which exports `KF6::KirigamiPlatform` and resolves Qt6 Core/Qml/Quick. The prior consumer test incorrectly searched for an umbrella `KF6Config.cmake` that Kirigami does not install.

Correcting the consumer harness does not alter KDE Framework build dependencies, package-validation ordering or provider authority. KQuickCharts remains a package-validation dependent only.

### Batch 10 cycle 3 retained predecessor proof

Run `35398956698` proved both sides of the package-validation relation. Kirigami `6.30.0-0supralinux2` completed every package gate and became a retained PASS. KQuickCharts job `105776448807` then downloaded that current-run artifact and verified all 19 Kirigami binary packages at exactly the SupraLINUX version before entering its own `sbuild`.

The subsequent QuickCharts FAIL is therefore local to its own symbols metadata, not a predecessor/provider failure. The next QuickCharts-only remediation may reuse Kirigami through campaign `pass_evidence`; this still does not create a KDE Framework build dependency.

## Batch 10 cycle 4 packaging-time QML dependency

Run `35400585402` proves the retained-predecessor path: KQuickCharts consumed the retained Kirigami PASS package set, passed `8/8` upstream tests and the reviewed symbols remediation, then failed only when `dh_qmldeps` could not resolve `org.kde.kirigami` inside the package-build environment.

For `6.30.0-0supralinux3`, `qml6-module-org-kde-kirigami (>= 6.30.0~)` is therefore a **Debian/QML packaging-time dependency**. It exists so `dh_qmldeps` can inspect the imported module while generating binary metadata. It is not a KDE Framework/CMake build dependency: KQuickCharts keeps `kde_framework_build_dependencies=[]`, does not add `libkirigami-dev`, and its upstream source-build dependency model is unchanged. The runner still enforces that Kirigami comes from retained/current SupraLINUX PASS evidence.

## Batch 10 cycle 6 ABI reference versus effective floor

KQuickCharts keeps Debian 6.28 as a technical ABI reference, not an authority. The retained `libquickcharts1.symbols` baseline has 393 exports, 2 optional exports and 9 non-optional exports inapplicable on amd64, so its historical required amd64 floor is 382.

SupraLINUX's reviewed symbols remediation changes two **existing** amd64 `std::_Sp_counted_ptr<QQuickItem *>` RTTI/vtable entries from required to `optional=templinst|arch=!riscv64`. That does not rewrite the historical baseline metadata: `reference_required_export_count_amd64` remains 382. It creates an explicit reviewed runtime contract `effective_required_export_count_amd64=380`. Run `35403658149` generated 381 QuickCharts exports, which is above that effective floor.

The runner now uses the effective floor only when the campaign records one explicitly; otherwise it falls back to the retained reference floor. This preserves both provenance and the reviewed remediation semantics.

## Batch 10 cycle 7 exported ECM consumer contract

KQuickCharts remains free of KDE Framework build dependencies. Separately, its installed KDE 6.30 development CMake config has an exported consumer requirement:

`KF6QuickChartsConfig.cmake -> find_dependency(ECM 6.30.0) -> ECMFindQmlModule.cmake`.

Therefore `libquickcharts-dev` must depend on `extra-cmake-modules (>= 6.30.0~)`. This is a **binary development/consumer dependency**, not a `kde_framework_build_dependencies` edge. KDE's exported config defines the need; SupraLINUX supplies its retained ECM `6.30.0-0supralinux3` PASS package.

Cycle 7 proved the omission in a clean consumer after all earlier gates passed. The Batch 10 consumer gate now includes the retained ECM package in the local install transaction and verifies the installed version exactly, so Ubuntu's older ECM cannot satisfy the contract.
