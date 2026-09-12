# KDE stable dependency DAG

Status: **ECM root PASS in hosted clean-package preflight; Tier 1 may begin**

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

`BLOCKED` is never counted as `FAIL`.

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
- architecture: `all`;
- current node state: **PASS** for the hosted clean-package DAG gate.

### Attempt 1 — FAIL

Commit `99b95b1c0897ed20af6c8add7aa1620ef1795019`, package `6.30.0-0supralinux1`, workflow run **34689672632**.

- artifact ID: **10296512341**;
- artifact digest: `sha256:d47ac7361106ceb5f04729c1a3dcb4103b30255684e5b3f53b833edd6d4f6558`;
- failure stage: `dh_auto_test`;
- cause: `BUILD_TESTING=OFF` removed Ninja's `test` target while debhelper still invoked `ninja test`.

### Attempt 2 — FAIL

Commit `801b99792dc60e7c14cb78d1846f9b8c9a476de8`, package `6.30.0-0supralinux2`, workflow run **34690027788**, job **103543538213**.

- artifact ID: **10296517706**;
- artifact digest: `sha256:89ef0003fd8282965a4c253bcd0150b8f040fe134ca0385d1365cd8c31808239`;
- clean sbuild binary build: PASS;
- Lintian findings: missing copyright metadata and missing Python runtime dependency;
- final failure stage: `consumer-smoke`;
- consumer cause: Qt-integrated ECM module processing could not find Qt 6 `qtpaths6` in the consumer environment.

The remediation that subsequently passed made `lintian --fail-on error` an explicit fatal gate, added the missing package metadata/runtime dependency, and installed/exposed `qtpaths6` from the selected Ubuntu Qt provider for the consumer smoke.

### Attempt 3 — PASS

Commit `cafc5aff98fd28efdc2edf889a2e0f9a73dacb48`, package `6.30.0-0supralinux3`, workflow run **34694951158**, job **103556722010**.

Evidence:

- artifact ID: **10298635300**;
- artifact digest: `sha256:181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`;
- final `result.json`: `state=PASS`, `stage=complete`, exit code `0`;
- Lintian: **PASS**;
- consumer Qt version: **6.10.2**;
- `find_package(ECM 6.30.0)`: **PASS**;
- representative ECM/KDE module inclusion and CMake generation: **PASS**;
- `downstream_eligible=yes`.

Retained SHA-256 values:

- `.deb`: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- `.changes`: `1ea11dda85d3c5e7b52d3fd82f53206ff8e0a669b16cc01b3b44e323c6c665c7`;
- `.buildinfo`: `440dc70274cd1b2660647b988b0243c935c058cf98d136929c1bee39ea542b1b`;
- `.dsc`: `b634ecc73a1c569e506a9d5d52e09a5e948854df248caba84f579ded983ffe21`;
- Debian tarball: `0256f17ee6201ffea0081804c04ab1e49611a23addfd2c64facb9d1dd41c8a83`;
- upstream/orig tarball: `22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e`;
- clean Resolute rootfs: `469407fc2d4e3e55d2f77d22ff487e66e7722d3b450c3e7b4bb6016a2f6e8b5a`.

The remediation candidate `6.30.0-0supralinux3` is therefore validated for this hosted gate. The full ECM upstream test suite remains a separate quality gate and this PASS does not claim authoritative release certification.

## Tier 1

KDE's official API index defines Tier 1 as Frameworks that depend only on Qt and possibly a small number of third-party libraries, but not on other KDE Frameworks. With ECM now PASS, independent Tier 1 nodes are eligible to be attempted in parallel after their exact Frameworks 6.30.0 tarballs, SHA-256 values and external build dependencies are resolved from upstream metadata.

The Tier 1 manifest must be derived from the current KDE upstream classification and the actual Frameworks 6.30.0 release set; no Ubuntu package version may remove or downgrade a selected upstream node.
