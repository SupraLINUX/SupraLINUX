# KMime legacy compatibility provider

Status: **PASS**

This lane implements the compatibility side of ADR-0002 without changing the authoritative KDE Frameworks KMime package.

## Purpose

SupraLINUX KDE uses `kf6-kmime 6.30.0`, `libKF6Mime.so.6` and `KF6::Mime`.

Some Ubuntu 26.04 applications are still linked to the older PIM contract `libKPim6Mime.so.6`. The stock Resolute runtime `libkpim6mime6 25.12.3-0ubuntu1` cannot currently be installed beside SupraLINUX KF6Mime because it requires `libkmime-data (= 25.12.3-0ubuntu1)`, while `libkf6mime-data` correctly `Breaks/Replaces` that duplicate data package.

The compatibility audit proved that the runtime libraries themselves do not conflict. The only collision is the data package.

## Selected package design

SupraLINUX therefore builds a dedicated compatibility provider from the exact Ubuntu/KDE PIM source snapshot `kmime 25.12.3-0ubuntu1`.

Candidate source version:

`25.12.3-0ubuntu1+supralinux1`

The arch:any build produces exactly:

- `libkpim6mime6` — real legacy runtime, SONAME `libKPim6Mime.so.6`;
- `libkmime-dev` — legacy development contract `KPim6Mime` / `KPim6::Mime`, available on demand.

It deliberately does **not** build/publish `libkmime-data` in this lane.

The only package relationship adaptation is the runtime data dependency:

`libkmime-data (= 25.12.3-0ubuntu1) | libkf6mime-data (>= 6.30.0-0supralinux1)`

This follows the coexistence pattern already observed in current Debian packaging. It does not claim ABI equivalence between the old and new libraries.

## Reproducibility

Materialization starts from the already captured Ubuntu Resolute source reference:

- source: `kmime 25.12.3-0ubuntu1`;
- `.dsc` SHA-256: `b34f080ee832e9c22112c8e93110d6fa966d0b22d5dc62f9f84458148e970395`;
- Debian tar SHA-256: `cb97254e6d5b081d31e7aaba9e6733cbdd9866e2670edaf7a41f92e4a638a6ef`;
- orig tar SHA-256: `fce3c603cac3fec9a3f0e101c49785c32ace07b8f60b52739b638d329f43826d`.

The materializer verifies all three before changing the packaging tree.

## PASS gates

A provider PASS requires:

- deterministic source materialization from the pinned source;
- clean Ubuntu 26.04 `sbuild --no-arch-all`;
- exactly `libkpim6mime6` + `libkmime-dev`;
- no `libkmime-data` binary output;
- `libKPim6Mime.so.6` SONAME preserved;
- `libkpim6mime6-25.12` versioned Provides preserved;
- the data-provider alternative present in the runtime Depends;
- Lintian with no errors;
- installation beside SupraLINUX `libkf6mime-data/libkf6mime6/libkf6mime-dev`;
- clean `apt-get check`;
- stock `libkmime-data` absent;
- a compiled/linked `KPim6::Mime` consumer resolving `libKPim6Mime.so.6`;
- a compiled/linked `KF6::Mime` consumer still resolving `libKF6Mime.so.6`.

The provider is compatibility-only and is never part of the default desktop install. PASS only makes it eligible for the SupraLINUX testing repository. Stable promotion remains manual and requires explicit user approval.


## Validated implementation — 2026-09-22

The compatibility provider is now materially proven, not only designed.

Materialization:
- workflow run `35691309612`;
- job `106628689878`;
- source artifact `10678479790`;
- artifact SHA-256 `6fcfc4357efd8852134ab2b36b2b2509b726a6282354fb347d48b025ba0b161b`;
- resulting version `25.12.3-0ubuntu1+supralinux1`;
- generated `.dsc` SHA-256 `3a464e45ebd997e09341864e94b4a52c3e735071fb67f69562a14cddc1343360`;
- generated Debian tar SHA-256 `81df557ceea954be7036b236b8450a69a917fe6ba845af6ed29758e16e9265c7`;
- unchanged orig tar SHA-256 `fce3c603cac3fec9a3f0e101c49785c32ace07b8f60b52739b638d329f43826d`.

Clean build and validation:
- build job `106628834481`;
- build artifact `10679420779`;
- artifact SHA-256 `f77517f13eab6a282d6050cb738f78b233a9392c076a23d54131073468d2ad4b`;
- clean rootfs artifact `10679200063`, SHA-256 `e09e001bd03b1b4c1dc46184626ed6d5536e5c66f1878cf6e8ca89dca53f0040`;
- clean `sbuild`: PASS;
- Lintian error gate: PASS;
- exact arch:any output `libkpim6mime6 + libkmime-dev`: PASS;
- no `libkmime-data` output: PASS;
- real SONAME `libKPim6Mime.so.6`: PASS;
- co-installation beside KF6Mime: PASS;
- `apt-get check`: PASS;
- legacy `KPim6::Mime` consumer: PASS;
- Frameworks `KF6::Mime` consumer remains PASS.

Retained binary hashes:
- `libkmime-dev_25.12.3-0ubuntu1+supralinux1_amd64.deb`: `22aa719c769f7d89191b11d91acff58cf883e058e36b88d96fb848b55db3ffa4`;
- `libkpim6mime6_25.12.3-0ubuntu1+supralinux1_amd64.deb`: `bfb152e6d452439eddeb658ae9cde5e8cfe2ac9f2453c8b7321aabade85ea01a`;
- buildinfo SHA-256: `6237acdc6010fa8125a712d5d919ac30dbfd59c131ca8e7cf4451f191368d689`.

This provider remains **on-demand compatibility only**. It does not become part of the default KDE desktop. PASS makes it eligible for `testing`; no promotion to `stable` is authorized without explicit user approval.


## CI semantic rebuild scope

The provider clean-build workflow now distinguishes package-consumed changes from state/evidence-only changes.

A rebuild is required when:
- the pinned source, package contract or dependency adaptation changes;
- the materializer or provider build runner changes;
- the materialize/rootfs/build semantics of the workflow change.

A canonical state promotion, retained evidence update, validator change or documentation-only update does not rebuild the already validated provider. The selector is covered by a repository-policy scope test. Manual `workflow_dispatch` remains an explicit forced rebuild path.
