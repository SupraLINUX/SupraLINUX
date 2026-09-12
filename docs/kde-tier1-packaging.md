# KDE Frameworks 6.30 Tier 1 — packaging preparation

Status: **provider preflight PASS; packaging-reference snapshot PASS; Framework packaging/build campaign pending**  
Last reviewed: **2026-09-12**

## Purpose

Before writing SupraLINUX `debian/` metadata for the 29 Tier 1 Frameworks, the project captures current Ubuntu Resolute and Debian sid source-packaging metadata as technical reference evidence.

This does **not** change project authority:

- KDE Frameworks 6.30.0 source/build metadata remains authoritative for KDE requirements, features and defaults;
- Ubuntu Resolute remains the platform and compatibility reference;
- Debian and Ubuntu packaging may inform package names, dependency expressions, Multi-Arch layout, symbols/shlibs handling and other Debian-policy details;
- neither distro is allowed to select the KDE version or silently disable an upstream default feature.

## Why two packaging references

Ubuntu Resolute is the direct compatibility target, but its Frameworks packages trail the selected KDE Frameworks 6.30.0 stack. Debian sid is closer to current Frameworks packaging and is therefore useful for newer packaging mechanics. Both remain references only.

The snapshot records what each archive actually publishes at execution time rather than hard-coding an assumed distro version into SupraLINUX architecture.

## Machine-readable mapping

`manifests/kde-frameworks-tier1-packaging-reference.json` maps each of the fixed 29 Tier 1 nodes to its Debian-family source package (`kf6-<framework>`).

The manifest is explicitly:

- `authority: false`;
- `role: packaging-reference-only`;
- backed by retained workflow/artifact evidence;
- prohibited from changing a Framework's build/DAG state.

Repository Policy verifies that this node set exactly matches `manifests/kde-frameworks-tier1.json` and that every Framework remains `packaging.state=pending` and `state=pending` until an actual package build is attempted.

## Isolated archive capture

`.github/workflows/kde-tier1-packaging-reference.yml` runs on Ubuntu 26.04 and invokes `scripts/run-kde-tier1-packaging-reference-snapshot.sh`.

The script keeps archive namespaces separate:

- Ubuntu source indexes: `resolute`, `resolute-updates` and `resolute-security`, components `main,universe`;
- Debian source index: `sid`, component `main`;
- only `deb-src` indexes are added for the reference capture;
- Debian binary repositories are never enabled;
- each reference has its own APT source list and APT list directory.

This prevents a Debian sid package from becoming an accidental provider on the Ubuntu runner.

## First retained snapshot PASS

Evidence:

- workflow run: `34701132721`;
- PR head: `943a99f7465e311bbc72d63cbe6555a29aa4b5ab`;
- artifact: `10299579234`;
- artifact SHA-256: `a2951c297f125ad81d1487075f0a0a6250114c4e875f3ba3870c3c18c09adaca`;
- normalized `snapshot.json` SHA-256: `601c668342c206af179e9c564bf87cac6a166f1070fe9af0b640cb57d2151597`;
- `versions.tsv` SHA-256: `af6fd90121801eaf322442c43b793422494dfd5a109edccf484f5d24b463ea9b`;
- result: `PASS`, `authority=false`, `role=packaging-reference-only`, `framework_package_build_certification=pending`.

The snapshot resolved all **58** expected source records: 29 from Ubuntu Resolute and the same 29 from Debian sid.

## Observed reference versions

Ubuntu Resolute is not uniform across this Tier 1 set:

- 28 nodes use upstream Frameworks `6.24.0` packaging;
- `modemmanager-qt` uses upstream `6.23.0` packaging.

Debian sid is also not a single exact Frameworks revision:

- 28 nodes use upstream `6.28.0` packaging;
- `syntax-highlighting` uses upstream `6.28.1` packaging.

These versions are evidence about reference packaging only. SupraLINUX remains selected on KDE Frameworks **6.30.0**.

## Binary-package contract comparison

The binary-package name sets are identical between the two reference distributions for **28 of 29** Tier 1 source packages.

The exception is `kirigami`. Debian 6.28 adds four binary libraries that are absent from the Ubuntu 6.24 reference:

- `libkirigamiforms6`;
- `libkirigamiformsprivatecards6`;
- `libkirigamiformsprivateflat6`;
- `libkirigamiformsprivatetemplates6`.

This is a concrete example of why SupraLINUX must derive the final binary split from KDE 6.30 installed outputs plus compatibility requirements, not merely freeze Ubuntu's older split.

## Build-Depends comparison

Fourteen Tier 1 source packages have at least one package-name difference in `Build-Depends` between the captured Ubuntu and Debian references.

Notable examples include:

- `kcoreaddons`: Debian adds `libmount-dev`, `qt6-base-private-dev`, `xauth` and `xvfb`; the first two align with dependencies already identified independently from KDE 6.30 upstream metadata;
- `kconfig`: Debian adds `qt6-base-private-dev` and moves D-Bus test infrastructure from `dbus-x11` to `dbus-daemon`;
- `kcalendarcore`, `kitemviews`, `kplotting` and `syntax-highlighting`: Debian adds `xauth`/`xvfb` test infrastructure;
- `ki18n`: Debian adds `iso-codes` and `locales-all`;
- `prison`: Debian adds `dh-sequence-pkgkde-symbolshelper`;
- `sonnet`: Debian adds `dh-sequence-qmldeps`.

These differences are reference signals. The selected SupraLINUX Build-Depends for each package must be justified against KDE 6.30.0 and the resolved provider manifest.

## Captured fields

For every Tier 1 source package and for both references, the snapshot records the newest source stanza visible in the isolated index, including:

- source package and Debian version;
- normalized upstream version;
- binary package names;
- architecture field;
- `Build-Depends` and `Build-Depends-Indep`;
- build conflicts when present;
- Standards-Version;
- Homepage and VCS metadata;
- archive `Directory`;
- published SHA-256 checksums for source artifacts.

Raw `apt-cache showsrc` records are retained beside the normalized `snapshot.json` and `versions.tsv` files.

## Safety gates

The snapshot fails rather than silently adapting when:

- any of the 29 expected source packages is absent from Ubuntu Resolute or Debian sid;
- the source-package mapping no longer matches the selected Tier 1 set;
- a reference upstream version is newer than the selected KDE 6.30.0 release;
- the workflow is not running on Ubuntu 26.04.

A reference moving ahead of KDE 6.30.0 is treated as a review signal because SupraLINUX must first re-evaluate the selected KDE stable release rather than ingest packaging for a newer desktop implicitly.

## Evidence semantics

A packaging-reference workflow PASS proves only that a coherent, current reference snapshot was captured. It does **not** prove that any SupraLINUX Framework package builds.

Therefore this PASS updates only the packaging-reference evidence state. It does not change any Framework node to PASS, FAIL or BLOCKED.

## Next gate

SupraLINUX packaging can now be authored node-by-node. Each `debian/` tree must be audited against exact KDE 6.30.0 defaults and the already resolved provider manifest rather than copied blindly from either reference distro.

The build campaign will reuse the established ECM model: exact KDE source + verified hash → Debian source package → fresh Resolute build root → `sbuild` → `.deb/.changes/.buildinfo` → package checks/tests → DAG evidence.

The first packaging proof is intentionally a simple Tier 1 leaf (`attica`) so the generalized Framework package pipeline can be validated before expanding to the remaining 28 independent Tier 1 nodes.
