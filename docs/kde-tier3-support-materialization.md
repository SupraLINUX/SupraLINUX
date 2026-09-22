# KDE Tier 3 support materialization

Status: **pending CI**

Reviewed: **2026-09-22**

This lane materializes the three finalized support package contracts without building binary packages.

Authority remains KDE upstream 6.30.0. For every node, the exact Debian 6.30 source record is downloaded from signed sid metadata, its `.dsc`, Debian tar and orig tar are verified against the promoted technical reference, and the orig tar must match the official KDE release SHA-256.

The Debian 6.30 packaging tree is then adapted only for SupraLINUX/Resolute integration:

- maintainer becomes the SupraLINUX build identity;
- Debian reference Uploaders/Vcs fields are removed;
- `debhelper-compat (= 14)` becomes `debhelper-compat (= 13)`, matching the Resolute packaging-tool baseline;
- the package version becomes the finalized SupraLINUX version.

No KDE source, feature selection, ABI or binary package contract is changed by this common adaptation. Breeze-specific transition relations and package epoch are retained unchanged from the finalized contract.

All three source materializations may run in parallel. Materialization has `package_attempted=false` and `package_state_effect=none`; it cannot make a package PASS.

Binary builds remain blocked until all three source materializations are promoted and validated.
