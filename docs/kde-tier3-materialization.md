# KDE Frameworks Tier 3 source materialization

Status: **Round 10 source materialization PASS retained; Attempt 6 closed; no Round 11 rematerialization authorized** as of 2026-09-24.

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
- apply exact counted `rules_text_replacements` when a reference conditional prevents the selected profile from taking effect;
- selectively reverse/remove explicitly rejected downstream patches while preserving unrelated active technical patches;
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


Repository Policy run `35813396247` validated the round-3 source promotion. Materialization remains closed at 20/20 PASS while the separate binary-build authority activates Level 0 attempt 4. No additional source rematerialization is requested.


## Round 4 selective materialization

Level 0 attempt 4 run `35813710318` validated KWallet's complete KDocTools/KArchive provider closure and all 3 upstream tests. The only remaining defect is the KWallet symbols template for `_ZSt19piecewise_construct@Base`.

The materialization queue therefore contains exactly **one node: KWallet**. Candidate revision is `6.30.0-0supralinux4`; all other 19 Tier 3 source materializations remain pinned to their already-promoted PASS evidence. This gate still has no canonical package-state effect.


## Round 4 promotion

Run `35817654811`, job `107042596959`, materialized KWallet `6.30.0-0supralinux4` successfully. Artifact `10731134598` has SHA-256 `de215dfb5f86816dadccc630f23360bdc4c79a010aa6f7a0e2e99b1969bcf4ef`.

The source evidence records: DSC SHA-256 `c97d75a119e3971c9c551ebb44f6b0f74e63771f0ffabb62e3d8c71bce1d0348`, Debian tar SHA-256 `c5b7629a60ed1dddc55142582c892e38d382b19e59bcf3a10a479405f67f5cf2`, source-tree SHA-256 `8759eef0fe99b844c7fdff5765012e73daabf67fb06899656308b1cbfbabff7c`, and materialized-tree SHA-256 `c5a73861d71245a913b2915013db22be9acb041999c85df020773461271f71c0`.

All 20 source materializations are again PASS. This still changes no binary package state. The next gate is Repository Policy validation before separate Level 0 Attempt 5 activation.


Repository Policy run `35817928654` validates the round-4 promotion and refreshed build campaign. Source materialization remains PASS; a separate Level 0 activation now consumes the promoted evidence in Attempt 5.


## Post-Attempt-5 state

Source materialization remains **20/20 PASS**. Attempt 5 consumed those exact source pins and produced 11 canonical package PASS nodes plus one retained KNewStuff build awaiting KCMUtils runtime validation.

No source rematerialization is required. The next gate is Tier 3 Level 1 planning.


## Round 5 selective KIO materialization

Level 1 preflight found source-packaging divergence before any Level 1 binary attempt. The materialization queue therefore contains exactly **KIO** at candidate revision `6.30.0-0supralinux2`.

The replacement source removes the two Debian-only false Framework Build-Depends, makes the selected Linux Wayland flag effective, and restores upstream behavior by removing only `report_error_removing_dirs`. The other 19 source-materialization artifacts remain pinned to their existing PASS evidence.

This gate has `package_attempted=false` and no canonical package-state effect. The 11 Level 0 PASS nodes remain PASS, KNewStuff remains runtime-validation-required, and Level 1 binary execution stays unauthorized.


## Round 5 promotion evidence

Run `35825070347`, job `107064960565`, produced source-only PASS artifact `10735250819`, SHA-256 `8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106`.

The promoted source hashes are: DSC `c9b8e0a660b3450f3662f7de99fce063041d71111952806d741e6b68b7999852`, Debian tar `98e558f4855c4ddf407ac0508fa9404926b727462da57263018b70030bd342e0`, source tree `1d020987f3a12eb5e588ca75d02b5f2efe0a5530e33b812012e3ef7719deaf23`, materialized tree `cdfa0bd2dc13f7ee75354bb3480951f6aebaf5d82a138746bcd56343a5ac15f9`, adapted control `b1ab7b4386e5076a2fcdddcf29b399ccf8093d1f7bcec20d717fc9ceaa8ec31b`, and adapted rules `87a32e610585ab989426006099b0e62a15f22d299ea70db3266b2a399f8dfd10`.

All 20 Tier 3 source materializations are again PASS. This promotion has no binary package-state effect.


### Round 5 activation handoff

The KIO `6.30.0-0supralinux2` materialization remains the exact PASS artifact from run `35825070347`. After Level 1 planning passed Repository Policy run `35826072726`, the materialization lifecycle hands off to `tier3-build-level1-attempt1`. No source artifact or hash changes at activation.


### Round 6 requires no materialization

Level 1 Attempt 1 failed before compilation because retained provider closure was incomplete. No source-package content changes.

The existing 20/20 materialization PASS remains authoritative, including KIO `6.30.0-0supralinux2` artifact `10735250819`. Round 6 has no materialization queue and no new source hash. The next action is Level 1 Attempt 2 activation only after Repository Policy validates the provider closure.


## Attempt 1 provider-closure result

Attempt 1 changes no source artifact. KIO remains `6.30.0-0supralinux2`; KXMLGui remains `6.30.0-0supralinux1`. The failure occurred in dependency installation before compilation and is corrected only by retained PASS provider artifacts.

Accordingly, round 6 has no materialization queue, no new source hash and no package revision bump. Attempt 2 is gated exclusively on provider-closure validation.


## Attempt 2 activation handoff

The round-6 closure remediation passed Repository Policy `35828634884`. Source materialization remains **20/20 PASS** with no new artifact or revision. Attempt 2 is a binary-only rerun consuming the already-promoted KIO and KXMLGui source packages.


## Round 7 selective materialization

Level 1 Attempt 2 (`35829170695`) crossed the round-6 provider-closure gate and established two source-packaging/test-environment remediations.

The materialization queue is exactly **KIO + KXMLGui**:

- KIO `6.30.0-0supralinux3`: adds the providers and deterministic test wrapper required to execute the complete upstream KIO suite without exclusions.
- KXMLGui `6.30.0-0supralinux2`: adds `python3-build` and `python3-setuptools` for the enabled ECM/Shiboken Python wheel path.

The previous KIO `-2` artifact `10735250819` and KXMLGui `-1` artifact `10703925009` remain retained as immutable history until replacements pass. Materialization is source-only: `package_attempted=false` and it cannot promote either package to PASS.


### Round 7 test-policy validator semantics

The materializer's no-test-suppression guard now distinguishes a disabled test override from a direct CTest runner. A direct `ctest` invocation is permitted only when failures remain fatal and no test-selection/exclusion options are present. KIO's round-7 wrapper therefore executes the complete suite while supplying environment isolation; it does not convert failing tests to PASS or filter them out.


## Round 7 promotion evidence

Selective source materialization run `35882795135` completed **2/2 SUCCESS** from commit `0d6c02f3f8dc41f716ba62ee7121f56371a8dc91`. This is source-only evidence: `package_attempted=false` and no binary package becomes PASS.

KIO `6.30.0-0supralinux3` is artifact `10760324592`, SHA-256 `b58b7a45f6df0c8f01e9bd9a37799c1470369124a7c1b48fecb82a5f7f86ae8d`. Its adapted control/rules hashes are `582159e83e2c36e16be0da212d67a4a5eb725341b5a28fe4828bc515a9b5f505` and `6db9a93621a73f87a6be3a38bfa914df065f9ab85962cc46738a1cb3a5817cab`.

KXMLGui `6.30.0-0supralinux2` is artifact `10761208629`, SHA-256 `72cd10276558264646a9e38d5beab7b231434338597ef8d276030e790ff02214`. Its adapted control/rules hashes are `734bbf0fb49ba1691ec9994ea83cb7ccb11446c8a9e098aa9ae796726c417c3b` and `914ecc0245b8680ca4869549d6030a974c1cde60904759a0c876fabd25a19fa6`.

All 20 Tier 3 source materializations are again PASS. Level 1 remains unauthorized until Repository Policy validates these refreshed pins; the next binary action is a separately authorized full Attempt 3.


### Attempt 3 handoff

The promoted round-7 materialization set remains **20/20 PASS**. After Policy validation, its next gate is now `tier3-build-level1-attempt3`; no source artifact changes at activation.

KIO remains pinned to artifact `10760324592` and KXMLGui to `10761208629`. Materialization itself still has no binary package-state effect.

## Round 8 selective materialization

Attempt 3 run `35887558758` establishes two narrow source-package test-environment deltas. The materialization queue is exactly **KIO + KXMLGui**.

- KIO `6.30.0-0supralinux4`: keep the round-7 test environment that improved the suite to 62/69 PASS, but stop forcing a shared `XDG_RUNTIME_DIR`.
- KXMLGui `6.30.0-0supralinux3`: retain the validated Python build providers and run the complete upstream `dh_auto_test` with `QT_QPA_PLATFORM=offscreen`.

The prior source PASS artifacts remain immutable evidence: KIO `-3` artifact `10760324592` and KXMLGui `-2` artifact `10761208629`. Round 8 changes no KDE DAG edge and suppresses no upstream test. Materialization remains source-only and cannot promote a binary package to PASS.

## Round 8 evidence

Workflow `35894317888` materialized both queued nodes successfully.

KIO evidence: job `107294403189`, artifact `10766471076`, SHA-256 `80959256047d70323b6ea311551bed573661cefb4b831f30750e27ed11076cf6`, source-tree SHA-256 `d88c3b4e7a8774cb2997cfa0c3d3bba73e97e8ef11bd073e64c49ead74fb229b`, materialized-tree SHA-256 `93d2d6e512b9e48048d1aa8469ecb176d619a2574e2edfb128e7434a8eff924c`.

KXMLGui evidence: job `107294403314`, artifact `10766665506`, SHA-256 `100cf903ca1ef17cf2b37bab58ba0b7bf1e562d111cc04107247c3f35b134d58`, source-tree SHA-256 `bcdab8c76d72dc9fc885ee87806760f8541b3a023e7ca9857be51a1db8024a94`, materialized-tree SHA-256 `4dfbea635019b76d9dbd435b90fc60f93cbacf77226e9dbffa847c48c65159e0`.

Both results are source-materialization PASS only: `package_attempted=false`, `package_state_effect=none`. The next gate is Level 1 planning validation.

### Attempt 4 handoff

The round-8 materialization set remains **20/20 PASS**. After planning validation, its next gate is now `tier3-build-level1-attempt4`; activation does not alter any source artifact.

KIO remains pinned to artifact `10766471076` and KXMLGui to `10766665506`. Materialization continues to have no binary package-state effect.

## Round 9 selective materialization

Attempt 4 `35961584503` leaves exactly two source-package test-environment deltas. The materialization queue remains exactly **KIO + KXMLGui**.

- KIO `6.30.0-0supralinux5`: add `xvfb <!nocheck>`; retain D-Bus, controlled HOME, KDECI, serial CTest and node-scoped network; run the complete suite through `QT_QPA_PLATFORM=xcb` on Xvfb and set `QT_QPA_SYSTEM_ICON_THEME=breeze`.
- KXMLGui `6.30.0-0supralinux4`: add `dbus-daemon <!nocheck>`; retain `QT_QPA_PLATFORM=offscreen`; run the complete upstream `dh_auto_test` inside `dbus-run-session`.

The promoted round-8 source artifacts remain immutable previous evidence until round 9 succeeds: KIO artifact `10766471076`, KXMLGui artifact `10766665506`. This gate remains source-only and cannot promote a binary package.

### Round 9 relation-validator scope

The materialization validator treats KIO/KXMLGui test-provider relations as round-scoped contracts: round 9 extends the retained round-8 sets with `xvfb <!nocheck>` for KIO and `dbus-daemon <!nocheck>` for KXMLGui. Historical round-8 validation continues to require its original relation sets.

## Round 9 evidence

Workflow `35965579279` materialized both queued nodes successfully at commit `8380856c8161dccc9de9c12745012c555baa26b0`.

KIO evidence: job `107523339110`, artifact `10794251210`, SHA-256 `45eac20aca30ca6a5ef78d8a94d15ee5408a8bed39c8fa72c6c8823134ffa0b2`, source-tree SHA-256 `fa3df7e7ef328c7e553b045530264ccdd824fb64724872f1aefc60f5f48210fd`, materialized-tree SHA-256 `aa5cdf630de7edfbf21689b7855c8f3e149f0c3d219448ae27cf525fdaac8dec`.

KXMLGui evidence: job `107523339321`, artifact `10793229286`, SHA-256 `44b9cf9d0ad12f06b12bda37c291fcda5ecf933e25cfdd61c42d9df6e11b0093`, source-tree SHA-256 `2869ebb158febcebec727ef5b661ea72c130b6ba7a82472c4ef09620b5b693dd`, materialized-tree SHA-256 `735268065ebb91c3dca48e303c2179cd5658f1086950ba00a537e15bf1949642`.

Both results are source-materialization PASS only: `package_attempted=false`, `package_state_effect=none`. The next gate is Level 1 planning validation; Attempt 5 remains unauthorized.

### Attempt 5 planning handoff

The round-9 materialization set remains **20/20 source PASS**. Repository Policy `35990068378` and the paused Level 1 planner `35990068382` validated the promoted source/campaign pins at commit `45675c1fb5a43f95204c2cf0c5c15df0ef703832`.

Materialization still has no binary package-state effect. Its future Attempt-5 handoff is being validator-prepared before activation; KIO remains artifact `10794251210`, KXMLGui remains artifact `10793229286`, and no source is rematerialized.

### Attempt 5 active handoff

The round-9 materialization set remains **20/20 source PASS** and is now handed to active Level 1 Attempt 5 after planning validation (`35990068378` / `35990068382`) and forward-compatible lifecycle validation (`35990715536` / `35990715990` / `35990715302`).

KIO remains pinned to artifact `10794251210` and KXMLGui to `10793229286`. Activation changes no source artifact and materialization still has no binary package-state effect.

## Round 10 selective materialization

Attempt 5 `35991007820` leaves two source-package deltas, so the materialization queue is again exactly **KIO + KXMLGui**.

- KIO `6.30.0-0supralinux6`: retain the proven D-Bus, Breeze, Xvfb, controlled HOME, KDECI, serial CTest and node-scoped network setup. During `override_dh_auto_configure`, append two CMake test-property overrides so only `kiowidgets-kdirmodeltest` and `kiofilewidgets-knewfilemenutest` use `QT_QPA_PLATFORM=xcb;QT_QPA_SYSTEM_ICON_THEME=breeze`. Every other upstream test retains its existing environment.
- KXMLGui `6.30.0-0supralinux5`: retain the now-proven 7/7 D-Bus/offscreen suite; add the test-only `libkf6textwidgets-dev (>= 6.30.0~) <!nocheck>` relation and one optional toolchain template-symbol baseline for `_ZSt19piecewise_construct@Base` at `6.30.0`.

The promoted round-9 source artifacts remain immutable previous evidence until round 10 succeeds: KIO artifact `10794251210`, KXMLGui artifact `10793229286`. This gate is source-only and cannot promote a binary package.

### Round 10 validator scope

The materialization validator now treats the retained source-relation baseline as round-aware: KIO keeps the round-9 Xvfb provider set in round 10, while KXMLGui extends the round-9 Python/D-Bus set only with the explicitly approved test-only KTextWidgets relation. This prevents historical equality checks from rejecting the documented round-10 packaging delta before either source is attempted.

## Round 10 evidence

Workflow `36002910277` materialized both queued Level 1 nodes successfully at commit `c0774e5514fd83995aad3c86e1f6a5b106b001a3`.

KIO evidence: job `107643756393`, artifact `10809231495`, artifact SHA-256 `5a0c2db21af5a87d4bd5ee2b02ebff7bce4dd98c66622398f00c67ef7210227b`, source-tree SHA-256 `2d9ece007442cccf7145e9dbf1424f10a150c9f28b01f3f548cf1ddbb25a3228`, materialized-tree SHA-256 `cc588e793e0c90b534b9be650ef402a3a766639ec33c38a03b846006ef7b612b`, adapted control SHA-256 `d291d67f1ae89ff839a1adab6c82eeecf8268cb5449d71dbed8f2c73386db280`, adapted rules SHA-256 `42e0d023a0ad42b194b649ae2026b3899575bed9823d6be05d9faf59fa6cc175`.

KXMLGui evidence: job `107643756357`, artifact `10808294092`, artifact SHA-256 `bccf76b46d0c9619e4306f1fe704ff5b501b9554a63f7968093e3afd4beb0d86`, source-tree SHA-256 `81b02b7bf9ecac390fbb5beb1694412f7faec2ecbc86ac2887ff134ba0ff99ef`, materialized-tree SHA-256 `2be38f32658e0b46dac4c9b0a1e7489f87d7e3759fd4470f6483fca54bddaf33`, adapted control SHA-256 `9284376c94338ed4399102ff41ab488912fbb149e6318ab5c18bf6319730462b`, adapted rules SHA-256 `65cd53913bb5e4ac48cd96b38606acf33bc0cc054128b9733508bffdd2d8a7b2`.

Both are source-materialization PASS only: `package_attempted=false`, `package_state_effect=none`. The next gate is Level 1 planning validation; Attempt 6 remains unauthorized.

### Attempt 6 planning handoff

The round-10 materialization set remains **20/20 source PASS**. Repository Policy `36032425645`, paused Level 1 `36032425729`, and the no-op materialization validation `36032425591` all passed at commit `0fee159ac1f24dc160e1edd9976a7708f89d657d`.

Materialization still has no binary package-state effect. Its future Attempt-6 handoff is being validator-prepared before activation; KIO remains artifact `10809231495`, KXMLGui remains artifact `10808294092`, and no source is rematerialized.

### Attempt 6 active handoff

The round-10 materialization set remains **20/20 source PASS** and is now handed to active Level 1 Attempt 6 after planning validation (`36032425645` / `36032425729`) and forward-compatible lifecycle validation (`36033162764` / `36033163019` / `36033162995`).

KIO remains pinned to artifact `10809231495` and KXMLGui to `10808294092`. Activation changes no source artifact and materialization still has no binary package-state effect.

## Level 1 Attempt 6 — canonical closure

Attempt 6 is closed from workflow `36035351270` at commit `f6d47684e4c69cf0765e2d24e8bb93807be04791`. The shared rootfs passed: artifact `10824730747`, SHA-256 `3ece315a28ecd5070a1e2139db45af8483126aebbe8f99bce1cf25999e218234`.

KXMLGui `6.30.0-0supralinux5` is a real canonical **PASS**: 7/7 upstream tests passed and the Python import check passed. Evidence: job `107754320420`, artifact `10824512023`, SHA-256 `da271b820ffe62c1bd4bf4e59874582ff482eb89b9e42d6bf6ae28c8cccc74e6`. It is downstream-eligible and eligible for the SupraLINUX `testing` channel; this does not authorize promotion to `stable`.

KIO `6.30.0-0supralinux6` is a real current **FAIL**: 66/69 upstream tests passed. The failing tests are `kiocore-krecentdocumenttest`, `kiowidgets-kdirmodeltest`, and `kiofilewidgets-knewfilemenutest`. Evidence: job `107754320435`, artifact `10824413911`, SHA-256 `61f2c1ad261fcc4fae4cd8064d71606af42542f5ab735a672e6ff77f6b2f5861`.

Canonical DAG state after closure: **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**. BLOCKED: `baloo`, `kcmutils`, `knotifyconfig`, `kparts`, `ktexteditor`, and `purpose`. `knewstuff` remains pending runtime validation rather than BLOCKED because its package build already succeeded and its deferred runtime validation depends on KCMUtils.

Execution is closed with `execution_authorized=false`. Level 2 is not authorized. The next gate is `tier3-round11-kio-remediation-definition`: define the KIO Round 11 remediation from evidence before changing source or package revision. This closure does not claim a Round 11 implementation or a `6.30.0-0supralinux7` package.

## Round 11 definition validated — KIO materialization active

Repository Policy `36072487004` validated the Round 11 remediation definition at commit `0dad8b3e82eb07bb02e90da4036001a82e885b0f`.

The executable remediation now advances only the KIO source package to candidate `6.30.0-0supralinux7`. Its two targeted icon tests use CMake `ENVIRONMENT_MODIFICATION` for `QT_QPA_PLATFORM=set:xcb` and `QT_QPA_SYSTEM_ICON_THEME=set:breeze`, preserving KDE/ECM's existing `QT_PLUGIN_PATH` and all other per-test environment entries. No test is suppressed.

KXMLGui remains canonical PASS and source-retained at `6.30.0-0supralinux5`; it is not rematerialized. It will be rerun together with KIO in the complete Level 1 Attempt 7 only after the KIO `-7` source artifact passes materialization and planning validation.

`krecentdocumenttest` remains unchanged and fatal. If its Attempt 6 timestamp-order failure reproduces in Attempt 7, it will be diagnosed independently rather than hidden.

Current canonical package state is still **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**. Binary execution remains unauthorized. Active gate: `tier3-round11-kio-materialization`.

## Round 11 KIO materialization — PASS

KIO candidate `6.30.0-0supralinux7` was materialized successfully in workflow `36073638711`, job `107879979760`, from commit `ebe60a0147e2a47b6c256ac015f43eea350c3ba2`.

Evidence artifact `10839162922` has SHA-256 `ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c`. Internal source evidence includes `dsc_sha256=fbba71c0d66cb4e0e09a9f6e2625dd416d642c075a7b8f9ae8bfcd51eee413ec`, `debian_tar_sha256=bccd518fc0be0e9f09bf06e9b346ad21d24143191eef73585cf4347a6fa41118`, `source_tree_sha256=8db83e361fa632ecb36fb171ae78ec021cc6f9e1d0b67fc0476f045e3afce923`, `materialized_tree_sha256=9138398b41e18849de47ac93a0f5f4a68b449607a3b8b02fd16607cf99b2e18d`, and `adapted_rules_sha256=c966d9328a0ab624ac5c7b5fb4d1b328d4812ac477446e0b0adf05671c410bfd`.

This remains **source materialization only**: no KIO binary package was built and canonical KIO remains FAIL at `6.30.0-0supralinux6` until a later Level 1 Attempt 7 succeeds. KXMLGui remains canonical PASS at `6.30.0-0supralinux5`.

The generated Tier 3 build campaign now references the KIO `-7` materialization artifact while `execution_authorized=false`. The next gate is `tier3-build-level1-planning-validation`.
