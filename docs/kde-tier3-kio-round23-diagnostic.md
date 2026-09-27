# KDE Tier 3 KIO Round 23 — methodology review

Status: **BLOCKED pending diagnostic infrastructure preflight**.

Round 23 was intended to reproduce the Attempt 8 KRecentDocument failure inside the exact retained sbuild rootfs. Package state has never changed during these diagnostics.

## Why Round 23 is blocked

Seven executions were infrastructure-invalid and none is usable as a KIO conclusion:

1. source staging copied a directory incorrectly;
2. a manual chroot wrapper assumed `useradd`;
3. shell initialization referenced an unset variable;
4. generated sbuild config mishandled literal `%p`;
5. a bind mount targeted a nonexistent chroot path;
6. workspace bind mount failed inside the user namespace;
7. native sbuild transport worked, but the KIO-specific manually reconstructed configure/build path failed before the diagnostic matrix completed.

Attempt 7 evidence:

- workflow run: `36282766027`
- job: `108517688179`
- branch commit: `66d3652c504e827c1a25cce19b6b5fb6c14319d1`
- artifact: `10919472201`
- artifact SHA-256: `c70ec7003ab48c6bdca8f99adc86fe2464abfa7c61b7a48eba61d32525754780`
- stage: `run-starting-build-commands`
- package attempted: **false**
- canonical state effect: **none**

## Methodology correction

```text
2 consecutive INFRA_INVALID
=> freeze target diagnostic
=> methodology review
=> cheap synthetic infrastructure preflight
=> only after PASS may the target diagnostic be redesigned/re-enabled
```

The preflight is package-independent and certifies sbuild/unshare transport, `%p`, native `sbuild` user, evidence return and stop-before-`dpkg-buildpackage` behavior without KIO.

After that gate passes, Round 23 must preserve the historical Attempt 8 Debian build path as closely as practical. The previous manually reconstructed `debian/rules` subset is not accepted as final parity evidence for a nondeterministic failure.

## Canonical state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
Round 23 = BLOCKED
Next gate = diagnostic-infrastructure-preflight-evidence
```
