# KDE Frameworks 6.30 Tier 1 — package batch 1

Status: **KDBusAddons PASS; ThreadWeaver PASS; KCodecs FAIL with `-0supralinux4` remediation prepared**  
Last reviewed: **2026-09-12**

## Scope and authority

Batch 1 contains three independent KDE Frameworks 6.30 Tier 1 nodes: `kcodecs`, `kdbusaddons`, and `threadweaver`. KDE upstream stable is the authority for source, dependency requirements, tests, ABI/API and release behavior. Ubuntu Resolute and Debian sid are technical packaging/provider references only.

Shared retained inputs:
- ECM `6.30.0-0supralinux3`: run `34694951158`, artifact `10298635300`, `.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- generic packaging trees: run `34708030450`, artifact `10301938362`, SHA-256 `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`.

The batch matrix uses `fail-fast: false`. PASS, FAIL and BLOCKED retain their project meanings; none of these nodes is BLOCKED because ECM is PASS and the three nodes are independent.

## Attempt 1 — three FAILs

Commit `50611225422b05803ee49d8d5fc8ff4f84a21d99`, run `34709829162`.

All three packages were actually attempted. They failed before KDE autotests because SupraLINUX had inserted an invalid full-tree `reuse lint` gate. Therefore autotests did not run in attempt 1.

- KCodecs: job `103596438631`, artifact `10302917591`, SHA-256 `6fcf23a69991e453d3563d580aa63fa082c27ce8490ad52dd9e125ee41cd8f6f`.
- KDBusAddons: job `103596438606`, artifact `10303285563`, SHA-256 `2a581e9f4c01c15c611b5b3d3a98343504177f1d52fb2225f92ce3c6428f54ed`.
- ThreadWeaver: job `103596438491`, artifact `10303265649`, SHA-256 `0b47374207ae54632c4ba9594eedbcc72d46eed552696b608110ebb5bce6acb6`.

The invented REUSE gate was removed rather than papered over with synthetic metadata. KDE autotests remain enabled.

## Attempt 2 — tests PASS, package gates still FAIL

Commit `3fa96423bb01b8a7cd63a62ab5947cf7ef57b482`, run `34710627400`.

- KCodecs: **8/8 tests PASS**; job `103598645411`, artifact `10303621032`, SHA-256 `722b83f04fadc67337129f6435547e0c9b3ad6b8b3d02655be258d86cb62e6a6`; final state FAIL because Ubuntu 6.24 symbols still contained two `KCharsets` constructors no longer present.
- KDBusAddons: **3/3 tests PASS**; job `103598645369`, artifact `10303366682`, SHA-256 `75879797c369c29c00eb6fa647cca9958645eb80437531f7dfee42fe99327763`; final state FAIL because absent Multi-Arch was normalized incorrectly and the watch-file PGP key was missing.
- ThreadWeaver: **8/8 tests PASS**; job `103598645228`, artifact `10302524114`, SHA-256 `5582b94c2e134011297a51fd02183464253c0c5f43678a79fd256f128b2f2d6f`; same package-contract/PGP findings as KDBusAddons.

Debian sid 6.28 had already removed the same two KCodecs constructors, so the KCodecs public symbols baseline moved to the retained Debian reference instead of weakening ABI checks.

## Attempt 3 — two PASS, one FAIL

Commit `c4de13b66184cb3b84283f1c4c5f0668f577b0de`, run `34713034164`. Repository Policy run `34713034169` is PASS.

### KDBusAddons — PASS

- package `6.30.0-0supralinux3`;
- job `103605147881`;
- artifact `10304340428`;
- artifact SHA-256 `2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799`;
- tests: **3/3 PASS**;
- Lintian error gate: PASS; retained warnings are `empty-binary-package` for the compatibility doc stub and missing manpage for `kquitapp6`;
- SONAME `libKF6DBusAddons.so.6`;
- consumer smoke PASS;
- ECM predecessor proof: `6.30.0-0supralinux3`;
- downstream eligible: yes.

### ThreadWeaver — PASS

- package `6.30.0-0supralinux3`;
- job `103605147772`;
- artifact `10303986419`;
- artifact SHA-256 `6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8`;
- tests: **8/8 PASS**;
- Lintian error gate: PASS; only the retained `empty-binary-package` doc warning remains;
- SONAME `libKF6ThreadWeaver.so.6`;
- consumer smoke PASS;
- ECM predecessor proof: `6.30.0-0supralinux3`;
- downstream eligible: yes.

### KCodecs — FAIL

- attempted package `6.30.0-0supralinux3`;
- job `103605147896`;
- artifact `10304255731`;
- artifact SHA-256 `336d771a73091f2b0a7c60cf55833b5205f2c4bc8a8e87802065fe38333c2b0d`;
- tests: **8/8 PASS**;
- source package, clean `sbuild`, binary split, Multi-Arch contract and SONAME all reached successfully;
- final stage: `lintian`;
- cause: 15 new libstdc++ `std::format`/Unicode implementation symbols were emitted into `libKF6Codecs.so.6`; `dpkg-gensymbols` assigned `6.30.0-0supralinux3` as their minimum version and Lintian correctly rejects a Debian revision in a symbol minimum.

KDE 6.30 itself now uses `<format>` in `UnicodeGroupProber.cpp`. These symbols are toolchain/template implementation details, not new KCodecs public API. Debian's source-symbols format explicitly supports the `optional` tag for private/template symbols whose presence can vary without constituting an ABI break.

## KCodecs attempt 4 remediation

Candidate: `6.30.0-0supralinux4`.

The retained Debian 6.28 public symbols file remains the base reference, SHA-256 `35f6b7b6885b3db41bcce95b99610b2e917e1b4e13d5ba7e801b93dd47c4f8c7`.

SupraLINUX adds an auditable source-template override `debian/libkf6codecs6.symbols.supralinux`, SHA-256 `b87cbfbfe47d7cf99248b57196257a2765987297a701310de513d1e36c51d696`. Exactly 15 new `std::format`/Unicode implementation symbols are tagged `(optional=toolchain)` with upstream minimum `6.30.0`. No existing public symbol minimum is weakened or removed.

The candidate template was checked locally with `dpkg-gensymbols -c4` against the `libKF6Codecs.so.6.30.0` binary produced by attempt 3 and passes without warnings. The real `-0supralinux4` clean build remains pending CI; KCodecs therefore remains current **FAIL** and is not downstream eligible.

## Current batch state

- KCodecs: **FAIL**, remediation `6.30.0-0supralinux4` pending validation.
- KDBusAddons: **PASS**, downstream eligible.
- ThreadWeaver: **PASS**, downstream eligible.
- BLOCKED: none.

`manifests/kde-tier1-package-campaign.json` is the canonical current attempt ledger for this in-flight batch. Synchronization of the top-level `manifests/kde-dag.json` and general Tier 1 status documentation is intentionally pending until the KCodecs attempt-4 result closes, so this preparatory commit does not falsely promote KCodecs or require a second state transition mid-attempt. The older embedded `packaging` placeholders in `manifests/kde-frameworks-tier1.json` are source-bootstrap metadata, not the current batch-attempt authority.

## CI scope

State/evidence-only changes to the campaign ledger no longer force all three packages to rebuild. The scope helper compares a per-node build-input fingerprint. A package-path change still rebuilds that node; shared runner/workflow changes still rebuild all affected nodes. This allows PASS nodes to remain untouched while KCodecs iterates independently.

Hosted PASS remains non-authoritative release evidence. Final candidate/stable promotion still requires the separate KVM/JIT/runtime/compatibility gates.
