# Ubuntu 26.04 runner contract

Status: **design contract; self-hosted image not yet certified**  
Last reviewed: **2026-09-11**

## Hosted runner

Repository checks use the explicit GitHub Actions label:

```text
ubuntu-26.04
```

`ubuntu-latest` is not permitted in SupraLINUX workflows.

Current external status: GitHub lists Ubuntu 26.04 x64 and arm64 hosted images, but marks them as public preview as of this review date.

## Self-hosted authoritative runner

The authoritative build runner is a disposable Ubuntu 26.04 VM, not a long-lived workstation and not a stateful build host.

Required conceptual labels:

```text
self-hosted
linux
x64
supralinux
ubuntu-26.04
ephemeral
```

Expected lifecycle:

1. boot a clean VM from the approved runner image;
2. register the GitHub Actions runner using ephemeral registration;
3. execute exactly one job;
4. export required build evidence;
5. unregister automatically;
6. destroy the VM.

## Expected toolchain

The runner image is expected to provide at least:

- `sbuild`;
- `schroot` or the selected supported sbuild backend;
- `debootstrap`;
- `devscripts`;
- `dpkg-dev`;
- `debhelper`;
- `build-essential`;
- `autopkgtest`;
- QEMU system tooling for VM tests;
- `aptly` for repository work where the runner role requires it;
- `gnupg` for non-secret verification operations;
- Git, jq and Python 3.

Exact package versions belong in the runner-image manifest once the image build exists.

## Certification requirement

A VM image is not a SupraLINUX authoritative runner merely because `/etc/os-release` says 26.04. Certification must capture the image revision, installed tool versions, virtualization capabilities and a successful clean sbuild/autopkgtest smoke campaign.

The manual `runner-contract` workflow exists to test the contract once such a runner is connected. Until then, the runner state is **pending**, not **passing**.
