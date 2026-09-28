# KDE Tier 3 KIO Attempt 9 remediation definition

Status: **definition pending CI and source materialization**.  
Attempt 9 package execution: **not authorized**.

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

This definition authorizes **source materialization only**.

Required sequence:

```text
definition PASS
→ materialize KIO 6.30.0-0supralinux9
→ verify source/package artifacts and hashes
→ planning validation
→ explicit Attempt 9 activation
→ binary build
```

No step in this definition authorizes the binary Attempt 9 itself.

KXMLGui remains a retained PASS/revalidation node. No KXMLGui source
rematerialization is required.

## Current state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
Round 26 = remediation-PASS / 69/69 combined proof
Candidate KIO = 6.30.0-0supralinux9
Next gate = tier3-attempt9-kio-remediation-materialization-evidence
```
