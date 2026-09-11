# Ubuntu 26.04 authoritative runner contract

Status: **design implemented in CI; KVM image not yet certified**  
Last reviewed: **2026-09-11**

## Hosted runner

Repository checks and the non-authoritative package-build preflight use the explicit GitHub Actions label:

```text
ubuntu-26.04
```

`ubuntu-latest` is not permitted in SupraLINUX workflows.

GitHub documents Ubuntu 26.04 hosted runners as public preview as of this review date. They are useful for early failure discovery but are not the release authority.

## Authoritative runner boundary

The authoritative runner is a disposable **KVM virtual machine** running Ubuntu 26.04. A long-lived physical host or workstation may provide libvirt/KVM capacity, but it is not itself the build runner.

Required conceptual GitHub labels:

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

## Lifecycle

1. Boot a clean VM from an approved Ubuntu 26.04 runner image.
2. Register the GitHub Actions runner with `--ephemeral`.
3. Execute exactly one job.
4. Upload build/test evidence and preserve runner diagnostics externally.
5. Allow the ephemeral runner registration to be removed after the job.
6. Destroy the VM and all writable state.

GitHub recommends ephemeral self-hosted runners for autoscaling because an ephemeral runner is assigned only one job. The image and lifecycle automation remain SupraLINUX responsibilities.

## Build isolation inside the VM

The outer KVM VM is not a replacement for package-level build isolation.

The package build still uses:

```text
Ubuntu 26.04 KVM runner VM
└── fresh sbuild/unshare build rootfs
    └── .deb + .changes + .buildinfo
```

The build artifacts and their hashes are captured immediately after `sbuild` succeeds. A later test failure must not erase evidence that the build gate already passed.

## System test isolation

System/package tests use a second VM boundary:

```text
Ubuntu 26.04 KVM runner VM
└── autopkgtest
    └── QEMU/KVM Ubuntu 26.04 test VM
```

Ubuntu 26.04 ships `autopkgtest 5.55`; its `autopkgtest-virt-qemu` backend uses a temporary overlay and does not modify the supplied base image. Ubuntu provides `autopkgtest-buildvm-ubuntu-cloud` to prepare an Ubuntu QEMU test image.

SupraLINUX reserves the following path inside the runner image:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

That image is not considered certified until a real SHA-256 and build provenance have been recorded. No hash is predeclared in the repository.

## Expected toolchain

The approved runner image must provide at least:

- `sbuild`;
- `mmdebstrap`;
- `uidmap`;
- `devscripts` and `dpkg-dev`;
- `debhelper` and `build-essential`;
- `autopkgtest`;
- `autopkgtest-buildvm-ubuntu-cloud`;
- `qemu-system-x86_64` and `qemu-img`;
- `aptly` for repository roles that require it;
- `gnupg` for non-secret verification operations;
- Git, jq and Python 3.

Exact package versions belong in certification evidence from the actual runner image.

## Provisioning implementation

The repository now contains guest-side preparation scripts:

- `scripts/provision-authoritative-runner-guest.sh` installs and records the real Ubuntu 26.04 build/test toolchain;
- `scripts/prepare-autopkgtest-qemu-image.sh` creates the real Resolute QEMU test image and records its generated SHA-256/provenance.

See `docs/runners/provisioning.md` for the handoff between the KVM host, guest-image preparation and ephemeral GitHub runner registration.

## Certification requirement

A VM is not authoritative merely because `/etc/os-release` says 26.04. Certification must capture at least:

- runner VM image revision/build identifier;
- Ubuntu release and kernel;
- `systemd-detect-virt` result;
- `/dev/kvm` access;
- relevant KVM module/nested state;
- installed tool versions;
- SHA-256 of the prepared `autopkgtest` QEMU base image;
- successful clean `sbuild` proof;
- successful `autopkgtest/QEMU` proof;
- workflow run ID and preserved logs/artifacts.

The manual `runner-contract` workflow checks the static contract. The separate authoritative package-proof workflow checks the complete build/test path. Until both have real passing evidence, authoritative status is **pending**, not `PASS`.
