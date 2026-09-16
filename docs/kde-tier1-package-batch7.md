# KDE Frameworks 6.30 Tier 1 — package Batch 7

Status: **REVISION -3 PREPARED — two real FAIL attempts retained; no Batch 7 PASS yet**

Canonical promoted Tier 1 remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. The Batch 7 attempt ledger separately records real FAIL attempts for the three still-pending nodes.

## Selection

Batch 7 contains three independent nodes:

- `kcalendarcore`
- `kcoreaddons`
- `kwidgetsaddons`

KGuiAddons remains deferred because its public `KImageCache` development surface consumes KCoreAddons. Its package/development contract must be fed by a retained local KCoreAddons PASS, not an Ubuntu KDE package.

## KDE defaults retained

Upstream-layout run `35086226149`, job `104761571679`, artifact `10443202060`, SHA-256 `c50a32b26e18ee84173b5a00cbd85e0c2b380660be9d939eb489c370f1317e77`, established:

- `BUILD_PYTHON_BINDINGS=ON` for all three nodes;
- `BUILD_TESTING=ON` for all three;
- `BUILD_DESIGNERPLUGIN=ON` for KWidgetsAddons.

SupraLINUX keeps those KDE 6.30 defaults explicit. Debian Python packaging uses `DEB_PYTHON_INSTALL_LAYOUT=deb`; the bindings remain split into `python3-*` packages under `/usr/lib/python3/dist-packages`.

## Attempt 1 — revision -1

Run `35102198701` attempted all three nodes with `fail-fast: false`.

All three failed in `sbuild` because Shiboken/ApiExtractor could not locate Clang's built-in include/resource directory in the clean environment. The first remediation added `clang`, `libclang-dev` and `llvm-dev` without changing KDE source or disabling bindings/tests.

Artifacts:

- KCalendarCore: job `104814147716`, artifact `10448034196`, SHA-256 `c76b9900d622e5ae4ab5823771baeabcbe8e2e180811ed01ac18d42b99f792e4`;
- KCoreAddons: job `104814147979`, artifact `10449051854`, SHA-256 `d7943a390efd8610cdab14422085c6c534f0d5877ece6910f36d8a01288acba7`;
- KWidgetsAddons: job `104814148006`, artifact `10448668591`, SHA-256 `227370b1da6151ed68155e2dfc65252db77f68e6ec03ee8f5737550709c8b995`.

## Attempt 2 — revision -2

Repository Policy for the Clang/LLVM remediation passed in run `35103681773`.

Run `35103681715` then attempted all three `6.30.0-0supralinux2` packages. The Clang/LLVM correction worked: each build passed Shiboken wrapper generation and reached final Python extension linking.

The new common failure occurred when ECM invoked:

`python3 -m build --wheel --no-isolation`

All three failed with:

`BackendUnavailable: Cannot import 'setuptools.build_meta'`

Artifacts:

- KCalendarCore: job `104819252283`, artifact `10449348134`, SHA-256 `5e24d94981c060541e008c81ef6e76e3f785b5e52fe249206aa117920c9d7040`;
- KCoreAddons: job `104819252182`, artifact `10449846512`, SHA-256 `17df43995650455389ee2f0d565ed966dd536abaeaf6f56bb44877c762c478af`;
- KWidgetsAddons: job `104819252378`, artifact `10449886366`, SHA-256 `0ded038e3a2b7cac8bc94dc5eb61e8183cc1cdcc45284d0040ddbc4ee9670760`.

These are real `FAIL`, not `BLOCKED`.

## Setuptools provider gate

Ubuntu Resolute is only the provider. KDE/ECM remains authority over the binding build flow.

Provider-only commit `78760b565dd49e981fa0891535da289120b40470` passed Repository Policy in run `35106561229`.

Dependency-provider run `35106561251`, job `104829186807`, artifact `10450572112`, SHA-256 `488592048a0514b8f6234e8820c959817a151782fef41c138b71f7a8b7fe8fc4`, passed and proved:

- `python3-build 1.4.0-1` frontend import PASS;
- `python3-setuptools 78.1.1-0.1build1` installed from Resolute;
- `setuptools.build_meta` import PASS.

Batch 7 run `35106561165` intentionally skipped all three nodes for that provider-only delta.

## Revision -3

The `6.30.0-0supralinux3` package revision adds `python3-setuptools` to Build-Depends for all three nodes. It keeps:

- KDE 6.30.0 source hashes unchanged;
- Python bindings and tests enabled;
- KWidgetsAddons Designer plugin enabled;
- `clang`, `libclang-dev`, `llvm-dev`;
- `DEB_PYTHON_INSTALL_LAYOUT=deb`;
- retained ECM and packaging-tree predecessors.

## PASS gate

A node becomes PASS only after a real clean build proves source hash, `sbuild`, non-zero 100% CTest pass, expected binary set, SONAME, source+binary Lintian error gate, exact local package installation/`apt-get check`, Python import, C++ consumer configure/build/run and retained reproducibility evidence.

Until then KCalendarCore, KCoreAddons and KWidgetsAddons remain canonical `pending` and downstream-ineligible.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
