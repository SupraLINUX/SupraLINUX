# Phase 1 — package-build proof

Status: **implementation in progress; hosted clean build demonstrated, authoritative KVM test pending**  
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

`.github/workflows/package-build-proof.yml` runs on explicit GitHub-hosted `ubuntu-26.04` and now limits its claim to the clean-build preflight:

1. verify Ubuntu 26.04;
2. verify user-namespace/subordinate-ID support;
3. create the Debian source package;
4. create a fresh Ubuntu 26.04 `buildd` rootfs with `mmdebstrap`;
5. build through `sbuild --chroot-mode=unshare`;
6. require `.deb`, `.changes` and `.buildinfo`;
7. immediately hash and preserve those artifacts;
8. upload complete build evidence.

This lane is **non-authoritative** and no longer runs `autopkgtest/unshare`. A PASS here means only that the clean package-build preflight passed.

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
- overall workflow/node state: **FAIL** because the attempted test gate failed;
- repository-policy run on the same commit: **PASS** (`34612685023`);
- source package creation: **PASS**;
- fresh `mmdebstrap` resolute buildd rootfs: **PASS**;
- binary `sbuild/unshare`: **PASS**;
- required `.deb`, `.changes`, `.buildinfo` existence check: **PASS**;
- `autopkgtest` smoke test body: **NOT EXECUTED**;
- `autopkgtest/unshare` testbed creation: **FAIL** with exit code `16` while extracting files whose UID/GID ownership could not be mapped;
- artifact upload: **PASS**;
- artifact ID: `10268924575`;
- artifact ZIP SHA-256: `bf7284454e04548936a89bc0576f96bef6ad9d1d141af3c02e817de7f926e0b8`;
- source `.dsc` SHA-256: `8582e9774ab04a9151e4675701bf09a9d815e482c0b7522dd44e4acd364305c4`;
- source tarball SHA-256: `51e293c475d19d97962d064ac86888bf35da474b4d6de1f5301ed433bd88d668`;
- sbuild rootfs tarball SHA-256: `2cda6d2612cedbb8211368083a57176d96dbd78dbf7b504f849c4877779213f1`.

The binary-build PASS is supported by the execution path: the script checked for all required binary build artifacts and then invoked `autopkgtest` with the concrete file `supralinux-build-test_0.1.0_all.deb`. However, attempt 2 exposed an evidence defect: the binary artifacts were copied to the evidence directory only *after* `autopkgtest`, so the subsequent testbed failure prevented them from being retained. `sbuild.log` was also empty because the previous invocation did not request verbose stdout logging.

Those evidence defects are corrected in the next implementation: binary artifacts and hashes are preserved immediately after `sbuild`, and `sbuild --verbose` is used.

## Architecture decision after attempt 2

The hosted runner remains useful for build preflight but is not the authoritative system-test environment.

The accepted Phase 1 architecture is now:

```text
GitHub-hosted ubuntu-26.04
└── non-authoritative source + sbuild preflight

Disposable Ubuntu 26.04 KVM runner VM
├── fresh sbuild/unshare package build
└── autopkgtest
    └── nested QEMU/KVM Ubuntu 26.04 test VM
```

This preserves the successful `sbuild/unshare` mechanism while moving the runtime/system test to the QEMU backend intended for full VM isolation.

## Completion criteria

Phase 1 is not complete until real evidence shows all of the following:

- hosted clean-build preflight PASS with preserved `.deb`, `.changes`, `.buildinfo` and non-empty build log;
- authoritative KVM runner contract PASS;
- authoritative clean `sbuild` package build PASS;
- authoritative `autopkgtest/QEMU` smoke test PASS;
- real hashes, logs and run IDs recorded in this document and the dated status document.
