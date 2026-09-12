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

Before the golden builder inspects or uses the local image, `scripts/verify-ubuntu-cloud-image-provenance.sh` revalidates the stored provenance and recalculates the image SHA-256. It requires:

- `release=resolute`;
- `architecture=amd64`;
- `signature=verified-with-gpgv`;
- exactly one valid `sha256` field;
- equality between that provenance hash and the current image bytes.

This is deliberately a second integrity check. Fetch-time verification proves what was downloaded; use-time verification detects later local modification before the image becomes a backing file.

## Preferred golden-image build

Golden-image preparation is automated by:

```bash
scripts/build-authoritative-runner-image.sh
```

The builder requires the KVM host preflight to pass and refuses to proceed without the verified source image and provenance. It then:

1. revalidates source-image provenance/SHA-256 and stores `source-image-verification.txt`;
2. inspects the now-revalidated image and creates a writable qcow2 preparation overlay;
3. boots an Ubuntu 26.04 preparation VM with `virt-install`, host CPU passthrough and cloud-init;
4. checks out the exact requested SupraLINUX commit inside the VM;
5. runs `scripts/provision-authoritative-runner-guest.sh`;
6. runs `scripts/prepare-autopkgtest-qemu-image.sh` as the runner user;
7. runs `scripts/seal-authoritative-runner-image.sh`;
8. removes the temporary `/opt/supralinux-src` build checkout from the guest and records that fact in completion evidence;
9. waits for the preparation VM to power off;
10. exports guest preparation evidence with libguestfs;
11. applies explicit offline `virt-sysprep` operations for machine identity, SSH host keys, DHCP state, logs and temporary files;
12. flattens the preparation overlay into a standalone qcow2 with `qemu-img convert`;
13. validates the final image with `qemu-img check`;
14. records the final golden-image SHA-256/provenance, including `source_image_provenance_verified=yes`.

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
2. use-time source-image provenance/SHA-256 revalidation;
3. successful automated golden-image build from an exact source commit;
4. confirmation that temporary build source is absent from the golden guest;
5. golden-image SHA-256 and offline sysprep/flatten/check evidence;
6. prepared nested QEMU test-image SHA-256;
7. `runner-contract.yml` PASS on a disposable JIT KVM guest;
8. `authoritative-package-proof.yml` PASS on a separate disposable JIT KVM guest;
9. preserved workflow artifacts and host/runner diagnostics.

The remaining dependency is an actual KVM/libvirt host on which to execute this implementation.
