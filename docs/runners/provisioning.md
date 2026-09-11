# Authoritative KVM runner provisioning

Status: **guest, host, golden-image and JIT orchestration implemented; no runner image certified yet**  
Last reviewed: **2026-09-11**

This document describes the preparation boundary between the long-lived KVM/libvirt host and the disposable Ubuntu 26.04 guest that acts as the authoritative GitHub Actions runner.

## Host boundary

The host provides KVM/libvirt capacity and exposes nested virtualization to the runner guest. It is not itself a SupraLINUX build runner. The authoritative identity begins inside the disposable Ubuntu 26.04 VM.

Host bootstrap/preflight is implemented by:

```text
scripts/provision-kvm-host.sh
scripts/check-kvm-host.sh
```

Host JIT orchestration is implemented by `scripts/run-kvm-jit-gate.sh` and documented in `docs/runners/host-kvm.md`.

## Source image

Use Ubuntu's released Resolute amd64 cloud image. `scripts/fetch-ubuntu-26.04-cloud-image.sh` downloads the release metadata, verifies `SHA256SUMS.gpg` with Ubuntu's cloud-image keyring, verifies the image SHA-256 and writes provenance next to the downloaded image.

A daily image must not silently replace the released-image source for the authoritative runner.

## Preferred golden-image build

Golden-image preparation is automated by:

```bash
scripts/build-authoritative-runner-image.sh
```

The builder requires the KVM host preflight to pass and refuses to proceed without the verified source image and its provenance file. It then:

1. creates a writable qcow2 preparation overlay from the verified Ubuntu image;
2. boots an Ubuntu 26.04 preparation VM with `virt-install`, host CPU passthrough and cloud-init;
3. checks out the exact requested SupraLINUX commit inside the VM;
4. runs `scripts/provision-authoritative-runner-guest.sh`;
5. runs `scripts/prepare-autopkgtest-qemu-image.sh` as the runner user;
6. runs `scripts/seal-authoritative-runner-image.sh`;
7. waits for the preparation VM to power off;
8. exports guest preparation evidence with libguestfs;
9. applies explicit offline `virt-sysprep` operations for machine identity, SSH host keys, DHCP state, logs and temporary files;
10. flattens the preparation overlay into a standalone qcow2 with `qemu-img convert`;
11. validates the final image with `qemu-img check`;
12. records the final golden-image SHA-256 and provenance.

The default target is:

```text
/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2
```

An existing golden image is never replaced implicitly. Replacement requires:

```bash
export SUPRALINUX_REPLACE_GOLDEN_IMAGE=1
```

A failed build preserves its preparation state/evidence for diagnosis and does not publish a final golden image.

## Guest preparation components

The automated builder calls these guest-side components. They remain individually runnable for diagnosis or controlled manual preparation.

### Runner guest toolchain

`scripts/provision-authoritative-runner-guest.sh` verifies Ubuntu 26.04/KVM, installs the declared build/test toolchain, configures subordinate UID/GID ranges when missing, adds the intended runner user to the `kvm` group, enables qemu-guest-agent, installs the GitHub Actions runner and records actual versions/provenance.

The Actions runner installer resolves the current stable `actions/runner` release, requires GitHub's published SHA-256 digest for the Linux x64 asset, verifies the archive and records the exact release/digest installed. No runner registration credential is stored in the image.

### Nested QEMU autopkgtest image

`scripts/prepare-autopkgtest-qemu-image.sh` calls Ubuntu's `autopkgtest-buildvm-ubuntu-cloud` for `resolute`/`amd64`, installs the result at:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

and generates its real SHA-256/provenance. No QEMU image hash is invented or predeclared.

### Guest-side seal

`scripts/seal-authoritative-runner-image.sh` records the Actions-runner evidence and nested QEMU-image SHA-256, removes runner registration/work state and cleans APT state. Clone identity is finalized offline by the host-side golden builder with explicit `virt-sysprep` operations after the VM is powered off.

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

The host applies a label only after the matching JIT runner is online. Both host and workflows reject fork PRs.

## Certification sequence

A prepared VM image remains **pending** until real evidence exists for:

1. signed Ubuntu source-image verification and recorded source SHA-256;
2. successful automated golden-image build with exact source commit recorded;
3. golden-image SHA-256 and offline sysprep/flatten/check evidence;
4. prepared nested QEMU test-image SHA-256;
5. `runner-contract.yml` PASS on a disposable JIT KVM guest;
6. `authoritative-package-proof.yml` PASS on a separate disposable JIT KVM guest;
7. preserved workflow artifacts and host/runner diagnostics.

The remaining dependency is an actual KVM/libvirt host on which to execute this implementation.
