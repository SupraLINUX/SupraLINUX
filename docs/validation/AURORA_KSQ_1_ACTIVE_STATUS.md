# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This is the current engineering status of KSQ-1. It is not a final KSQ-1 acceptance record and does not authorize entry into KSQ-2.

- KSQ-0: **CERTIFIED / CLOSED**.
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
- KSQ-2: **BLOCKED**.
- C4.1: **PAUSED**.

## Fixed contract

KSQ-1 consumes the certified 101-source DAG, Ubuntu Resolute snapshot `20260829T022000Z`, and the exact package/source identities established by KSQ-0.

The maintained source-build architecture is:

`GitHub-hosted Ubuntu 26.04 -> immutable local snapshot slice -> mmdebstrap --mode=unshare --variant=buildd -> sbuild --chroot-mode=unshare --no-enable-network`

The maintained path does not use Docker, privileged containers, host AppArmor relaxation, a custom AppArmor profile, or the historical uidmap file-capability rewrite.

Canonical build-order SHA-256:

`9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`

APT Recommends remain at normal/default behavior. The obsolete `--no-install-recommends` closure policy is not used to emulate sbuild.

## Immutable r2 historical input

Slice `20260829T022000Z-r2` remains immutable historical evidence:

- upstream snapshot: `20260829T022000Z`;
- release ID: `381836501`;
- archive asset: `542414026`;
- archive bytes: `1054177280`;
- archive SHA-256: `23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b`;
- manifest asset: `542414028`;
- manifest SHA-256: `6ed95b495ded7744f081335684c2918eeae96dbc822fa53b0d9fb5bc2da0f481`;
- 1783 binary `.deb` objects / `785219274` bytes;
- 301 Ubuntu source objects;
- 4 Debian source objects;
- normal/default APT Recommends policy.

Independent r2 publication validation remains PASS. r2 remains the exact slice originally used by the accepted builds through order 65, but it is now **proven insufficient as a universal payload closure for all real 101-source sbuild contexts**. It must never be mutated.

## Accepted maintained checkpoint chain through order 80

### Orders 001–020

- run `33546093974`;
- artifact `9818465016`;
- digest `sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba`;
- 20/20 sources PASS;
- accumulated DEBs: `103`.

### Orders 021–040

- run `33561782526`;
- artifact `9824689982`;
- digest `sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e`;
- 20/20 sources PASS;
- accumulated DEBs: `192`.

### Orders 041–043

- run `33753437984`;
- artifact `9892762100`;
- digest `sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0`;
- 3/3 sources PASS;
- accumulated DEBs: `205`.

### Orders 044–060

- run `33767306768`;
- artifact `9900367299`;
- digest `sha256:41a50bb17ea5ca4ab63c43a6aa6d6d030dae310ba716866824ac72d6c61dc4f3`;
- 17/17 sources PASS;
- accumulated DEBs: `275`.

### Orders 061–065 + KWallet package/install/PAM gate

Build evidence:

- run `33805321380`;
- artifact `9913134271`;
- digest `sha256:035b5930f3821d764f51f7bf4b3bd2b8e82a302539e70c2c612b93f41d3e2e65`;
- 5/5 sources PASS;
- 20 new DEBs;
- accumulated DEBs: `295`.

Independent post-validation:

- run `33819688197`;
- artifact `9917851669`;
- digest `sha256:12b398c5f7388844861cca60f3fac37256eb94b3a32f57a31df8802bdf258a5c`;
- SUCCESS.

Independent fail-closed acceptance:

- run `33821228782`;
- artifact `9918320108`;
- digest `sha256:50c33e99c7593ce6b8d4a67c8ee11c1598ad93545ed362078a57410c4a892730`;
- SUCCESS.

The accepted 1–65 chain remains valid under the proven r3 regression. The independently accepted r3 range 66–80 below advances the maintained checkpoint to **order 80 / 345 accumulated DEBs**.

Detailed record: `docs/validation/AURORA_KSQ_1_RANGE_061_065_KWALLET.md`.

## KWallet scope

The accepted order-65 solver selects exactly `375` packages. Its three separately qualified runtime objects remain in immutable sidecar `20260829T022000Z-kwallet-runtime-r1`:

- `lsb-base=11.6build1`;
- `libwrap0=7.6.q-36build2`;
- `socat=1.8.1.1-1ubuntu0.1`.

Sidecar identity:

- release `382325880`;
- archive asset `543326513`, SHA-256 `89f9861d061a68498950bddb96b1f22ed41ddd205db118719f23b8836284b40e`;
- manifest asset `543326512`, SHA-256 `40a2a1f2e720dd07c93ecdfc52c42b1cd2202a495a749d2722109028cbdf0c32`.

This certifies package relationships, local installation and PAM registration only. Runtime session automatic unlock remains explicitly **NOT CERTIFIED**.

## r2 closure defect — root cause closed

The first maintained 66–80 attempt against r2 was run `33821750759`, artifact `9919609367`, digest `sha256:e04615715fcee3450c14db3f1a7085d09cd937c7db8d2520c0bff49f60546998`.

Orders 66–73 built but were not accepted because order 74 `xdg-desktop-portal-kde` failed while installing Build-Depends. The signed r2 metadata advertised two `libjpeg8-empty` transition payloads that were not physically materialized in r2.

The cause was not KDE source drift, Recommends, AppArmor or Internet access. The invalid r2 assumption was that one aggregate APT transaction over all direct roots necessarily yields a payload superset of every independent sbuild Build-Depends transaction. Provider/alternative choices differ by transaction context.

Detailed record: `docs/validation/AURORA_KSQ_1_RANGE_066_080_R2_BLOCKER.md`.

## Complete build-context witness — PROVEN

Authoritative real build-context witness parent run:

- run `33929720702`;
- witness HEAD `84596eaf2f7d7735b74f48a48fdde82229500f7a`;
- ranges 66–80, 81–90 and 91–101: **36/36 source builds SUCCESS**;
- final witness candidate state: `424` accumulated DEBs;
- new packaging adaptations in 66–101: `0`.

The parent run is globally red only because its obsolete embedded analyzer failed after all real build jobs had succeeded. Those build artifacts were then consumed by an independent explicit analyzer with exact run/head/artifact/digest provenance.

Authoritative independent analysis:

- run `33962296018`;
- artifact `9968317241`;
- digest `sha256:b7db4224c5bd7cd89f6e274cb8a0c617327bc917cee1185cff9e0b2a07ea0694`;
- `AURORA_KSQ_1_BUILD_CONTEXT_WITNESS_STATUS=PROVEN`;
- 36 sources / 36 logs;
- 1114 observed package objects;
- 492106800 observed payload bytes;
- r2 objects: 1783;
- exact gap: **3 objects / 547318 bytes**;
- remote policy: `fixed-snapshot-only`;
- manual package additions: `0`.

The machine-derived r2 gap is exactly:

- `libcurl4-openssl-dev=8.18.0-1ubuntu2.4`, payload SHA-256 `997e26288998c0243109bf60b4f8c9a90b6f3613c30e58c977e4ad0a8b84b2c7`;
- `libjpeg-dev=8c-2ubuntu12`, payload SHA-256 `6606cd1c27def2b3d7290b7dff160a282bd04c4307bc94e9edfff529ad1c6c52`;
- `libjpeg8-dev=8c-2ubuntu12`, payload SHA-256 `a78cf5d66c47f957441c019ab2316a028bb14ee70fb503cc4fad35ec2ac467ff`.

These names are output evidence, not hard-coded materializer seeds. They also match the prior historical oracle 3/3.

## Immutable r3 candidate — materialized and independently validated

New slice identity: `20260829T022000Z-r3`.

r3 was generated algorithmically from immutable r2 plus the machine-derived witness set difference. It does not mutate r2 and does not contain manually appended exception names.

Materialization/publication run:

- run `33964548214`;
- 1786 binary objects (`1783 + 3`);
- binary payload bytes: `785766592` (`785219274 + 547318`);
- archive bytes: `1055590400`;
- archive SHA-256: `cb904b478afe186b96823b1b2872d5937517e3de10c6d2dd3170ec29fea09bc6`;
- release tag: `ksq-snapshot-20260829T022000Z-r3`;
- manifest SHA-256: `b683797c7850c47bcd6d80e093504301deac05e78010f6395af0885fb9ce005e`;
- manual package additions: `0`.

Independent r3 validation:

- run `33964782073`;
- artifact `9969086882`;
- digest `sha256:6fc4c3cae63f53d5484d1e5c168f51c01fb285af5697bc6f1f8438a2cb899907`;
- strict r2 extension: PASS;
- signed metadata identity: PASS;
- pre-existing 1783 payload identity: PASS;
- source-input identity: PASS;
- exact witness gap inclusion: PASS.

r3 preserves the same signed Ubuntu package universe and exact versions as r2; it changes payload completeness only.

## Required r3 regression through accepted order 65 — PASS

The r3 change was not allowed to inherit prior acceptance without proof.

Final regression run:

- run `33965237362`;
- artifact `9969240177`;
- digest `sha256:8b829f4cd81afc26c340d727561b2ea2c5438487c4e1a945ce01f1eaa940165f`;
- accepted checkpoint restored: order `65` / `295` DEBs;
- historical successful build logs examined: `65`;
- Ubuntu acquisition events: `28215`;
- unique Ubuntu package identities: `1052`;
- r3 delta intersection with all accepted 1–65 acquisitions: `0`;
- all historical required payload identities present in r3: PASS;
- KWallet solver/install replay against r3: PASS;
- KWallet selected packages: `375`;
- KWallet selection identity versus accepted r2 evidence: PASS;
- generic `mmdebstrap --mode=unshare --variant=buildd` bootstrap against r3: PASS;
- AppArmor denials: `0`;
- Docker/custom AppArmor/uidmap-filecap hacks: `0`.

This proves that a complete 1–65 source rebuild is not required solely because r3 materialized three already-advertised payloads. The existing order-65 acceptance remains valid under the explicitly proven r3 regression contract.

KWallet automatic session unlock remains **NOT CERTIFIED**; this regression does not broaden its certification scope.

## Orders 066–080 — ACCEPTED on r3

The complete local-only range and its separate fail-closed acceptance are PASS.

Source-build evidence:

- run `33973287438`;
- source HEAD `e812059c50f8f1def9a1a18489840bbee1762231`;
- artifact `9972463409`;
- digest `sha256:e1c9dccad9164a8e8445ff2487fc17d61c55816bfa3c22da385c336cca3feda5`;
- 15/15 sources PASS;
- 50 new DEBs;
- accumulated DEBs: `345`;
- packaging adaptations: `0`;
- external APT HTTP(S) during source builds: `0`;
- relevant AppArmor denials: `0`;
- Docker/custom AppArmor/uidmap-filecap hacks: `0/0/0`.

Independent acceptance:

- run `33978315934`;
- acceptance HEAD `2772d36a07722d142ed37c5fe8295d1b64d8a1d7`;
- artifact `9972976872`;
- digest `sha256:ebd60471d9834efbb4fad9f5680c6a153000aa8b9393f4821a70ff148edc2511`;
- `evidence.sha256`: PASS after independent download/extraction;
- accepted checkpoint: **order 80 / 345 DEBs**.

Order 68 `drkonqi` built normally and is included in the accepted dependency checkpoint, but its dedicated reproducibility obligation remains explicitly **NOT CERTIFIED**.

Detailed record: `docs/validation/AURORA_KSQ_1_RANGE_066_080_R3.md`.

The two earlier pre-build red runs remain classified as tooling failures: `33965423386` exposed host APT fragment leakage and `33972965871` exposed an ephemeral `build/ksq-0/canonical` assumption. Neither built a source or demonstrated a product/snapshot defect.

## Orders 081–090 — current local-only gate

Range 81–90 is active from the exact independently accepted order-80 checkpoint. Its maintained workflow consumes both the accepted-080 evidence artifact and the exact 66–80 source artifact, reconstructs the complete 345-DEB predecessor state, validates immutable r3 again and rebuilds orders 81–90 with the same local-only unshare/sbuild network-isolation contract.

Current run: `33978550975` on source HEAD `8b54e2aa98e7df0d82a09b0d840cd2163913c409`.

Order 81 `kf6-ktexteditor` may pass its normal range build without satisfying its later dedicated reproducibility requirement.

## Reproducibility contract

KSQ-1 retains the maintained `95 + 6` contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against independent reference evidence;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild proof against the final candidate.

The six dedicated nodes are:

- 29 `syntax-highlighting`;
- 68 `drkonqi`;
- 81 `kf6-ktexteditor`;
- 99 `plasma-workspace`;
- 100 `plasma-desktop`;
- 101 `powerdevil`.

A normal witness/range build PASS does not satisfy those dedicated reproducibility obligations. In particular:

`DRKONQI_REPRODUCIBILITY_CERTIFIED=no`

remains mandatory until its independent rebuild gate passes.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- Ubuntu snapshot: **20260829T022000Z / FIXED**;
- r2: **IMMUTABLE / historical / proven under-closed for universal sbuild payload service**;
- 66–101 build-context witness: **PROVEN / 36 of 36 builds SUCCESS**;
- independent witness gap analysis: **PROVEN / 3 objects / 547318 bytes**;
- r3: **IMMUTABLE CANDIDATE / MATERIALIZED / INDEPENDENTLY VALIDATED**;
- r3 accepted-065 regression: **PASS**;
- maintained accepted checkpoint: **order 80 / 345 DEBs**;
- KWallet package/install/PAM regression under r3: **PASS**;
- KWallet automatic session unlock: **NOT CERTIFIED**;
- orders 066–080: **PASS / INDEPENDENTLY ACCEPTED**;
- orders 081–090: **LOCAL-ONLY BUILD ACTIVE / NOT ACCEPTED**;
- orders 091–101: **NOT ACCEPTED**;
- DrKonqi dedicated reproducibility: **NOT CERTIFIED**;
- complete 101-source candidate: **NOT ACCEPTED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
