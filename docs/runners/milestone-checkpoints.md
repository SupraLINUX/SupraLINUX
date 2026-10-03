# SupraLINUX milestone execution checkpoints

Milestone images are an optimization for the active KDE/Plasma campaign. They prevent repeated reconstruction of already-closed dependencies while preserving artifacts and manifests as the canonical source of truth.

## Current checkpoint

`frameworks-6.30-pass` is required before Plasma Level 0 package execution.

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
