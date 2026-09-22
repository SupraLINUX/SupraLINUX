# KDE Frameworks Tier 3 package contracts

Status: **reference capture PASS — packaging-tree review pending**

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


## Reference capture PASS

Run `35726410174`, job `106741028368`, artifact `10693663804`, artifact SHA-256 `5e8f5989fe636e771b703814ab653ef60034396f5c5256a8af1dd8d37003a82b`: **PASS**.

Normalized snapshot SHA-256: `6ca804f733769e2b770beb65226e0183d17b80eb38abf1e116ac9b6290391bb6`.

Versions table SHA-256: `e405c341cb5fdd81a8952965e97ac7d8fd82c267260346d081df167a2bfbcbaa`.

Results:
- all 20 Ubuntu Resolute references remain KDE upstream 6.24.0;
- all 20 Debian sid references are exactly `6.30.0-1`;
- the Debian 6.30 orig tar SHA-256 matches the KDE-authority source SHA-256 for every node;
- Ubuntu and Debian expose the same binary-package identity set for every one of the 20 Frameworks.

The matching binary names reduce compatibility churn, but do not finalize the SupraLINUX contracts. The next gate extracts the exact pinned Ubuntu and Debian `debian/` trees so relations, symbols, install files, rules, maintscripts and build profiles can be reviewed before package revisions are authorized.

This phase changes no package state. Tier 3 remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.
