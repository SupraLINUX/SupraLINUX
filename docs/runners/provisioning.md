# Authoritative KVM runner provisioning

Status: **guest, host, golden-image and JIT orchestration implemented; no runner image certified yet**  
Last reviewed: **2026-09-11**

This document describes the preparation boundary between the long-lived KVM/libvirt host and the disposable Ubuntu 26.04 guest that acts as the authoritative GitHub Actions runner.

## Host boundary

The host provides KVM/libvirt capacity and exposes nested virtualization to the runner guest. It is not itself a SupraLINUX build runner. The authoritative identity begins inside the disposable Ubuntu 26.04 VM.

Host bootstrap/preflight is implemented by `scripts/provision-kvm-host.sh` and `scripts/check-kvm-host.sh`. Host JIT orchestration is implemented by `scripts/run-kvm-jit-gate.sh`.

## Source image

Use Ubuntu's released Resolute amd64 cloud image. `scripts/fetch-ubuntu-26.04-cloud-image.sh` verifies `SHA256SUMS.gpg`, verifies the selected image SHA-256 and writes provenance beside it.

The default host storage is intentionally outside the source checkout:

```text
/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img
```

This keeps the backing image in stable host infrastructure storage for `qemu:///system` instead of under a developer checkout/home directory. An alternate writable host path can be selected explicitly with `SUPRALINUX_CLOUD_IMAGE_DIR` / `SUPRALINUX_SOURCE_IMAGE`.

A daily image must not silently replace the released-image source.

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
7. removes the temporary `/opt/supralinux-src` build checkout from the guest and records that fact in completion evidence;
8. waits for the preparation VM to power off;
9. exports guest preparation evidence with libguestfs;
10. applies explicit offline `virt-sysprep` operations for machine identity, SSH host keys, DHCP state, logs and temporary files;
11. flattens the preparation overlay into a standalone qcow2 with `qemu-img convert`;
12. validates the final image with `qemu-img check`;
13. records the final golden-image SHA-256 and provenance.

The default target is:

```text
/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2
```

An existing golden image is never replaced implicitly. Replacement requires `SUPRALINUX_REPLACE_GOLDEN_IMAGE=1`. A failed build preserves its preparation state/evidence for diagnosis and does not publish a final golden image.

## Guest preparation components

The automated builder calls these guest-side components; they remain individually runnable for diagnosis.

`scripts/provision-authoritative-runner-guest.sh` verifies Ubuntu 26.04/KVM, installs the declared build/test toolchain, configures subordinate UID/GID ranges, grants the runner user KVM access, enables qemu-guest-agent, installs the verified GitHub Actions runner and records actual versions/provenance.

`scripts/prepare-autopkgtest-qemu-image.sh` builds the Resolute/amd64 nested QEMU test image at:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

and records its real SHA-256/provenance.

`scripts/seal-authoritative-runner-image.sh` removes runner registration/work state and cleans guest package state. Final clone identity cleanup occurs offline after poweroff through `virt-sysprep` in the host-side golden builder.

## Runtime JIT registration

The golden image contains runner software but **no GitHub registration token, PAT, JIT configuration or build-source checkout**.

At runtime the libvirt host obtains `encoded_jit_config`, boots a fresh overlay guest, injects the JIT configuration into `/run` through qemu-guest-agent, executes one job, exports diagnostics/evidence and destroys the overlay.

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

The Draft PR can be certified with controlled label events:

```text
ci:runner-contract
ci:authoritative-package-proof
```

The host adds a label only after the matching JIT runner is online. Both host and workflows reject fork PRs.

## Certification sequence

A prepared image remains **pending** until real evidence exists for:

1. signed Ubuntu source-image verification and real source SHA-256;
2. successful automated golden-image build from an exact source commit;
3. confirmation that temporary build source is absent from the golden guest;
4. golden-image SHA-256 and offline sysprep/flatten/check evidence;
5. prepared nested QEMU test-image SHA-256;
6. `runner-contract.yml` PASS on a disposable JIT KVM guest;
7. `authoritative-package-proof.yml` PASS on a separate disposable JIT KVM guest;
8. preserved workflow artifacts and host/runner diagnostics.

The remaining dependency is an actual KVM/libvirt host on which to execute this implementation.
