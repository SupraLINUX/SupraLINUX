# KDE Frameworks 6.30 — Attica packaging

Status: **packaging reference-tree capture pending; SupraLINUX package implementation pending**  
Last reviewed: **2026-09-12**

## Scope

`attica` is the first KDE Frameworks 6.30 Tier 1 node selected for an actual SupraLINUX package proof. It remains `packaging.state=pending` and DAG `state=pending` until a real package-build campaign is attempted.

KDE upstream `v6.30.0` is authoritative for the build. The pinned source is:

- URL: `https://download.kde.org/stable/frameworks/6.30/attica-6.30.0.tar.xz`;
- SHA-256: `3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c`;
- root CMake blob: `92ae57c6bf82a8fad6c412b5b47a8c45a8652d88`.

Attica 6.30 requires ECM 6.30 and Qt Core/Network >= 6.9.0. The selected SupraLINUX provider baseline is Ubuntu Resolute Qt 6.10.2. The library keeps `SOVERSION 6`.

## Retained binary contract

The already retained Ubuntu/Debian binary-contract snapshots agree on the structural package split:

- `libkf6attica6`: runtime library, `Multi-Arch: same`;
- `libkf6attica-dev`: development package depending on the exact matching runtime package and Qt base development package, recommending the exact matching documentation package;
- `libkf6attica-doc`: `Architecture: all`, `Multi-Arch: foreign`;
- no reference package declares `Provides`, `Breaks`, `Replaces` or `Conflicts`.

These are compatibility inputs, not KDE authority.

## Pinned packaging-tree reference gate

Before authoring the SupraLINUX `debian/` tree, `.github/workflows/kde-attica-packaging-reference.yml` runs `scripts/run-kde-attica-packaging-reference.sh`.

It downloads only the two Debian metadata tarballs already identified by the retained source snapshot:

- Ubuntu Resolute `kf6-attica 6.24.0-0ubuntu1`: SHA-256 `a3bdf81f4d7c624fd2003b4446e0a038cd2d47db45970fd0153027a76a422b9e`;
- Debian sid `kf6-attica 6.28.0-1`: SHA-256 `17f7367dce612b888be9dd5e1b249a48e21a0e86a99afa3f304c0051bb7d1c4f`.

The gate verifies those hashes and requires both references to provide:

- `debian/control`;
- `debian/rules`;
- `debian/copyright`;
- the three Attica `.install` files;
- `debian/libkf6attica6.symbols`.

It retains the complete extracted `debian/` trees plus a normalized hash summary. It does not build a package, does not install Debian packages, and does not change any Framework DAG state.

## Why this capture exists

The source/binary archive snapshots already establish package names, Build-Depends and installed binary contracts, but they do not expose the complete symbols baseline, install-path rules or machine-readable copyright data used by the reference packaging.

SupraLINUX must inspect those files rather than infer them. The final `debian/` tree may reuse Debian-family packaging techniques where justified, but KDE 6.30 source/defaults and the SupraLINUX provider profile remain controlling inputs.

## ECM predecessor

Any subsequent Attica `sbuild` must consume the retained SupraLINUX ECM artifact, not Ubuntu's older ECM package:

- ECM package: `extra-cmake-modules 6.30.0-0supralinux3`;
- workflow run: `34694951158`;
- artifact: `10298635300`;
- artifact ZIP SHA-256: `181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`;
- `.deb` SHA-256: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`.

The future Attica build must inject this exact `.deb` through sbuild's local extra-package mechanism so Ubuntu cannot substitute its Frameworks 6.24 ECM.

## Next gate

After the packaging-tree reference capture has a retained PASS artifact, inspect its exact `control`, `rules`, install lists, symbols and copyright data. Then author the SupraLINUX Attica 6.30 package and run it in a fresh Resolute `sbuild` with the pinned ECM PASS artifact.
