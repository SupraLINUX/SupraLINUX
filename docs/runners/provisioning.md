# Authoritative KVM runner provisioning

Status: **implementation available; no runner image certified yet**  
Last reviewed: **2026-09-11**

This document describes preparation of the Ubuntu 26.04 guest that acts as the authoritative GitHub Actions runner. It does not describe the long-lived KVM/libvirt host, whose physical placement is infrastructure-specific.

## Host boundary

The host must provide KVM virtualization and expose nested KVM to the Ubuntu 26.04 runner guest. The guest should use host CPU virtualization capabilities (for example, libvirt host-passthrough) so that `/dev/kvm` is available inside the guest.

The host itself is not a SupraLINUX build runner. Its role is to create and destroy disposable guest VMs.

## Guest preparation

Inside a freshly installed Ubuntu 26.04 KVM guest, run:

```bash
scripts/provision-authoritative-runner-guest.sh
```

The script verifies that the guest is Ubuntu 26.04 running under KVM, installs the declared build/test toolchain, configures subordinate UID/GID ranges when missing, adds the intended runner user to the `kvm` group, and records the actual package versions used during provisioning.

A new login/session is required after adding the runner user to the `kvm` group.

## QEMU autopkgtest image

After `/dev/kvm` is readable/writable by the runner user, run:

```bash
scripts/prepare-autopkgtest-qemu-image.sh
```

The script calls Ubuntu's `autopkgtest-buildvm-ubuntu-cloud` for `resolute`/`amd64`, installs the resulting image at:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

and generates real SHA-256/provenance evidence beside it. No QEMU image hash is hard-coded in source control before the image actually exists.

## GitHub runner registration

Registration is deliberately outside the baked image because the registration/JIT token is short-lived and sensitive. At VM boot, the orchestration layer must obtain a fresh token, register the runner with `--ephemeral`, and apply the labels:

```text
self-hosted
linux
x64
supralinux
ubuntu-26.04
kvm
ephemeral
```

After one job, the runner is de-registered by GitHub and the orchestration layer must destroy the VM.

## Certification sequence

A prepared VM image is still **pending**, not authoritative, until real evidence exists for:

1. `runner-contract.yml` PASS;
2. the QEMU image SHA-256;
3. `authoritative-package-proof.yml` PASS;
4. preserved runner/build/test logs and artifacts.

The next infrastructure dependency is therefore a KVM/libvirt host that can boot this guest with nested KVM and perform ephemeral GitHub runner registration.
