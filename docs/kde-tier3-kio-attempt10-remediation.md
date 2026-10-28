# KDE Tier 3 KIO Attempt 10 symbol-metadata remediation

Status: **Attempt 10 CLOSED-PASS; KIO canonical PASS**.  
Attempt 10 binary execution: **closed; no further Level 1 execution authorized**.

## Attempt 9 evidence

Attempt 9 workflow `36416891314` proved the functional remediation in the real package path:

- KIO `6.30.0-0supralinux9`: **69/69 upstream tests PASS**;
- KXMLGui `6.30.0-0supralinux5`: **7/7 PASS** plus Python import PASS;
- KIO binary packages were produced;
- KIO failed only at Lintian symbol metadata.

The failure is package-owned, so Attempt 9 remains FAIL for KIO despite the complete upstream test PASS.

## Root cause

With `BUILD_TESTING=ON`, KIO 6.30 exposes 34 symbols absent from the Debian 6.30 symbols templates:

- 1 KIOCore symbol: `Worker::setTestWorkerFactory`, a private test hook declared in `worker_p.h`;
- 33 KIOGui `FilePreviewJob` symbols. Upstream wraps the class export in `KIOGUI_TEST_EXPORT`, which expands to `KIOGUI_EXPORT` only when `BUILD_TESTING` is enabled.

Because the templates omitted them, `dpkg-gensymbols` assigned `6.30.0-0supralinux9` as their first version. Lintian correctly rejected that Debian-revision ABI baseline.

## Remediation

Materialize those 34 symbols as:

- `(optional)`;
- minimum version `6.30.0`;
- private/test-build metadata, not public ABI;
- no Lintian override or suppression.

The exact KRecent source patch, visible test HOME, Qt SVG provider and complete 69-test policy remain unchanged.

## Package revision

```text
previous:  6.30.0-0supralinux9
candidate: 6.30.0-0supralinux10
```

The revision bump is required because the Debian symbols templates change.

## Lifecycle

This definition authorizes **KIO source/package materialization only**.

```text
Attempt 9 CLOSED-MIXED
→ Attempt 10 definition
→ materialize KIO 6.30.0-0supralinux10 — PASS
→ verify symbols/source/package artifacts — PASS
→ planning validation — PASS
→ explicit Attempt 10 activation — ACTIVE
→ binary build — PASS
→ canonical KIO promotion — PASS
→ Level 2 planning — NEXT
```

KXMLGui is retained at `6.30.0-0supralinux5` and will be revalidated only in the full Level 1 rerun. Binary Attempt 10 remains unauthorized.

Current canonical state:

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux9 = FAIL
KXMLGui 6.30.0-0supralinux5 = PASS
Candidate KIO = 6.30.0-0supralinux10
Next gate = tier3-build-level2-planning
```


## Materialization evidence

KIO `6.30.0-0supralinux10` materialization passed on commit `a77f6e1f247792ccb486720010d969e2cbc41680`.

- workflow: `36424068585`
- job: `108933677695`
- artifact: `10970466420`
- artifact SHA-256: `f25ae14e1f393d24f95b1118680d7967f6bef449c8790981b170cfb78a1f3d22`
- source tree: `05a15e08edad1e95358383e97ae326d41c308b64a116cb0dcaf37a11f4677d0e`
- materialized tree: `06bbd34131df5bc52793703782b7db2b5f6a3a9c8541d82c4ee8daeba947c8a8`
- Debian tar: `801680a76fa4013f07ae2891a0f4ab3c98f31b974bc94385912333b625719fd5`
- 34 private/test-only symbols remain modeled as optional at upstream `6.30.0`.

Repository Policy `36424068693` passed the Attempt 10 definition on the same commit. Binary execution remains blocked until planning validation passes and a separate activation occurs.


## Planning and activation

Planning validation passed on commit `0471d2332eef5f02344b2ffad96828f31ee3a405`:

- Repository Policy: `36424710656`
- Level 1 planner: `36424710626`
- the Level 1 run skipped rootfs and binary matrix execution while authorization was false.

Attempt 10 is now authorized for the full Level 1 scope:

- KIO `6.30.0-0supralinux10`;
- retained KXMLGui `6.30.0-0supralinux5` revalidation.

Canonical KIO remains FAIL at `6.30.0-0supralinux9` until the real Attempt 10 package job passes every package gate.


## Attempt 10 result

Workflow `36425867815` completed **2 SUCCESS / 0 FAIL**.

KIO `6.30.0-0supralinux10`:
- 69/69 upstream CTest targets PASS;
- Lintian error gate PASS;
- APT closure PASS;
- ABI contract PASS;
- installed CMake consumer PASS;
- exact predecessor/buildinfo proof PASS;
- artifact `10972557457`, SHA-256 `700a7abebfaca99ae76e36cfb8f54798694732f248b0002224025cfc80d94056`.

This validates both the Round 26 functional remediation and the Attempt 10 optional-symbol metadata remediation in the real package path.

KXMLGui `6.30.0-0supralinux5` revalidated PASS with 7/7 tests and Python import PASS; artifact `10971509790`, SHA-256 `a4a5bac1ca996792cc9d44e20d68d451ac61ea0a30811781260299bf87a04c00`.

Canonical state is now:

```text
13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED
KIO 6.30.0-0supralinux10 = PASS / downstream eligible
KXMLGui 6.30.0-0supralinux5 = PASS
KNewStuff = runtime-validation-required
Next gate = tier3-build-level2-planning
```
