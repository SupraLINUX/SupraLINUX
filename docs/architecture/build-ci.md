# Build, CI and promotion architecture

Status: **active architecture**  
Last reviewed: **2026-09-11**

## Principles

SupraLINUX uses a DAG-guided hybrid build strategy. The purpose is to discover independent failures early without converting downstream dependency fallout into false failures.

Each build node has exactly one terminal state:

- `PASS`: the node was actually built/tested successfully for the gate being evaluated and its artifacts may feed dependents;
- `FAIL`: the node or gate was actually attempted and failed for its own build/test reason;
- `BLOCKED`: the node or gate was not attempted because a required dependency or execution capability is unavailable.

`BLOCKED` must never be counted as `FAIL`.

## Execution strategy

For each campaign:

1. resolve the selected source/version manifest;
2. construct the dependency DAG;
3. identify topological levels;
4. attempt every buildable node in a level, parallelizing independent nodes;
5. continue independent branches after failures;
6. expose only artifacts that passed the required build gate to dependents;
7. mark impossible downstream nodes `BLOCKED`;
8. preserve logs and metadata for every attempted node/gate;
9. fix root causes incrementally;
10. rerun the complete campaign before promotion.

## Runner classes

### Hosted preflight lane

GitHub-hosted `ubuntu-26.04` is used for repository validation, metadata checks and non-authoritative package-build preflight. `ubuntu-latest` is forbidden.

The hosted package proof creates a fresh Ubuntu 26.04 `buildd` rootfs with `mmdebstrap`, builds through `sbuild --chroot-mode=unshare`, and preserves `.deb`, `.changes`, `.buildinfo`, logs and hashes. It does not claim the authoritative system-test gate.

`autopkgtest/unshare` is not part of the authoritative testing contract because a real hosted attempt failed in testbed setup because of UID/GID ownership mapping even though binary `sbuild/unshare` had completed.

The expensive hosted build is gated on the actual event delta. On `pull_request/synchronize`, the workflow compares the event `before` and `after` SHAs and invokes `scripts/package-preflight-needed.sh`. Infrastructure/documentation-only deltas still run the small scope-check job but explicitly skip `sbuild`. Run `34658857824` is real evidence that this skip path works as intended.

### Authoritative KVM build/test lane

Release-relevant package evidence is produced inside disposable self-hosted **KVM virtual machines** running Ubuntu 26.04. The KVM guest, not the long-lived host, is the GitHub Actions runner.

Required labels:

`self-hosted`, `linux`, `x64`, `supralinux`, `ubuntu-26.04`, `kvm`, `ephemeral`

The runner uses repository-scoped GitHub JIT configuration. The host requests fresh `encoded_jit_config`, injects it into guest tmpfs, executes exactly one controlled job, exports diagnostics and destroys writable VM state.

Pre-merge authoritative gates use controlled `pull_request` label events: `ci:runner-contract` and `ci:authoritative-package-proof`. Both workflow and host orchestration reject fork PRs before self-hosted code execution.

Inside the authoritative runner VM:

- package compilation uses fresh `sbuild/unshare` isolation;
- `.deb`, `.changes`, `.buildinfo` and hashes are captured before later gates;
- system testing uses `autopkgtest/QEMU` with a prepared Ubuntu 26.04 image;
- nested KVM is mandatory so the authoritative system-test gate cannot silently fall back to software emulation.

This gives distinct boundaries for host, runner VM, package build rootfs and package runtime test VM.

## Host and golden runner image supply chain

The supported bootstrap recipe currently targets Ubuntu 26.04 amd64/x86_64 as an infrastructure provider. Host provisioning may install/configure KVM/libvirt and the standard network but does not silently modify firmware or force KVM-module reloads.

The host must pass `scripts/check-kvm-host.sh` before golden-image construction or authoritative execution.

The golden-image chain is:

```text
Ubuntu released Resolute cloud image
-> signed checksum verification
-> temporary qcow2 preparation overlay
-> Ubuntu 26.04 KVM preparation VM
-> exact SupraLINUX source commit checkout
-> runner/toolchain provisioning
-> nested autopkgtest QEMU image creation
-> guest-side seal
-> VM poweroff
-> offline virt-sysprep
-> qemu-img flatten + check
-> standalone golden qcow2 + SHA-256/provenance
```

`scripts/build-authoritative-runner-image.sh` implements this sequence. It refuses to publish over an existing golden image unless `SUPRALINUX_REPLACE_GOLDEN_IMAGE=1` is set explicitly. Failed preparation state is retained for diagnosis.

The Actions runner archive is accepted only after verifying GitHub's published SHA-256 digest. The nested `autopkgtest` image and final golden qcow2 receive real generated SHA-256 evidence. No image hash is invented in source control.

A built golden image is still **pending**, not authoritative, until real KVM/JIT contract and package-proof workflows pass using that image.

## Evidence contract

Important builds retain, where applicable:

- source identifier/archive/version/commit/tag;
- SHA-256 of downloaded source inputs;
- resolved build dependencies and configuration;
- complete build/test logs;
- `.deb`, `.changes`, `.buildinfo` and manifests;
- host provisioning/preflight evidence;
- signed Ubuntu source-image provenance and SHA-256;
- exact repository commit used to build the golden image;
- GitHub Actions runner release/digest evidence;
- nested `autopkgtest` QEMU-image SHA-256;
- offline sysprep and qcow2 validation logs;
- final golden-image SHA-256/provenance;
- PR head SHA and CI run identifiers;
- runner/VM diagnostics;
- terminal gate state.

Hashes and test results are evidence, not placeholders. They must never be invented or copied from unrelated builds.

## Repository/promotion model

The intended package flow is:

`upstream stable -> SupraLINUX packaging -> authoritative clean build -> authoritative tests -> incoming/staging -> candidate -> stable`

Repository publication and signing are separate from compilation. Builders should not require the stable repository private signing key.

## Gates

Initial gates are:

- repository/manifest validation;
- source integrity;
- hosted clean-build preflight;
- host KVM/nested-virtualization preflight;
- verified Ubuntu runner source image;
- reproducible golden runner-image build/provenance;
- authoritative Ubuntu 26.04 KVM runner certification;
- authoritative clean package build under `sbuild`;
- package metadata validation;
- `autopkgtest/QEMU` system/package tests;
- dependency DAG consistency;
- install/upgrade tests;
- KDE session/runtime smoke tests;
- Ubuntu application compatibility tests for replaced shared libraries;
- repository publication verification.

Existing gates must not be removed silently; architecture documentation and machine-readable policy must change with implementation.
