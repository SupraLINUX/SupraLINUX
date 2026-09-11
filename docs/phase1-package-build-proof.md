# Phase 1 — package-build proof

Status: **hosted clean-build preflight PASS; authoritative KVM test pending**  
Last reviewed: **2026-09-11**

## Purpose

This phase proves the mechanics required before SupraLINUX starts building the real KDE dependency graph.

The proof package is intentionally trivial. Its value is the build, isolation, test and evidence path, not the payload.

## Package

`packages/supralinux-build-test`

It is a native Debian source package with:

- `debhelper-compat (= 13)`;
- an architecture-independent binary package;
- one installed command and one data marker;
- one superficial `autopkgtest` smoke test.

The package is not part of the intended desktop product.

## Hosted preflight lane

`.github/workflows/package-build-proof.yml` runs on explicit GitHub-hosted `ubuntu-26.04` and limits its claim to the clean-build preflight:

1. verify Ubuntu 26.04;
2. verify user-namespace/subordinate-ID support;
3. create the Debian source package;
4. create a fresh Ubuntu 26.04 `buildd` rootfs with `mmdebstrap`;
5. build through `sbuild --chroot-mode=unshare`;
6. require `.deb`, `.changes` and `.buildinfo`;
7. immediately hash and preserve those artifacts;
8. upload complete build evidence.

This lane is **non-authoritative** and does not claim the system-test gate.

## Authoritative lane

`.github/workflows/authoritative-package-proof.yml` targets only runners labeled:

```text
self-hosted, linux, x64, supralinux, ubuntu-26.04, kvm, ephemeral
```

The runner must itself be a disposable Ubuntu 26.04 KVM guest. Inside that guest the package is built with fresh `sbuild/unshare`, artifacts are preserved, and the package smoke test is then executed with `autopkgtest/QEMU` against a prepared Ubuntu 26.04 QEMU image.

Until a certified runner exists, this lane is pending and is not dispatched merely to produce a queued/failing result.

## Evidence state

### Historical attempt 1 — schroot session failure

- commit: `0caf24e421c5db2083fbcdab3e6a5e185d888b9c`;
- workflow run: `34610526616`;
- overall node state: **FAIL**;
- source package creation: **PASS**;
- clean rootfs creation: **PASS**;
- binary `sbuild`: **FAIL** while opening the schroot session;
- observed error: `E: Error creating chroot session: skipping supralinux-build-test`;
- artifact upload: **PASS**;
- artifact ID: `10268843020`;
- artifact ZIP SHA-256: `0e17798003bdb563d0fd99a299e8d4b316fd9ffbd2467e0faf70019687c95450`.

### Historical attempt 2 — build passed, autopkgtest/unshare infrastructure failed

- commit: `2191257afab786906ba75ef693e63d4394828126`;
- workflow run: `34612684880`;
- overall workflow/node state: **FAIL** because the attempted testbed gate failed;
- repository-policy run on the same commit: **PASS** (`34612685023`);
- source package creation: **PASS**;
- fresh `mmdebstrap` resolute buildd rootfs: **PASS**;
- binary `sbuild/unshare`: **PASS**;
- required `.deb`, `.changes`, `.buildinfo` existence check: **PASS**;
- `autopkgtest` smoke test body: **NOT EXECUTED**;
- `autopkgtest/unshare` testbed creation: **FAIL** with exit code `16` while extracting files whose UID/GID ownership could not be mapped;
- artifact upload: **PASS**;
- artifact ID: `10268924575`;
- artifact ZIP SHA-256: `bf7284454e04548936a89bc0576f96bef6ad9d1d141af3c02e817de7f926e0b8`.

Attempt 2 exposed an evidence defect: binary artifacts were copied only after `autopkgtest`, and `sbuild.log` was empty. Both were corrected before attempt 3.

### Attempt 3 — hosted clean-build preflight PASS

- commit: `616d1f91b5aff2b1891bbe8ebfafb409e573818e`;
- workflow run: `34615234032`;
- result: **PASS**;
- repository-policy run: **PASS** (`34615233851`);
- artifact ID: `10269819217`;
- artifact ZIP SHA-256: `6ac6862bd712e346934472cfc3b6e2c50d49165dbc608216a2ed52eb0623befc`;
- `.deb` SHA-256: `3422149c39160b984a1fe3afa8e04286b29050144029a305c5058a7dadc5caf4`;
- `.changes` SHA-256: `4cc921de00dbd0bf448809f5394bbceb94282fb626a3c39c473d58f81db87839`;
- `.buildinfo` SHA-256: `7cd6415472b3cf7b1f01e67249b6030210bd4d1011c0b11e622cb7bf49c5c46f`;
- source `.dsc` SHA-256: `8582e9774ab04a9151e4675701bf09a9d815e482c0b7522dd44e4acd364305c4`;
- source tarball SHA-256: `51e293c475d19d97962d064ac86888bf35da474b4d6de1f5301ed433bd88d668`;
- fresh sbuild rootfs SHA-256: `a7915cb70414103ddb9bcda5228a7ec30c2ce1c8d1a0161e54df7184cdb821eb`;
- `sbuild.log`: **101653 bytes**, ending with `Status: successful`;
- Lintian completed successfully with one warning (`no-manual-page`) on the intentionally trivial proof package.

The artifact was downloaded and inspected after the workflow completed. It contains the actual `.deb`, `.changes`, `.buildinfo`, build/rootfs/source hashes, logs and `result.json`. `result.json` explicitly records `state: PASS`, `authoritative: false`, `scope: source-and-clean-sbuild-only`, and no system-test backend.

## Accepted Phase 1 architecture

```text
GitHub-hosted ubuntu-26.04
└── non-authoritative source + sbuild preflight  [PASS demonstrated]

Disposable Ubuntu 26.04 KVM runner VM
├── fresh sbuild/unshare package build          [pending authoritative evidence]
└── autopkgtest
    └── nested QEMU/KVM Ubuntu 26.04 test VM    [pending authoritative evidence]
```

Guest preparation is implemented by `scripts/provision-authoritative-runner-guest.sh` and `scripts/prepare-autopkgtest-qemu-image.sh`; see `docs/runners/provisioning.md`.

## Completion criteria

Phase 1 is not complete until real evidence shows all of the following:

- hosted clean-build preflight PASS with preserved `.deb`, `.changes`, `.buildinfo` and non-empty build log — **PASS**;
- authoritative KVM runner contract PASS — **pending**;
- authoritative clean `sbuild` package build PASS — **pending**;
- authoritative `autopkgtest/QEMU` smoke test PASS — **pending**;
- real hashes, logs and run IDs recorded in this document and the dated status document.
