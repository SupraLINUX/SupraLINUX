# KDE Frameworks 6.30 — Attica packaging

Status: **hosted clean-package PASS; downstream eligible; authoritative release certification pending**  
Last reviewed: **2026-09-12**

## Scope and authority

`attica` is the first KDE Frameworks 6.30 Tier 1 node with a real SupraLINUX package PASS. KDE upstream `v6.30.0` remains authoritative for source, build requirements and defaults.

Pinned upstream source:

- URL: `https://download.kde.org/stable/frameworks/6.30/attica-6.30.0.tar.xz`;
- SHA-256: `3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c`;
- root CMake blob: `92ae57c6bf82a8fad6c412b5b47a8c45a8652d88`;
- Qt minimum: `6.9.0`;
- selected Resolute Qt provider exercised by this build: Qt 6.10.2;
- library SOVERSION: `6`.

This PASS is a GitHub-hosted clean-package DAG preflight. It is sufficient to feed hosted downstream work, but it is **not** the authoritative KVM/JIT release certification.

## Reference evidence

The Debian-family packaging tree reference remains technical input only:

- workflow run: `34704689773`;
- artifact: `10301617541`;
- artifact SHA-256: `ce9e9949f643736f25ec27d2850cb0654334b64a28dfcd293df78ae1b1f60407`;
- Ubuntu Resolute reference: `kf6-attica 6.24.0-0ubuntu1`;
- Debian sid reference: `kf6-attica 6.28.0-1`;
- Ubuntu symbols baseline SHA-256: `e67d131171c8e3ea79c6bbbb2434aa2492580d19ba7dccdaa7038766cd9827ad`.

The selected SupraLINUX package remains KDE Attica **6.30.0**, not either distro version.

## Preserved package contract

SupraLINUX preserves the established Debian-family binary split and structural contracts:

- `libkf6attica6` — runtime library, `Architecture: any`, `Multi-Arch: same`;
- `libkf6attica-dev` — exact-version dependency on `libkf6attica6`, Qt base development dependency, exact-version recommendation on documentation;
- `libkf6attica-doc` — `Architecture: all`, `Multi-Arch: foreign`;
- no `Provides`, `Breaks`, `Replaces` or `Conflicts` are introduced.

Direct Build-Depends are justified from Attica 6.30/default packaging mechanics: debhelper 13, `dh-sequence-kf6`, `dh-sequence-pkgkde-symbolshelper`, CMake >=3.29, ECM >=6.30.0, Qt base >=6.9.0, Python 3 and REUSE. Older distro-only dependencies are not copied merely because they appeared in reference packaging.

## Tests and deterministic build profile

`BUILD_TESTING=ON` and `SKIP_LICENSE_TESTS=OFF` remain enabled.

The only upstream test disabled is `providertest.cpp`, because Attica 6.30 still performs live requests to `https://autoconfig.kde.org/ocs/providers.xml`. This is a reproducibility/integration patch, not a KDE feature substitution.

The validated build executed **6/6 tests successfully** inside the clean Resolute `sbuild` environment.

## QDoc compatibility package

Attica 6.30 uses `ECMGenerateQDoc`, whose current documentation targets are explicit and are not part of the normal package build. SupraLINUX therefore does not carry the obsolete/inert `BUILD_QCH=ON` assumption from older packaging.

`libkf6attica-doc` is retained for package-contract compatibility. In this build it remains a documentation stub and Lintian reports the warning `empty-binary-package`. The package gate uses `lintian --fail-on error`; there were **no Lintian errors**. A project-wide Frameworks QDoc policy remains separate future work.

## ECM predecessor

The Attica build consumed the retained SupraLINUX ECM PASS package, not Ubuntu's older ECM:

- `extra-cmake-modules 6.30.0-0supralinux3`;
- ECM run: `34694951158`;
- ECM artifact: `10298635300`;
- ECM artifact SHA-256: `181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`;
- ECM `.deb` SHA-256: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`.

The successful Attica `.buildinfo` explicitly contains `extra-cmake-modules (= 6.30.0-0supralinux3)`.

## Attempt 1 — FAIL

Commit `c18c8dcd1934a5bba874e642ba9b14729d2e69df` attempted `6.30.0-0supralinux1`.

- workflow run: `34705165994`;
- artifact: `10300903114`;
- artifact SHA-256: `171cfe8553aba2af8f42a640ee5f50f82988005edbd104b737d93b639dc38300`;
- failure stage: `source-package`.

Cause: `dpkg-buildpackage -S` executed `debian/rules clean` on the GitHub host and attempted to load `dh-sequence-kf6` before entering the clean build environment. The failure was correctly retained as a real Attica/pipeline FAIL; it was not a Qt, KDE upstream, ECM or ABI failure.

## Attempt 2 — PASS

Commit `9945bfa92d776d432c76e17516b0ff9452b6d159` attempted `6.30.0-0supralinux2` after changing source-package assembly to `dpkg-source -b`, keeping build helpers inside `sbuild`.

Evidence:

- workflow run: `34706416753`;
- artifact: `10301851297`;
- artifact SHA-256: `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`;
- final state/stage: `PASS` / `complete`;
- tests: **6/6 PASS**;
- Lintian error gate: **PASS**;
- consumer smoke: **PASS**;
- ABI SONAME: `libKF6Attica.so.6`;
- downstream eligibility: **yes**.

Retained hashes:

- `libkf6attica6_6.30.0-0supralinux2_amd64.deb`: `5f52b2ce38c6dc1ad884d16e9d616c781b098a0445a68485d24087c4572d86de`;
- `libkf6attica-dev_6.30.0-0supralinux2_amd64.deb`: `884e917a29b9618000621029d0dd42c00d4f2e1c925aa03cbf905978b82f0a4b`;
- `libkf6attica-doc_6.30.0-0supralinux2_all.deb`: `30bb8e97a2a087809a1ca6d017f6beb8dcee5933d416d958c555033020d77a83`;
- `.changes`: `859b76c5cd99a7c949071098e44ae43943e8619a7174c120cfe2a1cf4ebc428e`;
- `.buildinfo`: `5e10c1f72d07f6f61beff17e3ed3f0cf0254016d23d8c2bd0d1dec9c983bd5f4`;
- `.dsc`: `25a0a2993787329d3ceae7a6485c9134605a3a188aed492bbc073ec5d5edbc72`;
- Debian tarball: `0fcfabd68df435228170d657754641259c92d75147e00925c5d4766eeb105aa0`;
- upstream/orig tarball: `3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c`;
- clean Resolute rootfs: `37cef66de0b97f406f0fb59be51d7cbb221b68936db998b5e5a91804cbe97763`.

The consumer CMake project found `KF6Attica 6.30.0`, linked against the produced `libKF6Attica.so.6.30.0` plus Ubuntu Qt 6.10.2, and executed successfully.

## CI event-delta scope

Attica's package-build and distro-reference workflows no longer use PR-wide `paths:` filtering as the decision for expensive work. On `pull_request/synchronize`, each workflow compares the exact event `before..after` delta after a full-history checkout.

The package build runs only when its actual inputs change: `packages/kde/attica/**`, the package runner, its scope helper or its workflow. The packaging-reference capture is independently scoped to its capture runner, scope helper and workflow. Documentation and machine-readable evidence/state changes therefore do not by themselves recreate the Resolute rootfs, download predecessor artifacts, execute `sbuild`, or recapture unchanged distro reference trees.

Repository Policy validates these scope invariants with `scripts/validate_kde_attica_ci_scope.py`. An intentional scope miss exits with the dedicated skip state and the workflow reports the skip instead of presenting it as a build failure.

## Current state

`attica` is now:

- package revision: `6.30.0-0supralinux2`;
- hosted DAG state: **PASS**;
- downstream eligible: **yes**;
- final authoritative release certification: **pending**.

The other 28 Tier 1 Frameworks remain `pending`; they are neither FAIL nor BLOCKED.

## Next gate

Generalize the proven ECM → Framework package path into the Tier 1 campaign and begin preparing/attempting the remaining independent Tier 1 nodes in parallel. Every node must retain its own source, package, ABI/policy/test and consumer evidence and must consume only PASS predecessors.
