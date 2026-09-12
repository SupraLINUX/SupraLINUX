# KDE stable dependency DAG

Status: **ECM root PASS; Attica Tier 1 PASS; 28 Tier 1 nodes pending in hosted clean-package lane**

Last reviewed: **2026-09-12**

## Authority

KDE upstream stable defines desktop versions and dependency requirements. Ubuntu 26.04 remains the platform provider for generic build/runtime dependencies, but Ubuntu's KDE package versions do not select the SupraLINUX KDE stack.

Current selected snapshot:

- Plasma 6.7.5;
- Frameworks 6.30.0;
- Gear 26.08.1;
- Qt profile selected by Plasma: 6.10;
- Ubuntu Qt 6.10.2 baseline provider preflight: PASS; final provider certification: pending.

## DAG semantics

Each node is one of:

- `PASS`: actually built and its retained artifact may feed dependents;
- `FAIL`: actually attempted and failed for its own cause;
- `BLOCKED`: not attempted because a required predecessor is not PASS;
- `pending`: not attempted yet.

`BLOCKED` is never counted as `FAIL`. Historical failed attempts remain evidence even after a later package revision promotes a node to PASS.

A hosted node PASS proves the hosted clean-package gate for that artifact. It does not replace later authoritative KVM/JIT, runtime or compatibility gates required before candidate/stable publication.

## Node 0 — Extra CMake Modules

KDE publishes Extra CMake Modules **6.30.0** as part of KDE Frameworks 6.30.0.

Upstream authority:

- source: `https://download.kde.org/stable/frameworks/6.30/extra-cmake-modules-6.30.0.tar.xz`;
- KDE release information: `https://kde.org/info/kde-frameworks-6.30.0/`;
- upstream SHA-256: `22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e`.

Ubuntu 26.04 currently carries `extra-cmake-modules` 6.24.0-0ubuntu1. That package is a technical packaging reference only; it does not constrain the SupraLINUX version.

SupraLINUX package identity:

- source package: `kf6-extra-cmake-modules`;
- binary package: `extra-cmake-modules`;
- validated hosted package revision: `6.30.0-0supralinux3`;
- current node state: **PASS**;
- downstream eligible: yes.

### ECM attempt 1 — FAIL

Commit `99b95b1c0897ed20af6c8add7aa1620ef1795019`, package `6.30.0-0supralinux1`, workflow run `34689672632`.

- artifact ID: `10296512341`;
- artifact SHA-256: `d47ac7361106ceb5f04729c1a3dcb4103b30255684e5b3f53b833edd6d4f6558`;
- failure stage: `dh_auto_test`;
- cause: `BUILD_TESTING=OFF` removed Ninja's test target while debhelper still invoked the test phase.

### ECM attempt 2 — FAIL

Commit `801b99792dc60e7c14cb78d1846f9b8c9a476de8`, package `6.30.0-0supralinux2`, workflow run `34690027788`, job `103543538213`.

- artifact ID: `10296517706`;
- artifact SHA-256: `89ef0003fd8282965a4c253bcd0150b8f040fe134ca0385d1365cd8c31808239`;
- binary build: PASS;
- packaging-policy findings: missing copyright metadata and Python runtime dependency;
- final stage: `consumer-smoke`;
- consumer cause: the Qt-integrated consumer lacked `qtpaths6`.

The remediation made `lintian --fail-on error` fatal, added missing package/runtime metadata and supplied `qtpaths6` from the selected Ubuntu Qt provider for the consumer smoke.

### ECM attempt 3 — PASS

Commit `cafc5aff98fd28efdc2edf889a2e0f9a73dacb48`, package `6.30.0-0supralinux3`, workflow run `34694951158`, job `103556722010`.

- artifact: `10298635300`;
- artifact SHA-256: `181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`;
- result/stage: PASS / complete;
- Lintian: PASS;
- Qt consumer version: 6.10.2;
- consumer smoke: PASS;
- downstream eligible: yes;
- `.deb` SHA-256: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- `.changes`: `1ea11dda85d3c5e7b52d3fd82f53206ff8e0a669b16cc01b3b44e323c6c665c7`;
- `.buildinfo`: `440dc70274cd1b2660647b988b0243c935c058cf98d136929c1bee39ea542b1b`;
- `.dsc`: `b634ecc73a1c569e506a9d5d52e09a5e948854df248caba84f579ded983ffe21`;
- Debian tarball: `0256f17ee6201ffea0081804c04ab1e49611a23addfd2c64facb9d1dd41c8a83`;
- upstream/orig tarball: `22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e`;
- clean Resolute rootfs: `469407fc2d4e3e55d2f77d22ff487e66e7722d3b450c3e7b4bb6016a2f6e8b5a`.

The ECM hosted package preflight does not claim the full upstream test suite; that remains a separate quality gate. This PASS is also not authoritative release certification.

## Tier 1 node — Attica

Attica depends on the PASS ECM root and no KDE Framework. It is the first actual Tier 1 package completed in the hosted lane.

Upstream:

- version: `6.30.0`;
- source SHA-256: `3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c`;
- required Qt: Core/Network >=6.9.0;
- SOVERSION: 6.

Package identity:

- source: `kf6-attica`;
- binaries: `libkf6attica6`, `libkf6attica-dev`, `libkf6attica-doc`;
- validated revision: `6.30.0-0supralinux2`;
- predecessor: `extra-cmake-modules 6.30.0-0supralinux3`;
- current hosted state: **PASS**;
- downstream eligible: yes.

### Attica attempt 1 — FAIL

- commit `c18c8dcd1934a5bba874e642ba9b14729d2e69df`;
- package `6.30.0-0supralinux1`;
- run `34705165994`;
- artifact `10300903114`;
- artifact SHA-256 `171cfe8553aba2af8f42a640ee5f50f82988005edbd104b737d93b639dc38300`;
- stage `source-package`;
- cause: `dpkg-buildpackage -S` executed build helpers on the host before clean `sbuild`.

### Attica attempt 2 — PASS

- commit `9945bfa92d776d432c76e17516b0ff9452b6d159`;
- package `6.30.0-0supralinux2`;
- run `34706416753`;
- artifact `10301851297`;
- artifact SHA-256 `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`;
- source assembly: `dpkg-source -b`;
- clean Resolute `sbuild`: PASS;
- tests: **6/6 PASS**;
- Lintian error gate: PASS;
- ABI SONAME: `libKF6Attica.so.6`;
- CMake consumer build/run: PASS;
- `.buildinfo` predecessor proof: ECM `6.30.0-0supralinux3`;
- downstream eligible: yes.

Retained Attica hashes include runtime `.deb` `5f52b2ce38c6dc1ad884d16e9d616c781b098a0445a68485d24087c4572d86de`, development `.deb` `884e917a29b9618000621029d0dd42c00d4f2e1c925aa03cbf905978b82f0a4b`, documentation `.deb` `30bb8e97a2a087809a1ca6d017f6beb8dcee5933d416d958c555033020d77a83`, `.buildinfo` `5e10c1f72d07f6f61beff17e3ed3f0cf0254016d23d8c2bd0d1dec9c983bd5f4` and rootfs `37cef66de0b97f406f0fb59be51d7cbb221b68936db998b5e5a91804cbe97763`.

## Remaining Tier 1

The other 28 Tier 1 nodes have source/dependency/provider/reference metadata resolved but no real package attempt yet. They remain `pending`, not FAIL and not BLOCKED.

Because Tier 1 nodes do not depend on one another, prepared nodes should run in parallel while consuming the retained ECM PASS artifact. An independent FAIL must not stop unrelated nodes.

## Next DAG expansion

Generalize the proven Attica package path into reusable hosted Tier 1 infrastructure while retaining package-specific binary contracts, symbols/ABI policy, test exclusions and consumer smokes. Then launch a batch of independent Tier 1 nodes in parallel.

The authoritative KVM/JIT lane remains required before final package promotion to candidate/stable.
