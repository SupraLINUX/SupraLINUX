# KDE Frameworks Tier 3 package contracts

Status: **round 7 source remediation pending — KIO -3 + KXMLGui -2**

Reviewed: **2026-09-23**

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


## Round 4 contract delta

Attempt 4 run `35813710318` reduced Level 0 to one real FAIL: KWallet. The previously selected KDocTools/KArchive provider closure is now validated and remains unchanged.

KWallet advances from `6.30.0-0supralinux3` to `6.30.0-0supralinux4` solely because its source symbols template changes. `libKF6WalletBackend.so.6` receives `(optional)_ZSt19piecewise_construct@Base 6.30.0`. This models an observed libstdc++/toolchain-dependent private export without declaring it KDE public ABI.

No KDE dependency edge, payload choice, test policy or provider closure changes in round 4. Only KWallet is eligible for selective rematerialization.


## Round 4 materialization result

KWallet `6.30.0-0supralinux4` materialized PASS in run `35817654811` from commit `1a9a4ba82b4aac9f1df9f6457faef8b905dd17cf`. The promoted source artifact is `10731134598`, SHA-256 `de215dfb5f86816dadccc630f23360bdc4c79a010aa6f7a0e2e99b1969bcf4ef`.

The materialized symbols template contains exactly `(optional)_ZSt19piecewise_construct@Base 6.30.0`. Promotion updates the source pin only; it does not make KWallet or any other Tier 3 node canonical PASS.


Attempt 5 is activated only after Repository Policy run `35817928654` validates the promoted KWallet `-4` source pin and regenerated campaign. Contract authority and provider decisions are unchanged; this activation is binary validation only.


## Level 0 Attempt 5 canonical transition

Attempt 5 run `35818120201` closes the source-contract validation loop for the Level 0 set. Eleven real package PASS results are promoted canonically and remain tied to their exact artifact IDs and SHA-256 digests.

KNewStuff is intentionally not promoted despite a successful build. Its package evidence remains retained while the canonical package state stays pending until KCMUtils can satisfy the deferred runtime-validation contract.

This transition does not alter any package-contract decision. It changes only package state/evidence and advances the next gate to Level 1 planning.


## Round 5 — KIO Level 1 preflight contract delta

KIO advances from `6.30.0-0supralinux1` to `6.30.0-0supralinux2` because its source packaging changes before Level 1 execution.

The contract removes Debian-only `libkf6auth-dev` and `libkf6configwidgets-dev` Build-Depends. KDE 6.30 KIO does not declare either as a CMake dependency, so neither may become a SupraLINUX KDE DAG edge.

The contract also materializes the selected Linux Wayland profile explicitly by correcting the reference Linux conditional, and reverses/removes only `report_error_removing_dirs` to restore upstream runtime behavior. The materializer now supports exact, counted `rules_text_replacements` and selective reference-patch removal while preserving unrelated active patches.

No Level 0 PASS state changes. Only KIO enters the selective source-materialization queue; Level 1 remains unauthorized until the replacement source artifact passes and is promoted.


### Round 5 source evidence

KIO `6.30.0-0supralinux2` materialized PASS in run `35825070347`, artifact `10735250819`, SHA-256 `8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106`.

Historical remediated revisions are monotonic: KJobWidgets and KWallet remain at their previously promoted `-4` revisions while KIO advances to `-2`; entering a later remediation round never reverts an earlier package contract.


### Round 5 activation handoff

KIO source materialization is already PASS and unchanged. Repository Policy run `35826072726` validated the Level 1 plan, so the round-5 contract handoff now points to `tier3-build-level1-attempt1`. This does not modify KIO's package contract; it records that the separate binary-execution gate has been satisfied.


### Round 6 — Level 1 provider closure only

Attempt 1 exposed no new KIO or KXMLGui source-contract defect. The failed install-deps phase instead proved that the retained artifact set was missing transitive Debian package providers.

Round 6 therefore has `source_changed_nodes=[]` and `provider_closure_only_nodes=[kio,kxmlgui]`. KIO stays at `6.30.0-0supralinux2`; KXMLGui stays at `6.30.0-0supralinux1`.

The closure rows are explicitly classified `transitive-deb-provider-closure` with `kde_dependency_edge=false`. They preserve package-manager closure without allowing Debian packaging relations to redefine the KDE-upstream DAG.


## Round 6 closure completion

The Level 1 package contracts keep KIO at `6.30.0-0supralinux2` and KXMLGui at `6.30.0-0supralinux1`. No source-package contract changed.

The provider closure is expanded to the full set proven by real predecessor `.deb` metadata, including KConfigWidgets for KIO's KBookmarks packaging closure and Breeze Icons for the KIconThemes runtime relation. These retained PASS providers are availability inputs only, not new KDE DAG edges and not direct `.buildinfo` requirements.

Attempt 2 requires a separate activation only after Repository Policy validates this closure-only remediation.


## Attempt 2 activation

The round-6 closure passed Repository Policy `35828634884` and Level 1 paused validation workflow `35828634887`. KIO remains `6.30.0-0supralinux2`; KXMLGui remains `6.30.0-0supralinux1`.

This activation changes only execution state. It does not alter source packaging, binary identities, selected profiles, KDE dependency edges or stable-publication policy.


## Round 7 — Level 1 Attempt 2 contract delta

Attempt 2 run `35829170695` proves that round 6 solved the transitive provider-closure failure: both nodes reached their own build logic. The remaining changes are therefore node-owned source-packaging/test-environment adaptations.

**KXMLGui** advances to `6.30.0-0supralinux2`. Its upstream-default Python bindings stay enabled. The contract adds `python3-build` and `python3-setuptools`, extending the already-proven KJobWidgets Resolute Python-build provider adaptation to KXMLGui.

**KIO** advances to `6.30.0-0supralinux3`. The contract does not suppress any of the 69 upstream CTest targets. It adds the test-only session-bus provider and the exact SupraLINUX Breeze theme payload, then supplies a deterministic offscreen/session-bus/HOME test environment with serial CTest execution.

Two KIO upstream tests explicitly access `google.com`. The binary-build manifest therefore records a node-scoped sbuild network exception for KIO only; this is CI execution policy, not a KDE dependency edge and not a global build-network policy.

No KDE DAG edge changes in round 7. Both revised source packages must rematerialize before Level 1 Attempt 3 can be authorized.

Repository Policy validation for round 7 must also retain the earlier round-5 KIO upstream-alignment decisions and round-6 provider-closure contracts. The contract validator therefore treats those as cumulative invariants, while extending the Resolute Python build frontend/backend provider scope from KJobWidgets to KXMLGui.


### Round 7 source materialization PASS

Both contract deltas materialized successfully in run `35882795135` at commit `0d6c02f3f8dc41f716ba62ee7121f56371a8dc91`: KIO `6.30.0-0supralinux3` artifact `10760324592` and KXMLGui `6.30.0-0supralinux2` artifact `10761208629`.

The promotion preserves the cumulative round-5 KIO upstream-alignment contract and round-6 provider closure. It changes no KDE DAG edge and grants no binary execution authority. The next gate is Level 1 planning validation for a separately authorized Attempt 3.
