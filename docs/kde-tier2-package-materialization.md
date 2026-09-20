# KDE Tier 2 package materialization

Status: **first five package contracts materialized; clean builds pending**  
Date: **2026-09-20**

The package tree is generated, not copied manually. The source side is always the official **KDE upstream** Frameworks 6.30.0 tarball verified against the canonical SHA-256. The Debian `debian.tar.xz` is downloaded at its exact pinned 6.30.0-1 version and SHA-256 and is used only as a technical packaging reference.

This deliberately separates authority from provider/reference. The Debian orig tarball is never the source authority; for Syndication it is explicitly rejected because its hash differs from KDE's official source.

The deterministic SupraLINUX overlay:

- changes the source-package revision to `6.30.0-0supralinux1`;
- marks the CI-only maintainer as `SupraLINUX Build System <build@supralinux.invalid>` and preserves the original Debian maintainer separately;
- records the SupraLINUX repository as the packaging VCS;
- passes the selected Linux CMake profile explicitly;
- changes Debian's `BUILD_PYTHON_BINDINGS=OFF` reference behavior to `BUILD_PYTHON_BINDINGS=ON` where KDE upstream enables it;
- adds Python binary splits for KNotifications, KStatusNotifierItem and KUnitConversion;
- retains Debian symbols/install metadata as a technical baseline to be verified by the real build.

The `.invalid` maintainer address is intentionally non-routable. Replacing it with an approved project contact is a publication blocker, not a build blocker.

Materialization runs `dpkg-source -b`, records content-based full-tree and `debian/` tree digests, and uploads the generated source package. A materialization PASS is **not a package PASS**: no clean binary build has happened and package state remains pending.


## Materialization PASS evidence

Run `35527533481` completed **5/5 PASS** for KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication. Each artifact contains the authoritative KDE orig tarball, generated SupraLINUX `.dsc` / `.debian.tar.xz`, full-tree digest and Debian-tree digest.

This promotion changes readiness from `package-contract-ready` to `build-ready`. It does **not** change package state: all five remain `pending` and `package_attempted=false`.

The campaign build queue is now these five nodes. A package PASS requires the next clean sbuild/test/Lintian/ABI/runtime/consumer stage.


## Resolute release target and Shiboken provider

Materialization explicitly writes the new SupraLINUX changelog entry for distribution `resolute`; generated package trees must not use `UNRELEASED` for clean-build candidates because that fails the Lintian error gate.

When a selected Framework keeps KDE upstream Python bindings enabled, the materializer also adds `llvm-dev` as the Ubuntu Resolute build-tool provider. Its purpose is to expose the default LLVM/Clang discovery surface, including `/usr/bin/llvm-config`, to Shiboken ApiExtractor. This is provider plumbing only: `BUILD_PYTHON_BINDINGS=ON` remains a KDE-owned profile decision.
