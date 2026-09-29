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


## Validation run 1 — INFRA_INVALID

The first authorized runtime validation executed in PR router run `36575095841`, job `109428639526`, from head commit `955c9189e720633b16791b7e6f1fb7f51e7439b4` (execution merge SHA `023661cb7e3181e383cb617eee17a24d67155665`).

Retained evidence:

- artifact: `11036509658`
- artifact SHA-256: `069046c2a72c5c280bb91152a093e1fae34b5debcdf4cb7aaea4646ae013815a`
- result: `INFRA_INVALID`
- stage: `artifact-contract`
- `package_attempted=false`
- canonical state effect: none

The retained `result.json` proves that the run failed before rootfs bootstrap or runtime installation. The mechanism selected artifacts with `glob("<artifact_id>-*")`; after download there are two matching filesystem entries: the extracted directory and its sibling `.zip`. This made the selector ambiguous even though every downloaded artifact passed its pinned outer SHA-256 check.

The remediation uses the exact extracted path `<artifact_id>-<label>`. Repository Policy now runs a synthetic preflight that deliberately creates both the directory and sibling ZIP and certifies that only the exact directory is selected. The runtime lane also depends on Repository Policy PASS, so the remediated infrastructure is validated before the KNewStuff runtime retry begins.

This is infrastructure evidence only. It does not consume a Package Attempt, does not make KNewStuff FAIL, and leaves the canonical snapshot at `17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED`.


## Validation run 2 — reported PASS, canonical INFRA_INVALID

The remediated runtime lane executed in PR router run `36576400800`, job `109433549606`, from head commit `438fb5cacf4b4bd7016557b87880ed92c73afa44` (execution merge SHA `dee8ca3945dd7140037ce49065fca73aaf3a1009`).

The runtime checks themselves completed successfully: exact KNewStuff/KCMUtils versions were installed, `apt-get check` passed, the ELF scan contained no `not found`, and the offscreen QML smoke completed. The retained evidence artifact is `11037137944`, SHA-256 `03847ee18320d15b4109dac0e9ec2bf71cde92d5b86308aba4e91f88f7f396ce`.

However, this run is **not canonical PASS**. Review of the executable runner showed that the planned contract item `verify-result-json-identity-and-internal-artifact-hashes` was not implemented: outer artifact ZIP hashes and package metadata were verified, but each retained artifact's internal `result.json.artifacts` SHA-256 map was not checked. Under the CI evidence rules this makes the validation evidence incomplete, so the canonical classification is `INFRA_INVALID`, not package/runtime FAIL and not promotable PASS.

This is the second consecutive `INFRA_INVALID` of the runtime-validation mechanism. Retries are therefore frozen:

```text
gate=tier3-knewstuff-runtime-validation-infrastructure-certification
state=infrastructure-certification-pending-policy-validation
execution_authorized=false
package_attempted=false
```

The certification adds a generic verifier for `result.json` identity plus every internal artifact SHA-256, and a synthetic preflight that proves a valid fixture passes and a tampered payload is rejected. Only after Repository Policy certifies this mechanism may runtime execution be reauthorized.


## Infrastructure certification PASS and execution reauthorization

Repository Policy certified the remediated runtime-validation mechanism in PR router run `36583737052`, job `109458398423`, at commit `f310c657cd3f0050ff4ffbebc0d3df284a8324d1`.

The synthetic preflight proved all required infrastructure properties:

- historical directory + sibling ZIP ambiguity reproduced;
- exact extracted-directory selector: PASS;
- internal `result.json` SHA-256 verifier: PASS;
- tampered payload rejection: PASS.

The verifier was additionally checked against retained real KNewStuff, KCMUtils and KIO artifact formats before reauthorization.

The live state is therefore reauthorized:

```text
gate=tier3-knewstuff-runtime-validation
state=execution-authorized
execution_authorized=true
package_attempted=false
```

The two previous `INFRA_INVALID` records remain immutable historical evidence. This reauthorization permits a fresh runtime validation run; it does not itself promote KNewStuff or alter the canonical snapshot.


## Validation run 3 — INFRA_INVALID: historical result.json schema evolution

The reauthorized runtime lane executed in PR router run `36585341825`, job `109464539716`, from head commit `7b92076e53eef84a874f3d5e51877cfa13d01741` (execution merge SHA `4410e30a6b47aed1f95ac87ac0bdb711a47767f2`).

KNewStuff and KCMUtils themselves passed the new internal-hash verifier. The run then stopped at Attica because its historical `result.json` predates `package_version`. This is infrastructure/schema incompatibility, not a package/runtime failure. Evidence artifact `11042070381` has SHA-256 `4afb676a88b08c150e8b3c28f4f2d1be12c5e4e81bab36f1323361e2e1fb2d1a`.

A complete audit of the 34 retained closure artifacts found:

- 34/34 pinned outer artifact SHA-256 values match;
- 15 node-only legacy `result.json` files;
- 7 with `package_version` but no `result` or internal hash map;
- 2 with PASS result/state but no internal hash map;
- 10 with a full internal `artifacts` SHA-256 map;
- 10/10 internal hash maps verify with zero mismatches.

The verifier must therefore follow the evidence that actually exists. It always requires the historical node identity. Optional historical fields such as `package_version` and `result` are enforced strictly when present. Every recorded internal artifact hash is verified when a hash map exists. Legacy artifacts that predate internal hash maps remain protected by their pinned outer artifact SHA-256 plus the runner's exact `.deb` version and binary-set checks.

Runtime execution is frozen while Repository Policy certifies this schema-adaptive verifier:

```text
gate=tier3-knewstuff-runtime-validation-infrastructure-remediation
state=infrastructure-remediation-pending-policy-validation
execution_authorized=false
package_attempted=false
```

KNewStuff remains pending/runtime-validation-required; the canonical snapshot remains `17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED`.


## Historical certification boundary correction

The prior infrastructure certification from run `36583737052` remains valid historical evidence for what it actually proved at that time, but it is no longer treated as the live certification object.

After validation run 3 exposed additional historical `result.json` schema generations, that earlier certification and its reauthorization became **superseded historical evidence**. The current live object is only the schema-remediation gate. This preserves the project rule that historical evidence is append-only while live state may advance or be frozen without rewriting the past.


## Infrastructure remediation certification PASS — round 2

Repository Policy certified the schema-adaptive verifier in PR router run `36591431061`, job `109485235871`, at commit `cfe5f54ae5ecfb16f2fd95bd1a0a526bd4257fc5`.

The certified preflight passed all four historical `result.json` generations and tamper rejection. The first certification/re-authorization remain immutable historical records; this is a distinct second certification and second live reauthorization.

The live state is now:

```text
gate=tier3-knewstuff-runtime-validation
state=execution-authorized
execution_authorized=true
package_attempted=false
```

This authorizes one fresh runtime-validation execution. It does not promote KNewStuff by itself and does not alter the canonical `17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED` snapshot.


## Validation run 4 — PASS and canonical promotion

The schema-adaptive runtime-validation lane completed successfully in PR router run `36595513031`, job `109499716109`, from head commit `49f7a2fabc15f0c75c7633e9048812801877cfc9` (execution merge SHA `83ed6e84491d80ee66415ae6544880f7f2c9d904`).

Retained evidence artifact `11046266772` has SHA-256 `01fc348f3b1a4fbee86599ab6d33c3781858f46264d082747bc155cf6cef9fad`. The run closed with `validation_result=PASS`, `stage=complete`, `package_attempted=false` and `consumes_package_attempt=false`.

The evidence proves:

- KNewStuff runtime packages exactly `6.30.0-0supralinux1`;
- KCMUtils runtime packages exactly `6.30.0-0supralinux3`;
- `apt-get check` PASS;
- no unresolved ELF dependency (`not found` count = 0);
- QML imports for `org.kde.newstuff` and `org.kde.kcmutils` PASS;
- installed `EntryDetails.qml` and `Page.qml` compile-load PASS;
- every retained artifact uses its pinned outer SHA-256, and every internal hash recorded by its historical `result.json` is verified.

The original KNewStuff build evidence remains immutable as `RUNTIME_PENDING`. Canonical PASS is a separate promotion record combining that retained successful build with this runtime PASS.

Canonical Tier 3 state is now:

```text
18 PASS / 2 pending / 0 current FAIL / 0 BLOCKED
```

The remaining pending nodes are KTextEditor and Purpose. KNewStuff is now downstream-eligible and present in the canonical DAG. This promotion does not publish anything to `stable`.
