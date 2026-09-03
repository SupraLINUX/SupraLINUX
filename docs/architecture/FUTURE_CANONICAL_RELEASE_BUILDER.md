# SupraLINUX — Future canonical release builder

Status: **FUTURE**

This document records a post-qualification release-engineering requirement. It does **not** change KSQ-1, Aurora package qualification, or the current use of GitHub Actions for development and qualification work.

## Decision

Before SupraLINUX performs production release builds, the project should operate a **canonical release builder** under a stable, explicitly controlled contract.

GitHub Actions may remain an orchestration, development, test, and qualification platform, but a hosted runner that is itself preview/experimental must not become the sole authority that produces artifacts promoted to the SupraLINUX stable release channel.

## Required properties

The canonical release builder must, before promotion to production use:

- run on a stable supported platform compatible with the SupraLINUX release base;
- be reproducible from documented/declarative configuration rather than hand-maintained machine state;
- consume pinned and authenticated source/package inputs, including the exact Ubuntu snapshot and SupraLINUX repository generation selected for the release;
- build in disposable isolated environments rather than mutating the builder host into the target system;
- preserve the same package-solver and build semantics qualified by SupraLINUX unless a separately certified migration replaces them;
- support network-isolated package builds where the qualification contract requires it;
- preserve source packages, binary packages, `.buildinfo`, `.changes`, logs, manifests, checksums, Build IDs and builder identity;
- generate or attach the release provenance/SBOM/attestation evidence required by the release pipeline;
- keep signing credentials separated from public serving infrastructure and from ordinary untrusted build jobs;
- support independent rebuild/comparison and an auditable testing-to-stable promotion process;
- be maintainable, recoverable and replaceable from documented automation.

## Current boundary

As of 2026-09-03, GitHub documents the hosted `ubuntu-26.04` runner as **Public preview**. SupraLINUX may use that runner to investigate and qualify the direct `mmdebstrap` + `sbuild --chroot-mode=unshare` architecture, but preview status prevents treating that hosted runner alone as the final canonical production release builder.

This FUTURE requirement must not cause a fallback to Ubuntu 24.04, Docker, privileged builds, or any other architecture change inside the active KSQ work without root-cause evidence and separate qualification.

## Promotion condition

Design and implementation of the canonical builder begin after the product/build architecture has stabilized sufficiently that its qualified build contract can be reproduced deliberately. The chosen implementation must itself pass reproducibility, clean-build, isolation, recovery, artifact-integrity and release-promotion certification before it becomes authoritative.
