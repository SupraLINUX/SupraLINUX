# SupraLINUX KSQ self-hosted runner

## Purpose

The KSQ self-hosted runner executes qualification jobs on project-controlled hardware while preserving a clean Ubuntu 26.04 LTS userspace for each job.

## Certified smoke-test baseline

- Runner labels: `self-hosted`, `Linux`, `X64`, `supralinux-ksq`, `docker`
- Job container: `ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`
- Expected container OS: Ubuntu 26.04 LTS (`resolute`)
- Expected architecture: `amd64`
- Jobs assigned to this runner must declare a job container.

## Host isolation

The runner must be started with:

```text
ACTIONS_RUNNER_REQUIRE_JOB_CONTAINER=true
```

This prevents a workflow from accidentally executing a KSQ job directly on the self-hosted machine.

The runner host is infrastructure only. Its installed packages, libraries and development tools are not part of the KSQ build environment. Build dependencies belong inside the pinned job container and/or the project-controlled KSQ preparation scripts.

## Qualification rule

No existing KSQ certification is transferred to the self-hosted environment by assumption. Before migrating heavy KSQ jobs, `.github/workflows/ksq-1-self-hosted-smoke.yml` must pass on the target runner. Any later change to the pinned container digest or relevant runner execution model requires the corresponding regression.
