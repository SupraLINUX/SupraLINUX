# Python wheel backend provider for KDE Frameworks 6.30 bindings

Status: **provider revalidation pending**

Date: **2026-09-16**

## Scope

This decision applies to Frameworks that keep KDE 6.30 Python bindings enabled and whose ECM-generated binding build executes:

`python3 -m build --wheel --no-isolation`

It currently affects Batch 7 (`kcalendarcore`, `kcoreaddons`, `kwidgetsaddons`) and will also apply to later binding-enabled Frameworks such as `kguiaddons`.

## Authority versus provider

KDE/ECM remains the authority for whether Python bindings are built and for the build flow. Ubuntu Resolute is only a provider of the Python packaging tools used to satisfy that upstream-selected flow.

`python3-build` provides the PEP 517 frontend (`python -m build`). It does **not** provide the Setuptools backend used by the generated wheel project. With `--no-isolation`, build dependencies are not downloaded into an isolated environment; they must already exist in the clean package build environment.

SupraLINUX therefore treats `python3-setuptools` as a **shared packaging-tool provider** for the ECM binding lane. This does not change KDE source, disable bindings, change test defaults, or make Ubuntu authoritative over KDE.

## Evidence that exposed the omission

Batch 7 remediation run `35103681715` attempted all three independent nodes at revision `6.30.0-0supralinux2`.

The previous Clang/LLVM remediation worked: Shiboken generated wrappers and each build reached final Python extension linking. All three then failed while invoking the wheel frontend because the backend was absent:

`BackendUnavailable: Cannot import 'setuptools.build_meta'`

Retained FAIL evidence:

- KCalendarCore: job `104819252283`, artifact `10449348134`, artifact SHA-256 `5e24d94981c060541e008c81ef6e76e3f785b5e52fe249206aa117920c9d7040`;
- KCoreAddons: job `104819252182`, artifact `10449846512`, artifact SHA-256 `17df43995650455389ee2f0d565ed966dd536abaeaf6f56bb44877c762c478af`;
- KWidgetsAddons: job `104819252378`, artifact `10449886366`, artifact SHA-256 `0ded038e3a2b7cac8bc94dc5eb61e8183cc1cdcc45284d0040ddbc4ee9670760`.

All three failures occurred at `stage: sbuild`. None is `BLOCKED`.

## Provider candidate

Ubuntu Resolute publishes `python3-setuptools 78.1.1-0.1build1`. The existing Resolute `python3-build 1.4.0-1` already depends on `python3-wheel`, so no additional explicit Wheel provider is introduced solely for this failure.

Before Batch 7 revision `-3` is attempted, the hosted provider preflight must:

1. require a Resolute candidate for `python3-setuptools`;
2. install it in the hosted provider environment;
3. import `setuptools.build_meta` successfully;
4. retain the installed package version and provider evidence artifact.

Only after that gate passes may the Batch 7 package trees add `python3-setuptools` and advance to revision `6.30.0-0supralinux3`.

## State separation

The canonical promoted Tier 1 state remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. The Batch 7 attempt ledger separately retains the real package failures. No Batch 7 node is downstream-eligible yet.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
