# SupraLINUX KSQ self-hosted runner

## Purpose

The KSQ self-hosted runner executes qualification jobs on project-controlled hardware while preserving a clean Ubuntu 26.04 LTS userspace for each job.

## Certified qualification baseline

Status: `PASS` as of 2026-08-31.

- Runner name: `espadarunica`
- Runner labels: `self-hosted`, `Linux`, `X64`, `supralinux-ksq`, `docker`
- Host OS at closure: Ubuntu 24.04.4 LTS (`noble`), `amd64`
- Host Docker Engine: `29.7.2`
- Docker experimental features: disabled (`false`)
- Actions Runner installed version: `2.336.0`
- Actions Runner global upstream latest at closure: `2.337.0`
- Runner update policy: GitHub progressive rollout; `2.336.0` was the repository-effective version at closure because a clean reconnect produced no automatic update.
- Job container: `ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`
- Expected container OS: Ubuntu 26.04 LTS (`resolute`)
- Expected architecture: `amd64`
- Jobs assigned to this runner must declare a job container.

Canonical final smoke evidence:

- Workflow: `.github/workflows/ksq-1-self-hosted-smoke.yml`
- Run: `33410973670`
- Attempt: `2`
- Job: `99552220167`
- Result: `PASS`
- All steps passed, including job-container initialization, pinned Resolute validation, container/workspace isolation, APT metadata/network access, PASS recording and container teardown.

## Host isolation

The runner must be started with:

```text
ACTIONS_RUNNER_REQUIRE_JOB_CONTAINER=true
```

This prevents a workflow from accidentally executing a KSQ job directly on the self-hosted machine.

The runner host is infrastructure only. Its installed packages, libraries and development tools are not part of the KSQ build environment. Build dependencies belong inside the pinned job container and/or the project-controlled KSQ preparation scripts.

The runner account has Docker socket access, which is host-equivalent control. The job container is therefore a reproducibility boundary, not a security sandbox against malicious repository code. Only trusted SupraLINUX workflows may target the `supralinux-ksq` runner labels.

## Qualification and regression rule

No existing KSQ certification is transferred to the self-hosted environment by assumption. The canonical smoke workflow must pass before heavy KSQ work is migrated to this runner.

The following changes invalidate this runner qualification and require the corresponding regression before the runner can be treated as certified again:

- pinned job-container digest;
- required runner labels or runner-group execution model;
- `ACTIONS_RUNNER_REQUIRE_JOB_CONTAINER` enforcement;
- relevant Docker Engine execution behavior or experimental-feature state;
- repository-effective Actions Runner version after GitHub rollout;
- build-environment preparation that changes what executes inside the pinned container.

GitHub Actions Runner releases use progressive rollout. A newer globally published stable runner is not forced manually merely because it exists upstream; the repository-effective version follows GitHub's supported rollout. Once GitHub offers a newer version to this repository, the runner must update and the smoke regression must be repeated before retaining `PASS`.
