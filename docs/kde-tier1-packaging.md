# KDE Frameworks 6.30 Tier 1 — packaging preparation

Status: **provider preflight PASS; packaging-reference snapshot implementation prepared; first snapshot pending; Framework packaging pending**  
Last reviewed: **2026-09-12**

## Purpose

Before writing SupraLINUX `debian/` metadata for the 29 Tier 1 Frameworks, the project captures current Ubuntu Resolute and Debian sid source-packaging metadata as technical reference evidence.

This does **not** change project authority:

- KDE Frameworks 6.30.0 source/build metadata remains authoritative for KDE requirements, features and defaults;
- Ubuntu Resolute remains the platform and compatibility reference;
- Debian and Ubuntu packaging may inform package names, dependency expressions, Multi-Arch layout, symbols/shlibs handling and other Debian-policy details;
- neither distro is allowed to select the KDE version or silently disable an upstream default feature.

## Why two packaging references

Ubuntu Resolute is the direct compatibility target, but its Frameworks packages currently trail the selected KDE Frameworks 6.30.0 stack. Debian sid is closer to current Frameworks packaging and is therefore useful for newer packaging mechanics. Both remain references only.

The snapshot intentionally records what each archive actually publishes at execution time rather than hard-coding an assumed distro version into SupraLINUX architecture.

## Machine-readable mapping

`manifests/kde-frameworks-tier1-packaging-reference.json` maps each of the fixed 29 Tier 1 nodes to its Debian-family source package (`kf6-<framework>`).

The manifest is explicitly:

- `authority: false`;
- `role: packaging-reference-only`;
- `snapshot.status: pending` until a real workflow PASS is retained.

Repository policy verifies that this node set exactly matches `manifests/kde-frameworks-tier1.json` and that every Framework remains `packaging.state=pending` and `state=pending` while reference metadata is being gathered.

## Isolated archive capture

`.github/workflows/kde-tier1-packaging-reference.yml` runs on Ubuntu 26.04 and invokes `scripts/run-kde-tier1-packaging-reference-snapshot.sh`.

The script keeps archive namespaces separate:

- Ubuntu source indexes: `resolute`, `resolute-updates` and `resolute-security`, components `main,universe`;
- Debian source index: `sid`, component `main`;
- only `deb-src` indexes are added for the reference capture;
- Debian binary repositories are never enabled;
- each reference has its own APT source list and APT list directory.

This prevents a Debian sid package from becoming an accidental provider on the Ubuntu runner.

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

Therefore a snapshot PASS may update only the packaging-reference evidence state. It may not change any Framework node to PASS, FAIL or BLOCKED.

## Next gate

After the first snapshot PASS is inspected and its artifact/hash are retained, SupraLINUX packaging can be authored node-by-node. Each `debian/` tree must be audited against exact KDE 6.30.0 defaults and the already resolved provider manifest rather than copied blindly from either reference distro.

The subsequent build campaign will reuse the established ECM model: exact KDE source + verified hash → Debian source package → fresh Resolute build root → `sbuild` → `.deb/.changes/.buildinfo` → package checks/tests → DAG evidence.
