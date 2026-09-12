# KDE stable dependency DAG

Status: **ECM root attempted; current state FAIL; remediation pending validation**

Last reviewed: **2026-09-12**

## Authority

KDE upstream stable defines the desktop versions and dependency requirements. Ubuntu 26.04 remains the platform provider for generic build/runtime dependencies, but Ubuntu's KDE package versions do not select the SupraLINUX KDE stack.

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

`extra-cmake-modules` is the build-system root for the selected Frameworks line. KDE publishes Extra CMake Modules **6.30.0** as part of KDE Frameworks 6.30.0.

Upstream authority:

- source: `https://download.kde.org/stable/frameworks/6.30/extra-cmake-modules-6.30.0.tar.xz`;
- KDE release information: `https://kde.org/info/kde-frameworks-6.30.0/`;
- upstream SHA-256: `22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e`.

Ubuntu 26.04 currently carries `extra-cmake-modules` 6.24.0-0ubuntu1. That package is a technical packaging reference only; it does not constrain the SupraLINUX version.

SupraLINUX package identity:

- source package: `kf6-extra-cmake-modules`;
- binary package: `extra-cmake-modules`;
- current remediation candidate: `6.30.0-0supralinux2`;
- architecture: `all`;
- current node state: **FAIL** until the remediation is actually rebuilt and passes.

### Attempt 1 — FAIL

Commit `99b95b1c0897ed20af6c8add7aa1620ef1795019` attempted `6.30.0-0supralinux1` in workflow run **34689672632**.

Evidence artifact:

- artifact ID: **10296512341**;
- artifact digest: `sha256:d47ac7361106ceb5f04729c1a3dcb4103b30255684e5b3f53b833edd6d4f6558`.

What passed before the failure:

- KDE upstream tarball download: PASS;
- exact KDE-published source SHA-256 verification: PASS;
- Debian source-package creation: PASS;
- clean Ubuntu 26.04 build environment preparation: PASS;
- CMake configure: PASS;
- Ninja build: PASS (`ninja: no work to do`, expected for this module-only package).

Actual root cause:

- package configuration deliberately used `BUILD_TESTING=OFF`;
- that means the generated Ninja build does not contain a `test` target;
- debhelper still executed `dh_auto_test`, which called `ninja test`;
- Ninja failed with `unknown target 'test'`;
- therefore the node is **FAIL at `dh_auto_test` by packaging integration**, not an ECM source, compiler, Qt or dependency failure.

A second non-causal issue was observed: the preflight generated `resolute-amd64-kde-ecm.tar.gz`, while `sbuild --chroot-mode=unshare` searches its cache for `resolute-amd64.tar`; consequently sbuild generated another rootfs instead of reusing ours.

### Remediation candidate — 6.30.0-0supralinux2

The next package revision makes the evidence unambiguous rather than rebuilding different packaging under the same Debian version.

Changes pending validation:

1. `override_dh_auto_test` explicitly does not invoke a nonexistent test target when the package-preflight profile sets `BUILD_TESTING=OFF`;
2. the post-build downstream consumer smoke remains mandatory and still has to resolve `find_package(ECM 6.30.0)` plus representative ECM/KDE modules from the produced `.deb`;
3. the reusable rootfs is generated as `${HOME}/.cache/sbuild/resolute-amd64.tar` with tar format, matching the cache convention reported by `sbuild/unshare`;
4. rootfs/source/artifact hashes continue to be retained.

This hosted package preflight does **not** claim that the full ECM upstream test suite has run. Upstream tests are a separate quality gate to add before production/stable certification. The current node PASS criterion is narrower: verified source + clean package build + Debian metadata + downstream consumer smoke, sufficient to feed subsequent hosted DAG discovery.

## Next nodes

KDE Frameworks Tier 1 contains nodes with no compile-time dependency on another Framework, so they can later be built in parallel using ECM and the Qt/provider baseline. They remain unattempted while ECM is FAIL; they are not mislabeled as FAIL.

Only after the ECM remediation actually produces a PASS artifact will that artifact become eligible to feed Tier 1.
