# Ubuntu 26.04 authoritative runner contract

Status: **design and repository implementation complete; KVM image not yet certified**  
Last reviewed: **2026-09-11**

## Hosted runner

Repository checks and non-authoritative package-build preflight use explicit GitHub Actions `ubuntu-26.04`. `ubuntu-latest` is not permitted.

Hosted success is useful preflight evidence but is not release-build certification. Expensive hosted package builds are now gated on the actual event delta; infrastructure/documentation-only updates run the scope check but skip `sbuild`.

## Authoritative runner boundary

The authoritative runner is a disposable **KVM virtual machine** running Ubuntu 26.04. A long-lived physical host may provide libvirt/KVM capacity, but it is not itself the build runner.

Required labels:

```text
self-hosted
linux
x64
supralinux
ubuntu-26.04
kvm
ephemeral
```

The guest must report Ubuntu 26.04 and KVM virtualization. `/dev/kvm` must be readable/writable by the runner user so `autopkgtest/QEMU` can use nested KVM.

## Golden image contract

The golden runner image must be created from a verified Ubuntu released Resolute cloud image. `scripts/build-authoritative-runner-image.sh` is the supported builder and must record:

- source-image signed-checksum provenance;
- exact SupraLINUX source commit;
- Actions runner release/digest evidence;
- nested `autopkgtest` image SHA-256;
- guest provisioning/seal evidence;
- offline `virt-sysprep` log;
- final qcow2 validation;
- final golden-image SHA-256/provenance.

The final image is not replaced implicitly; replacement requires explicit operator opt-in. A successfully built image is still **pending certification** until real JIT/KVM workflows pass.

## Runtime lifecycle

1. create a writable overlay from the sealed golden image;
2. boot the Ubuntu 26.04 KVM guest with host CPU virtualization exposed;
3. request a repository-scoped GitHub JIT configuration;
4. inject the JIT configuration only into guest tmpfs;
5. execute one controlled job;
6. upload workflow evidence and export runner diagnostics;
7. remove stale labels/runner records if necessary;
8. destroy the VM and writable state.

Pre-merge certification uses controlled PR labels `ci:runner-contract` and `ci:authoritative-package-proof`; fork PRs are refused by both workflow and host orchestration.

## Build isolation inside the VM

The outer KVM VM does not replace package-level build isolation:

```text
Ubuntu 26.04 KVM runner VM
└── fresh sbuild/unshare rootfs
    └── .deb + .changes + .buildinfo
```

Artifacts and hashes are captured immediately after `sbuild` succeeds.

## System test isolation

System/package tests use a second virtualization boundary:

```text
Ubuntu 26.04 KVM runner VM
└── autopkgtest
    └── QEMU/KVM Ubuntu 26.04 test VM
```

SupraLINUX reserves:

```text
/var/lib/supralinux/autopkgtest/resolute-amd64.img
```

No QEMU-image hash is source-controlled before the image actually exists.

## Certification requirement

Certification must capture at least:

- host preflight state;
- golden runner image SHA-256/provenance;
- Ubuntu release/kernel and KVM boundary;
- `/dev/kvm` and nested virtualization state;
- installed tool versions;
- nested `autopkgtest` image SHA-256;
- successful `runner-contract.yml`;
- successful authoritative `sbuild` proof;
- successful `autopkgtest/QEMU` proof;
- workflow IDs, logs and artifacts.

Until the real KVM host executes both authoritative workflows successfully, authoritative status remains **pending**, not `PASS`.
