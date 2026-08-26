# SupraLINUX Roadmap

This roadmap prioritizes integration correctness before branding or custom applications.

## Phase 0 — Foundation

Status: **complete**

- [x] Create private GitHub organization/repository
- [x] Establish `PROJECT_RULES.md`
- [x] Define Ubuntu 26.04 LTS base
- [x] Define KDE Plasma + Wayland baseline
- [x] Define DEB/APT + Flatpak policy
- [x] Define Snap-blocked-by-default policy
- [x] Define monorepo and branch model
- [x] Define versioning model
- [x] Finalize first generation codename: Aurora
- [x] Add initial packaging skeleton
- [x] Add initial test matrix

## Phase 1 — Minimal Ubuntu → complete vanilla Plasma

Goal: a clean Ubuntu 26.04 base can become the SupraLINUX baseline through packages/configuration only.

- [x] Define the first candidate Ubuntu 26.04 base composition (`supralinux-base`); clean validation still pending
- [x] Inventory the first Plasma 6 package/KCM surface available in Ubuntu 26.04; audit remains iterative
- [ ] Freeze the exact `supralinux-desktop` dependency set after clean-system evidence
- [ ] Ensure Wayland session boots reliably
- [ ] Ensure SDDM integration is correct
- [ ] Validate Polkit integration
- [ ] Validate NetworkManager integration
- [ ] Validate PipeWire/audio integration
- [ ] Validate portals and screen sharing
- [ ] Validate KRDP/KRDC integration where shipped
- [ ] Validate Bluetooth
- [ ] Validate printing/scanning baseline
- [ ] Validate removable-media handling
- [ ] Validate Samba/network-share UX
- [ ] Validate archive/file-format support
- [ ] Validate language/locale/XDG directory behavior
- [ ] Validate power management and suspend/resume
- [ ] Validate Flatpak desktop integration
- [x] Build repeatable development DEB package prototypes
- [x] Add Ubuntu 26.04 package-build/APT-resolution CI gate
- [ ] Build the first clean-system VM validation harness

**Exit criterion:** Plasma looks close to upstream and every feature SupraLINUX exposes in the baseline works without requiring the user to discover missing packages.

## Phase 2 — SupraLINUX packaging

Development prototypes already exist for `supralinux-base`, `supralinux-desktop`, and `supralinux-snap-policy`; the checkboxes below mean release-ready/frozen packages, not merely that a development directory exists.

- [ ] `supralinux-base`
- [ ] `supralinux-desktop`
- [ ] `supralinux-settings`
- [ ] `supralinux-release`
- [ ] `supralinux-artwork`
- [ ] `supralinux-default-apps`
- [ ] `supralinux-flatpak`
- [ ] `supralinux-installer`
- [ ] `supralinux-welcome`
- [ ] `supralinux-meta`
- [ ] `supralinux-snap-policy`

**Exit criterion:** installing SupraLINUX packages on a clean compatible Ubuntu base reproducibly produces the intended system.

## Phase 3 — SupraLINUX APT repository

- [ ] Define repository metadata layout
- [ ] Create `testing/main`
- [ ] Create `stable/main`
- [ ] Design signing-key workflow
- [ ] Keep signing key outside public web-serving infrastructure
- [ ] Publish repository through HTTPS
- [ ] Add explicit package promotion flow testing → stable

Target endpoint: `repo.supralinux.com` (provisional until infrastructure is deployed).

## Phase 4 — Live system and installer

- [ ] Build reproducible live rootfs
- [ ] Build bootable UEFI ISO
- [ ] Integrate Calamares
- [ ] Locale/language installation tests
- [ ] ext4 automatic partitioning
- [ ] manual partitioning
- [ ] user creation
- [ ] bootloader installation
- [ ] first boot verification

## Phase 5 — Out-of-box desktop capability set

Only after the Plasma baseline is complete:

- [ ] Browser decision + redistribution review
- [ ] Office suite decision
- [ ] PDF reader/editor decision + redistribution review
- [ ] Common archives including RAR capability
- [ ] Common media codecs
- [ ] Audio/video player
- [ ] Torrent client
- [ ] Network sharing baseline
- [ ] Other everyday desktop capabilities

## Phase 6 — Quality and hardware validation

- [ ] Intel graphics
- [ ] AMD graphics
- [ ] NVIDIA graphics
- [ ] laptops
- [ ] Wi-Fi
- [ ] Bluetooth
- [ ] audio
- [ ] suspend/resume
- [ ] multi-monitor
- [ ] HiDPI
- [ ] UEFI
- [ ] Secure Boot strategy validation
- [ ] dual boot
- [ ] upgrades

## Phase 7 — Minimal SupraLINUX visual identity

Only after the baseline is reliable:

- [ ] Base color integration (`#51A2DA`)
- [ ] Wallpaper
- [ ] SDDM
- [ ] Plymouth
- [ ] GRUB
- [ ] Plasma splash
- [ ] motion/animation specification

## Phase 8 — SupraLINUX applications

Future work, individually justified:

- [ ] Supra Control Center
- [ ] Supra Store
- [ ] Supra Menu
- [ ] Supra Clock/widget
- [ ] Supra Backup
- [ ] Supra Recovery
- [ ] Supra Welcome/help experience

These components should extend/integrate with Plasma rather than requiring a Plasma fork.

## Phase 9 — Recovery and backup platform

- [ ] User-data backup
- [ ] Plasma personalization backup
- [ ] application inventory/restore
- [ ] compatible app settings restore
- [ ] external-drive target
- [ ] Nextcloud/WebDAV target
- [ ] secure handling of credentials/secrets
- [ ] reset preserving user files
- [ ] full reset
- [ ] local recovery environment
- [ ] signed cached recovery image
- [ ] online recovery design

## Phase 10 — Public release

- [ ] Internal alpha
- [ ] Public alpha
- [ ] Beta
- [ ] Release candidate
- [ ] Signed APT repository
- [ ] Published ISO checksums
- [ ] Documentation
- [ ] Upgrade/recovery testing
- [ ] SupraLINUX 1.0.0

Stable release promotion is always explicit; CI success alone never publishes stable.
