# Plasma 6.7.5 Level 0

Status: **definition complete / materialization infrastructure preflight pending**.

Level 0 is derived directly from the canonical executable DAG and contains 34 independent Plasma sources. All have zero internal Plasma predecessors, so later package builds may be parallelized only after their external providers and materialized packaging contracts are valid.

## Execution boundary

- `package_execution_authorized=false`
- `materialization_authorized=false`
- no `sbuild` starts in this gate
- no Plasma package Attempt is consumed
- a preflight failure is `INFRA_INVALID`, never package `FAIL`

The new source-materialization path is therefore tested first with `kf6-kconfig`, a known Frameworks source outside Plasma Level 0. The preflight only exercises Ubuntu source-index lookup, `apt-get source --download-only`, `.dsc` handling, `dpkg-source -x`, and deterministic capture of the Debian packaging tree.

## Provider and packaging-reference policy

KDE Plasma 6.7.5 remains source and desktop authority. Ubuntu Resolute is the compatibility/provider platform and a technical packaging reference.

For Level 0, Ubuntu source references are selected from `resolute`, `resolute-updates`, and `resolute-security`. Candidate SupraLINUX Debian revisions are intentionally **not assigned yet**. Version assignment happens only after reference materialization and must pass `dpkg --compare-versions`, including preservation of any Debian epoch.

### Discover correction

The earlier same-name resolver found Ubuntu source `discover` `2.1.2-10.1build1`; that is not KDE Discover. The correct Ubuntu source is `plasma-discover`, currently `6.6.6-0ubuntu0.1` in Resolute Updates. This alias is explicit in the Level 0 manifest and is validated before materialization.

## Level 0 nodes

- `breeze-grub`
- `breeze-plymouth`
- `discover`
- `drkonqi`
- `flatpak-kcm`
- `kactivitymanagerd`
- `kde-cli-tools`
- `kdecoration`
- `kgamma`
- `kglobalacceld`
- `kmenuedit`
- `knighttime`
- `kpipewire`
- `ksshaskpass`
- `kwallet-pam`
- `kwayland`
- `kwayland-integration`
- `kwrited`
- `layer-shell-qt`
- `libkscreen`
- `libksysguard`
- `ocean-sound-theme`
- `oxygen-sounds`
- `plasma-activities`
- `plasma-dialer`
- `plasma-disks`
- `plasma-firewall`
- `plasma-thunderbolt`
- `plasma-workspace-wallpapers`
- `plymouth-kcm`
- `polkit-kde-agent-1`
- `qqc2-breeze-style`
- `sddm-kcm`
- `spacebar`

Next gate after a PASS preflight: `plasma-level0-materialization`. Package execution remains locked after that transition until package contracts/materialization evidence are promoted and an explicit build gate is authorized.


## Execution checkpoint

The reusable Frameworks milestone cache is now **PASS**:

```text
/var/lib/supralinux/images/milestones/frameworks-6.30-pass.qcow2
sha256=ec38f99e306d5a13333d6b247a9433b3526ec4a6d1a272631242c68df56c3e97
```

It contains the retained Frameworks 6.30 PASS binary pool and a prewarmed Resolute sbuild rootfs. It is an execution cache only; artifacts/manifests remain canonical. No Plasma package execution was started by creating this checkpoint, and Plasma package Attempts remain zero.


## Level 0 materialization

The synthetic source-materialization infrastructure preflight is **PASS** from PR CI router run `37161541259`, job `111316001972`, artifact `11286979140`.

The materialization gate, closed on 2026-10-04, processes all 34 Level 0 nodes without running `sbuild`:

- KDE Plasma 6.7.5 tarballs are downloaded, SHA-256 checked and detached-signature verified against fingerprint `0AAC775BB6437A8D9AF7A3ACFE0784117FBCE11D`;
- Ubuntu Resolute-family source references are downloaded and extracted;
- only the Ubuntu `debian/` packaging trees and metadata are retained as technical references;
- `discover` is explicitly mapped to Ubuntu source `plasma-discover`;
- candidate SupraLINUX Debian versions were deferred until materialization evidence was closed;
- package execution remains locked and Plasma package Attempts remain zero.

The materialization job processes independent Level 0 nodes concurrently (maximum six) and produces one retained artifact that can be cached for subsequent package preparation.

## Materialization closure and candidate versions

PR CI router run `37226892171`, job `111508551648`, is PASS for all 34 selected sources. Artifact `11312113744` has SHA-256 `85e5d78bd4f6bba9de810a01894669dee9efde9341b685c8a32f42794e09c3c8`; the retained `result.json` has SHA-256 `bf58313053bfa90f33d13b4b66872abea56b2bc6ef9f8f266cde7dde296bc8de`.

The complete original ZIP is retained locally under `.artifacts/plasma-level0-3177bcda/`. Every source/reference hash and all detached signatures were reverified locally. Source metadata is retained in `manifests/evidence/kde-plasma-level0-materialization-result.json`.

`scripts/assign-plasma-candidate-versions.py` assigned all 34 candidate versions and compared them with every captured Ubuntu source version using dpkg. The 16 non-zero Ubuntu epochs were preserved. If Ubuntu already carries the selected upstream version, the planner uses a revision that supersedes Ubuntu's revision; if Ubuntu carries a newer upstream version, it requires transition review. No pin priority substitutes for version ordering.

The current gate is `plasma-level0-packaging-preparation`. The source-materialization gate is closed and no longer runs on ordinary PR updates. Next work is to adapt and validate the captured packaging against the selected upstream source, its dependency/features contract, source construction and package tests before an authoritative package build. Plasma package Attempts remain zero.
