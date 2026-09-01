# Aurora KSQ-1 self-hosted runner namespace qualification

Status: **HISTORICAL / SUPERSEDED EXECUTION HOST — NOT KSQ-1 ACCEPTANCE**

This document preserves root-cause and diagnostic evidence obtained on the dedicated `espadarunica` self-hosted GitHub Actions runner. It no longer defines the active KSQ-1 execution architecture.

The selected architecture is documented in `docs/validation/AURORA_KSQ_1_GITHUB_HOSTED_RUNNER.md` and now uses GitHub-hosted `ubuntu-26.04`.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-1 remains **ACTIVE / NOT CERTIFIED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Historical environment

Observed `espadarunica` runner host during this investigation:

- Ubuntu 24.04.4 LTS;
- kernel `6.8.0-138-generic`;
- Docker Engine 29.7.2;
- cgroup v2/systemd;
- AppArmor enabled;
- runner registered as `actions.runner.SupraLINUX-SupraLINUX.espadarunica.service`.

Pinned job image used by the investigation:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

Certified Ubuntu snapshot identity under investigation:

`20260829T022000Z`

The host being Ubuntu 24.04 is the reason this environment is no longer selected as the canonical KSQ host now that GitHub-hosted Ubuntu 26.04 has passed the same architecture qualification.

## Invariant preserved from the investigation

The investigation established and retained the unprivileged build model:

- `mmdebstrap --mode=unshare`;
- `sbuild --chroot-mode=unshare`;
- no Docker `--privileged`;
- no parent-container `CAP_SYS_ADMIN` grant;
- no global disabling of Ubuntu's AppArmor unprivileged-user-namespace restriction.

Those invariants remain part of the active GitHub-hosted Ubuntu 26.04 path.

## Runner-session diagnostic

The runner had originally been launched manually. A transient broker/session failure produced `409 Conflict` / `job assignment is invalid: MissingKey` while jobs remained queued.

The existing registration was installed as the normal systemd service:

`actions.runner.SupraLINUX-SupraLINUX.espadarunica.service`

A fresh broker session was then created and subsequent diagnostic jobs were acquired normally. This was a runner-session issue, not a KDE or Ubuntu package issue.

## Root cause 1 — Ubuntu `uidmap` setuid privilege model

Baseline run `33417711530`, job `99572254357`, established that subordinate IDs existed and ordinary Docker/userns prerequisites were present, while stock subordinate-ID mapping still failed with `EPERM`.

Final root-cause run:

- run `33422301732`;
- job `99587377840`;
- engineering commit `2e8f77f1599e4b6ca3faa941d971769f7a029404`;
- artifact `aurora-ksq-self-hosted-uidmap-root-cause`;
- artifact ID `9769394431`;
- SHA-256 `9e0118b99fd6bbc7447611e24a957120eaa2251cd7c453c57418f9d33e69bd55`.

Pinned Resolute evidence showed:

- `uidmap 1:4.17.4-2ubuntu3`;
- stock helpers mode 4755 with no file capabilities;
- the packaged helper lacks the capability-aware upstream libcap path;
- Ubuntu's `shadow 1:4.17.4-2ubuntu3` Build-Depends omit `libcap-dev`.

Controlled A/B:

- parent-container root direct map write: FAIL (`EPERM`);
- stock setuid `newuidmap`: FAIL (`EPERM`);
- same Ubuntu helper with setuid removed and `cap_setuid=ep`: PASS;
- corresponding `newgidmap` with `cap_setgid=ep`: PASS;
- util-linux `unshare --map-auto ...`: PASS.

The run emitted `AURORA_KSQ_UIDMAP_ROOT_CAUSE_PROVEN` only after those assertions passed.

### Accepted disposable-builder normalization

```text
chmod u-s /usr/bin/newuidmap /usr/bin/newgidmap
setcap cap_setuid=ep /usr/bin/newuidmap
setcap cap_setgid=ep /usr/bin/newgidmap
```

This remains CI-environment normalization, not a SupraLINUX product-package change. Every current workflow using it must verify the resulting modes and capabilities.

Removal condition: remove only when the certified Ubuntu `uidmap` package provides the capability-aware upstream behavior or an equivalent correct privilege model, followed by regression.

## Root cause 2 — AppArmor mount mediation

After uidmap normalization, namespace creation progressed to a mount-propagation denial. Docker's default AppArmor policy was too restrictive for the required unshare mount contract.

The narrow project profile is maintained at:

`scripts/ci/apparmor/supralinux-ksq-unshare`

Host loader:

`scripts/ci/install-ksq-apparmor-profile.sh`

The profile remains enforcing and does not add parent-container `CAP_SYS_ADMIN`, privileged mode or a global host sysctl exception.

An `apparmor=unconfined` control run (`33417921991`, job `99572936219`) was also rejected as a solution because it exposed the process to Ubuntu's restricted-unprivileged-userns policy and did not provide the required behavior.

## Namespace and mmdebstrap evidence

With uidmap file capabilities and the scoped AppArmor profile, the complete user/mount/PID/UTS/IPC namespace preflight passed.

Canonical mmdebstrap qualification:

- run `33424405355`, attempt 2;
- job `99597668841`;
- artifact ID `9770652766`;
- SHA-256 `a6b95edd919ce652f5a4de0e4ebaacb6cffb23c884c1910a5b1ad28d9b759a6f`.

Observed versions included:

- `mmdebstrap 1.5.7-3`;
- `sbuild 0.91.2ubuntu3`;
- `uidmap 1:4.17.4-2ubuntu3`.

The run emitted:

- `AURORA_KSQ_MMDEBSTRAP_RC=0`;
- `AURORA_KSQ_1_BUILD_ENV_BACKEND=unshare`;
- `AURORA_KSQ_1_BUILD_ENV_SUCCESS`;
- `AURORA_KSQ_MMDEBSTRAP_UNSHARE_PASS`.

A direct proc mount was rejected and mmdebstrap used its implemented bind fallback. That behavior remains explicitly recorded rather than represented as a direct-proc-mount PASS.

## Exact sbuild contract evidence

Run `33427689971`, job `99605172945`, captured the installed Resolute implementation:

- `sbuild 0.91.2ubuntu3`;
- `libsbuild-perl 0.91.2ubuntu3`;
- `/usr/libexec/sbuild-usernsexec` SHA-256 `218821c4a8892c60847be58c80e4d1fb02702b17ac6f7dce412faadecd8afc0a`;
- `/usr/share/perl5/Sbuild/ChrootUnshare.pm` SHA-256 `480f2e51744483d9fc354653efe3b11a2e7eaceb6faa547c41eb445402d5bc5d`;
- artifact ID `9771406315`;
- artifact SHA-256 `f0c734d6e7005041c79d26a680d077ce3d32710624dcca3e22cffaa619060356`.

This evidence identified the actual mount contract used by `sbuild-usernsexec` and prevented broad, symptom-driven AppArmor grants.

## Historical sbuild smoke failure

Run `33431673769`, job `99618246774`, recorded an sbuild create-session denial at the temporary root's self-rbind operation:

```text
mount: /tmp/tmp.sbuild.glni_uEpvI: bind /tmp/tmp.sbuild.glni_uEpvI failed.
Fail-Stage: create-session
```

Artifact:

- ID `9772938403`;
- SHA-256 `ba762e48bc63d64de0d4b62e213262416a4809c34e61e9138df5f4a243cadc88`.

Profile commit `9c2f2411657c5ab8cc99f3de2f1f9756532ea4a7` added only the sbuild temporary-root mount contract. It did not grant arbitrary bind mounts, `pivot_root`, parent `CAP_SYS_ADMIN` or privileged mode.

This subsection preserves the historical failure and its root-cause evidence. It is **not a current sub-gate** and must not be read as the present architecture state.

## Superseding GitHub-hosted Ubuntu 26.04 proof

The active architecture has now passed the real equivalent path on a GitHub-hosted Ubuntu 26.04 VM:

- qualifying commit `067d6b160f0b8c0b2411a36beecc21cd7e8dc5da`;
- run `33467690494`;
- job `99730854792`;
- result **SUCCESS**;
- artifact ID `9785447790`;
- artifact SHA-256 `fbcaa74ec5810f4495396c1f0afe8eb3f1b1ab67ed34723ded0ffed12e293988`.

That run passed:

- Ubuntu 26.04 host identity;
- AppArmor profile load enforcing;
- namespace preflight;
- real `mmdebstrap --mode=unshare`;
- real `sbuild --chroot-mode=unshare` producing `.deb`, `.build`, `.buildinfo` and `.changes`.

The current execution-host qualification is therefore maintained in `AURORA_KSQ_1_GITHUB_HOSTED_RUNNER.md`.

## Current disposition

- self-hosted namespace/root-cause evidence: **RETAINED AS HISTORICAL EVIDENCE**;
- `espadarunica` as canonical KSQ host: **SUPERSEDED**;
- GitHub-hosted Ubuntu 26.04 architecture: **QUALIFIED**;
- self-hosted runner service/config: **temporary fallback/debug resource pending cleanup conditions**;
- source node 001 on the new hosted local-snapshot path: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.

No diagnostic run in this document may be represented as a source-build or KSQ-1 PASS.
