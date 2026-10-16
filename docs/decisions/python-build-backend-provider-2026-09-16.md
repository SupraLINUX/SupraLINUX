# Python wheel backend provider for KDE Frameworks 6.30 bindings

Status: **PASS — Ubuntu Resolute provider validated**

Date: **2026-09-16**

## Scope

This decision applies to Frameworks that keep KDE 6.30 Python bindings enabled and whose ECM-generated binding build executes:

`python3 -m build --wheel --no-isolation`

It currently affects Batch 7 (`kcalendarcore`, `kcoreaddons`, `kwidgetsaddons`) and will also apply to later binding-enabled Frameworks such as `kguiaddons`.

## Authority versus provider

KDE/ECM remains the authority for whether Python bindings are built and for the build flow. Ubuntu Resolute is only a provider of the Python packaging tools used to satisfy that upstream-selected flow.

`python3-build` provides the PEP 517 frontend (`python -m build`). It does not provide the Setuptools backend used by the generated wheel project. With `--no-isolation`, the backend must already exist in the clean package build environment.

SupraLINUX therefore treats `python3-setuptools` as a **shared packaging-tool provider** for the ECM binding lane. This does not change KDE source, disable bindings, change tests, alter KWidgetsAddons Designer support, or change the Debian Python layout `DEB_PYTHON_INSTALL_LAYOUT=deb`.

## Evidence that exposed the omission

Batch 7 remediation run `35103681715` attempted all three independent nodes at revision `6.30.0-0supralinux2`.

The previous Clang/LLVM remediation worked: Shiboken generated wrappers and each build reached final Python extension linking. All three then failed while invoking the wheel frontend because the backend was absent:

`BackendUnavailable: Cannot import 'setuptools.build_meta'`

Retained FAIL evidence:

- KCalendarCore: job `104819252283`, artifact `10449348134`, artifact SHA-256 `5e24d94981c060541e008c81ef6e76e3f785b5e52fe249206aa117920c9d7040`;
- KCoreAddons: job `104819252182`, artifact `10449846512`, artifact SHA-256 `17df43995650455389ee2f0d565ed966dd536abaeaf6f56bb44877c762c478af`;
- KWidgetsAddons: job `104819252378`, artifact `10449886366`, artifact SHA-256 `0ded038e3a2b7cac8bc94dc5eb61e8183cc1cdcc45284d0040ddbc4ee9670760`.

All three failures occurred at `stage: sbuild`. None is `BLOCKED`.

## Provider validation

Provider-only commit `78760b565dd49e981fa0891535da289120b40470` intentionally did not alter the Batch 7 package trees.

Repository Policy passed in run `35106561229`.

The hosted dependency-provider preflight passed in run `35106561251`, job `104829186807`, artifact `10450572112`, SHA-256 `488592048a0514b8f6234e8820c959817a151782fef41c138b71f7a8b7fe8fc4`.

Retained evidence proves:

- `python3-build 1.4.0-1`: frontend import PASS;
- `python3-setuptools 78.1.1-0.1build1`: installed from Ubuntu Resolute;
- `setuptools.build_meta`: import PASS;
- Qt/PySide/Shiboken baseline remains `6.10.2`;
- provider claim remains non-authoritative and limited to availability.

Batch 7 run `35106561165` for the provider-only commit skipped all three package builds intentionally, confirming the semantic scope gate.

## Packaging consequence

Batch 7 revision `6.30.0-0supralinux3` may now add exactly `python3-setuptools` to the three package Build-Depends while retaining:

- KDE Frameworks 6.30.0 sources unchanged;
- `BUILD_PYTHON_BINDINGS=ON`;
- `BUILD_TESTING=ON`;
- `BUILD_DESIGNERPLUGIN=ON` for KWidgetsAddons;
- `DEB_PYTHON_INSTALL_LAYOUT=deb`;
- the validated Clang/LLVM binding-generator toolchain.

The package revision must still pass its own clean `sbuild`, tests, Lintian, binary contracts, Python import and C++ consumer smoke before any node is promoted.

## State separation

The canonical promoted Tier 1 state remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. The Batch 7 attempt ledger separately retains the real package failures. No Batch 7 node is downstream-eligible yet.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
