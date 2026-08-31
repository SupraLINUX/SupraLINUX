# Aurora KSQ-1 self-hosted runner namespace qualification

Status: **ACTIVE DIAGNOSTIC — NOT KSQ-1 ACCEPTANCE**

This document records the qualification of the dedicated self-hosted GitHub Actions execution environment used for KSQ-1. None of the runs below certifies source node 001 or KSQ-1 itself.

## Scope and invariant

KSQ-1 intends to retain the upstream-supported unprivileged build model:

- `mmdebstrap --mode=unshare`;
- `sbuild --chroot-mode=unshare`;
- no Docker `--privileged`;
- no parent-container `CAP_SYS_ADMIN` grant;
- no global disabling of Ubuntu's AppArmor unprivileged-user-namespace restriction.

The runner host observed during qualification is Ubuntu 24.04.4 LTS with kernel `6.8.0-138-generic`, Docker Engine 29.7.2, cgroup v2/systemd and AppArmor enabled. The job image remains the pinned Ubuntu 26.04 image:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

The certified Ubuntu archive snapshot remains `20260829T022000Z`.

## Runner service state

The runner had originally been launched manually. A transient broker/session failure then produced `409 Conflict` / `job assignment is invalid: MissingKey` while jobs remained queued.

The existing runner registration was installed as the normal systemd service for host user `chmodmasx` using the runner's `svc.sh`. The service is now enabled and active as:

`actions.runner.SupraLINUX-SupraLINUX.espadarunica.service`

A fresh broker session was created successfully and subsequent diagnostic jobs were acquired normally. The runner remains on stable version 2.336.0 during this qualification so runner-version changes do not contaminate the namespace experiments.

## Baseline namespace diagnostic

Run `33417711530`, job `99572254357`, established:

- Docker job container is not under Docker daemon `userns-remap`; parent UID/GID maps cover the initial namespace (`0 0 4294967295`);
- Docker default capabilities include `CAP_SETUID`, `CAP_SETGID` and `CAP_SETFCAP`;
- `NoNewPrivs=0`;
- seccomp is disabled for this diagnostic (`Seccomp=0`);
- `/usr/bin/newuidmap` and `/usr/bin/newgidmap` are root-owned mode 4755;
- `ubuntu:100000:65536` is present in both `/etc/subuid` and `/etc/subgid`;
- the container root filesystem is not mounted `nosuid`;
- host `kernel.unprivileged_userns_clone=1`;
- host `user.max_user_namespaces=30059`;
- host `kernel.apparmor_restrict_unprivileged_userns=1`;
- `unshare --user --map-root-user true` succeeds;
- the documented subordinate-ID mapping path fails at `newuidmap` with `EPERM`.

This ruled out missing subordinate-ID delegation, missing setuid bits, `nosuid`, seccomp, Docker daemon userns-remap and the ordinary Docker capability set as explanations for the first failure.

## AppArmor unconfined control

Run `33417921991`, job `99572936219`, changed only the container AppArmor selection to `apparmor=unconfined` while retaining `seccomp=unconfined`.

Result:

- even the simple `--map-root-user` control failed;
- subordinate-ID mapping still failed.

Therefore disabling the container AppArmor profile is not a solution on this Ubuntu 24.04 host. It exposes the process to Ubuntu's restricted-unprivileged-userns policy instead of providing the scoped confinement required by the host policy. `apparmor=unconfined` is rejected for KSQ.

## Proven root cause 1 — Ubuntu `uidmap` setuid privilege model

Final root-cause run: `33422301732`, job `99587377840`, engineering commit `2e8f77f1599e4b6ca3faa941d971769f7a029404`.

Artifact:

- name: `aurora-ksq-self-hosted-uidmap-root-cause`;
- artifact ID: `9769394431`;
- artifact SHA-256: `9e0118b99fd6bbc7447611e24a957120eaa2251cd7c453c57418f9d33e69bd55`.

Exact package evidence inside the pinned Resolute environment:

- `uidmap 1:4.17.4-2ubuntu3`;
- stock `newuidmap` / `newgidmap`: root-owned mode 4755;
- no file capabilities on the stock helpers;
- `newuidmap` has no `libcap.so` dynamic dependency;
- the binary does not contain the `capset`, `prctl` or `seteuid` symbols/diagnostic strings corresponding to shadow 4.17.4's conditional libcap path.

Ubuntu's `shadow 1:4.17.4-2ubuntu3` source Build-Depends omit `libcap-dev`. Upstream shadow 4.17.4 wraps the capability-aware setuid handling in `#if __has_include(<sys/capability.h>)`. In a build without that header, the helper remains setuid-root but does not execute upstream's `PR_SET_KEEPCAPS` + return-to-real-euid path before writing the map.

This matters because the user namespace is created by effective UID 1000. Linux grants the namespace-owner relationship to UID 1000. The kernel's mapping write path also checks the credentials that opened `uid_map` for `CAP_SYS_ADMIN` over the target user namespace. The stock setuid helper remains effective UID 0 inside the Docker parent namespace, where Docker intentionally does not grant `CAP_SYS_ADMIN`; effective UID 0 is not the target namespace owner UID 1000. The write is rejected with `EPERM`.

The controlled A/B result is conclusive:

- direct write by parent-container root: `RC=1`, `Operation not permitted`;
- stock setuid `newuidmap`: `RC=1`, `Operation not permitted`;
- same installed helper after removing setuid and assigning `cap_setuid=ep`: `RC=0`;
- corresponding `newgidmap` receives only `cap_setgid=ep`;
- util-linux `unshare --map-auto ...`: `RC=0` with the file-capability helpers.

The run emitted `AURORA_KSQ_UIDMAP_ROOT_CAUSE_PROVEN` only after those assertions passed.

### Accepted CI normalization for further qualification

For the disposable KSQ build container, further experiments may normalize the Ubuntu-provided helpers after package installation:

```text
chmod u-s /usr/bin/newuidmap /usr/bin/newgidmap
setcap cap_setuid=ep /usr/bin/newuidmap
setcap cap_setgid=ep /usr/bin/newgidmap
```

This is not a product-package change. It is a scoped builder-environment privilege normalization using the same Ubuntu binaries and the privilege model explicitly supported by shadow upstream. The workflow must verify the resulting modes/capabilities before relying on them.

Removal condition: delete this normalization once the Ubuntu `uidmap` package used by the certified builder contains the capability-aware upstream path or ships an equivalent correct file-capability model, after rerunning the namespace regression.

## Exposed root cause 2 — mount propagation mediation

After root cause 1 is normalized, the complete namespace request advances past UID/GID mapping and fails at:

`unshare: cannot change root filesystem propagation: Permission denied`

util-linux documents that `unshare --mount` recursively changes propagation in the new mount namespace to private by default, equivalent to:

`mount --make-rprivate /`

Docker's generated `docker-default` AppArmor profile contains an unconditional `deny mount,` rule. This aligns exactly with the new failure point.

A scoped test profile is maintained at:

`scripts/ci/apparmor/supralinux-ksq-unshare`

It is derived from Docker's current default profile and changes only the mount policy needed for the next controlled experiment: the blanket mount deny is replaced by:

`mount options=(rw,make-rprivate) -> /,`

All other unlisted mount operations remain denied by AppArmor default-deny behavior. The profile does not add parent-container `CAP_SYS_ADMIN`, privileged mode, or a global host sysctl exception.

Host loader:

`scripts/ci/install-ksq-apparmor-profile.sh`

The profile is not considered accepted merely because it parses. The next controlled workflow must prove that:

1. the container is actually confined by `supralinux-ksq-unshare`;
2. stock `docker-default` + filecap normalization fails at propagation;
3. `supralinux-ksq-unshare` + the same normalization passes the exact full namespace preflight;
4. no broader Docker capability or host-policy change was introduced.

Only after that A/B passes may `prepare-ksq-1-runner.sh` / `mmdebstrap --mode=unshare` be exercised to discover any additional mount operations. Any additional AppArmor rule must be justified by a concrete denied operation and independently regression-tested.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- source node 001: **not rerun yet**;
- builds 001–020: **not started from this diagnostic work**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.

Diagnostic workflow success must never be represented as a source-build or KSQ-1 PASS.
