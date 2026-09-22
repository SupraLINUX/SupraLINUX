# KDE Tier 3 support package contracts

Status: **reference capture PASS — packaging-tree capture pending**

Reviewed: **2026-09-22**

## Scope

This lane prepares packaging contracts for the three KDE Frameworks 6.30 support components selected to be provided by SupraLINUX:

- Breeze Icons;
- KDocTools;
- KDED.

The provider decision is already PASS and does not need to be repeated. This gate captures packaging references only.

## Authority versus reference

KDE upstream 6.30.0 remains authoritative for source, feature defaults and dependencies.

Ubuntu Resolute and Debian sid are used only as **technical packaging references**. Their package names, dependency metadata and Debian packaging can inform compatibility/materialization, but cannot lower or replace the selected KDE source.

The hosted reference job uses signed `deb-src` metadata for both distributions and records:

- source package/version;
- binary package set;
- Build-Depends / Build-Depends-Indep;
- VCS metadata;
- source-file SHA-256 records.

For Debian, the selector requires an exact 6.30.0 source reference when available and fails rather than silently materializing from a different KDE series.

## Lifecycle

Reference capture has `package_state_effect=none`. No source package is built and no Tier 3/support node becomes PASS.

After capture PASS, the resulting records must be reviewed into explicit SupraLINUX contracts before materialization is authorized. Promotion to `stable` remains impossible without explicit user approval.


## Reference capture PASS — 2026-09-22

Run `35696911023`, job `106645687497`, artifact `10680304903`, SHA-256 `677f5a0065d3fab2983471a0ccc54ba640b980d25740773e35eea1c5ef9ee95d`: **PASS**.

Normalized snapshot SHA-256: `27012f04c7686e94061055a6aeb33d12f2d17521a151c5742b5e2b2863d5c4d8`.

Captured source references:
- Breeze Icons: Ubuntu `6.24.0-0ubuntu1`; Debian `4:6.30.0-1`.
- KDocTools: Ubuntu `6.24.0-0ubuntu1`; Debian `6.30.0-1`.
- KDED: Ubuntu `6.24.0-0ubuntu1`; Debian `6.30.0-1`.

Debian's 6.30 Breeze source exposes both the newer `breeze-icon-theme*` packages and the `kf6-breeze-icon-theme*` compatibility names, while Ubuntu 6.24 exposes only the latter. Because that distinction affects Ubuntu compatibility and future KDE consumers, the package contract is not finalized from source-record metadata alone.

The active next gate downloads and verifies the exact pinned Ubuntu/Debian source files, extracts both `debian/` trees, records deterministic tree hashes, and retains parsed control relations. It remains a technical-reference operation with `package_state_effect=none`.
