# supralinux-desktop

Development metapackage for the **SupraLINUX 1.x - Aurora** KDE Plasma baseline.

## Purpose

This package declares the Plasma desktop and integration components that SupraLINUX intends to guarantee as part of the base desktop experience. It deliberately does **not** depend on `kubuntu-desktop`.

The dependency set is built from the project rule:

> If a Plasma feature is exposed in the shipped desktop, its frontend, backend, dependencies, permissions, session integration, and tests must be present.

## Status

`0.1.0~dev1` is a development candidate only. It is not the SupraLINUX 1.0.0 release package and its dependency list is not frozen.

Current process:

1. Audit Ubuntu 26.04 Plasma/KWin/System Settings packages.
2. Map visible features to backends and dependencies.
3. Build this metapackage.
4. Install it on a clean Ubuntu 26.04 base.
5. Boot Plasma Wayland.
6. Record every missing or broken surface.
7. Correct dependencies/integration and repeat.

See:

- `docs/PLASMA_PACKAGE_AUDIT.md`
- `docs/PLASMA_INTEGRATION_MATRIX.md`
- `PROJECT_RULES.md`

## Packaging validation

The current Debian source layout parses successfully as a native `3.0 (native)` source package. A full binary build and dependency-install test must be performed in the clean Ubuntu 26.04 test environment before the package is considered usable.

`debian/rules` is intentionally stored executable, as required by normal Debian package tooling.
