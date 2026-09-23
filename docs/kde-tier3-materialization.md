# KDE Frameworks Tier 3 source materialization

Status: **PASS — round-3 KJobWidgets materialization promoted; Level 0 attempt 4 activation pending validation** as of 2026-09-22.

This gate materializes the 20 canonical KDE Frameworks Tier 3 source packages from the already-approved SupraLINUX package contracts. It does **not** build binary packages and cannot make a Tier 3 node `PASS` or downstream-eligible.

## Authority and baseline

- KDE upstream stable 6.30.0 remains source/feature/default authority.
- The official KDE 6.30 tarball is downloaded independently and verified against the pinned SHA-256 in `manifests/kde-frameworks-tier3.json`.
- Debian sid `6.30.0-1` is only the exact technical packaging baseline. Its `.dsc`, `debian.tar` and orig tar are pinned by SHA-256, and the extracted `debian/` tree must reproduce the promoted tree hash before any adaptation is applied.
- Ubuntu 26.04 Resolute is the platform/provider target, not desktop authority.

The upstream stable directory was rechecked on 2026-09-22; `6.30/` is the newest published stable Frameworks directory: <https://download.kde.org/stable/frameworks/>.

## Deterministic adaptations

The materializer applies only the decisions already recorded in `manifests/kde-tier3-package-contracts.json`:

- replace Debian packaging-tool baseline `debhelper-compat (= 14)` with Resolute-supported `13`;
- target changelog distribution `resolute` and SupraLINUX maintainer metadata;
- remove reference distribution Uploaders/VCS metadata;
- force `BUILD_TESTING=ON` and remove only no-op test suppression;
- preserve/force selected Linux profile flags from KDE upstream;
- select `KDESU_USE_SUDO_DEFAULT=ON` only for the documented Ubuntu-family integration exception;
- retain KIO Wayland/Designer/app-template profile and `kwallet6` runtime provider closure;
- preserve Purpose KDE Connect as optional (`Suggests`), never mandatory;
- materialize the upstream-enabled Python bindings for KJobWidgets and KXMLGui, including their binary package stanzas/install manifests and the verified Resolute PySide6/Shiboken/LLVM build-provider closure.

For KJobWidgets and KXMLGui, Resolute currently provides PySide6/Shiboken 6.10.2 and LLVM 21 provider packages. These are provider facts only; KDE 6.30 remains the feature authority.

## Evidence contract

Each matrix node retains:

- pipeline log and structured `result.json`;
- verified KDE orig tar and SHA-256;
- pre-adaptation Debian packaging-tree hash;
- resulting materialized `debian/` tree and hash;
- `.dsc` and `.debian.tar.*`;
- deterministic complete source-tree tarball;
- adapted `control`/`rules` hashes;
- file-level SHA-256 manifest.

A materialization PASS always records:

- `package_attempted=false`;
- `package_state_effect=none`.

Therefore **materialization PASS is not package PASS**.

## Lifecycle

Current state:

- Tier 3 packages: **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**;
- promoted materialization baseline: **20/20 PASS** from run `35746667704`;
- current materialization manifest: `remediation-pending-ci` for 5 nodes;
- Level 0 binary execution: **paused until remediation materialization is promoted**;
- active gate: `tier3-build-level0` remediation;
- stable publication: never automatic and always requires explicit user approval.

Run `35746667704` materialized all **20/20** source packages successfully from commit `39fcab118709bcdb7e97524333d3f74d1b4edec4`. Repository Policy run `35746667671` also passed. Every promoted node records its job ID, artifact ID and GitHub artifact SHA-256; the artifact itself retains the complete `result.json`, source-package hashes, deterministic source-tree hash and adapted `debian/` payload.

Materialization changed no package state: `package_attempted=false` and `package_state_effect=none`. The subsequent `build-campaign-planning` gate has since passed Repository Policy and Level 0 now has its own explicit execution manifest. This document remains the canonical materialization record; current build execution state is documented in `docs/kde-tier3-build-level0.md`.

## Promotion validation history

Promotion-validation run `35748536747` is retained as a historical CI FAIL: materialization scope correctly skipped the 20-node matrix because semantic inputs were unchanged, but the promoted validator contained a literal `\\n` escape and failed Python parsing. This did not change or invalidate any materialized artifact or package state; the validator-only defect is corrected in the next commit.

Repository Policy run `35748772874` is also retained as a historical lifecycle-validation FAIL: the promoted canonical next gate `tier3-build-campaign-planning` was correct, but five support-component validators still limited their accepted historical next-gate set to `tier3-materialization`. No support/package state changed; those lifecycle validators are widened in the next commit.


## Selective rematerialization after Level 0 attempt 1

Level 0 run `35755924197` exposed five package-owned packaging/provider defects. The previous 20/20 materialization PASS remains historical evidence, but exactly five source packages now require a new packaging revision and therefore new source artifacts:

- KIconThemes `6.30.0-0supralinux2`;
- KDAV `6.30.0-0supralinux2`;
- KWallet `6.30.0-0supralinux2`;
- KRunner `6.30.0-0supralinux2`;
- KJobWidgets `6.30.0-0supralinux2`.

The materialization matrix is intentionally restricted to this remediation queue. The other 15 source materializations remain unchanged and are not rebuilt.

The new deterministic adaptations are contract-driven:

- remove Debian-only mandatory source/binary dependency relations that contradict KDE upstream dependency semantics for KIconThemes, KDAV and KWallet;
- add Resolute `python3-build` as the provider required by upstream-enabled KJobWidgets Python bindings;
- remove KIconThemes' Debian `EXCLUDED_TESTS` suppression;
- reverse/drop KRunner's Debian `skip-flaky-test.patch` so the upstream test actually executes;
- mark only two toolchain-dependent KRunner libstdc++ template implementation symbols `optional=templinst`, retaining the existing architecture condition.

The global build-campaign plan continues to validate against the last promoted materialization PASS while this selective materialization is pending. After all five new artifacts pass, their exact workflow/job/artifact IDs and SHA-256 digests will replace the old pins, the generated plan will be refreshed, and only then will Level 0 execution be reauthorized.

Materialization still has `package_attempted=false` and cannot itself produce package PASS.


## Remediation promotion evidence

Run `35759443440` completed the selective remediation matrix with **5/5 SUCCESS**. The promoted source-artifact digests are recorded in `manifests/kde-tier3-materialization.json`, `manifests/kde-tier3-build-campaign.json` and the canonical Tier 3 inventory.

The promoted nodes are KIconThemes, KDAV, KWallet, KRunner and KJobWidgets at `6.30.0-0supralinux2`. Their previous `-0supralinux1` materialization evidence remains retained as history.

The materialization scope selector now hashes only inputs that can change the produced source package. Lifecycle/evidence promotion and selector-only changes do not trigger a new materialization; semantic contract changes, the materializer itself, and the workflow still do.


## Selective remediation round 2

Level 0 attempt 2 (run `35770505868`) reduced the unresolved set from five nodes to three. The promoted `-0supralinux2` evidence remains the active baseline and is preserved in each node's materialization history.

Only the following source packages are rematerialized:

- KIconThemes `6.30.0-0supralinux3`: add Resolute `qt6-svg-plugins <!nocheck>` so the upstream SVG tests have the QImage format provider they actually exercise.
- KJobWidgets `6.30.0-0supralinux3`: add `python3-setuptools` as the backend required by the already-enabled upstream Python wheel build.
- KWallet `6.30.0-0supralinux3`: provide `libkf6doctools-dev (>= 6.30.0~)` from the PASS SupraLINUX KDocTools artifact so the selected `kwallet-query.1` payload is generated.

The other 17 source materializations are not rebuilt. Materialization remains source-only: `package_attempted=false` and it cannot create package PASS.


## Round 2 promotion evidence

Selective materialization run `35806738003` completed **3/3 SUCCESS** from commit `d6aa9a9550dc3c870a9f1beb00fe216d8c20c3d6`.

The promoted source artifacts are:

- KIconThemes `6.30.0-0supralinux3`: artifact `10728445324`, SHA-256 `f03028a64343b09d02327376fdec0be9e8c06ad9e75d59c86e1195a1350a49d4`;
- KJobWidgets `6.30.0-0supralinux3`: artifact `10728630058`, SHA-256 `6e5e293abd09904380a61980d69a77bcf9ac91189d16a429e5270f5c4060ddc5`;
- KWallet `6.30.0-0supralinux3`: artifact `10727054712`, SHA-256 `46ad7064b20ffbfb5b8b5d2242378a8e2ab082452edf0985dd9d1f6fb9074deb`.

All 20 Tier 3 nodes are again materialized. Seventeen retain their previous source artifacts; only the three round-2 nodes changed. Materialization remains source-only and has no package-state effect.

Level 0 remains intentionally paused. Attempt 3 can be activated only after Repository Policy validates these refreshed canonical pins.


Repository Policy run `35807934729` validated the round-2 promotion. Source materialization is closed again at 20/20, and the separate Level 0 authority has now activated attempt 3. No additional source rematerialization is requested by that activation.


### Validator lifecycle note

The materialization validator accepts both legitimate post-promotion states: a validated source promotion that is still waiting for Level 0 activation, and a separately validated Level 0 activation that leaves source materialization unchanged at PASS. Activating a binary-build campaign must not make the already-closed source-materialization definition invalid.


## Round 3 selective materialization

Level 0 attempt 3 (`35808764577`) leaves two binary failures, but only **KJobWidgets** changes source packaging.

KJobWidgets advances from `6.30.0-0supralinux3` to `6.30.0-0supralinux4`. Its build and 3/3 upstream tests already succeeded; the new materialization changes only the symbols template by declaring the observed libstdc++/toolchain-dependent `_ZSt19piecewise_construct@Base` as `(optional)` with minimum upstream version `6.30.0`. Debian's source-symbol format defines `optional` for private symbols whose disappearance is not an ABI break.

KWallet stays at `6.30.0-0supralinux3` and **must not rematerialize**. Its round-3 fix is solely a Level 0 provider-closure change: add the existing PASS KArchive artifact so the KDocTools support provider can satisfy `libkf6archive-dev >= 6.30`.

The materialization queue is therefore exactly `[kjobwidgets]`. All other 19 promoted source artifacts remain unchanged. Source materialization continues to have no package-state effect.


## Round 3 promotion evidence

Selective materialization run `35812918054` completed **PASS** for KJobWidgets `6.30.0-0supralinux4` from commit `a57c13059dfc206ddf57390e1cd0cfd280471965`.

Promoted source artifact:

- job `107028214719`;
- artifact `10730956293`;
- artifact SHA-256 `bcd505c1d4cbc65b45861335f41d8b03f18d53995bb9ba1d9036295bd5ce7804`;
- `.dsc` SHA-256 `ca067a32fcf3baf22622ce8bb98f6fa8766dcbddb7e3c06ce1aa504fb148c39b`;
- `debian.tar` SHA-256 `61ed9e5ddf96a3568007ff602bd3b22962403952ad6c7ae8e95eb9fab3faea17`;
- materialized packaging-tree SHA-256 `3c54397e2f29e1724d023c28faea5e5be83e9e1bbf160841c82d9fcdfaf41fac`.

The retained KDE upstream tarball SHA-256 remains `bf36e3619df1c6ad3d900bd36433d97ab295be41c1cc401ff0e766380788bbae`. The materialized symbols template contains the explicit optional `_ZSt19piecewise_construct@Base` entry at upstream version `6.30.0`.

All 20 Tier 3 nodes are again source-materialized. Nineteen retain their previous source artifacts; only KJobWidgets changed. KWallet remains source-identical at `6.30.0-0supralinux3`.

This promotion does **not** authorize binary builds. Level 0 stays paused until Repository Policy validates the refreshed KJobWidgets pin and the KWallet KArchive provider closure.
