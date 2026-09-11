# Ubuntu 26.04 authoritative runner contract

Status: **design and orchestration implemented; KVM image not yet certified**  
Last reviewed: **2026-09-11**

## Hosted runner

Repository checks and the non-authoritative package-build preflight use the explicit GitHub Actions label:

```text
ubuntu-26.04
```

`ubuntu-latest` is not permitted in SupraLINUX workflows. GitHub documents Ubuntu 26.04 hosted runners as public preview as of this review date. They are useful for early failure discovery but are not the release authority.

## Authoritative runner boundary

The authoritative runner is a disposable **KVM virtual machine** running Ubuntu 26.04. A long-lived physical host or workstation may provide libvirt/KVM capacity, but it is not itself the build runner.

Required GitHub labels:

```text
self-hosted
linux
x64
supralinux
ubuntu-26.04
kvm
ephemeral
```

The guest must report:

```text
ID=ubuntu
VERSION_ID=26.04
systemd-detect-virt --vm -> kvm
```

For the authoritative system-test gate, `/dev/kvm` must be present and readable/writable by the runner user. This is the explicit nested-KVM contract for running `autopkgtest/QEMU` inside the runner VM.

## JIT lifecycle

The golden image contains the GitHub Actions runner binary but no registration credential. At runtime the KVM host requests repository-scoped JIT configuration from GitHub and supplies `encoded_jit_config` to `run.sh --jitconfig` inside the fresh guest.

Lifecycle:

1. create a fresh writable overlay from the sealed Ubuntu 26.04 golden image;
2. boot the KVM guest;
3. request a fresh JIT runner configuration;
4. inject it into guest tmpfs rather than the golden disk;
5. wait for the runner to become online;
6. trigger one controlled authoritative gate;
7. execute one job;
8. preserve workflow evidence and runner diagnostics;
9. remove the transient gate label/stale runner record if needed;
10. destroy the guest and overlay.

The workflows support pre-merge certification via controlled PR labels. They also require the PR head repository to equal the SupraLINUX repository, so fork code is not intentionally admitted to the self-hosted runner.

## Build isolation inside the VM

The outer KVM VM is not a replacement for package-level build isolation:

```text
Ubuntu 26.04 KVM runner VM
└── fresh sbuild/unshare build rootfs
    └── .deb + .changes + .buildinfo
```

Build artifacts and hashes are captured immediately after `sbuild` succeeds. A later test failure must not erase evidence that the build gate already passed.

## System-test isolation

System/package tests use a second VM boundary:

```text
Ubuntu 26.04 KVM runner VM
└── autopkgtest
    └── QEMU/KVM Ubuntu 26.04 test VM
```

Ubuntu 26.04 ships `autopkgtest 5.55`; its QEMU backend uses a temporary overlay and does not modify the supplied base image. Ubuntu provides `autopkgtest-buildvm-ubuntu-cloud` to prepare an Ubuntu QEMU test image.

SupraLINUX reserves:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

That image is not considered certified until a real SHA-256 and build provenance have been recorded. No hash is predeclared in the repository.

## Runner-image supply chain

The source runner image is Ubuntu's **released** Resolute amd64 cloud image. Its signed `SHA256SUMS` metadata must be verified before use. The repository provides `scripts/fetch-ubuntu-26.04-cloud-image.sh` for that check.

The guest provisioning script installs the required build/test tools and a GitHub Actions runner archive. The runner installer requires GitHub release metadata to provide a SHA-256 digest and verifies the archive before extraction. Exact observed versions and hashes are evidence from the real image, not architecture constants.

Before cloning, `scripts/seal-authoritative-runner-image.sh` removes runner registration/job state and resets cloud-init/machine identity for the next boot.

## Expected toolchain

The approved runner image must provide at least:

- `sbuild` and `mmdebstrap`;
- `uidmap`;
- `devscripts`, `dpkg-dev`, `debhelper` and `build-essential`;
- `autopkgtest` and `autopkgtest-buildvm-ubuntu-cloud`;
- `qemu-system-x86_64`, `qemu-img` and qemu-guest-agent;
- `aptly` where the runner role requires repository work;
- `gnupg` for non-secret verification operations;
- Git, curl, jq and Python 3;
- verified GitHub Actions runner software.

Exact package versions belong in certification evidence from the actual runner image.

## Repository implementation

The relevant implementation is split intentionally:

- `scripts/fetch-ubuntu-26.04-cloud-image.sh`: signed released-image verification;
- `scripts/install-actions-runner.sh`: verified runner installation;
- `scripts/provision-authoritative-runner-guest.sh`: guest toolchain preparation;
- `scripts/prepare-autopkgtest-qemu-image.sh`: nested QEMU test-image preparation;
- `scripts/seal-authoritative-runner-image.sh`: golden-image cleanup/seal;
- `scripts/run-kvm-jit-gate.sh`: host-side JIT VM lifecycle and gate trigger;
- `.github/workflows/runner-contract.yml`: static runner certification gate;
- `.github/workflows/authoritative-package-proof.yml`: complete package build/test gate.

See `docs/runners/provisioning.md` and `docs/runners/host-kvm.md`.

## Certification requirement

A VM is not authoritative merely because `/etc/os-release` says 26.04. Certification must capture at least:

- signed source-image verification and source SHA-256;
- golden runner image revision/build evidence;
- Ubuntu release and kernel;
- `systemd-detect-virt` result;
- `/dev/kvm` access and relevant nested-KVM state;
- installed tool versions;
- GitHub Actions runner version/digest;
- SHA-256 of the prepared `autopkgtest` QEMU base image;
- successful clean `sbuild` proof;
- successful `autopkgtest/QEMU` proof;
- PR head SHA, workflow run ID and preserved host/runner/build logs.

Until both real authoritative workflows pass on disposable JIT KVM guests, authoritative status is **pending**, not `PASS`.
