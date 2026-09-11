# Build, CI and promotion architecture

Status: **active architecture**  
Last reviewed: **2026-09-11**

## Principles

SupraLINUX uses a DAG-guided hybrid build strategy. The purpose is to discover independent failures early without converting downstream dependency fallout into false failures.

Each build node has exactly one of these terminal states:

- `PASS`: the node was actually built successfully and its artifacts may feed dependents;
- `FAIL`: the node was actually attempted and failed for its own build/test reason;
- `BLOCKED`: the node was not attempted because at least one required dependency is `FAIL` or unavailable.

`BLOCKED` must never be counted as `FAIL`.

## Execution strategy

For each campaign:

1. resolve the selected source/version manifest;
2. construct the dependency DAG;
3. identify topological levels;
4. attempt every buildable node in a level, parallelizing independent nodes;
5. continue independent branches after failures;
6. expose only `PASS` artifacts to dependent levels;
7. mark impossible downstream nodes `BLOCKED`;
8. preserve logs and metadata for every attempted node;
9. fix root causes incrementally;
10. rerun the complete campaign before promotion.

## Runner classes

### Hosted policy lane

GitHub-hosted `ubuntu-26.04` is suitable for repository validation, metadata checks and lightweight reproducible probes. The label is explicit; `ubuntu-latest` is forbidden because it lets GitHub change the platform underneath the project.

As of 2026-09-11 GitHub documents Ubuntu 26.04 hosted runners as public preview. Therefore hosted-runner success is useful CI evidence but is not, by itself, release-build certification.

### Authoritative build lane

Release-relevant package builds are designed for disposable self-hosted VMs with labels similar to:

`self-hosted`, `linux`, `x64`, `supralinux`, `ubuntu-26.04`, `ephemeral`

The VM lifecycle is one job per disposable instance. Build state is not reused between jobs. The runner registration must be ephemeral and the VM must be destroyed after the job.

The build environment should use clean `sbuild` environments based on Ubuntu 26.04. Containers may be used for auxiliary services, but they must not silently replace the authoritative package build environment when doing so changes package-build semantics.

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
- CI run identifiers and result state.

Hashes and test results are evidence, not placeholders. They must never be invented or copied from unrelated builds.

## Repository/promotion model

The intended package flow is:

`upstream stable -> SupraLINUX packaging -> clean build -> tests -> incoming/staging -> candidate -> stable`

Repository publication and signing are separate from compilation. Builders should not require the stable repository private signing key. Promotion to stable is a gated publisher operation after required evidence passes.

## Gates

The initial gates are:

- repository/manifest validation;
- source integrity;
- clean package build;
- package metadata validation;
- package-level tests;
- dependency DAG consistency;
- install/upgrade tests;
- KDE session/runtime smoke tests;
- Ubuntu application compatibility tests for replaced shared libraries;
- repository publication verification.

Additional gates can be added, but existing gates must not be removed silently; the architecture documentation and manifest policy must change with the implementation.
