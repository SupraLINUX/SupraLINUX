# KDE Frameworks 6.30 Tier 1 — packaging preparation and campaign

Status: **reference gates PASS; Attica + Batch 1 package proofs PASS; 4 Tier 1 PASS / 25 pending**

Last reviewed: **2026-09-12**

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
10. `.deb`, `.changes`, `.buildinfo`, `.dsc`, source/rootfs hashes and logs retained;
11. PASS/FAIL assigned only from the real attempt.

## Current PASS packages

Attica `6.30.0-0supralinux2` established the first proof.

Batch 1 then generalized the path with `fail-fast: false`:

- KCodecs `6.30.0-0supralinux4`: run `34716761551`, artifact `10305050385`, 8/8 tests PASS.
- KDBusAddons `6.30.0-0supralinux3`: run `34713034164`, artifact `10304340428`, 3/3 tests PASS.
- ThreadWeaver `6.30.0-0supralinux3`: run `34713034164`, artifact `10303986419`, 8/8 tests PASS.

All four Tier 1 PASS artifacts are hosted/non-authoritative but downstream eligible inside the hosted DAG lane.

## KCodecs reviewed symbols

KCodecs is deliberately not forced to the older Ubuntu 6.24 symbols baseline. Debian 6.28 already reflects the removal of two old `KCharsets` constructors. SupraLINUX retains that newer reference and layers a reviewed symbols override for 15 compiler/libstdc++ implementation symbols caused by KDE 6.30 `std::format` use.

Those 15 entries are `(optional=toolchain)` with minimum `6.30.0`. This prevents compiler-specific implementation leakage from being mistaken for a stable public ABI while preserving visibility and auditability.

## Scope discipline

Evidence-only or state-only edits must not rebuild packages. The initial Batch 1 semantic fingerprint was too broad and selected two already-PASS nodes on run `34716761551`; both aborted at `campaign-validation` before a package attempt. This is retained as infrastructure-scope evidence and has no package-state effect.

The corrected fingerprint compares only fields consumed by the runner plus package/consumer file changes and shared runner/workflow changes.

## Current campaign state

`manifests/kde-frameworks-tier1.json` now records **4 PASS and 25 pending**. `manifests/kde-dag.json` records ECM plus Attica/KCodecs/KDBusAddons/ThreadWeaver as PASS. There are **0 current FAIL and 0 BLOCKED** Tier 1 nodes.

## Next implementation step

Prepare Batch 2 from the remaining 25 Tier 1 nodes, favoring independent packages with straightforward Qt/external dependencies so they can be built in parallel. Keep package-specific contracts explicit rather than over-generalizing the runner.
