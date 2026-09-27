# Diagnostic infrastructure preflight

Status: **active architecture decision**  
Date: **2026-09-26**

## Decision

A complex diagnostic mechanism must be certified with a cheap synthetic probe before it is used on the failing package it is meant to investigate.

A target package such as KIO must not simultaneously serve as:

- the subject of the diagnosis;
- the first test of a new sbuild/chroot transport;
- the first test of new evidence extraction;
- the first test of hook semantics.

SupraLINUX therefore introduces `diagnostic-infrastructure-preflight` as a reusable/manual hosted gate.

## Trigger for this decision

KIO Round 23 accumulated repeated `INFRA_INVALID` executions while package state correctly remained unchanged. FAIL vs infrastructure-invalid was modeled correctly, but CI was being used to discover runner/sbuild integration defects one push at a time.

The cutoff policy is now explicit:

`max_consecutive_infra_invalid_before_methodology_review = 2`

After two consecutive infrastructure-invalid attempts of the same diagnostic mechanism:

1. stop target-package retries;
2. freeze target diagnostic execution;
3. inspect authoritative tool documentation and the historical run being reproduced;
4. isolate the mechanism behind a cheap synthetic preflight;
5. validate scripts/configuration locally where possible;
6. resume the target diagnostic only after the infrastructure preflight has PASS evidence.

## Cheap synthetic probe

The preflight uses GitHub-hosted Ubuntu 26.04, `sbuild 0.91.2ubuntu3`, `--chroot-mode=unshare`, the exact retained Attempt 8 rootfs, and a tiny synthetic Debian source package — never KIO.

It must prove host-to-chroot transfer through `pre-build-commands` + `%SBUILD_CHROOT_EXEC`, in-chroot execution through `starting-build-commands`, the native `sbuild` user, `%p`, evidence return over stdout, and deliberate stop before `dpkg-buildpackage`. It must produce no `.deb`, `.changes` or `.buildinfo`.

The generated hook is checked with `bash -n`; generated `sbuild-config.pl` is checked with `perl -c` before sbuild starts.

## KIO Round 23

Round 23 is **BLOCKED pending diagnostic infrastructure preflight**. This is not a new KIO `FAIL`, not a package attempt and not authorization for Attempt 9.

After preflight PASS, Round 23 must be redesigned against the historical Attempt 8 execution path. A nondeterministic reproduction must preserve the original Debian build path as closely as practical instead of manually recreating selected build steps.

## General rule

Diagnostic infrastructure is a dependency. Uncertified infrastructure makes the target diagnostic `BLOCKED`. Infrastructure FAIL/INFRA_INVALID never changes package state.
