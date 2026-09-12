# Ubuntu 26.04 authoritative runner contract

Status: **repository implementation complete; real KVM certification pending**  
Last reviewed: **2026-09-11**

## Hosted lane

Repository policy and the non-authoritative package-build preflight use explicit GitHub-hosted `ubuntu-26.04`; `ubuntu-latest` is forbidden. Expensive hosted `sbuild` work is gated on the actual event delta, so infrastructure/documentation-only updates execute the scope check but skip the package build.

## Authoritative boundary

The authoritative runner is a disposable Ubuntu 26.04 **KVM VM**. The long-lived libvirt host supplies infrastructure only and is not release-build evidence.

Required runner labels:

```text
self-hosted
linux
x64
supralinux
ubuntu-26.04
kvm
ephemeral
```

The guest must report Ubuntu 26.04 under KVM and expose readable/writable `/dev/kvm` to the runner user.

## Nested KVM is a runtime gate

The presence of `/dev/kvm` or KVM support in the QEMU binary is not sufficient evidence. `scripts/check-nested-kvm-runtime.sh` starts a minimal paused x86_64 QEMU instance with:

```text
-machine q35 -accel kvm -cpu host
```

A healthy probe stays alive until `timeout(1)` terminates it. Any earlier QEMU failure makes the gate fail and the probe output is retained.

`runner-contract.yml` runs this probe. `scripts/run-authoritative-package-proof.sh` runs it again before package work so runtime nested-KVM capability is established for the actual job.

## Deterministic QEMU/KVM command

Ubuntu 26.04 `autopkgtest-virt-qemu` can run without hardware acceleration when KVM is unavailable. SupraLINUX does not accept software emulation as authoritative evidence.

The repository therefore provides:

```text
scripts/qemu-kvm-required.sh
```

which executes:

```text
qemu-system-x86_64 -accel kvm <autopkgtest arguments>
```

The authoritative proof supplies that wrapper through `autopkgtest-virt-qemu --qemu-command` and pins `--qemu-architecture=x86_64`. Because SupraLINUX supplies the QEMU command itself, the test does not rely on autopkgtest's acceleration auto-detection and has no TCG fallback path in the wrapper.

The wrapper is hashed into the authoritative evidence as `qemu-kvm-wrapper-sha256.txt`. Result evidence records `system_test_acceleration: kvm-required`.

## Golden image contract

The golden runner image is built from a signed and verified released Ubuntu Resolute cloud image by `scripts/build-authoritative-runner-image.sh`. Required provenance includes:

- signed source-image metadata and SHA-256;
- exact SupraLINUX source commit;
- verified GitHub Actions runner release/digest;
- nested `autopkgtest` image SHA-256;
- guest provisioning/seal evidence;
- removal of the temporary build-source checkout;
- offline `virt-sysprep` evidence;
- final qcow2 validation and SHA-256.

The golden image contains runner software but no persistent GitHub credential and no temporary SupraLINUX build checkout.

## Runtime JIT lifecycle

The host obtains repository-scoped `encoded_jit_config`, injects it into guest tmpfs and starts the runner as a non-root login user. Host-local `flock` serializes authoritative gates on the supported single-host setup.

Before triggering, the orchestrator refuses to start if another authoritative workflow is queued or active. It snapshots existing workflow-run IDs for the exact PR head SHA, adds the controlled label only after the JIT runner is online, then binds evidence to exactly one newly-created workflow run ID for that SHA. Ambiguous attribution fails closed.

Controlled pre-merge labels:

```text
ci:runner-contract
ci:authoritative-package-proof
```

Fork PRs are refused by both workflow conditions and host orchestration.

## Package isolation

```text
Ubuntu 26.04 KVM JIT runner VM
├── fresh sbuild/unshare build rootfs
│   └── .deb + .changes + .buildinfo + hashes
└── autopkgtest/QEMU
    └── scripts/qemu-kvm-required.sh -> qemu-system-x86_64 -accel kvm
        └── nested Ubuntu 26.04 KVM test VM
```

Build artifacts are captured immediately after successful `sbuild`, before later test gates.

## Continuous repository validation

Repository Policy executes `bash -n scripts/*.sh` and `scripts/validate_repository.py` on GitHub-hosted Ubuntu 26.04. The policy requires the runtime nested-KVM probe, deterministic KVM-only QEMU wrapper, exact workflow-run binding, golden-image provenance, same-repository PR guard and the rest of the authoritative contract.

## Certification requirement

A runner image/campaign becomes authoritative only after real evidence exists for:

1. host KVM/nested preflight;
2. verified Ubuntu source image and real golden-image provenance;
3. nested-KVM runtime probe PASS;
4. `runner-contract.yml` PASS on a disposable JIT guest;
5. authoritative `sbuild` PASS with retained `.deb/.changes/.buildinfo`;
6. `autopkgtest/QEMU` PASS through the KVM-only QEMU wrapper;
7. bound workflow IDs, hashes, logs and artifacts.

Until those real KVM executions occur, authoritative status remains **pending**, not PASS.
