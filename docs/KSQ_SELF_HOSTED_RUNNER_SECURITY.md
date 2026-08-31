# KSQ self-hosted runner security notes

The repository-level self-hosted runner executes only trusted SupraLINUX workflows. Pull-request jobs from untrusted forks must not be routed to the `supralinux-ksq` label set.

The Docker socket is available to the runner host account and therefore grants host-equivalent control. The isolation boundary for KSQ reproducibility is the pinned job container, not a security sandbox against malicious repository code.

For that reason:

- KSQ jobs assigned to the self-hosted runner must require a job container.
- The pinned Ubuntu container digest is part of qualification provenance.
- No repository secrets are required for the build jobs unless explicitly introduced and reviewed later.
- Changes to runner labels, container digest, Docker execution model, or build-environment preparation trigger runner qualification regression.
