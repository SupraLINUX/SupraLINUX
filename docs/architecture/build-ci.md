# Build, CI and promotion architecture

Status: **active architecture**  
Last reviewed: **2026-09-11**

## Principles

SupraLINUX uses a DAG-guided hybrid build strategy. Each build node has exactly one terminal state:

- `PASS`: actually built/tested successfully for the evaluated gate;
- `FAIL`: actually attempted and failed for its own reason;
- `BLOCKED`: not attempted because a required dependency or execution capability is unavailable.

`BLOCKED` is never counted as `FAIL`.

For each campaign, resolve the source/version manifest, construct the dependency DAG, build all possible nodes by topological level, continue independent branches after failures, expose only PASS artifacts to dependents, preserve evidence and rerun the complete campaign before promotion.

## Hosted preflight lane

GitHub-hosted `ubuntu-26.04` performs repository validation, metadata checks and non-authoritative clean package-build preflight. `ubuntu-latest` is forbidden.

The hosted package proof creates a fresh Resolute `buildd` rootfs with `mmdebstrap`, builds through `sbuild --chroot-mode=unshare`, and preserves `.deb`, `.changes`, `.buildinfo`, logs and hashes. It intentionally does not claim the authoritative system-test gate.

A historical `autopkgtest/unshare` attempt failed during testbed setup after `sbuild/unshare` had succeeded. That backend is therefore not the authoritative system-test boundary.

The expensive hosted build is gated on the actual PR event delta. Infrastructure/documentation-only `synchronize` events execute the scope-check but skip `sbuild`; this behavior has real PASS evidence.

## Authoritative KVM/JIT lane

Release-relevant evidence is produced inside disposable self-hosted Ubuntu 26.04 **KVM VMs**. Required labels are:

`self-hosted`, `linux`, `x64`, `supralinux`, `ubuntu-26.04`, `kvm`, `ephemeral`.

The host requests fresh repository-scoped JIT configuration, injects it into guest tmpfs, executes one controlled job, exports diagnostics and destroys writable VM state. Pre-merge gates use controlled labels `ci:runner-contract` and `ci:authoritative-package-proof`; fork PRs are refused before self-hosted code execution.

Host orchestration is serialized locally. Before a runner is created, pre-existing queued/active authoritative workflows are rejected. Workflow evidence is bound to exactly one newly-created run ID for the exact PR head SHA; ambiguous attribution fails closed.

## Runtime KVM requirement

Nested KVM is an executable runtime gate, not merely a runner label or `/dev/kvm` existence check.

`scripts/check-nested-kvm-runtime.sh` starts a minimal paused QEMU process using `-accel kvm -cpu host`. A healthy process remains alive until the probe timeout terminates it. Early QEMU failure is a gate failure.

The runner-contract workflow and authoritative package proof both execute this probe.

## Deterministic system-test virtualization

Ubuntu's `autopkgtest-virt-qemu` can operate without hardware acceleration. Software emulation cannot count as authoritative SupraLINUX evidence.

The authoritative proof therefore supplies `scripts/qemu-kvm-required.sh` through `autopkgtest-virt-qemu --qemu-command` and pins `--qemu-architecture=x86_64`. The wrapper executes only:

```text
qemu-system-x86_64 -accel kvm <autopkgtest arguments>
```

There is no TCG fallback in the wrapper. The wrapper SHA-256 is retained in the run evidence.

Inside the authoritative runner VM the package path is:

```text
fresh sbuild/unshare
└── .deb + .changes + .buildinfo + hashes

then

autopkgtest/QEMU
└── KVM-only QEMU command wrapper
    └── nested Ubuntu 26.04 KVM test VM
```

Build artifacts are captured before the runtime test so a later test failure cannot erase evidence of a build PASS.

## Host and golden-image supply chain

The supported infrastructure recipe currently targets Ubuntu 26.04 amd64/x86_64. Host provisioning can install/configure KVM/libvirt and its network, but must not silently change BIOS/firmware or force KVM-module reloads.

The host must pass `scripts/check-kvm-host.sh`. The verified Ubuntu source image defaults to stable host storage under `/var/lib/supralinux/images/source/resolute/` rather than a developer checkout.

Golden-image chain:

```text
released Ubuntu Resolute cloud image
-> signed checksum verification
-> temporary qcow2 preparation overlay
-> Ubuntu 26.04 KVM preparation VM
-> exact SupraLINUX commit checkout
-> runner/toolchain provisioning
-> nested autopkgtest image creation
-> runner seal + temporary source checkout removal
-> VM poweroff
-> offline virt-sysprep
-> qemu-img flatten + check
-> standalone golden qcow2 + real SHA-256/provenance
```

The GitHub Actions runner archive is accepted only after verifying GitHub's published SHA-256 digest. Existing golden images are not replaced without explicit opt-in.

## Evidence contract

Important builds retain, where applicable:

- source/version/commit/tag and input hashes;
- resolved build dependencies/configuration;
- complete logs;
- `.deb`, `.changes`, `.buildinfo`, manifests and hashes;
- host preflight and verified Ubuntu source-image provenance;
- exact source commit used for the golden image;
- Actions runner release/digest;
- nested `autopkgtest` image SHA-256;
- offline sysprep/qcow2 validation;
- final golden-image SHA-256/provenance;
- nested-KVM runtime-probe evidence;
- KVM-only QEMU wrapper SHA-256;
- PR head SHA, bound workflow run ID and CI identifiers;
- runner/VM diagnostics and terminal gate state.

Hashes and results are evidence, never placeholders.

## Repository/promotion model

`upstream stable -> SupraLINUX packaging -> authoritative clean build -> authoritative tests -> incoming/staging -> candidate -> stable`

Repository publication/signing are separate from compilation. Builders should not require the stable repository private signing key.

## Initial gates

- repository/manifest and shell-syntax validation;
- source integrity;
- hosted clean-build preflight;
- host KVM/nested preflight;
- verified Ubuntu runner source image;
- reproducible golden-image provenance;
- authoritative Ubuntu 26.04 JIT/KVM runner certification;
- real nested-KVM runtime probe;
- authoritative clean `sbuild` build;
- package metadata validation;
- `autopkgtest/QEMU` through the KVM-only QEMU wrapper;
- dependency DAG consistency;
- install/upgrade tests;
- KDE session/runtime smoke tests;
- Ubuntu application compatibility tests for replaced shared libraries;
- repository publication verification.

Existing gates must not be removed silently; policy and documentation must change with implementation.
