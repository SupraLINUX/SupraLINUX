# KDE Frameworks 6.30 — Attica packaging

Status: **packaging reference-tree PASS; first SupraLINUX package attempt FAIL; remediation revision 6.30.0-0supralinux2 prepared**  
Last reviewed: **2026-09-12**

## Scope

`attica` is the first KDE Frameworks 6.30 Tier 1 node selected for an actual SupraLINUX package proof.

KDE upstream `v6.30.0` is authoritative for the build. The pinned source is:

- URL: `https://download.kde.org/stable/frameworks/6.30/attica-6.30.0.tar.xz`;
- SHA-256: `3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c`;
- root CMake blob: `92ae57c6bf82a8fad6c412b5b47a8c45a8652d88`.

Attica 6.30 requires ECM 6.30 and Qt Core/Network >= 6.9.0. With `BUILD_TESTING=ON`, the remaining test/example targets use Qt Test and Qt Widgets; these are supplied by `qt6-base-dev`. The selected SupraLINUX provider baseline is Ubuntu Resolute Qt 6.10.2. The library keeps `SOVERSION 6`.

## Packaging reference-tree PASS

The exact Debian metadata trees used for technical comparison were captured and retained:

- workflow run: `34704689773`;
- PR head: `214e0355cb5f8edf922d15e4c217c5851a51fc3e`;
- artifact: `10301617541`;
- artifact SHA-256: `ce9e9949f643736f25ec27d2850cb0654334b64a28dfcd293df78ae1b1f60407`.

The gate verified the already-pinned distro metadata tarballs:

- Ubuntu Resolute `kf6-attica 6.24.0-0ubuntu1`, Debian tarball SHA-256 `a3bdf81f4d7c624fd2003b4446e0a038cd2d47db45970fd0153027a76a422b9e`;
- Debian sid `kf6-attica 6.28.0-1`, Debian tarball SHA-256 `17f7367dce612b888be9dd5e1b249a48e21a0e86a99afa3f304c0051bb7d1c4f`.

This evidence is non-authoritative and exists only to inspect Debian packaging techniques and compatibility contracts.

## Retained binary contract

The retained Ubuntu/Debian binary-contract snapshots agree on the structural package split:

- `libkf6attica6`: runtime library, `Architecture: any`, `Multi-Arch: same`;
- `libkf6attica-dev`: development package depending on the exact matching runtime package and Qt base development package, recommending the exact matching documentation package;
- `libkf6attica-doc`: `Architecture: all`, `Multi-Arch: foreign`;
- no reference package declares `Provides`, `Breaks`, `Replaces` or `Conflicts`.

The SupraLINUX `debian/control` preserves those structural contracts while updating the direct Qt floor to KDE 6.30's requirement (`>= 6.9.0~`).

## Selected Build-Depends

SupraLINUX does not copy the full distro Build-Depends list. Each retained item must be justified against Attica 6.30 or Debian packaging mechanics.

Selected direct build dependencies are:

- `debhelper-compat (= 13)` — Debian packaging framework;
- `dh-sequence-kf6` — KDE/Debian helper sequence;
- `dh-sequence-pkgkde-symbolshelper` — symbols/ABI handling used by the established KF6 package contract;
- `cmake (>= 3.29)` — exact upstream CMake floor;
- `extra-cmake-modules (>= 6.30.0~)` — exact KDE Frameworks predecessor series;
- `qt6-base-dev (>= 6.9.0~)` — supplies Core, Network, Test and Widgets required by Attica's selected build/test profile;
- `python3` and `reuse` — preserve ECMCheckOutboundLicense/REUSE license tests.

The older reference-only dependencies `doxygen`, `libxkbcommon-dev` and `qt6-tools-dev` are not direct requirements of the selected default Attica 6.30 build and are not carried into this package merely because older distro packaging lists them.

## Tests and deterministic build policy

`BUILD_TESTING=ON` and `SKIP_LICENSE_TESTS=OFF` are explicit in `debian/rules`.

The only disabled upstream test is `providertest.cpp`. Attica 6.30 still performs live requests to `https://autoconfig.kde.org/ocs/providers.xml`, so Debian/Ubuntu's long-standing network-test patch remains technically applicable. Disabling that test makes the clean package build independent of external network state while retaining `configtest`, `persontest` and the REUSE outbound-license tests.

This is an integration/reproducibility patch, not a KDE feature substitution.

## QDoc decision

Attica 6.30 uses `ECMGenerateQDoc`. In ECM 6.30, documentation is exposed through explicit `prepare_docs`, `generate_docs`, `generate_qch`, `install_html_docs` and `install_qch_docs` targets; it is not part of the normal build.

The `BUILD_QCH=ON` flag inherited from current Debian/Ubuntu packaging does not control this current macro and is not used by SupraLINUX.

The package name `libkf6attica-doc` is retained for compatibility. In this first default-build profile it contains only debhelper-generated package documentation, matching the observable Resolute binary package contents. A later project-wide Frameworks documentation phase can choose to invoke KDE's explicit QDoc targets consistently rather than enabling them ad hoc for one Framework.

## Symbols / ABI baseline

The package proof starts `dpkg-gensymbols` from the exact Ubuntu Resolute `libkf6attica6.symbols` compatibility baseline retained in artifact `10301617541`:

- symbols SHA-256: `e67d131171c8e3ea79c6bbbb2434aa2492580d19ba7dccdaa7038766cd9827ad`.

Because that file is large, the repository stores a small `libkf6attica6.symbols.reference` record. `scripts/run-kde-attica-package-preflight.sh` verifies and copies the retained full symbols file into `debian/libkf6attica6.symbols` before creating the Debian source package. The retained `.dsc`/`.debian.tar.xz` from a successful source-package stage therefore contains the complete symbols baseline actually used.

An ABI delta reported by `dpkg-gensymbols` is not suppressed. It is a real Attica packaging/build result that must be reviewed and, if appropriate, used to establish the SupraLINUX 6.30 symbols baseline.

## ECM predecessor

The clean Attica build is not allowed to resolve Ubuntu's older ECM. It must consume the retained SupraLINUX ECM PASS artifact:

- package: `extra-cmake-modules 6.30.0-0supralinux3`;
- workflow run: `34694951158`;
- artifact: `10298635300`;
- artifact ZIP SHA-256: `181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`;
- `.deb` SHA-256: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`.

The Attica workflow downloads that exact retained artifact and passes its `.deb` through sbuild's `--extra-package` mechanism. The resulting `.buildinfo` must explicitly prove `extra-cmake-modules (= 6.30.0-0supralinux3)` or the gate fails.

## Package attempt 1 — FAIL

Commit `c18c8dcd1934a5bba874e642ba9b14729d2e69df` attempted package `6.30.0-0supralinux1`.

- workflow run: `34705165994`;
- result: **FAIL**;
- evidence artifact: `10300903114`;
- artifact SHA-256: `171cfe8553aba2af8f42a640ee5f50f82988005edbd104b737d93b639dc38300`;
- failure stage: `source-package`.

The retained ECM and Attica packaging-reference artifacts both downloaded and verified successfully. The failure occurred before `sbuild`: `dpkg-buildpackage -S` invoked `debian/rules clean` on the GitHub-hosted runner, and debhelper attempted to load `dh-sequence-kf6`, which intentionally belongs to the clean build environment rather than the source-assembly host.

This is a real Attica/pipeline FAIL because the node was actually attempted. It is not a KDE upstream, Qt-provider, ECM-predecessor or ABI failure.

## Remediation revision 6.30.0-0supralinux2

The remediation does not install KDE build helpers into the host runner. Instead, the source package is assembled with `dpkg-source -b` using source format `3.0 (quilt)`. `dpkg-source` creates the `.dsc` and Debian tarball without executing `debian/rules`; the actual Build-Depends, including `dh-sequence-kf6`, are then resolved only inside the fresh Resolute `sbuild` environment.

This keeps the host as source-assembly infrastructure and preserves the clean-build boundary. Debian's `dpkg-source(1)` explicitly defines `-b/--build directory` as the operation for building a source package from a debianized source tree.

The first failed revision remains in `debian/changelog`; the candidate is `6.30.0-0supralinux2`.

## Remediation package gate

`.github/workflows/kde-attica-package-preflight.yml` reruns the package in a fresh Ubuntu Resolute `sbuild` root. The gate requires:

1. KDE source SHA-256 verification;
2. exact ECM artifact and symbols-reference verification;
3. source-package assembly through `dpkg-source -b` without host-side KDE build helpers;
4. build/tests in a fresh Resolute buildd root;
5. exactly `libkf6attica6`, `libkf6attica-dev` and `libkf6attica-doc` at `6.30.0-0supralinux2`;
6. preserved Multi-Arch/dependency/compatibility fields;
7. SONAME `libKF6Attica.so.6`;
8. retained `.deb`, `.changes`, `.buildinfo`, `.dsc`, source tarballs and hashes;
9. Lintian with errors fatal;
10. a real CMake consumer build and execution against the generated runtime/dev packages.

The result of that actual remediation build determines whether Attica can move to PASS or remains FAIL. The other 28 Tier 1 nodes are unaffected and remain pending.
