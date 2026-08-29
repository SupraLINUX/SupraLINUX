# SupraLINUX Architecture

## Baseline

SupraLINUX is built from Ubuntu 26.04 LTS base/minimal. It does not inherit Ubuntu Desktop or the `kubuntu-desktop` metapackage.

Ubuntu owns the platform. SupraLINUX owns product composition and may own a qualified KDE desktop stack when that is required to satisfy the accepted KDE release policy.

```text
Ubuntu 26.04 LTS base
        │
        ├── kernel / firmware / drivers
        ├── systemd
        ├── APT / dpkg
        ├── NetworkManager
        ├── PipeWire
        ├── Mesa
        ├── Wayland runtime
        └── Qt
                │
                ▼
        SupraLINUX desktop layer
                │
        ├── qualified KDE Frameworks / Plasma / KWin
        ├── narrowly required KDE/protocol backports
        ├── supralinux-base
        ├── supralinux-desktop
        ├── supralinux-settings
        ├── supralinux-release
        ├── supralinux-artwork
        ├── supralinux-default-apps
        ├── supralinux-flatpak
        ├── supralinux-installer
        ├── supralinux-welcome
        └── supralinux-meta
```

## KDE stack status

The previously certified development baseline uses Ubuntu 26.04 KDE packages (Plasma 6.6.6 / Frameworks 6.24). That baseline remains useful historical evidence but is not frozen as Aurora's release stack.

The active qualification candidate is:

```text
Ubuntu 26.04 LTS
├── Qt 6.10.2                    Ubuntu
├── kernel / Mesa / Wayland      Ubuntu
├── KDE Frameworks 6.29.x        SupraLINUX candidate
├── Plasma 6.7.4                 SupraLINUX candidate
├── KWin 6.7.4                   SupraLINUX candidate
└── KDE Gear                     separate later review
```

The candidate is **PROVISIONAL** until `docs/KDE_STACK_QUALIFICATION.md` closes every required gate. A failed qualification returns Aurora to the last known-good architecture rather than forcing the newer stack into the product.

## Design rule

SupraLINUX integrates Plasma; it does not fork Plasma for identity. Upstream KDE/Qt extension points and Linux desktop interfaces are preferred over invasive patches.

Rebuilding official stable KDE source releases as reproducible DEBs is an integration/packaging responsibility, not permission to diverge arbitrarily from upstream. Prefer maintained Debian/Kubuntu packaging where technically valid, document every SupraLINUX delta, and keep patches minimal and removable.

A KDE update must not drag the whole Ubuntu platform forward merely because newer components exist. Qt, Wayland runtime, Mesa, kernel and other foundational layers stay on Ubuntu unless independent evidence and an explicit architecture decision justify crossing that boundary.

## Desktop completeness

For every feature exposed in the shipped desktop, the distribution must account for:

1. frontend
2. backend
3. runtime dependencies
4. permissions/policy
5. session integration
6. localization
7. installation state
8. tests

A visible control that fails because SupraLINUX omitted a required package or backend is a distribution defect.

## Package responsibilities

### `supralinux-base`

Base operating-system policy and SupraLINUX-wide dependencies that are not desktop-specific.

### `supralinux-desktop`

Declarative Plasma desktop selection and integration layer. This package is expected to pull in the complete set required for the features SupraLINUX ships as part of Plasma.

### `supralinux-settings`

SupraLINUX defaults and policy configuration. Persistent settings belong here rather than in undocumented post-install shell commands.

### `supralinux-release`

System identity, release metadata, version, codename metadata, and related files.

### `supralinux-artwork`

Brand assets: wallpaper, SDDM, Plymouth, GRUB, Plasma splash, avatars, installer branding, and related assets.

### `supralinux-default-apps`

The deliberate out-of-box application/capability baseline. Proprietary third-party software requires redistribution/license review before inclusion.

### `supralinux-flatpak`

Flatpak integration and policy.

### `supralinux-installer`

Calamares configuration, branding, and SupraLINUX installation integration.

### `supralinux-welcome`

Future first-run/help experience. It must not exist to finish an incomplete installation.

### `supralinux-meta`

Top-level metapackage(s) used to compose a complete SupraLINUX installation.

## Repositories

Installed systems use both Ubuntu and SupraLINUX repositories.

```text
Ubuntu repositories
├── base system
├── security updates
├── kernel
├── firmware
├── drivers
├── Mesa
├── Wayland runtime
├── Qt
└── most applications/libraries

SupraLINUX repository
├── SupraLINUX packages
├── settings
├── artwork
├── installer integration
├── intentional documented overrides/backports
└── qualified KDE Frameworks / Plasma / KWin when adopted
```

Initial SupraLINUX channels:

```text
stable/main
testing/main
```

There is no blanket higher APT priority for all SupraLINUX-origin packages. Overrides are explicit. New KDE builds enter `testing` first and require explicit promotion after qualification; CI success alone never means stable promotion.

SupraLINUX must not depend on a KDE neon runtime repository or another third-party binary repository to assemble the supported product. Such projects may be used as engineering references, but supported packages must have documented source provenance and be built under the SupraLINUX qualification model.

## Snap policy

Snap is blocked by default and `snapd` is not installed by default. The block must be reversible. A future SupraLINUX UI may remove the block, but removing it must not itself install Snap.

## Flatpak policy

Flatpak is a supported application layer and must be fully integrated with Plasma, including the desktop-facing configuration/permissions experience that SupraLINUX chooses to expose.

## Build model

The ISO is an artifact produced from declarative inputs:

```text
Ubuntu base
+ Ubuntu repositories
+ SupraLINUX repository/packages
+ live configuration
+ Calamares
= SupraLINUX ISO
```

Manual ISO remastering is not part of the release process.

## Future SupraLINUX applications

Future applications should communicate through documented interfaces where appropriate, including D-Bus, KConfig, XDG standards, systemd services, supported KDE/Qt APIs, PackageKit/APT, and Flatpak APIs. Public inter-component contracts must be versioned.
