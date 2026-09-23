# KDE Frameworks Tier 3 package contracts

Status: **contracts retained — round 3 promoted; attempt 4 active**

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


## Packaging-tree capture activated

The next gate now downloads the exact source files pinned by the promoted reference snapshot for all 20 Frameworks on both Ubuntu Resolute and Debian sid, verifies their SHA-256 values, extracts each `debian/` tree, and records deterministic tree/control/package-file hashes.

The artifact retains all 40 extracted packaging trees so the subsequent contract review can inspect relations, install manifests, symbols, maintscripts, rules and compatibility deltas directly.

State: `package-contract-tree-pending`. This remains a technical-reference operation with `package_state_effect=none`; no Tier 3 binary build is authorized.


## Packaging-tree capture PASS

Run `35729077373`, job `106750146405`, artifact `10694324518`, artifact SHA-256 `43a1089660033d9a1a1ae785e348f0b1e8f17636f3085b4449fd9c65f0f2091a`: **PASS**.

The normalized index SHA-256 is `3f975678343f872c8094b20425e76b4026a59d1c5f50c1d5b2c5c1b48a00c7fb`.

All **40** pinned packaging trees (20 Frameworks × Ubuntu/Debian) were downloaded from the exact source versions recorded by the reference-capture PASS, source-file SHA-256 values were reverified, and each extracted `debian/` tree received deterministic tree, control-summary and packaging-file digests.

This remains technical evidence only. No package version, adaptation, materialization or package PASS is implied.

The next gate is **Tier 3 package-contract review**: compare KDE 6.30 upstream requirements against the exact Debian 6.30 tree and Ubuntu compatibility surface, then explicitly record any provider adaptation before materialization is authorized.


## Contract review activated

The contract-review lane consumes the promoted packaging-tree artifact and revalidates its index/tree hashes before comparing the exact Ubuntu and Debian package metadata.

Canonical readiness is now `package-contract-review-pending`. The review captures Build-Depends, binary relationship, `debian/rules`, install-manifest, symbols and maintscript deltas alongside the KDE-upstream dependency classes.

Differences are evidence, not automatic FAILs and not automatic contract decisions. Materialization and package builds remain explicitly unauthorized until the resulting review is promoted and each relevant delta is classified.


## Contract review PASS

Run `35730670337` captured and hashed the package-contract deltas for all 20 nodes. Canonical readiness is now `package-contract-review-pass`.

The review is not itself a contract choice: every node remains package-state `pending`, and materialization/build are unauthorized until SupraLINUX classifies the recorded deltas against KDE-upstream requirements and the Ubuntu compatibility objective.


## Package-contract decisions PASS

The reviewed deltas are now explicitly classified in `docs/kde-tier3-contract-decisions.md` and in this manifest's `contract_decision`/per-node contract records.

All 20 nodes originally entered materialization with candidate `6.30.0-0supralinux1`. Level 0 attempt 1 later produced evidence requiring source-packaging changes for KIconThemes, KDAV, KWallet, KRunner and KJobWidgets; only those five now use remediation candidate `6.30.0-0supralinux2`.
## Materialization handoff

The initial source-only materialization passed 20/20 in run `35746667704`. Level 0 was subsequently activated and run `35755924197` exposed five packaging/provider defects. Those five contracts now carry explicit remediation overrides and are selectively rematerialized before the complete Level 0 campaign is repeated. No attempt-1 result has been canonically promoted.



Selective materialization run `35759443440` proved the five revised contracts at `6.30.0-0supralinux2`. The generated build plan now consumes those exact promoted source-artifact pins; Level 0 activation remains a separate step.


## Round 2 contract delta

Attempt 2 evidence changes only three candidate revisions:

- KIconThemes → `6.30.0-0supralinux3`, adding the Resolute Qt SVG image-format plugin provider for upstream tests;
- KJobWidgets → `6.30.0-0supralinux3`, adding the setuptools PEP 517 backend provider;
- KWallet → `6.30.0-0supralinux3`, restoring KDocTools as an explicit support provider for the selected manpage payload.

The five-node round-1 contract/evidence remains retained as history. KDAV and KRunner stay on their proven `-0supralinux2` revisions.


## Round 2 contract materialization evidence

Run `35806738003` materialized the three `6.30.0-0supralinux3` contracts successfully. The exact source artifacts are now canonical pins for the next Level 0 run.

This promotion proves contract materialization only. Binary package PASS still requires the complete Level 0 attempt 3; no package state is promoted by this step.


Repository Policy run `35807934729` validated the three refreshed source pins. The package-contract phase is unchanged; attempt 3 is the binary-build validation of those already-promoted contracts.


## Round 3 contract delta

The package-contract delta after Level 0 attempt 3 is deliberately minimal.

**KJobWidgets** advances to `6.30.0-0supralinux4`. Existing Python provider adaptations remain unchanged. One symbols-template addition models `_ZSt19piecewise_construct@Base` at minimum version `6.30.0` with the Debian `optional` tag because the symbol is toolchain/private rather than KDE API.

**KWallet** remains `6.30.0-0supralinux3`. Its source Build-Depends contract is unchanged. The Level 0 provider closure now records KArchive `6.30.0-0supralinux4` artifact `10364726750` as the provider of `libkf6archive-dev` required transitively by the selected KDocTools support artifact.

No round-3 decision changes KDE upstream dependency semantics or canonical package state.


## Round 3 materialization result

KJobWidgets `6.30.0-0supralinux4` source materialization is PASS in run `35812918054` and is now the canonical source pin for the next Level 0 campaign. The exact artifact is `10730956293` with SHA-256 `bcd505c1d4cbc65b45861335f41d8b03f18d53995bb9ba1d9036295bd5ce7804`.

KWallet keeps its `6.30.0-0supralinux3` source pin; only its build-provider closure changes. Neither transition changes canonical package state.


Attempt 4 is activated after Repository Policy run `35813396247`. KJobWidgets uses the promoted `6.30.0-0supralinux4` source contract and KWallet uses the unchanged `6.30.0-0supralinux3` source contract plus its complete KDocTools/KArchive provider closure.
