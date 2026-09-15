# KDE Frameworks 6.30 Tier 1 — packaging preparation and campaign

Status: **reference gates PASS; package Batches 1–3 closed; 10 Tier 1 PASS / 19 pending / 0 current FAIL / 0 BLOCKED**

Last reviewed: **2026-09-15**

## Authority model

KDE Frameworks 6.30.0 source/build metadata defines the selected KDE version, requirements and defaults. Ubuntu Resolute is platform/provider and compatibility target. Ubuntu/Debian packaging trees are technical references for Debian contracts only.

Reference evidence cannot promote a Framework. Only an actual package attempt produces PASS/FAIL. BLOCKED means no attempt occurred because a required predecessor is FAIL.

## Retained reference gates

Source packaging-reference PASS:

- run `34701132721`;
- artifact `10299579234`;
- SHA-256 `a2951c297f125ad81d1487075f0a0a6250114c4e875f3ba3870c3c18c09adaca`.

Binary-contract reference PASS:

- run `34704117024`;
- artifact `10301282501`;
- SHA-256 `9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97`.

Generic full `debian/` tree PASS:

- run `34708030450`;
- artifact `10301938362`;
- SHA-256 `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`;
- 29 Ubuntu + 29 Debian trees = 58 hash-verified packaging trees.

These remain reference inputs, not authority.

## Proven package path

The hosted package contract is:

1. exact KDE source and KDE SHA-256;
2. package metadata audited against KDE requirements and retained compatibility references;
3. source package assembled without executing package Build-Depends on the host;
4. retained ECM `6.30.0-0supralinux3`;
5. fresh Resolute `sbuild`;
6. upstream tests;
7. package-specific binary/ABI/symbol checks;
8. fatal `lintian --fail-on error`;
9. package-specific CMake consumer smoke;
10. `.deb`, `.ddeb` when generated, `.changes`, `.buildinfo`, `.dsc`, source/rootfs hashes and logs retained;
11. PASS/FAIL assigned only from the real attempt.

## Canonical PASS packages

The ten current Tier 1 PASS nodes are:

- Attica `6.30.0-0supralinux2`;
- KCodecs `6.30.0-0supralinux4`;
- KDBusAddons `6.30.0-0supralinux3`;
- ThreadWeaver `6.30.0-0supralinux3`;
- KTextTemplate `6.30.0-0supralinux3`;
- KArchive `6.30.0-0supralinux4`;
- KHolidays `6.30.0-0supralinux4`;
- KItemModels `6.30.0-0supralinux1`;
- KPlotting `6.30.0-0supralinux1`;
- BluezQt `6.30.0-0supralinux2`.

All are hosted/non-authoritative package proofs and downstream eligible inside the hosted DAG lane.

## Reviewed ABI/symbol policy

KCodecs uses Debian 6.28 as the closest technical symbols baseline and marks 15 compiler/libstdc++ implementation symbols caused by KDE 6.30 `std::format` as `(optional=toolchain)` at upstream minimum `6.30.0`.

BluezQt follows the same principle for `_ZSt19piecewise_construct@Base`. Attempt 1 (`6.30.0-0supralinux1`) remains a historical real FAIL after 18/18 upstream tests because Lintian rejected the package revision as an ABI minimum. The reviewed deterministic transform produced revision `6.30.0-0supralinux2`, which passed workflow `34945979836`, job `104305337324`, artifact `10387429776`, artifact SHA-256 `db8a3718a31eaae00d5f9fbdb60014dfeb1faf1c2bc84a88f9ab0d9bffec07ed`, with 18/18 tests, Lintian error gate and consumer smoke PASS.

Historical FAIL evidence is retained; a later PASS never erases it.

## Scope and validator discipline

Evidence-only, state-only and documentation-only edits must not rebuild packages. The semantic scope detector compares consumed package inputs rather than descriptive metadata.

Repository Policy run `34945979830` exposed a validator false positive: the Batch 3 validator treated the Make target `override_dh_makeshlibs:` as if it were execution of `dh_makeshlibs`. The package recipe already had the correct order. The validator now locates the actual Make recipe command and verifies that the symbols transform executes before the real `dh_makeshlibs` invocation.

This incident has no package-state effect.

## Current campaign state

`manifests/kde-frameworks-tier1.json` and `manifests/kde-dag.json` record **10 PASS / 19 pending / 0 current FAIL / 0 BLOCKED** after canonical Batch 3 closure.

Only retained PASS artifacts may feed downstream builds.

## Next implementation step

Re-check current KDE upstream stable metadata, then select the next ready Tier 1 group from the remaining 19 nodes. Prefer independent nodes that fit the current runner; extend the runner explicitly where a Framework exposes multiple ABI libraries rather than forcing it into a single-library contract.

Keep PR #1 Draft. No merge is authorized at this stage.
