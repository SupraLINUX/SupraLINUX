# KDE Frameworks 6.30 Tier 1 — package batch 3

Status: **PREPARED — build attempts pending**

Last reviewed: **2026-09-14**

## Selection

Batch 3 contains three independent Tier 1 nodes:

- `kitemmodels`;
- `bluez-qt`;
- `kplotting`.

All depend only on the retained ECM `6.30.0-0supralinux3` root inside the KDE DAG and none depends on another KDE Framework.

KDE Frameworks `6.30.0` remains the current stable upstream release and KDE upstream remains the source/build authority. Ubuntu Resolute is the compatibility target/provider; Debian sid 6.28 packaging is used only as a technical ABI/packaging reference.

## Why these nodes

The current package runner models one primary ABI library, one SONAME and one symbols baseline per node. KItemModels, BluezQt and KPlotting fit that model and have contained external dependency profiles.

`KConfig` is intentionally deferred. It exports multiple ABI libraries/symbol files (`ConfigCore`, `ConfigGui`, `ConfigQml`), so packaging it correctly requires an explicit multi-library extension of the runner rather than forcing it into a single-library model.

## Packaging policy

Each node starts at revision `6.30.0-0supralinux1`.

Debian-family binary package names and Multi-Arch contracts are preserved as compatibility inputs.

The retained Debian 6.28 symbols files are injected from workflow `34708030450`, artifact `10301938362`; they do not select the KDE version and any KDE 6.30 ABI delta must be reviewed from a real build.

QCH is disabled in the current common Frameworks profile. Documentation package names are retained as compatibility stubs and do not claim QCH payload.

Upstream autotests remain enabled.

## CI gates from attempt 1

Batch 3 starts with the corrected evidence boundary learned from Batch 2:

- clean `sbuild`/unshare on Ubuntu 26.04;
- retained ECM PASS consumed as an explicit predecessor;
- source SHA-256 verified against KDE release metadata;
- expected binary package/Multi-Arch contracts checked;
- SONAME checked;
- all generated `.ddeb` referenced by `.changes` preserved;
- `sbuild` Lintian status checked;
- `lintian --fail-on error` run against both `.dsc` and `.changes`;
- consumer CMake configuration/build checked;
- consumer performs `dlopen()` of the expected SONAME, avoiding false environmental dependencies on BlueZ, a live D-Bus service, or a GUI display;
- host evidence records Ubuntu, `sbuild`, `mmdebstrap` and Lintian versions.

A node becomes PASS only after all of those gates complete. A real node failure is FAIL; independent nodes continue; BLOCKED is reserved for downstream nodes that cannot be attempted because a predecessor FAILed.

## Canonical state before attempts

Tier 1 remains **7 PASS / 22 pending / 0 current FAIL / 0 BLOCKED**.

Preparing Batch 3 does not promote any node.
