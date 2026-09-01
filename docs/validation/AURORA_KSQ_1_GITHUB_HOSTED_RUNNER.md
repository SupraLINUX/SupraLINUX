# Aurora KSQ-1 GitHub-hosted builder qualification

Status: **ARCHITECTURE QUALIFIED — NOT KSQ-1 ACCEPTANCE**

This document records qualification of the GitHub-hosted Ubuntu 26.04 execution architecture selected for the remaining Aurora KSQ-1 work. It does not certify source node 001, a complete KDE candidate/reference build, reproducibility, technical acceptance, or KSQ-1 itself.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-1 remains **ACTIVE / NOT CERTIFIED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Accepted architecture

The selected build architecture is:

1. GitHub-hosted standard x64 runner `ubuntu-26.04`;
2. load the narrow SupraLINUX AppArmor profile on that ephemeral Ubuntu 26.04 VM;
3. launch the pinned Ubuntu 26.04 Resolute container manually through Docker;
4. normalize the certified Resolute `uidmap` helpers to the already-proven file-capability model;
5. run `mmdebstrap --mode=unshare` and `sbuild --chroot-mode=unshare` inside that container;
6. provide the certified Ubuntu snapshot slice as a verified local file tree mounted read-only into the container;
7. prohibit live Ubuntu archive and remote Snapshot Service fallback for certification builds.

Pinned build container:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

Certified Ubuntu snapshot:

`20260829T022000Z`

The GitHub-hosted VM and the disposable build userspace are therefore both Ubuntu 26.04. The host kernel/security environment remains a separately observed CI dependency, while the container fixes the builder userspace by digest.

## Public-preview policy

As of 2026-09-01 GitHub still labels `ubuntu-26.04` as **Public preview**. That label applies to GitHub's hosted runner image/service, not to Ubuntu 26.04 LTS itself.

SupraLINUX does not treat the preview label as an automatic acceptance or rejection. Instead, the exact infrastructure behavior required by KSQ is qualified empirically and must be regressed whenever a runner-image/toolchain change can invalidate previous evidence.

This document is that qualification record for the observed image below.

## Why the container is launched manually

The AppArmor profile must be loaded on the ephemeral GitHub-hosted VM before Docker creates the KSQ container.

A GitHub Actions job-level `container:` is created before workflow steps execute, so it cannot depend on a profile loaded by a preceding step in the same job. The accepted architecture therefore runs the workflow directly on `ubuntu-26.04`, loads:

`scripts/ci/apparmor/supralinux-ksq-unshare`

through:

`scripts/ci/install-ksq-apparmor-profile.sh`

and only then executes `docker run` with:

- `--security-opt seccomp=unconfined`;
- `--security-opt apparmor=supralinux-ksq-unshare`;
- no `--privileged`;
- no parent `CAP_SYS_ADMIN`;
- no global user-namespace weakening.

## Canonical Ubuntu 26.04 architecture probe

Workflow:

`.github/workflows/ksq-github-hosted-builder-profile-probe.yml`

Qualifying commit:

`067d6b160f0b8c0b2411a36beecc21cd7e8dc5da`

Run:

`33467690494`

Job:

`99730854792`

Result:

**SUCCESS**

Evidence artifact:

- name `aurora-ksq-github-hosted-2604-builder-profile-probe`;
- ID `9785447790`;
- size `12150` bytes;
- digest `sha256:fbcaa74ec5810f4495396c1f0afe8eb3f1b1ab67ed34723ded0ffed12e293988`.

The workflow emitted:

`AURORA_KSQ_GITHUB_HOSTED_2604_REAL_SBUILD_PASS`

## Observed GitHub-hosted Ubuntu 26.04 host

The qualifying run observed:

- runner version `2.337.0`;
- host `Ubuntu 26.04 LTS (Resolute Raccoon)`;
- runner image `ubuntu-26.04`;
- runner image version `20260824.116.1`;
- kernel `7.0.0-1012-azure`;
- Docker Engine `29.4.2`;
- Docker experimental mode `false`;
- AppArmor module loaded;
- `kernel.apparmor_restrict_unprivileged_userns=1`.

The narrow profile loaded successfully and remained enforcing:

`AURORA_KSQ_APPARMOR_PROFILE_STATUS=LOADED_ENFORCE`

Inside the pinned Resolute container, `/proc/self/attr/current` reported:

`supralinux-ksq-unshare (enforce)`

## Proven Resolute toolchain in the qualifying container

The successful probe used:

- `sbuild 0.91.2ubuntu3`;
- `libsbuild-perl 0.91.2ubuntu3`;
- `mmdebstrap 1.5.7-3`;
- `uidmap 1:4.17.4-2ubuntu3`;
- `libcap2-bin 1:2.75-10ubuntu2`;
- `util-linux 2.41.3-3ubuntu2`.

The previously proven disposable-builder uidmap normalization was applied:

```text
chmod u-s /usr/bin/newuidmap /usr/bin/newgidmap
setcap cap_setuid=ep /usr/bin/newuidmap
setcap cap_setgid=ep /usr/bin/newgidmap
```

The resulting helpers were verified as mode 0755 with:

- `newuidmap cap_setuid=ep`;
- `newgidmap cap_setgid=ep`;
- subordinate range `ubuntu:100000:65536` for both UID and GID.

The full user/mount/PID/UTS/IPC namespace preflight passed.

## Real mmdebstrap proof

The probe executed:

`mmdebstrap --mode=unshare --variant=buildd --architectures=amd64`

and completed successfully in approximately 25.2 seconds.

The direct proc mount was denied and mmdebstrap used its implemented bind-mount fallback:

```text
mount: .../proc: permission denied
W: since mounting /proc normally failed, /proc is now bind-mounted instead
```

The overall mmdebstrap operation then completed with `I: success`. This remains recorded as supported fallback behavior, not as a direct-proc-mount PASS.

## Real sbuild proof

The probe generated a real minimal Debian source package and built it through:

`sbuild --chroot-mode=unshare`

with the same major isolation flags used by the KSQ path, including `--no-enable-network`.

The build produced:

- `supralinux-hosted-smoke_1.0_all.deb`;
- `supralinux-hosted-smoke_1.0_amd64-2026-09-01T03:51:50Z.build`;
- `supralinux-hosted-smoke_1.0_amd64.buildinfo`;
- `supralinux-hosted-smoke_1.0_amd64.changes`.

Therefore the observed GitHub-hosted Ubuntu 26.04 image + pinned Resolute container is proven capable of executing Aurora's actual unshare build machinery without privileged Docker, parent `CAP_SYS_ADMIN`, `apparmor=unconfined`, or global userns weakening.

## Diagnostic-only use of the live archive

The architecture probe intentionally used the current Resolute archive only to acquire the diagnostic toolchain and create a disposable buildd environment. This was acceptable because the run tested host/container namespace architecture, not KDE package identity.

It is **not** source-build evidence and does not authorize live archive use in KSQ-1 candidate/reference/reproducibility builds.

The certification path must consume the local certified snapshot slice for `20260829T022000Z`.

## Superseded Ubuntu 24.04 hosted probe

Run `33466042319` remains valid historical evidence that the same machinery also worked on GitHub-hosted Ubuntu 24.04. It is no longer the selected execution architecture because the project requires the canonical host itself to match Aurora's Ubuntu 26.04 platform generation where host kernel/security semantics participate in the test.

Its evidence must not be represented as the current canonical host qualification.

## Snapshot distribution decision

The durable canonical snapshot slice will not depend on `espadarunica`.

Target distribution is a dedicated GitHub Release asset containing the byte-preserved certified slice, together with committed provenance, exact byte size and SHA-256 identity. GitHub permits individual Release assets below 2 GiB; the certified raw slice upper bound is `0.9324 GiB`, so the slice fits without splitting even before compression.

Each hosted job must:

1. download the exact declared Release asset;
2. verify its repository-pinned SHA-256 before extraction;
3. extract it onto the job's ephemeral SSD;
4. validate its internal manifests/provenance;
5. mount it read-only into the pinned Resolute container;
6. use only `file:` APT sources for the certified snapshot;
7. fail if any HTTP/HTTPS Ubuntu archive or Snapshot Service fallback becomes reachable or required.

GitHub Actions cache may be used only as a verified acceleration/staging mechanism. It must never become the canonical identity or trust source for the slice.

## Effect on `espadarunica`

The self-hosted work remains valid historical root-cause and regression evidence, especially for:

- the `uidmap` cause;
- AppArmor mediation;
- the narrow profile design;
- exact `mmdebstrap` and `sbuild` contracts.

However, `espadarunica` is not the selected KSQ-1 execution host. Its runner service, local snapshot staging and self-hosted-only diagnostics remain only as temporary fallback/debug infrastructure until the Ubuntu 26.04 hosted local-slice path passes its canonical smoke and source-001 regression.

## Current gate state

- GitHub-hosted Ubuntu 26.04 host identity: **PASS**;
- narrow AppArmor profile load on hosted VM: **PASS**;
- pinned Resolute container: **PASS**;
- uidmap normalization: **PASS**;
- namespace preflight: **PASS**;
- real `mmdebstrap --mode=unshare`: **PASS**;
- real trivial `sbuild --chroot-mode=unshare`: **PASS**;
- GitHub-hosted Ubuntu 26.04 execution architecture: **QUALIFIED**;
- certified snapshot Release asset: **NOT CREATED**;
- local-only APT gate from Release asset: **NOT RUN**;
- canonical snapshot-backed mmdebstrap regression: **NOT RUN**;
- canonical snapshot-backed sbuild smoke: **NOT RUN**;
- source DAG 001 on hosted local-slice path: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
