# Build, CI and promotion architecture

Status: **active architecture**  
Last reviewed: **2026-09-11**

## Principles

SupraLINUX uses a DAG-guided hybrid build strategy. The purpose is to discover independent failures early without converting downstream dependency fallout into false failures.

Each build node has exactly one of these terminal states:

- `PASS`: the node was actually built/tested successfully for the gate being evaluated and its artifacts may feed dependents;
- `FAIL`: the node or gate was actually attempted and failed for its own build/test reason;
- `BLOCKED`: the node or gate was not attempted because at least one required dependency or execution capability is unavailable.

`BLOCKED` must never be counted as `FAIL`.

## Execution strategy

For each campaign:

1. resolve the selected source/version manifest;
2. construct the dependency DAG;
3. identify topological levels;
4. attempt every buildable node in a level, parallelizing independent nodes;
5. continue independent branches after failures;
6. expose only artifacts that passed the required build gate to dependent levels;
7. mark impossible downstream nodes `BLOCKED`;
8. preserve logs and metadata for every attempted node/gate;
9. fix root causes incrementally;
10. rerun the complete campaign before promotion.

## Runner classes

### Hosted preflight lane

GitHub-hosted `ubuntu-26.04` is suitable for repository validation, metadata checks and non-authoritative package-build preflight. The label is explicit; `ubuntu-latest` is forbidden because it lets GitHub change the platform underneath the project.

As of 2026-09-11 GitHub documents Ubuntu 26.04 hosted runners as public preview. Hosted success is useful CI evidence but is not release-build certification.

The hosted package-build preflight creates a fresh Ubuntu 26.04 `buildd` rootfs with `mmdebstrap`, builds the proof package through `sbuild --chroot-mode=unshare`, and preserves `.deb`, `.changes`, `.buildinfo`, logs and hashes. It intentionally does **not** claim the authoritative system-test gate.

A real hosted attempt on 2026-09-11 demonstrated that `sbuild/unshare` can complete but `autopkgtest/unshare` can fail while constructing its testbed because of UID/GID ownership mapping. That backend is therefore not part of the authoritative testing contract.

### Authoritative KVM build/test lane

Release-relevant package evidence is produced inside disposable self-hosted **KVM virtual machines** running Ubuntu 26.04. The KVM guest, not the long-lived physical/virtualization host, is the GitHub Actions runner.

Required conceptual labels:

`self-hosted`, `linux`, `x64`, `supralinux`, `ubuntu-26.04`, `kvm`, `ephemeral`

The VM lifecycle is one job per disposable instance:

1. boot a clean VM from the approved Ubuntu 26.04 runner image;
2. register the GitHub Actions runner with ephemeral registration;
3. execute exactly one job;
4. export build/test evidence and runner logs;
5. allow GitHub to de-register the ephemeral runner;
6. destroy the VM and its writable disk state.

Inside the authoritative runner VM:

- package compilation uses a fresh `sbuild` environment;
- `sbuild` uses the `unshare` backend while that backend remains certified for the runner image;
- `.deb`, `.changes`, `.buildinfo` and hashes are captured immediately after a successful build, before later gates run;
- package/system testing uses `autopkgtest` with its QEMU backend and a prepared Ubuntu 26.04 image;
- nested KVM is required for the authoritative QEMU test gate so that system tests run with hardware virtualization rather than silently falling back to software emulation.

This gives separate isolation boundaries for the runner VM, the package build environment and the package runtime test VM.

Containers may be used for auxiliary services, but they must not replace either the authoritative KVM runner boundary or the QEMU system-test boundary when doing so changes semantics.

See `docs/runners/ubuntu-26.04.md`.

## Evidence contract

Important builds must retain, where applicable:

- source identifier and source archive;
- upstream version;
- upstream commit/tag;
- SHA-256 of downloaded source inputs;
- resolved build dependencies;
- build configuration and environment manifest;
- complete build/test logs;
- generated `.deb` packages;
- `.changes`;
- `.buildinfo`;
- package manifests;
- runner VM image revision and certification evidence;
- SHA-256 of the prepared `autopkgtest` QEMU base image used by the run;
- CI run identifiers and result state.

Hashes and test results are evidence, not placeholders. They must never be invented or copied from unrelated builds.

## Repository/promotion model

The intended package flow is:

`upstream stable -> SupraLINUX packaging -> authoritative clean build -> authoritative tests -> incoming/staging -> candidate -> stable`

Repository publication and signing are separate from compilation. Builders should not require the stable repository private signing key. Promotion to stable is a gated publisher operation after required evidence passes.

## Gates

The initial gates are:

- repository/manifest validation;
- source integrity;
- hosted clean-build preflight;
- authoritative Ubuntu 26.04 KVM runner certification;
- authoritative clean package build under `sbuild`;
- package metadata validation;
- `autopkgtest/QEMU` system/package tests;
- dependency DAG consistency;
- install/upgrade tests;
- KDE session/runtime smoke tests;
- Ubuntu application compatibility tests for replaced shared libraries;
- repository publication verification.

Additional gates can be added, but existing gates must not be removed silently; architecture documentation and machine-readable policy must change with the implementation.
