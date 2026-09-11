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

GitHub's top-level `pull_request.paths` filter compares the PR against its base, so in a long-lived PR it remains true after a relevant file was changed once. SupraLINUX therefore does not use that filter as the expensive-build suppression mechanism. On `pull_request/synchronize`, the hosted workflow compares the webhook's `before` and `after` SHAs and runs the expensive package build only when that event delta touches the proof package, its build script, the delta detector, or the workflow itself. `opened`/`reopened` conservatively compare the PR base and head; manual dispatch always runs. The small scope-check job may still run for documentation/infrastructure changes, but the expensive `sbuild` work is intentionally skipped.

The `pull_request/synchronize` payload's `before`/`after` SHAs are part of GitHub's current webhook schema. `scripts/package-preflight-needed.sh` owns the repository path policy so the workflow does not duplicate it.

### Authoritative KVM build/test lane

Release-relevant package evidence is produced inside disposable self-hosted **KVM virtual machines** running Ubuntu 26.04. The KVM guest, not the long-lived physical/virtualization host, is the GitHub Actions runner.

Required labels are:

`self-hosted`, `linux`, `x64`, `supralinux`, `ubuntu-26.04`, `kvm`, `ephemeral`

The authoritative runner uses GitHub's just-in-time runner configuration. The host requests a fresh `encoded_jit_config` for each guest and starts the already-installed runner with `run.sh --jitconfig`. No persistent GitHub runner credential is stored in the golden image.

The VM lifecycle is one job per disposable instance:

1. create a writable qcow2 overlay from the sealed Ubuntu 26.04 golden image;
2. boot a KVM VM with nested virtualization exposed;
3. request and inject a fresh JIT runner configuration into guest tmpfs;
4. wait until the JIT runner is online;
5. trigger exactly one controlled authoritative PR gate;
6. execute exactly one job;
7. upload build/test evidence and export runner diagnostics;
8. remove any transient trigger label/stale runner record;
9. destroy the VM and writable disk state.

Pre-merge authoritative gates use `pull_request` `labeled` events because `workflow_dispatch` is not used as a dependency for workflows that have not yet reached the default branch. The controlled labels are `ci:runner-contract` and `ci:authoritative-package-proof`. Both the workflows and host orchestrator reject fork PRs before any self-hosted code execution.

Inside the authoritative runner VM:

- package compilation uses a fresh `sbuild` environment;
- `sbuild` uses the `unshare` backend while that backend remains certified for the runner image;
- `.deb`, `.changes`, `.buildinfo` and hashes are captured immediately after a successful build, before later gates run;
- package/system testing uses `autopkgtest` with its QEMU backend and a prepared Ubuntu 26.04 image;
- nested KVM is required for the authoritative QEMU test gate so system tests do not silently fall back to software emulation.

This gives separate isolation boundaries for the host, runner VM, package build environment and package runtime test VM.

Containers may be used for auxiliary services, but they must not replace either the authoritative KVM runner boundary or the QEMU system-test boundary when doing so changes semantics.

See `docs/runners/ubuntu-26.04.md`, `docs/runners/provisioning.md` and `docs/runners/host-kvm.md`.

## Golden runner image supply chain

The runner image begins from Ubuntu's released Resolute amd64 cloud image. Its `SHA256SUMS.gpg` signature and the selected image checksum must be verified before the source image is admitted.

Guest preparation records installed tool versions. The GitHub Actions runner archive is accepted only after checking the SHA-256 digest published in GitHub release metadata. The nested `autopkgtest` QEMU image receives its own generated SHA-256/provenance. The golden image is then cleaned of runner registration/job state and clone identity before use as a read-only backing image.

A prepared image is not authoritative merely because these steps were scripted. Certification still requires execution on real KVM infrastructure.

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
- source/golden runner VM image revision and certification evidence;
- verified GitHub Actions runner release/digest;
- SHA-256 of the prepared `autopkgtest` QEMU base image used by the run;
- PR head SHA and CI run identifiers;
- host-side runner/VM diagnostics where applicable;
- terminal gate state.

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
