# Aurora KSQ-1 self-hosted runner namespace qualification

Status: **ACTIVE DIAGNOSTIC — NOT KSQ-1 ACCEPTANCE**

This document records qualification of the dedicated self-hosted GitHub Actions execution environment used for KSQ-1. Diagnostic success does not certify source node 001 or KSQ-1 itself.

## Scope and invariant

KSQ-1 retains the unprivileged build model:

- `mmdebstrap --mode=unshare`;
- `sbuild --chroot-mode=unshare`;
- no Docker `--privileged`;
- no parent-container `CAP_SYS_ADMIN` grant;
- no global disabling of Ubuntu's AppArmor unprivileged-user-namespace restriction.

Observed runner host during qualification:

- Ubuntu 24.04.4 LTS;
- kernel `6.8.0-138-generic`;
- Docker Engine 29.7.2;
- cgroup v2/systemd;
- AppArmor enabled;
- runner registration running as a systemd service for host user `chmodmasx`.

Pinned job image:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

Certified Ubuntu archive snapshot:

`20260829T022000Z`

## Runner service state

The runner had originally been launched manually. A transient broker/session failure produced `409 Conflict` / `job assignment is invalid: MissingKey` while jobs remained queued.

The existing registration was installed as the normal systemd service:

`actions.runner.SupraLINUX-SupraLINUX.espadarunica.service`

A fresh broker session was then created and subsequent diagnostic jobs were acquired normally. The runner remains on stable version 2.336.0 during this qualification so runner-version changes do not contaminate the namespace experiments.

## Baseline namespace diagnostic

Run `33417711530`, job `99572254357`, established:

- Docker daemon userns-remap is not active for the job container;
- Docker supplies `CAP_SETUID`, `CAP_SETGID` and `CAP_SETFCAP`;
- `NoNewPrivs=0`;
- seccomp is disabled for the diagnostic (`Seccomp=0`);
- stock `newuidmap` / `newgidmap` are root-owned mode 4755;
- `ubuntu:100000:65536` exists in `/etc/subuid` and `/etc/subgid`;
- the root filesystem is not `nosuid`;
- host `kernel.unprivileged_userns_clone=1`;
- host `user.max_user_namespaces=30059`;
- host `kernel.apparmor_restrict_unprivileged_userns=1`;
- `unshare --user --map-root-user true` succeeds;
- subordinate-ID mapping through stock `newuidmap` fails with `EPERM`.

This eliminated missing subordinate-ID delegation, missing setuid bits, `nosuid`, seccomp, Docker daemon userns-remap and the ordinary Docker capability set as explanations.

## AppArmor unconfined control

Run `33417921991`, job `99572936219`, changed only the container AppArmor selection to `apparmor=unconfined` while retaining `seccomp=unconfined`.

Even the simple `--map-root-user` control then failed. Therefore disabling AppArmor is not a solution on this Ubuntu 24.04 host; it exposes the process to Ubuntu's restricted-unprivileged-userns policy. `apparmor=unconfined` is rejected for KSQ.

## Proven root cause 1 — Ubuntu `uidmap` setuid privilege model

Final root-cause run: `33422301732`, job `99587377840`, engineering commit `2e8f77f1599e4b6ca3faa941d971769f7a029404`.

Artifact:

- name `aurora-ksq-self-hosted-uidmap-root-cause`;
- ID `9769394431`;
- SHA-256 `9e0118b99fd6bbc7447611e24a957120eaa2251cd7c453c57418f9d33e69bd55`.

Pinned Resolute evidence:

- `uidmap 1:4.17.4-2ubuntu3`;
- stock helpers are mode 4755 with no file capabilities;
- `newuidmap` has no `libcap.so` dependency and lacks the capability-aware symbols/diagnostic strings from shadow 4.17.4's conditional libcap path;
- Ubuntu's `shadow 1:4.17.4-2ubuntu3` Build-Depends omit `libcap-dev`.

Controlled A/B:

- parent-container root direct map write: FAIL (`EPERM`);
- stock setuid `newuidmap`: FAIL (`EPERM`);
- same Ubuntu helper with setuid removed and `cap_setuid=ep`: PASS;
- corresponding `newgidmap` with `cap_setgid=ep`: PASS;
- util-linux `unshare --map-auto ...`: PASS.

The run emitted `AURORA_KSQ_UIDMAP_ROOT_CAUSE_PROVEN` only after these assertions passed.

### Accepted disposable-builder normalization

For the disposable KSQ job container:

```text
chmod u-s /usr/bin/newuidmap /usr/bin/newgidmap
setcap cap_setuid=ep /usr/bin/newuidmap
setcap cap_setgid=ep /usr/bin/newgidmap
```

This is CI environment normalization, not a SupraLINUX product-package change. The workflow must verify the resulting modes and capabilities each run.

Removal condition: remove this normalization when the certified Ubuntu `uidmap` package provides the capability-aware upstream behavior or an equivalent correct privilege model, followed by namespace regression.

## Proven root cause 2 — AppArmor mount mediation

After uidmap normalization, the full user+mount+pid+uts+ipc namespace request progressed to:

`unshare: cannot change root filesystem propagation: Permission denied`

The relevant util-linux operation is the recursive private propagation change on `/`. Docker's `docker-default` profile denies mounts by default, so a dedicated KSQ profile is maintained at:

`scripts/ci/apparmor/supralinux-ksq-unshare`

Host loader:

`scripts/ci/install-ksq-apparmor-profile.sh`

The profile remains enforcing and does not add parent-container `CAP_SYS_ADMIN`, privileged mode or a global host sysctl exception.

## Full namespace preflight

With uidmap file capabilities and the scoped AppArmor profile, the exact namespace set required by mmdebstrap passed:

- subordinate UID/GID mapping: PASS;
- user namespace: PASS;
- mount namespace: PASS;
- PID namespace: PASS;
- UTS namespace: PASS;
- IPC namespace: PASS.

This gate is closed for the currently pinned toolchain/profile combination, subject to regression if either changes.

## Canonical mmdebstrap qualification

The first canonical mmdebstrap exercise exposed a real bind-mount denial at `/dev/full`. The installed `mmdebstrap 1.5.7-3` setup contract was then used to restrict permissions to its temporary root `/tmp/mmdebstrap.*/` for the canonical devices, devpts, `/sys` and `/proc` setup.

Run `33424405355`, attempt 2, job `99597668841`, then passed end-to-end:

- `mmdebstrap 1.5.7-3`;
- `sbuild 0.91.2ubuntu3` installed in the builder environment;
- `uidmap 1:4.17.4-2ubuntu3` normalized to file capabilities;
- AppArmor `supralinux-ksq-unshare (enforce)`;
- `AURORA_KSQ_MMDEBSTRAP_RC=0`;
- `AURORA_KSQ_1_BUILD_ENV_BACKEND=unshare`;
- `AURORA_KSQ_1_BUILD_ENV_SUCCESS`;
- `AURORA_KSQ_MMDEBSTRAP_UNSHARE_PASS`.

Artifact:

- ID `9770652766`;
- SHA-256 `a6b95edd919ce652f5a4de0e4ebaacb6cffb23c884c1910a5b1ad28d9b759a6f`.

A direct proc mount was rejected, after which mmdebstrap used its implemented rbind fallback and completed successfully. This is recorded as observed supported behavior, not silently treated as a direct-proc PASS.

## Exact sbuild unshare contract

Run `33427689971`, job `99605172945`, captured the exact installed Resolute implementation:

- `sbuild 0.91.2ubuntu3`;
- `libsbuild-perl 0.91.2ubuntu3`;
- `/usr/libexec/sbuild-usernsexec` SHA-256 `218821c4a8892c60847be58c80e4d1fb02702b17ac6f7dce412faadecd8afc0a`;
- `/usr/share/perl5/Sbuild/ChrootUnshare.pm` SHA-256 `480f2e51744483d9fc354653efe3b11a2e7eaceb6faa547c41eb445402d5bc5d`.

Artifact:

- ID `9771406315`;
- SHA-256 `f0c734d6e7005041c79d26a680d077ce3d32710624dcca3e22cffaa619060356`.

The installed helper's chroot-session path performs:

- `rbind` of the unpack root onto itself;
- canonical `/dev/{null,zero,full,random,urandom,tty,console}` bind mounts when present;
- a private devpts instance;
- tmpfs at `/dev/shm`;
- `rbind /sys`;
- tmpfs over `/sys/kernel`;
- proc mount;
- optional `pivot_root` only when `SBUILD_ENABLE_PIVOT_ROOT` is defined.

Resolute's documented default `UNSHARE_TMPDIR_TEMPLATE` is `/tmp/tmp.sbuild.XXXXXXXXXX`, and default `UNSHARE_BIND_MOUNTS` is empty.

## sbuild end-to-end smoke gate

A deliberately trivial source package is used to exercise the same `sbuild --chroot-mode=unshare` path and major flags as source 001 without consuming source node 001 itself.

Run `33431673769`, job `99618246774`, with the mmdebstrap-qualified profile failed at create-session. Evidence showed:

```text
I: Unpacking ... to /tmp/tmp.sbuild.glni_uEpvI...
mount: /tmp/tmp.sbuild.glni_uEpvI: bind /tmp/tmp.sbuild.glni_uEpvI failed.
mount failed ... at /usr/libexec/sbuild-usernsexec line 374.
Fail-Stage: create-session
```

This is the exact first sbuild-specific denied operation: helper line 374 is `mount -o rbind $rootdir $rootdir`.

The smoke run also proved `SBUILD_ENABLE_PIVOT_ROOT=<unset>`, therefore the KSQ profile must not grant `pivot_root` for this path.

Artifact:

- ID `9772938403`;
- SHA-256 `ba762e48bc63d64de0d4b62e213262416a4809c34e61e9138df5f4a243cadc88`.

Profile commit `9c2f2411657c5ab8cc99f3de2f1f9756532ea4a7` adds only the sbuild temporary-root mount contract described above. It does not grant arbitrary `UNSHARE_BIND_MOUNTS`, `pivot_root`, parent-container `CAP_SYS_ADMIN` or privileged mode.

**Current sub-gate:** reload that profile on the runner host and rerun the same smoke workflow. Source 001 remains blocked until this smoke produces `.deb`, `.buildinfo` and `.changes` with exit code 0.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- namespace preflight: **PASS**;
- canonical mmdebstrap unshare: **PASS**;
- sbuild unshare smoke: **BLOCKED pending profile reload/regression**;
- source node 001: **not rerun yet**;
- builds 001–020: **not started from this diagnostic work**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.

No diagnostic run may be represented as a source-build or KSQ-1 PASS.
