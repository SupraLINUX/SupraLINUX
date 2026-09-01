# Aurora KSQ-1 GitHub-hosted builder qualification

Status: **ARCHITECTURE QUALIFIED — NOT KSQ-1 ACCEPTANCE**

This document records the qualification of the GitHub-hosted execution architecture selected for the remaining Aurora KSQ-1 work. It does not certify source node 001, a full candidate/reference build, reproducibility, technical acceptance, or KSQ-1 itself.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-1 remains **ACTIVE / NOT CERTIFIED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Accepted architecture

The selected build architecture is:

1. GitHub-hosted standard runner `ubuntu-24.04`;
2. load the narrow SupraLINUX AppArmor profile on that ephemeral VM;
3. launch the pinned Ubuntu 26.04 Resolute container manually through Docker;
4. normalize the certified Resolute `uidmap` helpers to the already-proven file-capability model;
5. run `mmdebstrap --mode=unshare` and `sbuild --chroot-mode=unshare` inside that container;
6. provide the certified Ubuntu snapshot slice as a verified local file tree mounted read-only into the container;
7. prohibit live Ubuntu archive and remote Snapshot Service fallback for certification builds.

Pinned container image:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

Certified Ubuntu snapshot:

`20260829T022000Z`

The GitHub-hosted VM is infrastructure only. Ubuntu 26.04 inside the pinned container remains the userspace build environment.

## Why `ubuntu-24.04` is used as the host label

As of 2026-09-01, GitHub documents `ubuntu-26.04` standard hosted runners as **Public preview**. Aurora's product policy does not put beta/preview infrastructure into its certification path when a stable alternative exists.

`ubuntu-24.04` is therefore the stable host label. This does not change Aurora's Ubuntu 26.04 base because the actual build userspace is the pinned Resolute OCI image.

## Why the container is launched manually

The AppArmor profile must be loaded on the ephemeral GitHub-hosted VM before Docker creates the KSQ container.

A GitHub Actions job-level `container:` is created before workflow steps execute, so it cannot depend on a profile loaded by a preceding step in the same job. The accepted architecture therefore runs the job on the host VM, loads:

`scripts/ci/apparmor/supralinux-ksq-unshare`

through:

`scripts/ci/install-ksq-apparmor-profile.sh`

and only then executes `docker run` with:

- `--security-opt seccomp=unconfined`;
- `--security-opt apparmor=supralinux-ksq-unshare`;
- no `--privileged`;
- no parent `CAP_SYS_ADMIN`;
- no global user-namespace weakening.

## Canonical architecture probe

Workflow:

`.github/workflows/ksq-github-hosted-builder-profile-probe.yml`

Final qualifying commit:

`6103bfda08a532ba54ac12e21361461cb856e54c`

Run:

`33466042319`

Job:

`99726002249`

Result:

**SUCCESS**

Evidence artifact:

- ID `9784900766`;
- digest `sha256:65546e6b93a08525bda0527eacf6953b92cede173374023d764605c62bf58354`.

## Observed GitHub-hosted host

The qualifying run observed:

- runner version `2.337.0`;
- Ubuntu `24.04.4 LTS` host;
- runner image `ubuntu-24.04`, image version `20260823.283.1`;
- kernel `6.17.0-1022-azure`;
- Docker Engine `28.0.4`;
- AppArmor enabled;
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
- `libcap2-bin 1:2.75-10ubuntu2`.

The previously proven disposable-builder uidmap normalization was applied:

```text
chmod u-s /usr/bin/newuidmap /usr/bin/newgidmap
setcap cap_setuid=ep /usr/bin/newuidmap
setcap cap_setgid=ep /usr/bin/newgidmap
```

The resulting helpers were verified as mode 0755 with:

- `newuidmap cap_setuid=ep`;
- `newgidmap cap_setgid=ep`.

The full user/mount/PID/UTS/IPC namespace preflight passed.

## Real mmdebstrap proof

The probe executed the real:

`mmdebstrap --mode=unshare --variant=buildd`

path and completed successfully.

As in the prior self-hosted qualification, the direct proc mount was denied and mmdebstrap used its implemented bind-mount fallback. The run completed successfully in approximately 32 seconds. This remains recorded as supported fallback behavior, not a direct-proc PASS.

## Real sbuild proof

The probe generated a real minimal Debian source package and built it through:

`sbuild --chroot-mode=unshare`

with the same major isolation flags used by the KSQ path, including `--no-enable-network`.

The build produced:

- `supralinux-hosted-smoke_1.0_all.deb`;
- a `.build` log;
- `supralinux-hosted-smoke_1.0_amd64.buildinfo`;
- `supralinux-hosted-smoke_1.0_amd64.changes`.

The workflow emitted:

`AURORA_KSQ_GITHUB_HOSTED_REAL_SBUILD_PASS`

Therefore GitHub-hosted Ubuntu 24.04 + the pinned Resolute container is proven capable of executing the actual Aurora unshare build machinery without privileged Docker, parent `CAP_SYS_ADMIN`, `apparmor=unconfined`, or global userns weakening.

## Diagnostic-only use of the live archive

The architecture probe intentionally used the current Resolute archive only to acquire the diagnostic toolchain and create a disposable buildd environment. This was acceptable because the run was testing host/container namespace architecture, not certifying KDE package content.

It is **not** source-build evidence and it does not authorize live archive use in KSQ-1 candidate/reference/reproducibility builds.

The certification path must instead consume the local certified snapshot slice for `20260829T022000Z`.

## Snapshot distribution decision

The durable canonical snapshot slice will not depend on `espadarunica`.

Target distribution is a dedicated GitHub Release asset containing the byte-preserved certified slice, for example a `tar.zst`, together with committed provenance and SHA-256 identity. GitHub currently permits individual Release assets below 2 GiB; the certified raw slice upper bound is only `0.9324 GiB`, so the slice fits within that limit even before compression.

Each hosted job must:

1. download the exact declared Release asset;
2. verify its repository-pinned SHA-256 before extraction;
3. extract it onto the job's ephemeral SSD;
4. validate its internal manifests/provenance;
5. mount it read-only into the pinned Resolute container;
6. use only `file:` APT sources for the certified snapshot;
7. fail if any HTTP/HTTPS Ubuntu archive or Snapshot Service fallback becomes reachable/required.

GitHub Actions cache may later be evaluated only as an acceleration layer. It must never become the identity or trust source for the slice.

## Effect on `espadarunica`

The self-hosted work remains valid historical root-cause and regression evidence, especially for:

- the `uidmap` cause;
- AppArmor mediation;
- the narrow profile design;
- exact `mmdebstrap` and `sbuild` contracts.

However, `espadarunica` is no longer technically required as the KSQ-1 execution host. Its runner service, local snapshot staging, and self-hosted-only diagnostic workflows become cleanup candidates **only after** the GitHub-hosted local-slice path has passed its canonical smoke and source-001 regression.

Do not remove that infrastructure before the replacement path is certified.

## Current gate state

- GitHub-hosted stable host architecture: **PASS**;
- narrow AppArmor profile load on hosted VM: **PASS**;
- pinned Resolute container: **PASS**;
- uidmap normalization: **PASS**;
- namespace preflight: **PASS**;
- real `mmdebstrap --mode=unshare`: **PASS**;
- real trivial `sbuild --chroot-mode=unshare`: **PASS**;
- certified snapshot Release asset: **NOT CREATED**;
- local-only APT gate from Release asset: **NOT RUN**;
- canonical snapshot-backed mmdebstrap regression: **NOT RUN**;
- canonical snapshot-backed sbuild smoke: **NOT RUN**;
- source DAG 001 on hosted local-slice path: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
