# KDE Frameworks Tier 3 package contracts

Status: **reference capture pending**

Reviewed: **2026-09-22**

## Scope

All 20 canonical KDE Frameworks Tier 3 nodes require SupraLINUX as provider because Ubuntu Resolute exposes KDE Frameworks 6.24.0 while KDE stable authority requires 6.30.0.

Package contracts are not inferred from Ubuntu package names alone. Before choosing SupraLINUX package versions, binary-package identities, transitions, symbols or provider adaptations, this gate captures technical references from:

- Ubuntu Resolute source metadata — compatibility reference only;
- Debian sid source metadata — packaging reference only.

Neither distribution becomes authority over KDE.

## Reference selection

For each `kf6-<framework>` source package, the capture records source version, upstream version, binary package set, Build-Depends, VCS metadata and signed SHA-256 source-file records.

Debian selection prefers an exact upstream 6.30.0 source record; if unavailable, it records the newest source not newer than KDE 6.30.0 so the absence of an exact technical reference is explicit rather than silently selecting a future KDE version.

The capture cross-checks the Ubuntu source version against the promoted provider audit.

## State semantics

This phase has `package_state_effect=none`.

All 20 Frameworks remain **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**. No package build is authorized until package contracts are reviewed from the captured evidence.

Stable publication remains subject to explicit user approval.
