# Aurora KSQ-1 — range 066–080 r2 blocker

Status: **BLOCKED / ROOT CAUSE PROVEN**

This record captures the proven state after the first maintained native attempt to build orders 66–80. It does not accept any part of the range as a checkpoint.

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

The canonical r2 repository metadata advertises all of them, but its materialized pool contains `libjpeg-turbo8-dev` and does not contain the two selected `libjpeg8-empty` development payloads:

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

This is **not** a package-addition prescription. The historical run did not complete orders 99–101, and current qualification must derive the complete requirement from current real build contexts rather than append this observed list manually.

## Corrective design boundary

No package is being added manually and `xdg-desktop-portal-kde` is not being patched.

The replacement closure must be generated from the union of real per-build dependency-resolution contexts, preserving:

- Ubuntu snapshot `20260829T022000Z`;
- APT `3.2.0` / sbuild `0.91.2ubuntu3` semantics qualified on the selected Ubuntu 26.04 runner;
- normal/default Recommends policy;
- architecture `amd64` with architecture variants disabled;
- exact accepted Supra binary checkpoints as they become available in DAG order;
- `--no-enable-network` for the package build itself while allowing the dependency resolver, only in the non-acceptance witness phase, to retrieve from the pinned Ubuntu snapshot;
- signed Ubuntu metadata as the authority mapping each observed package/version/architecture to its exact `Filename`, `Size` and `SHA256`.

The active corrective step is therefore a current **build-context witness** for orders 66–101 starting from the accepted order-65 / 295-DEB checkpoint. Its output will be compared against the 1783 r2 objects. Only the complete set difference produced by that algorithm may be materialized into a new immutable slice identity.

A replacement slice is not accepted merely because its witness set closes the observed gap. It must be independently materialized/validated and then re-run through the required local-only regression chain before the maintained checkpoint can advance.

## Gate state

- accepted KSQ-1 checkpoint remains: **order 65 / 295 DEBs**;
- orders 66–80: **NOT ACCEPTED**;
- orders 81–101: **NOT ACCEPTED**;
- r2: remains immutable historical/canonical input for the accepted-through-65 evidence, but is proven insufficient as a general payload closure for continuing the 101-source build;
- r2 aggregate-closure root cause: **PROVEN**;
- replacement build-context witness: **ACTIVE**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.

Any replacement build slice is a new immutable identity and triggers the required downstream regression before earlier PASS evidence may be carried forward.
