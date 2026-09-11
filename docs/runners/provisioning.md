# Authoritative KVM runner provisioning

Status: **guest and host orchestration implemented; no runner image certified yet**  
Last reviewed: **2026-09-11**

This document describes the preparation boundary between the long-lived KVM/libvirt host and the disposable Ubuntu 26.04 guest that acts as the authoritative GitHub Actions runner.

## Host boundary

The host provides KVM/libvirt capacity and exposes nested virtualization to the runner guest. It is not itself a SupraLINUX build runner. The authoritative identity begins inside the disposable Ubuntu 26.04 VM.

Host orchestration is implemented in `scripts/run-kvm-jit-gate.sh` and documented in `docs/runners/host-kvm.md`.

## Source image

Use Ubuntu's released Resolute amd64 cloud image. `scripts/fetch-ubuntu-26.04-cloud-image.sh` downloads the release metadata, verifies `SHA256SUMS.gpg` with Ubuntu's cloud-image keyring, verifies the image SHA-256 and writes provenance next to the downloaded image.

A daily image must not silently replace the released-image source for the authoritative runner.

## Guest preparation

Inside a freshly booted Ubuntu 26.04 KVM preparation guest, run:

```bash
scripts/provision-authoritative-runner-guest.sh
```

The script verifies Ubuntu 26.04/KVM, installs the declared build/test toolchain, configures subordinate UID/GID ranges when missing, adds the intended runner user to the `kvm` group, enables qemu-guest-agent, installs the GitHub Actions runner and records actual versions/provenance.

The Actions runner installer resolves the current stable `actions/runner` release, requires GitHub's published SHA-256 digest for the Linux x64 asset, verifies the archive and records the exact release/digest installed. No runner registration credential is stored in the image.

A new login/session is required after adding the runner user to the `kvm` group.

## QEMU autopkgtest image

After `/dev/kvm` is readable/writable by the runner user, run:

```bash
scripts/prepare-autopkgtest-qemu-image.sh
```

The script calls Ubuntu's `autopkgtest-buildvm-ubuntu-cloud` for `resolute`/`amd64`, installs the image at:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

and generates its real SHA-256/provenance. No QEMU image hash is invented or predeclared.

## Golden-image seal

After guest provisioning and QEMU-image preparation, run:

```bash
scripts/seal-authoritative-runner-image.sh
```

The seal records the current Actions-runner evidence and QEMU-image SHA-256, removes any runner registration/work state, cleans APT cache, and resets cloud-init/machine identity for safe cloning. Power the VM off immediately afterwards and use the sealed disk only as a backing image.

## Runtime JIT registration

The golden image contains the runner software but **no GitHub registration token, PAT or JIT configuration**.

At runtime the libvirt host calls GitHub's repository JIT endpoint, receives `encoded_jit_config`, boots a fresh overlay guest and injects the JIT configuration into `/run` through qemu-guest-agent. The runner executes one job and is then removed. The host destroys the overlay after exporting diagnostics/evidence.

Required runtime labels are:

```text
self-hosted
linux
x64
supralinux
ubuntu-26.04
kvm
ephemeral
```

## Pre-merge gate activation

The KVM workflows can be certified while the PR remains Draft. They listen for controlled label events:

```text
ci:runner-contract
ci:authoritative-package-proof
```

The host applies a label only after the matching JIT runner is online, preventing a self-hosted job from sitting queued with no intended runner. Both host and workflows reject fork PRs.

## Certification sequence

A prepared VM image remains **pending** until real evidence exists for:

1. signed Ubuntu source-image verification and recorded source SHA-256;
2. golden-image preparation/seal provenance;
3. prepared QEMU test-image SHA-256;
4. `runner-contract.yml` PASS on a disposable JIT KVM guest;
5. `authoritative-package-proof.yml` PASS on a separate disposable JIT KVM guest;
6. preserved workflow artifacts and host/runner diagnostics.

The remaining dependency is an actual KVM/libvirt host on which to execute this implementation.
