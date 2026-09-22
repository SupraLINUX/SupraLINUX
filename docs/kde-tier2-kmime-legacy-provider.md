# KMime legacy compatibility provider

Status: **materialization pending**

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
