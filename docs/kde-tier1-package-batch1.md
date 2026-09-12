# KDE Frameworks 6.30 Tier 1 — package batch 1

Status: **attempt 1 FAIL on all three nodes; remediation `-0supralinux2` prepared**  
Last reviewed: **2026-09-12**

## Scope

The first generalized package batch contains three independent KDE Frameworks 6.30 Tier 1 nodes:

- `kcodecs`;
- `kdbusaddons`;
- `threadweaver`.

All three depend only on the retained Extra CMake Modules PASS root in the KDE DAG. The matrix uses `fail-fast: false`, so every independent node is attempted even when another fails.

## Authority and provider split

KDE upstream `v6.30.0` defines source, CMake requirements, Qt minimums, defaults and test structure. Ubuntu Resolute supplies compatible Qt/general build dependencies and is the package/application compatibility target. Ubuntu/Debian `debian/` trees remain non-authoritative technical references.

Retained inputs:

- ECM `6.30.0-0supralinux3`: run `34694951158`, artifact `10298635300`, `.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- generic Tier 1 packaging trees: run `34708030450`, artifact `10301938362`, artifact SHA-256 `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`.

## Selected build requirements

### KCodecs

KDE 6.30 root CMake blob `a4844477467d5c7b47875f837fa6db0b22550397` requires ECM 6.30 and Qt Core >=6.9. `ECMPoQmTools` resolves Qt LinguistTools, so Resolute `qt6-tools-dev` is justified. Historical distro dependencies `gperf`, Doxygen and `libxkbcommon-dev` are not copied without an upstream requirement.

Source SHA-256: `a42c79ff3237b73789d1c63cdfd848c0d59671ce5e93723a2efa128f00cb3450`. Ubuntu symbols baseline SHA-256: `8dfcf6c469195a45e5f1d038a42cf1f223fe12d00c3ee1e3aa5125142935e1a3`.

### KDBusAddons

KDE 6.30 root CMake blob `26cde2148db4d86adeea0f4bda597f0f9e610816` requires Qt DBus >=6.9. With the selected Qt 6.10 provider and upstream `WITH_X11=ON`, KDE explicitly requires `Qt6GuiPrivate`, supplied by `qt6-base-private-dev`. Translation processing uses `qt6-tools-dev`. Tests run in a private D-Bus session through `dbus-run-session`.

Source SHA-256: `063ef80460f76d86dc4b033ef04b65b69ba82ee0de410440fe609465e7f5a997`. Ubuntu symbols baseline SHA-256: `03b48faa6b7c5b400f3a165c38c4c5e7e7fc454a0b099ef1ad776b3809851683`.

### ThreadWeaver

KDE 6.30 root CMake blob `309efd1d962d925a71610ea65fed2a1007ef055d` requires Qt Core >=6.9. The always-built examples additionally use Qt Widgets/Test, supplied by Qt Base. No Qt translation-tools, Doxygen or `libxkbcommon-dev` dependency is added.

Source SHA-256: `e5400968a41820393e76190ab5dbb276c09513263d1b185d64b40f82dcd9b457`. Ubuntu symbols baseline SHA-256: `a7403ee234e24d20f20502ed4a07b13ef265ec285cd5fb2b44709dfea39907b7`.

## Attempt 1 — three real FAILs

Commit `50611225422b05803ee49d8d5fc8ff4f84a21d99` triggered workflow run `34709829162`. All three matrix nodes were actually attempted; none is BLOCKED.

Evidence:

- KCodecs — job `103596438631`, artifact `10302917591`, artifact SHA-256 `6fcf23a69991e453d3563d580aa63fa082c27ce8490ad52dd9e125ee41cd8f6f`;
- KDBusAddons — job `103596438606`, artifact `10303285563`, artifact SHA-256 `2a581e9f4c01c15c611b5b3d3a98343504177f1d52fb2225f92ce3c6428f54ed`;
- ThreadWeaver — job `103596438491`, artifact `10303265649`, artifact SHA-256 `0b47374207ae54632c4ba9594eedbcc72d46eed552696b608110ebb5bce6acb6`.

All three artifacts report `state=FAIL`, `stage=sbuild`, package revision `6.30.0-0supralinux1`. Source verification, retained ECM/reference validation, source-package assembly, clean Resolute root creation, CMake configuration and compilation were reached.

The common failure occurred in the SupraLINUX packaging override before the real KDE autotests:

`override_dh_auto_test -> reuse lint -> FAIL`

Therefore **the KDE autotests did not run** in attempt 1. No test PASS or FAIL is attributed to KDE upstream for these attempts.

## Root cause — invalid SupraLINUX REUSE gate

The initial packaging added `reuse` as a Build-Depends and called `reuse lint` over the entire unpacked/package build tree. That was not an upstream KDE 6.30 build requirement.

The check was conceptually wrong for two independent reasons:

1. after configure/build, the tree contains generated `obj-*`, `.pc` and packaging files that are outside upstream source licensing metadata;
2. the KDE 6.30 repositories themselves contain `LICENSES/` and SPDX metadata but do not declare complete full-tree REUSE compliance for every repository/build metadata file, so SupraLINUX must not invent such a release gate.

The failure is therefore classified as a SupraLINUX package-test-policy error, not a KDE, Qt, ECM, ABI or upstream-test failure.

The initial Repository Policy run `34709829038` also failed independently because ShellCheck found three unused variables in the generic runner (`UPSTREAM_TARBALL`, `DEV_DEB`, `DOC_DEB`). That is CI infrastructure evidence, not a Framework package FAIL. The variables are removed rather than suppressing ShellCheck.

## Remediation — `6.30.0-0supralinux2`

For all three packages:

- remove `reuse` from `Build-Depends`;
- remove the invented `reuse lint` command;
- keep `BUILD_TESTING=ON`;
- execute the real upstream tests with `dh_auto_test`;
- keep KDBusAddons tests wrapped in `dbus-run-session`;
- preserve exact source, ECM predecessor, symbols baseline, binary split, Architecture/Multi-Arch contract, SONAME, Lintian error gate and consumer smoke;
- retain the `-0supralinux1` changelog entries and CI artifacts as historical FAIL evidence.

Candidate revisions are now:

- KCodecs `6.30.0-0supralinux2`;
- KDBusAddons `6.30.0-0supralinux2`;
- ThreadWeaver `6.30.0-0supralinux2`.

`manifests/kde-tier1-package-campaign.json` is the attempt ledger for this remediation and records all three first-attempt FAILs. The canonical Tier 1 package/DAG manifest will be synchronized to the resulting current states when attempt 2 closes, while preserving these historical attempts.

## Shared package gate

The generic hosted preflight continues to require:

1. exact KDE 6.30 source + SHA-256;
2. exact retained ECM PASS artifact;
3. exact retained Ubuntu symbols reference and Debian copyright reference;
4. source assembly with `dpkg-source -b` without package helpers on the host;
5. fresh Resolute `sbuild --chroot-mode=unshare`;
6. `.buildinfo` proof of ECM `6.30.0-0supralinux3`;
7. real KDE autotests;
8. expected binary package split, Architecture/Multi-Arch and compatibility fields;
9. SONAME validation;
10. `.deb`, `.changes`, `.buildinfo`, `.dsc`, source/rootfs hashes and logs;
11. `lintian --fail-on error`;
12. package-specific CMake consumer compile/run.

## Current state before attempt 2

The first attempts are historical real FAILs. The remediation campaign state is `remediation-pending-build`; none of these nodes is PASS or BLOCKED. Because ECM is PASS and the three nodes are independent, attempt 2 will again execute all three in parallel with `fail-fast: false`.
