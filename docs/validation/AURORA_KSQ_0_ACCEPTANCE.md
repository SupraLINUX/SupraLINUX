# Aurora KSQ-0 Acceptance — Source and Dependency Inventory

Status: **CERTIFIED**

Certification date: **2026-08-29**

Candidate stack scoped by this acceptance:

- Ubuntu base: Ubuntu 26.04 LTS (`resolute`)
- Qt: Ubuntu Qt 6.10.2
- KDE Plasma / KWin: 6.7.4
- KDE Frameworks: 6.29.0
- KDE Gear: not certified by KSQ-0; separate review remains required

This acceptance closes only **KSQ-0**. It does not certify that the candidate binaries build, install, upgrade, boot, or function end-to-end. Those requirements belong to KSQ-1 and later stages.

## Certified repository state

Canonical engineering commit:

`4e7db453f626e78ca72c353ab314e16e00c9003f`

Branch:

`feature/kde-stack-qualification`

`development` was not modified by this qualification work.

## Canonical evidence

### Official release/source inventory

Workflow: `Aurora KSQ-0 source inventory`

Run: `33231880014`

Artifact: `aurora-ksq-0-source-inventory-33231880014-1`

Artifact ID: `9708729431`

Artifact digest:

`sha256:06e7d6cb23a6c9b06173fb61ff39eda6e1f66962ce71120463fe841848b83af0`

Accepted inventory:

- Plasma 6.7.4 upstream modules: 75
- Frameworks 6.29.0 upstream modules: 74
- `supralinux-desktop` classified package roots: 62
- unknown/unclassified roots: 0

The package-root count is 62 because the obsolete `plasma-session-wayland` root was removed. Plasma 6.7.4 installs the Wayland session through `plasma-workspace`; retaining the old binary name would model a package no longer produced by the current 6.7.4 source package.

### Strict source Build-Depends closure

Workflow: `Aurora KSQ-0 source and dependency qualification`

Run: `33231879994`

Artifact: `aurora-ksq-0-dependency-closure`

Artifact ID: `9708738867`

Artifact digest:

`sha256:5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50`

Pinned Ubuntu archive snapshot:

`20260829T022000Z`

The workflow uses snapshot-only APT metadata. Resolute provides binary and source metadata; Stonking is source metadata only and cannot satisfy runtime binary dependencies accidentally.

Accepted closure:

- total selected source packages: 101
- topologically ordered source packages: 101
- unresolved dependencies: 0
- unresolved source/package decisions: 0
- Frameworks 6.29.0 source packages in closure: 59
- Plasma 6.7.4 source packages in closure: 39
- KDE-adjacent explicit backports: 2
- Ubuntu-platform compatibility backports: 1
- explicit build-dependency packaging overrides: 1

The canonical resolver is `scripts/ci/generate-kde-build-closure.py`. The workflow executes it in strict mode; there is no `--allow-unresolved` escape in the certification path. It independently asserts that `unresolved.tsv` and `source-decision-candidates.tsv` contain only their headers, that every selected source is topologically ordered, that exactly three source selections are consumed, and that exactly one build-dependency override is consumed.

## Explicit source selections

### `plasma-wayland-protocols` 1.21.0-1

Origin: Ubuntu Stonking source metadata from the pinned Ubuntu snapshot.

Reason: KWin and `plasma-workspace` 6.7.4 require `plasma-wayland-protocols >= 1.21.0`; Resolute provides 1.20.0.

Classification: KDE-adjacent backport.

### `qtkeychain` 0.17.0-1

Origin: Ubuntu Stonking source metadata from the pinned Ubuntu snapshot.

Reason: `plasma-nm` 6.7.4 requires `qtkeychain-qt6-dev >= 0.16.0`; Resolute provides 0.15.0.

Classification: KDE-adjacent backport.

### `wayland-protocols` 1.48-1

Origin: Debian source package, retrieved reproducibly from Debian Snapshot by immutable content hash and checked against pinned SHA-256 values.

Reason: KWin 6.7.4 requires `wayland-protocols >= 1.48`. Resolute provides 1.47. The selected Debian 1.48-1 packaging requires `libwayland-dev >= 1.23.0` and is compatible with the Resolute Wayland runtime generation. Newer 1.49 packaging would require `libwayland-dev >= 1.25.0`, which would unnecessarily expand the Ubuntu platform boundary.

Classification: Ubuntu-platform compatibility backport.

This is a protocol-data/build-package backport. It does **not** authorize replacing the Ubuntu Wayland runtime.

## `kwallet-pam` packaging adaptation

Selected upstream/Ubuntu source:

`kwallet-pam 4:6.7.4-0ubuntu3`

Required Resolute packaging delta:

`debhelper-compat (= 14)` → `debhelper-compat (= 13)`

No functional PAM behavior is intentionally changed by this adaptation.

The source audit proves that Ubuntu `0ubuntu3` contains the Debian 6.7.4-3 PAM integration and that these functional packaging files are byte-identical to Debian 6.7.4-3:

- `debian/libpam-kwallet-common.install`
- `debian/libpam-kwallet-common.postinst`
- `debian/libpam-kwallet-common.prerm`
- `debian/pam-configs/kde-kwallet`

The audit also requires:

- `libpam-runtime` dependency present;
- `pam-auth-update` integration present;
- Password PAM profile present;
- Debian's post-install test contract to remain `pam_kwallet5.so` present in both `/etc/pam.d/common-session` and `/etc/pam.d/common-auth`.

The repository tracks `scripts/ci/validate-kwallet-pam-installation.sh` for execution against the actual rebuilt/installed candidate in KSQ-1/KSQ-3. KSQ-0 proves the source/packaging contract; it does not falsely claim an installation test before the candidate package exists.

## Platform boundary result

KSQ-0 found no justification to replace any of the following Ubuntu 26.04 platform layers:

- kernel / firmware
- Mesa / libdrm
- systemd
- PipeWire / WirePlumber
- NetworkManager
- Wayland runtime
- Qt
- base compiler/runtime libraries

The candidate therefore remains architecturally compatible with the project's Ubuntu-owned platform boundary at the source-dependency level.

## Provenance model

Ubuntu metadata and selected Ubuntu sources are pinned to the Ubuntu Snapshot Service timestamp above. The snapshot's signed archive metadata is the canonical package-index provenance and APT verifies package/source hashes against that metadata.

Historical Debian source objects required deliberately by the candidate are retrieved through Debian Snapshot by immutable content identity and then checked against separately pinned SHA-256 values. A current mirror is not treated as a reproducibility dependency.

All selected source files and their hashes are retained in the canonical closure artifact.

## Exit criteria evaluation

KSQ-0 PASS criteria from `docs/KDE_STACK_QUALIFICATION.md`:

- exact KDE release-set/source-package inventory: **PASS**
- exact Frameworks inventory required by the release set: **PASS**
- complete build-dependency DAG: **PASS**
- explicit Resolute-satisfied dependency evidence: **PASS**
- explicit backport/override list: **PASS**
- unresolved package-name/API assumptions: **0 / PASS**
- source provenance/checksum strategy documented and exercised: **PASS**

**KSQ-0 is CERTIFIED.**

The next permitted phase is **KSQ-1 — Reproducible source builds**. No KSQ-1 result may inherit KSQ-0 assumptions if the candidate release set, source selections, packaging overrides, snapshot, or relevant Ubuntu platform versions change; such a change reopens the corresponding KSQ-0 regression.
