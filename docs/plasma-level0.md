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
