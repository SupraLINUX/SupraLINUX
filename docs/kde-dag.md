# KDE stable dependency DAG

Status: **ECM root attempted; current state FAIL; remediation 6.30.0-0supralinux3 pending validation**

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
- current remediation candidate: `6.30.0-0supralinux3`;
- architecture: `all`;
- current node state: **FAIL** until the remediation is actually rebuilt and passes.

### Attempt 1 — FAIL

Commit `99b95b1c0897ed20af6c8add7aa1620ef1795019`, package `6.30.0-0supralinux1`, workflow run **34689672632**.

- artifact ID: **10296512341**;
- artifact digest: `sha256:d47ac7361106ceb5f04729c1a3dcb4103b30255684e5b3f53b833edd6d4f6558`;
- verified KDE source, Debian source package and clean configure/build: PASS;
- failure stage: `dh_auto_test`;
- cause: `BUILD_TESTING=OFF` removed Ninja's `test` target while debhelper still invoked `ninja test`.

The remediation explicitly overrides `dh_auto_test` for this package-preflight profile and aligns the reusable sbuild rootfs with `${HOME}/.cache/sbuild/resolute-amd64.tar`.

### Attempt 2 — FAIL

Commit `801b99792dc60e7c14cb78d1846f9b8c9a476de8`, package `6.30.0-0supralinux2`, workflow run **34690027788**, job **103543538213**.

- artifact ID: **10296517706**;
- artifact digest: `sha256:89ef0003fd8282965a4c253bcd0150b8f040fe134ca0385d1365cd8c31808239`;
- clean sbuild binary build: PASS;
- attempt-1 `dh_auto_test` defect: resolved;
- Lintian findings: `no-copyright-file`, `python3-script-but-no-python3-dep`, and source warning `no-debian-copyright-in-source`;
- final `result.json` failure stage: `consumer-smoke`;
- consumer cause: `KDEInstallDirs6` reached `ECMQueryQt.cmake`, which could not find a Qt 6 `qtpaths` executable in the test environment.

The build itself was successful; the node nevertheless remains FAIL because packaging policy and the required downstream consumer gate did not both pass.

### Remediation candidate — 6.30.0-0supralinux3

This revision:

1. adds Debian copyright metadata for the upstream BSD-3-Clause/BSD-2-Clause/MIT aggregate license set;
2. declares `python3:any` for installed Python helper scripts;
3. makes a separate `lintian --fail-on error` invocation mandatory, so packaging errors cannot be hidden behind a successful sbuild status;
4. provides Ubuntu `qt6-base-dev`/`qtpaths6` to the Qt-integrated consumer environment and records the Qt version/path;
5. captures `.deb`, `.changes`, `.buildinfo`, package metadata and hashes before post-build gates so any later FAIL remains inspectable.

This hosted package preflight does **not** claim that the full ECM upstream test suite has run. The upstream test suite remains a separate quality gate before stable/production certification.

## Next nodes

Frameworks Tier 1 remains unattempted while ECM is FAIL. Only after `6.30.0-0supralinux3` actually produces a PASS artifact may that artifact feed the next topological level. Independent Tier 1 nodes can then run in parallel according to the upstream-derived DAG.
