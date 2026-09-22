# KDE Tier 3 support materialization

Status: **PASS**

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


## PASS evidence — 2026-09-22

Workflow run `35698463205` materialized all three support sources successfully from commit `080cdd5ddf75d46b914efb0baca85981deee0765`.

- Breeze Icons: job `106650704762`, artifact `10680459412`, artifact SHA-256 `80955df1f6e90b6ad519b2f91cadbf1e4b56278e69a9827cdfa0b498a960fdb1`; DSC `656cb25eeca440541c96dac702b77ea8007683ea8f4b40538fc8240a73add9fa`; Debian tar `373b83d55799bf8202986b761b0c91fd5cca2c981017971bb021db7b9a1d5879`.
- KDocTools: job `106650704804`, artifact `10680938435`, artifact SHA-256 `cf5c18889e9de6582ca05b4e8290686948942493aeaf54a318a2b4f4925cf5ac`; DSC `677d1d29efc3b247750861bf8f22c86f20df03cd288403b4db92f7d5b8b7f4b5`; Debian tar `49880de46bf0dda23cecd1abd34393743f40efb35666718632528046298a8e94`.
- KDED: job `106650704776`, artifact `10680629132`, artifact SHA-256 `680ec2d408e1dd021b091c7adfe1d63a3077144bf54516da3164191d427efa99`; DSC `fe48627801159b62904c354794e7a980ecf8175a20c3c282d8a378f25083e4de`; Debian tar `5f971aa53129d6c1a70347b19876731addeca02fa3d21060af9a396aedd7be9d`.

All three retained the exact KDE 6.30 orig-tar SHA-256 and use the Resolute-compatible debhelper level 13.

This PASS is still source materialization only: `package_attempted=false`, `package_state_effect=none`. The next gate is binary build level 0: Breeze Icons and KDocTools. KDED remains blocked from binary build until KDocTools itself reaches real package PASS.
