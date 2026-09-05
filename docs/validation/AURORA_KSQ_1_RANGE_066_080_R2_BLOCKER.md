# Aurora KSQ-1 — range 066–080 r2 blocker

Status: **HISTORICAL BLOCKER / ROOT CAUSE PROVEN / CORRECTIVE r3 MATERIALIZED**

This record captures the proven r2 failure and its corrective closure. It does not by itself accept any source in orders 66–80.

## Causal run

- workflow: `.github/workflows/ksq-native-range-066-080-r2.yml`
- run: `33821750759`
- artifact: `9919609367`
- artifact digest: `sha256:e04615715fcee3450c14db3f1a7085d09cd937c7db8d2520c0bff49f60546998`
- prior accepted checkpoint: order 65 / 295 accumulated DEBs
- run result: **FAIL**

The runner, exact 001–065 checkpoint chain, independent order-65/KWallet acceptance artifact, canonical r2 slice and clean native buildd recreation all passed before source building began.

## Build result

The run produced successful source builds for orders 66–73:

- 66 `kf6-kxmlgui`
- 67 `kf6-kio`
- 68 `drkonqi`
- 69 `kf6-baloo`
- 70 `kf6-kcmutils`
- 71 `kf6-knotifyconfig`
- 72 `kf6-kparts`
- 73 `kglobalacceld`

These eight successful builds are **partial evidence inside a failed range**, not an accepted checkpoint. DrKonqi order 68 is not reproducibility certification.

The first causal failure is:

- order: `74`
- source: `xdg-desktop-portal-kde`
- packaging base: `6.7.4-0ubuntu1`
- `sbuild` exit: `3`
- completed prior order: `73`
- new DEBs before failure: `27`
- accumulated DEBs before failure: `322`

## Proven failure mechanism

`xdg-desktop-portal-kde` Build-Depends contains `libcups2-dev`.

During the real `sbuild 0.91.2ubuntu3` APT dependency installation, APT selected the following Resolute packages among the transitive build dependency closure:

- `libjpeg-turbo8-dev=2.1.5-4ubuntu4`
- `libjpeg8-dev=8c-2ubuntu12`
- `libjpeg-dev=8c-2ubuntu12`

The r2 repository metadata advertises all of them, but its materialized pool contains `libjpeg-turbo8-dev` and does not contain the two selected `libjpeg8-empty` development payloads:

- `pool/main/libj/libjpeg8-empty/libjpeg8-dev_8c-2ubuntu12_amd64.deb`
- `pool/main/libj/libjpeg8-empty/libjpeg-dev_8c-2ubuntu12_amd64.deb`

The real build therefore fails while fetching from the local-only r2 archive with `File not found`; there is no external network fallback.

The historical r2 closure-generation evidence (`9883249125`) contains 1783 selected binary objects and includes only `pool/main/libj/libjpeg8-empty/libjpeg8_8c-2ubuntu12_amd64.deb` from `libjpeg8-empty`. Its `binary-print-uris.txt` includes `libjpeg-turbo8-dev` but not `libjpeg8-dev` or `libjpeg-dev`.

Thus the demonstrated defect is **not an unsatisfied KDE Build-Depends relation**. It is a mismatch between the full signed APT metadata exposed by r2 and the subset of payload objects chosen by the r2 closure-generation transaction.

## Root-cause A/B proof

Controlled run `33862761542` on Ubuntu 26.04.1 / APT `3.2.0` reproduced the exact historical r2 input artifact `9883249125` by its immutable ZIP SHA-256 and resolved the same pinned Ubuntu snapshot `20260829T022000Z` under normal/default Recommends semantics.

Artifact:

- ID `9933323436`;
- digest `sha256:4cdc54e59e77238cfc9d8c9c238e8dc947fb531241dcb43a3263f6278db7f987`.

The probe compared three contexts:

1. the original r2 direct multi-root transaction containing all 244 certified Ubuntu binary/version seeds plus the baseline roots;
2. direct installation of `libcups2-dev=2.4.16-1ubuntu1.3` in an otherwise empty dpkg state;
3. installation of an sbuild-style local dependency dummy whose `Depends` is exactly `libcups2-dev (= 2.4.16-1ubuntu1.3)`.

Observed provider selection:

| Context | `libjpeg-turbo8-dev` | `libjpeg8-dev` | `libjpeg-dev` |
|---|---|---|---|
| global 244-seed direct transaction | yes | no | no |
| isolated `libcups2-dev` direct transaction | yes | yes | yes |
| isolated sbuild-style dummy | yes | yes | yes |

This closes the causal question. The sbuild dummy representation is **not** what introduces the missing JPEG packages: direct isolated `libcups2-dev` produces the same three-package selection. The under-closure is caused by collapsing the Build-Depends requirements of many independent source builds into one aggregate APT transaction. Other roots present in that aggregate transaction change provider/transition-package decisions and allow APT to omit payloads that are selected when a particular source build is resolved in its real per-build context.

Therefore the r2 generation algorithm is not a valid proof that its payload subset is a superset of all 101 real source-build dependency transactions, even though the aggregate transaction itself is internally satisfiable.

A second minimal probe, run `33864043456`, did not reach dependency resolution because its independent snapshot metadata refresh hit transient HTTP `520/522` transport failures. It supplies no contradictory dependency result and is not used as causal evidence.

## Historical regression oracle

The old non-maintained full-DAG run `33281736655` is not accepted as current qualification evidence. It is useful only as an independent regression oracle because its completed source builds used the same fixed snapshot and real sbuild dependency resolver.

Across the available successful build logs through order 98, after normalizing Debian epochs in APT cache filenames, exactly three Ubuntu payloads observed by real build contexts are absent from r2:

- `libjpeg8-dev_8c-2ubuntu12_amd64.deb`;
- `libjpeg-dev_8c-2ubuntu12_amd64.deb`;
- `libcurl4-openssl-dev_8.18.0-1ubuntu2.4_amd64.deb`.

This was **not** treated as a package-addition prescription. Because the historical run did not provide complete valid build logs through 101, current qualification extended the proof with a new real build-context witness through order 101.

## Corrective build-context witness — completed

The replacement-closure input was derived from the union of real per-build dependency-resolution contexts while preserving:

- Ubuntu snapshot `20260829T022000Z`;
- APT/sbuild semantics qualified on Ubuntu 26.04;
- normal/default Recommends policy;
- generic `amd64`;
- exact accepted Supra binary checkpoint through order 65;
- real sbuild source-build contexts;
- signed Ubuntu metadata as the authority mapping package/version/architecture to `Filename`, `Size` and `SHA256`.

Witness parent run `33929720702` completed all source builds 66–101 successfully: **36/36 PASS**. The parent conclusion is red only because its obsolete embedded analyzer failed after the builds; the three build artifacts were subsequently consumed by an independent explicit analysis.

Authoritative analyzer:

- run `33962296018`;
- artifact `9968317241`;
- digest `sha256:b7db4224c5bd7cd89f6e274cb8a0c617327bc917cee1185cff9e0b2a07ea0694`;
- witness status: `PROVEN`;
- observed package objects: `1114`;
- r2 objects: `1783`;
- exact set difference: **3 objects / 547318 bytes**;
- manual package additions: `0`.

The resulting complete gap is exactly the three objects previously seen by the historical oracle, now including current coverage through orders 99–101. The agreement is 3/3, but the authoritative input is the machine-derived current witness result.

## r3 corrective slice — completed

The corrective slice has a new immutable identity:

`20260829T022000Z-r3`

It was generated algorithmically from immutable r2 plus the proven witness set difference. No filename exception list was inserted into the materializer.

Materialization/publication:

- run `33964548214`;
- 1786 binary objects;
- binary payload bytes: `785766592`;
- archive bytes: `1055590400`;
- archive SHA-256: `cb904b478afe186b96823b1b2872d5937517e3de10c6d2dd3170ec29fea09bc6`;
- tag: `ksq-snapshot-20260829T022000Z-r3`;
- manifest SHA-256: `b683797c7850c47bcd6d80e093504301deac05e78010f6395af0885fb9ce005e`;
- manual package additions: `0`.

Independent validation:

- run `33964782073`;
- artifact `9969086882`;
- digest `sha256:6fc4c3cae63f53d5484d1e5c168f51c01fb285af5697bc6f1f8438a2cb899907`;
- strict r2 extension: PASS;
- signed metadata identity: PASS;
- all 1783 pre-existing payload identities: PASS;
- source-input identity: PASS;
- exact witness-gap inclusion: PASS.

r2 remains immutable. r3 is a distinct candidate slice.

## Regression caused by r3 — completed through accepted order 65

Because r3 changes payload availability, prior acceptance was not carried forward by assertion.

Regression run `33965237362`, artifact `9969240177`, digest `sha256:8b829f4cd81afc26c340d727561b2ea2c5438487c4e1a945ce01f1eaa940165f`, proves:

- exact checkpoint 1–65 / 295 DEBs restored;
- 65 successful historical build logs inspected;
- 28215 Ubuntu acquisition events / 1052 unique Ubuntu identities;
- intersection between all accepted 1–65 acquisitions and the three newly materialized r3 objects: `0`;
- every historical payload identity still present in r3;
- KWallet solver/install replay against r3: PASS;
- KWallet exact 375-package selection identity: PASS;
- generic buildd bootstrap against r3: PASS;
- AppArmor denials: `0`;
- Docker/custom AppArmor/uidmap-filecap hacks: `0`.

KWallet automatic runtime session unlock remains **NOT CERTIFIED**.

## Current use of this blocker record

The r2 blocker itself is closed as a causal investigation. It remains historical evidence explaining why r2 cannot be used as the universal 101-source payload service.

It does **not** certify 66–80. The maintained path has moved to r3 and must still pass the real local-only range plus independent acceptance.

The current r3 local-only 66–80 run is `33973287438` on source HEAD `e812059c50f8f1def9a1a18489840bbee1762231`. Before entering source compilation it had already passed exact r3 validation provenance, accepted-065 r3 regression provenance, checkpoint restore, r3 release validation and clean local-only APT/buildd preparation. Its source-build result is intentionally not recorded as PASS here until that run and independent acceptance finish.

## Gate state

- accepted KSQ-1 checkpoint: **order 65 / 295 DEBs**;
- r2 root cause: **PROVEN / CLOSED**;
- build-context witness 66–101: **PROVEN / 36 of 36 source builds SUCCESS**;
- witness set difference: **3 objects / 547318 bytes**;
- r3: **MATERIALIZED / INDEPENDENTLY VALIDATED / DISTINCT IMMUTABLE IDENTITY**;
- accepted-065 regression against r3: **PASS**;
- orders 66–80: **LOCAL-ONLY r3 GATE ACTIVE / NOT ACCEPTED**;
- orders 81–101: **NOT ACCEPTED**;
- DrKonqi dedicated reproducibility: **NOT CERTIFIED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
