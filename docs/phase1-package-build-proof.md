# Phase 1 — package-build proof

Status: **hosted clean-build preflight PASS; authoritative KVM execution pending**  
Last reviewed: **2026-09-11**

## Purpose

Phase 1 proves the build, isolation, runtime-test and evidence mechanics required before SupraLINUX starts the real KDE dependency graph. The package itself is intentionally trivial; the pipeline is the subject under test.

## Proof package

`packages/supralinux-build-test`

It is a native Debian source package with `debhelper-compat (= 13)`, one architecture-independent binary package, one installed command/data marker and one `autopkgtest` smoke test. It is not part of the intended desktop product.

## Hosted preflight lane

`.github/workflows/package-build-proof.yml` runs on explicit GitHub-hosted `ubuntu-26.04` and limits its claim to source + clean `sbuild/unshare` mechanics:

1. validate Ubuntu/user-namespace prerequisites;
2. create the source package;
3. create a fresh Resolute `buildd` rootfs with `mmdebstrap`;
4. build through `sbuild --chroot-mode=unshare`;
5. require `.deb`, `.changes` and `.buildinfo`;
6. hash/copy those artifacts before any later gate;
7. upload build evidence.

This lane is **non-authoritative** and deliberately does not run the system-test gate. Its expensive build is gated on the actual event delta; infrastructure/documentation-only PR synchronizations execute the scope-check but skip `sbuild`.

## Authoritative lane

`.github/workflows/authoritative-package-proof.yml` targets only:

```text
self-hosted, linux, x64, supralinux, ubuntu-26.04, kvm, ephemeral
```

The runner must be a disposable Ubuntu 26.04 KVM guest. Inside it:

1. `scripts/check-nested-kvm-runtime.sh` must prove a real `qemu-system-x86_64 -accel kvm -cpu host` process initializes successfully;
2. the proof package is rebuilt in a fresh `sbuild/unshare` rootfs;
3. `.deb`, `.changes`, `.buildinfo` and hashes are preserved immediately after build success;
4. `autopkgtest/QEMU` runs against the prepared Resolute image;
5. autopkgtest is given `scripts/qemu-kvm-required.sh` via `--qemu-command` and `--qemu-architecture=x86_64`;
6. that wrapper executes QEMU with `-accel kvm` and has no TCG fallback;
7. the wrapper itself is hashed into evidence.

A package/runtime test cannot count as authoritative if nested KVM is unavailable or QEMU falls back to software emulation.

## Evidence history

### Historical attempt 1 — schroot session failure

- commit `0caf24e421c5db2083fbcdab3e6a5e185d888b9c`;
- run `34610526616`;
- overall state **FAIL**;
- source package/rootfs creation **PASS**;
- binary `sbuild` **FAIL** while opening schroot session;
- artifact `10268843020`;
- artifact ZIP SHA-256 `0e17798003bdb563d0fd99a299e8d4b316fd9ffbd2467e0faf70019687c95450`.

### Historical attempt 2 — build passed; autopkgtest/unshare infrastructure failed

- commit `2191257afab786906ba75ef693e63d4394828126`;
- run `34612684880`;
- overall state **FAIL** because the attempted testbed gate failed;
- source + fresh `mmdebstrap` rootfs + binary `sbuild/unshare` **PASS**;
- package smoke body **NOT EXECUTED**;
- `autopkgtest/unshare` testbed setup **FAIL**, exit 16, on UID/GID ownership mapping;
- artifact `10268924575`;
- artifact ZIP SHA-256 `bf7284454e04548936a89bc0576f96bef6ad9d1d141af3c02e817de7f926e0b8`.

This exposed two evidence defects: binary artifacts were preserved too late and `sbuild.log` was empty. Both were corrected.

### Hosted clean-build PASS

Run `34615234032` on commit `616d1f91b5aff2b1891bbe8ebfafb409e573818e` completed **PASS**. Inspected artifact `10269819217`, ZIP SHA-256 `6ac6862bd712e346934472cfc3b6e2c50d49165dbc608216a2ed52eb0623befc`, contains the actual `.deb`, `.changes`, `.buildinfo`, source/rootfs/artifact hashes and a non-empty successful `sbuild.log`.

Hashes:

- `.deb`: `3422149c39160b984a1fe3afa8e04286b29050144029a305c5058a7dadc5caf4`;
- `.changes`: `4cc921de00dbd0bf448809f5394bbceb94282fb626a3c39c473d58f81db87839`;
- `.buildinfo`: `7cd6415472b3cf7b1f01e67249b6030210bd4d1011c0b11e622cb7bf49c5c46f`;
- `.dsc`: `8582e9774ab04a9151e4675701bf09a9d815e482c0b7522dd44e4acd364305c4`;
- source tarball: `51e293c475d19d97962d064ac86888bf35da474b4d6de1f5301ed433bd88d668`;
- fresh sbuild rootfs: `a7915cb70414103ddb9bcda5228a7ec30c2ce1c8d1a0161e54df7184cdb821eb`.

A later full hosted proof, run `34640717571`, also completed **PASS**; artifact `10280122077`, ZIP SHA-256 `db0f3688e8964393995607aca59d8adaee378ec250e6b497fbb74d98908f9a49`.

## Current Phase 1 architecture

```text
GitHub-hosted ubuntu-26.04
└── non-authoritative source + sbuild preflight       [PASS demonstrated]

Disposable Ubuntu 26.04 KVM JIT runner VM
├── nested-KVM runtime probe                          [pending real host]
├── fresh sbuild/unshare package build               [pending authoritative evidence]
└── autopkgtest/QEMU --qemu-command=<KVM-only wrapper>
    └── nested Ubuntu 26.04 KVM test VM               [pending authoritative evidence]
```

The runner image/toolchain/JIT lifecycle are implemented by the scripts under `scripts/` and documented in `docs/runners/`.

## Completion criteria

Phase 1 is complete only when real evidence shows:

- hosted clean-build preflight PASS with retained binary artifacts/logs — **PASS**;
- real KVM host and golden-image provenance — **pending**;
- authoritative runner-contract PASS including runtime nested-KVM probe — **pending**;
- authoritative clean `sbuild` package build PASS — **pending**;
- authoritative `autopkgtest/QEMU` smoke test PASS through the KVM-only QEMU command wrapper — **pending**;
- all real hashes, workflow IDs, logs and artifacts recorded here and in the dated status document.
