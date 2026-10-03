# SupraLINUX milestone execution checkpoints

Milestone images are an optimization for the active KDE/Plasma campaign. They prevent repeated reconstruction of already-closed dependencies while preserving artifacts and manifests as the canonical source of truth.

## Current checkpoint

`frameworks-6.30-pass` is **PASS** and is required before Plasma Level 0 package execution.

It is built from the admitted Ubuntu 26.04 authoritative golden image plus the 65 current Frameworks PASS GitHub artifacts. The builder caches downloaded artifact ZIPs on the host, extracts only binary `.deb` packages into a local pool, builds a `Packages` index and creates one reusable Resolute sbuild rootfs.

The sbuild rootfs deliberately does **not** have all Frameworks packages preinstalled. This matters: preinstalling development packages could make a package succeed despite a missing Build-Depends declaration. Future package runners must select required retained packages from the cached pool.

Default paths:

```text
golden:
  /var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2

Frameworks milestone:
  /var/lib/supralinux/images/milestones/frameworks-6.30-pass.qcow2

download cache:
  /var/lib/supralinux/milestone-cache/frameworks-6.30/downloads
```

Build:

```bash
SUPRALINUX_GITHUB_TOKEN=... ./scripts/build-frameworks-milestone-image.sh
```

Validate:

```bash
./scripts/check-frameworks-milestone-image.sh
```

The builder refuses to replace an existing admitted cache unless `SUPRALINUX_REPLACE_MILESTONE_IMAGE=1` is explicitly supplied.

## Plasma policy

After a complete topological level reaches PASS, its package artifacts are retained canonically and a new milestone image may be generated from the previous milestone plus the closed level's artifacts. A later level starts from that checkpoint.

No milestone is generated from FAIL, BLOCKED, diagnostic or INFRA_INVALID state. A checkpoint build failure never changes canonical package state and never consumes a package Attempt.

A full from-scratch campaign remains the final reproducibility test after the incremental campaign is closed.


## Frameworks 6.30 admitted checkpoint

Host-local build result: **PASS**.

- image: `/var/lib/supralinux/images/milestones/frameworks-6.30-pass.qcow2`
- SHA-256: `ec38f99e306d5a13333d6b247a9433b3526ec4a6d1a272631242c68df56c3e97`
- builder commit: `92defdaf79e573897e0e9836a9365aa3f2c7eb2d`
- retained Frameworks PASS artifacts: 65
- local APT index: 336 binary entries
- reusable Resolute sbuild rootfs: PASS
- `qemu-img check`: PASS
- package execution: not started
- package Attempts consumed: 0
- canonical package state effect: none

This closes only the execution-cache milestone. Plasma Level 0 remains behind its materialization/preflight gates and package execution remains locked.
