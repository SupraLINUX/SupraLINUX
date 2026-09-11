# Ubuntu 26.04 authoritative runner contract

Status: **repository implementation complete; real KVM certification pending**  
Last reviewed: **2026-09-11**

## Hosted lane

Repository policy and non-authoritative package-build preflight use explicit GitHub-hosted `ubuntu-26.04`; `ubuntu-latest` is forbidden. The expensive hosted `sbuild` proof is gated on the actual event delta, so infrastructure/documentation-only updates run the scope check but skip the package build.

## Authoritative boundary

The authoritative runner is a disposable Ubuntu 26.04 **KVM VM**. The long-lived libvirt host only supplies infrastructure and is not release-build evidence.

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

## Nested KVM is a runtime requirement, not a label

Checking that `/dev/kvm` exists or that QEMU was compiled with KVM support is insufficient. `scripts/check-nested-kvm-runtime.sh` actually starts a minimal paused x86_64 QEMU instance with:

```text
-machine q35 -accel kvm -cpu host
```

A healthy probe remains running until `timeout(1)` terminates it; any early QEMU failure is a gate failure and its output is preserved as evidence.

`runner-contract.yml` executes this runtime probe. `scripts/run-authoritative-package-proof.sh` executes it again immediately before build/test work, so a runner cannot pass merely because KVM was available when its golden image was created.

## System-test acceleration must not fall back to TCG

Ubuntu 26.04 `autopkgtest-virt-qemu` can run QEMU without hardware acceleration when KVM is unavailable. SupraLINUX explicitly forbids that for authoritative evidence.

The authoritative package proof therefore invokes the QEMU backend with:

```text
--qemu-options='-accel kvm'
```

This selects only the KVM accelerator. If nested KVM cannot initialize, the QEMU/autopkgtest gate fails instead of silently degrading to software emulation. Result evidence records `system_test_acceleration: kvm-required`.

## Golden image contract

The golden runner image is built from a signed/verified released Ubuntu Resolute cloud image by `scripts/build-authoritative-runner-image.sh`. Required provenance includes the source image SHA-256, exact SupraLINUX source commit, verified Actions runner digest, nested `autopkgtest` image SHA-256, offline sysprep evidence, final qcow2 validation and final golden-image SHA-256.

The golden image contains runner software but no persistent GitHub credential and no temporary SupraLINUX build-source checkout.

## Runtime JIT lifecycle

The host obtains repository-scoped `encoded_jit_config`, injects it into guest tmpfs and launches the runner as a non-root login user. One host-local `flock` serializes authoritative gates on the supported single-host setup.

Before triggering, the orchestrator refuses to start if an authoritative workflow is already queued/active. It snapshots prior workflow run IDs for the exact PR head SHA, applies the controlled label only after the JIT runner is online, then binds evidence to exactly one newly-created workflow run ID for that SHA. Ambiguous attribution fails closed.

Controlled pre-merge labels:

```text
ci:runner-contract
ci:authoritative-package-proof
```

Fork PRs are refused by both workflow conditions and host orchestration.

## Package isolation

The authoritative package path is:

```text
Ubuntu 26.04 KVM JIT runner VM
├── fresh sbuild/unshare build rootfs
│   └── .deb + .changes + .buildinfo + hashes
└── autopkgtest/QEMU with -accel kvm
    └── nested Ubuntu 26.04 KVM test VM
```

Build artifacts are captured immediately after successful `sbuild`, before later test gates.

## Continuous repository validation

Repository Policy runs `bash -n scripts/*.sh` and the machine-readable policy validator on GitHub-hosted Ubuntu 26.04. This validates syntax and required architectural invariants before host-side scripts reach real infrastructure.

## Certification requirement

A runner image/campaign becomes authoritative only after real evidence exists for:

1. host KVM/nested preflight;
2. verified Ubuntu source image and golden-image provenance;
3. real nested-KVM runtime probe PASS;
4. `runner-contract.yml` PASS on a disposable JIT guest;
5. authoritative `sbuild` PASS with retained `.deb/.changes/.buildinfo`;
6. `autopkgtest/QEMU` PASS with KVM forced;
7. bound workflow IDs, logs, hashes and artifacts.

Until those real KVM executions occur, authoritative status remains **pending**, not PASS.
