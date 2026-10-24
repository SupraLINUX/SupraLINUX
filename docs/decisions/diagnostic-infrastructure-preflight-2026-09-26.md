# Diagnostic infrastructure preflight

Status: **PASS — historical evidence closed**  
Decision date: **2026-09-26**  
PASS evidence date: **2026-09-27 UTC**

## Decision

A complex diagnostic mechanism must be certified with a cheap synthetic probe before it is used on the failing package it is meant to investigate.

A target package such as KIO must not simultaneously serve as:

- the subject of the diagnosis;
- the first test of a new sbuild/chroot transport;
- the first test of new evidence extraction;
- the first test of hook semantics.

SupraLINUX therefore uses `diagnostic-infrastructure-preflight` as a reusable/manual hosted gate.

## Trigger for this decision

KIO Round 23 accumulated repeated `INFRA_INVALID` executions while package state correctly remained unchanged. FAIL vs infrastructure-invalid was modeled correctly, but CI was being used to discover runner/sbuild integration defects one push at a time.

The cutoff policy is explicit:

`max_consecutive_infra_invalid_before_methodology_review = 2`

After two consecutive infrastructure-invalid attempts of the same diagnostic mechanism:

1. stop target-package retries;
2. freeze target diagnostic execution;
3. inspect authoritative tool documentation and the historical run being reproduced;
4. isolate the mechanism behind a cheap synthetic preflight;
5. validate scripts/configuration locally where possible;
6. resume the target diagnostic only after the infrastructure preflight has PASS evidence.

## Synthetic probe contract

The preflight used GitHub-hosted Ubuntu 26.04, `sbuild 0.91.2ubuntu3`, `--chroot-mode=unshare`, the exact retained Attempt 8 rootfs, and a tiny synthetic Debian source package — never KIO.

It certified:

- host-to-chroot transfer through `pre-build-commands` + `%SBUILD_CHROOT_EXEC`;
- `starting-build-commands` execution inside the exact rootfs;
- `%p` resolution;
- the native `sbuild` user and `runuser` behavior;
- chroot-to-host evidence over stdout;
- deliberate stop before `dpkg-buildpackage`;
- absence of `.deb`, `.changes` and `.buildinfo` outputs.

The generated hook was checked with `bash -n`; generated `sbuild-config.pl` was checked with `perl -c` before sbuild started.

## Closed PASS evidence

- workflow run: `36286096599`
- job: `108527097646`
- commit: `340da99451a86b65513efcbfcae6b6b7145a2a96`
- artifact: `10920194622`
- artifact SHA-256: `ee6adecf77aa5110db735220bca0ebecd2a4a41b4a2b8dacc6692816866c1d39`
- exact rootfs tar SHA-256: `790139881455b78e00621f1b8ab02efaee899b7e6873f4d65ae0ff7fa295020e`
- result: `PASS`
- package attempted: **false**
- canonical state effect: **none**

This evidence is historical and must remain valid even after the live lifecycle advances. The preflight validator therefore validates the closed evidence itself, not the current Round 23 gate.

## KIO Round 23 handoff

Preflight PASS does not authorize Attempt 9 and does not change KIO from its existing canonical `FAIL`.

It only unblocks redesign of Round 23. The redesigned diagnostic must preserve the historical Attempt 8 Debian build path:

`sbuild -> dpkg-buildpackage --sanitize-env -us -uc -b -> debian/rules binary`

Instrumentation may be inserted in the disposable diagnostic worktree, but configure/build may not be manually reconstructed by the starting-build hook. The diagnostic runs from `override_dh_auto_test`, must restore the modified worktree files before exit, and must abort before candidate package artifacts are produced.

## General rule

Diagnostic infrastructure is a dependency. Uncertified infrastructure makes the target diagnostic `BLOCKED`. Infrastructure FAIL/INFRA_INVALID never changes package state. Closed historical PASS evidence is not coupled to later live-state transitions.
