# KDE Frameworks 6.30 Tier 1 — package batch 3

Status: **PASS — canonical closure complete**

Last reviewed: **2026-09-15**

## Selection

Batch 3 contains three independent Tier 1 nodes:

- `kitemmodels`;
- `bluez-qt`;
- `kplotting`.

All depend only on retained ECM `6.30.0-0supralinux3` inside the KDE DAG; none depends on another KDE Framework.

KDE Frameworks `6.30.0` remains the selected stable upstream release and KDE upstream remains the source/build authority. Ubuntu Resolute is the compatibility target/provider. Debian sid 6.28 packaging is used only as a technical ABI/packaging reference.

## Why these nodes

The current package runner models one primary ABI library, one SONAME and one symbols baseline per node. KItemModels, BluezQt and KPlotting fit that model and have contained external dependency profiles.

`KConfig` remains intentionally deferred. It exports multiple ABI libraries/symbol files (`ConfigCore`, `ConfigGui`, `ConfigQml`), so packaging it correctly requires an explicit multi-library extension of the runner rather than forcing it into a single-library model.

## Packaging policy

KItemModels and KPlotting remain at revision `6.30.0-0supralinux1`. BluezQt is certified at `6.30.0-0supralinux2` after its reviewed symbols remediation.

Debian-family binary package names and Multi-Arch contracts are preserved as compatibility inputs. The retained Debian 6.28 symbols files came from workflow `34708030450`, artifact `10301938362`; they do not select the KDE version. KDE 6.30 remains authoritative.

QCH is disabled in the current common Frameworks profile. Documentation package names are retained as compatibility stubs and do not claim QCH payload. Upstream autotests remain enabled.

## Attempt 1 — run 34896417969

All three nodes were actually attempted from commit `806d16476b034e796658ea1ab9028eb3a9a14e1b`.

### KItemModels — PASS retained

- job `104151531993`;
- package `6.30.0-0supralinux1`;
- artifact `10369501432`;
- artifact SHA-256 `b806eaf27f733c1a2b5cc1d108ca442fef673b6dc0a53cfc5fff38abd2bf6732`;
- upstream tests `13/13 PASS`;
- Lintian error gate PASS;
- SONAME `libKF6ItemModels.so.6` PASS;
- consumer CMake/build/runtime smoke PASS;
- consumed ECM `6.30.0-0supralinux3`.

### KPlotting — PASS retained

- job `104151532320`;
- package `6.30.0-0supralinux1`;
- artifact `10369086459`;
- artifact SHA-256 `f4c4f7425e582b5001fdffced34d045dc46152074422bd2bcf994e544bb96bb8`;
- upstream tests `5/5 PASS`;
- Lintian error gate PASS;
- SONAME `libKF6Plotting.so.6` PASS;
- consumer CMake/build/runtime smoke PASS;
- consumed ECM `6.30.0-0supralinux3`.

### BluezQt — historical real FAIL, retained

Attempt 1 remains recorded and is not rewritten as PASS or BLOCKED:

- job `104151532330`;
- attempted package `6.30.0-0supralinux1`;
- artifact `10369725265`;
- artifact SHA-256 `ab85b1c2eeef6bf2dc9d622d6695b95427cca6e246ac13a0f825034e9e63d195`;
- upstream build succeeded;
- upstream tests `18/18 PASS`;
- failure stage: `sbuild` Lintian gate.

The failure was `symbols-file-contains-current-version-with-debian-revision` for `_ZSt19piecewise_construct@Base` in `libKF6BluezQt.so.6`. The remediation deliberately changes only the reviewed symbols policy: `debian/apply-symbols-delta.py` pins the Debian 6.28 baseline SHA-256 `b72bea28842160da234b3bbab7975623616cd58f3e522b1e5d8705a279eef4f7`, adds `(optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0`, and verifies transformed SHA-256 `0fd10c9d93b303fa48aa5cd66aaf4727fbc27f4b784926f5ce5f8d20606bf37a`. The transform file itself is SHA-256 `6e7f4a36c5b5b71c80728c23da82180af0772b4d9abf2f3feb834ffda0007565`.

## BluezQt remediation PASS — run 34945979836

BluezQt `6.30.0-0supralinux2` was rebuilt from commit `b58b5e6072bb14487e304857d34a53659ec50f60` and completed successfully:

- job `104305337324`;
- artifact `10387429776`;
- artifact SHA-256 `db8a3718a31eaae00d5f9fbdb60014dfeb1faf1c2bc84a88f9ab0d9bffec07ed`;
- upstream tests `18/18 PASS`;
- Lintian `--fail-on error` PASS; only non-fatal warnings remained;
- SONAME `libKF6BluezQt.so.6` PASS;
- consumer CMake configure/build/runtime smoke PASS;
- consumed ECM `6.30.0-0supralinux3`;
- downstream eligibility: PASS.

The artifact also preserves `.deb`, `.ddeb`, `.changes`, `.buildinfo`, `.dsc`, source hashes, rootfs hash, build logs, consumer logs and Lintian evidence.

## Repository Policy false positive and validator correction

Repository Policy run `34945979830`, job `104305336760`, failed at the Batch 3 preparation validator even though the BluezQt package job itself passed. This was an infrastructure validator defect, not a Framework FAIL.

The old validator used a raw string search for the first occurrence of `dh_makeshlibs`. In `debian/rules`, that matched the target name `override_dh_makeshlibs:` before the recipe line that actually executes `dh_makeshlibs`, producing a false ordering failure.

The validator now distinguishes the target `override_dh_makeshlibs:` from an **invocación real** del comando. It locates Make recipe command lines after trimming indentation and verifies that `python3 debian/apply-symbols-delta.py` executes before the real `dh_makeshlibs` invocation. BluezQt packaging itself is unchanged because the real recipe order was already correct.

## CI scope

The remediation run also verifies intended scope behavior: KItemModels and KPlotting completed via the scope-skip path, with package build/download/upload steps skipped, while only BluezQt rebuilt. State/evidence/documentation changes therefore do not invalidate retained PASS artifacts.

The Batch 3 closure commit changes canonical state, evidence, documentation and validator semantics. It must not request package rebuilds unless a consumed package input changes.

## Canonical Tier 1 state after Batch 3 closure

Batch 3 is canonically closed with:

- KItemModels: PASS retained;
- KPlotting: PASS retained;
- BluezQt `6.30.0-0supralinux2`: new real PASS;
- BluezQt attempt-1 FAIL: retained as historical evidence.

Canonical Tier 1 state is now **10 PASS / 19 pending / 0 current FAIL / 0 BLOCKED**.

PR #1 remains Draft. No merge is authorized.
