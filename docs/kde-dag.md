# KDE stable dependency DAG

Status: **implementation started; first node pending CI**

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

SupraLINUX packaging target:

- source package: `kf6-extra-cmake-modules`;
- binary package: `extra-cmake-modules`;
- version: `6.30.0-0supralinux1`;
- architecture: `all`;
- current node state: **pending**.

The hosted preflight must:

1. download the KDE upstream tarball;
2. verify the exact KDE-published SHA-256 before extraction;
3. create a Debian `3.0 (quilt)` source package;
4. build it in a fresh Ubuntu 26.04 `sbuild/unshare` rootfs;
5. retain `.deb`, `.changes`, `.buildinfo`, source hashes and rootfs hash;
6. inspect binary metadata;
7. extract the resulting `.deb` without installing it globally;
8. configure a downstream CMake consumer with `find_package(ECM 6.30.0)` and representative KDE/ECM modules;
9. mark the artifact `downstream_eligible=yes` only after all prior stages PASS.

The hosted lane is non-authoritative, but a PASS artifact is valid input for subsequent hosted DAG discovery. Authoritative package/system-test evidence still requires the KVM/JIT infrastructure described by Phase 1.

## Next nodes

After ECM PASS, Frameworks nodes will be added by dependency tier from actual KDE upstream CMake requirements. Independent nodes in the same topological level should build in parallel. A failed node blocks only its dependents; unrelated branches continue.
