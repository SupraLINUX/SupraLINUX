# KDE Tier 3 — KNewStuff deferred runtime validation

## Purpose

KNewStuff 6.30.0 already has a retained clean package build. Workflow run `35818120201`, job `107044336736`, artifact `10732461923` (SHA-256 `2d2b71cd19923c9d9896926f92c86a209fc633f5a2db04597c0ea10488b7ae4b`) completed the package build with **5/5 tests PASS**, Lintian, APT closure, ABI, CMake consumer and QML payload checks all passing.

Its result is intentionally `RUNTIME_PENDING`, not canonical PASS. KNewStuff remained `downstream_eligible=false` because its deferred runtime contract requires KCMUtils.

KCMUtils is now canonical PASS at `6.30.0-0supralinux3`. Its retained PASS evidence is workflow run `36503684811`, job `109200408066`, artifact `11006467074` (SHA-256 `4dc1045a571b0cb05e61e25600a56fbdc59e5a80cde071cc3ad6af78f7b884a7`).

## Why the deferred gate is real

The historical KNewStuff runtime closure used Ubuntu's KCMUtils `6.24.0-0ubuntu1`, including `qml6-module-org-kde-kcmutils`. That was sufficient for the build-time package validation but did not prove the SupraLINUX 6.30 runtime integration.

The installed KNewStuff QML surface contains two concrete consumers:

- `EntryDetails.qml` imports `org.kde.kcmutils` and uses `KCMUtils.SimpleKCM`.
- `Page.qml` imports `org.kde.kcmutils` and uses `KCMUtils.GridViewKCM`.

The runtime gate therefore validates this actual QML relationship instead of inventing a false KNewStuff → KCMUtils build dependency.

## Planning contract

This phase is planning only:

```text
state=planning-pending-policy-validation
execution_authorized=false
validation_run_kind=runtime-only
package_attempted=false
```

The runtime check is a **validation_run**, not a Package Attempt. It must not invoke `sbuild` and cannot consume or increment a package attempt counter.

The canonical state remains:

```text
17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED
```

KNewStuff remains pending/runtime-validation-required and outside the canonical DAG until runtime evidence is reviewed and promoted.

## Inputs and closure

The validation must use the retained KNewStuff artifact and the canonical KCMUtils PASS artifact, both verified by artifact ID and SHA-256. Internal `result.json` artifact hashes, exact package versions and exact binary sets are verified before installation.

The dependency closure is derived from the already-closed Level 0 KNewStuff inputs plus the canonical Level 2 KCMUtils retained/provider closure. Only canonical SupraLINUX PASS artifacts may satisfy SupraLINUX providers. Ubuntu Resolute may provide ordinary base dependencies, but falling back to Ubuntu KCMUtils 6.24 is explicitly forbidden.

A fresh reproducible Resolute runtime rootfs is created for the validation. Historical rootfs artifacts and VM/container snapshots are execution caches only and never source-of-truth evidence.

## Required runtime checks

The eventual execution gate must:

1. download all retained artifacts by pinned ID and SHA-256;
2. validate artifact identity and the internal package hashes recorded by each artifact;
3. verify the exact KNewStuff and KCMUtils binary-package sets;
4. install the canonical SupraLINUX runtime closure in a fresh Resolute environment;
5. run `apt-get check`;
6. prove KNewStuff is exactly `6.30.0-0supralinux1`;
7. prove KCMUtils is exactly `6.30.0-0supralinux3`;
8. prove no Ubuntu KCMUtils `6.24.0-0ubuntu1` provider remains installed;
9. resolve relevant ELF/QML plugin shared-object dependencies with no `not found`;
10. perform an offscreen QML import smoke for `org.kde.newstuff` and `org.kde.kcmutils`;
11. compile-load the installed `EntryDetails.qml` and `Page.qml` through Qt 6 `QQmlEngine` / `QQmlComponent` with `QT_QPA_PLATFORM=offscreen` and no smoke-test network access.

## Result semantics

A runtime **PASS** may promote the already-built KNewStuff package to canonical PASS, make it downstream-eligible and add it to the Tier 3 DAG after evidence review.

A runtime **FAIL** leaves KNewStuff pending/runtime-validation-required and records a validation failure. It is not automatically a package FAIL, does not consume a Package Attempt and does not justify a rebuild by itself.

An `INFRA_INVALID` result has no canonical package-state effect. Infrastructure failures remain separate from package and runtime-contract results.

## Next gate

Repository Policy must validate this planning contract first. Only after that PASS may a separate activation transition authorize:

```text
tier3-knewstuff-runtime-validation-activation
```

That later activation will define/authorize the executable runtime workflow. Stable promotion remains separate and always requires explicit user approval.


## Activation checkpoint — 2026-09-29

Planning Policy passed in PR router run `36567527801`, job `109403055592`, at commit `c139f70509cd321913c1e1c89565bfa60a7f22ff`.

The executable runtime lane is defined but remains unauthorized until this activation contract passes Repository Policy. The next transition is `tier3-knewstuff-runtime-validation-execution-authorization`. The lane performs no `sbuild` and never consumes a Package Attempt.


## Execution authorization checkpoint — 2026-09-29

The activation contract passed Repository Policy in PR router run `36573815831`, job `109424159153`, at commit `76261018520c0f566f152b319d41e6d770fdc310`.

The live runtime-validation state is now:

```text
gate=tier3-knewstuff-runtime-validation
state=execution-authorized
execution_authorized=true
validation_run_kind=runtime-only
package_attempted=false
```

This authorization permits the router to execute the deferred KNewStuff + KCMUtils runtime validation. It does not promote KNewStuff, does not change the canonical snapshot, and does not consume a Package Attempt. Promotion requires a separate review of PASS runtime evidence.
