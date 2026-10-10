# KDE Tier 3 KIO Attempt 9 remediation definition

Status: **Attempt 9 closed MIXED**.  
Definition contract: **PASS**.  
Functional KIO test remediation: **PASS (69/69)**.  
Package result: **FAIL at Lintian symbol metadata**.

## Inputs already proven

Round 26 closed the two remaining Attempt 8 failures:

- hidden test HOME reproduced the historical KDirModel signature 10/10;
- visible test HOME passed KDirModel 20/20;
- the exact deterministic KRecent patch plus visible HOME passed the complete KIO suite 69/69.

The production candidate therefore contains exactly two remediation changes:

1. KRecent deterministic tie ordering in `src/core/krecentdocument.cpp`;
2. test-only HOME changes from `debian/.supralinux-test-home/sbuild` to `debian/supralinux-test-home/sbuild`.

## Package revision

```text
previous:  6.30.0-0supralinux8
candidate: 6.30.0-0supralinux9
```

The revision bump is mandatory because both source and packaging/test-environment materialization change.

## Source identity

The materializer must reproduce exactly:

```text
patch SHA-256:
8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602

patched src/core/krecentdocument.cpp SHA-256:
57d20f3786220178316b31819ba266432207b1f4d55859ccf8d1fad37645021b
```

The patch is emitted as a normal Debian quilt patch named
`supralinux-krecent-deterministic-ordering.patch`. It changes no public API,
ABI, timestamp format or XBEL schema.

## Lifecycle

The definition authorized **source materialization only**. That materialization is now closed with PASS evidence.

Required sequence:

```text
definition PASS
→ materialize KIO 6.30.0-0supralinux9 — PASS
→ verify source/package artifacts and hashes — PASS
→ planning validation — PASS
→ explicit Attempt 9 activation — ACTIVE
→ binary build — CLOSED MIXED
```

Materialization PASS evidence: workflow `36413768965`, job `108899950721`, artifact `10965892140` (SHA-256 `b11e6cf5142aab878578f5d7662b3c0e2cf41fd306b3ecaffbc76e78c1e63f2c`). The source package is `6.30.0-0supralinux9`; the exact KRecent patch and patched-source hashes match the Round 26 candidate.

Planning validation passed in Repository Policy `36415650130` and Level 1 workflow `36415653322` for commit `bcc76458eecff8118d5526c043d18aa7de3b4b4c`.

Attempt 9 is now authorized for the full Level 1 scope: KIO `6.30.0-0supralinux9` plus retained KXMLGui `6.30.0-0supralinux5`. Canonical KIO remains FAIL/downstream-ineligible until the real package job passes.

KXMLGui remains a retained PASS/revalidation node. No KXMLGui source
rematerialization is required.

## Current state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = CLOSED-MIXED
Round 26 = remediation-PASS / 69/69 combined proof
Candidate KIO = 6.30.0-0supralinux9
Next gate = tier3-attempt10-kio-symbol-metadata-materialization-evidence
```


## Attempt 9 result

Workflow `36416891314` on `e7dfc689bf18aea5ed194df03f31e9c74627ead0` executed the full Level 1 rerun.

- KXMLGui `6.30.0-0supralinux5`: PASS, 7/7 upstream tests and Python import PASS.
- KIO `6.30.0-0supralinux9`: all 69/69 upstream CTest targets PASS.
- KIO binary packages were produced.
- KIO then failed the package gate at Lintian, not at compile or test time.
- Lintian found 34 symbols whose generated minimum version was `6.30.0-0supralinux9`, which is invalid because it embeds the Debian/SupraLINUX revision.

Upstream KIO 6.30 establishes that the 33 `FilePreviewJob` symbols are exported only when `BUILD_TESTING` is enabled, and `Worker::setTestWorkerFactory` is a private test hook declared in `worker_p.h`. They are therefore packaging/test-build symbols, not new public ABI.

Canonical KIO becomes FAIL at `6.30.0-0supralinux9` and remains downstream-ineligible. The canonical snapshot stays **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.
