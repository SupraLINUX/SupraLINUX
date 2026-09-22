# KDE Tier 3 support package contracts

Status: **reference capture pending**

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
