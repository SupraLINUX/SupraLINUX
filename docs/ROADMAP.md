# SupraLINUX Roadmap

This roadmap prioritizes integration correctness before branding or custom applications.

## Phase 0 — Foundation

Status: **complete**

- [x] Create GitHub organization/repository
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
- [x] Mark repository as public pre-alpha development with no supported release/ISO

## Phase 1 — Minimal Ubuntu → complete vanilla Plasma

Goal: a clean Ubuntu 26.04 base can become the SupraLINUX baseline through packages/configuration only.

### Composition/session foundations

- [x] Define the first candidate Ubuntu 26.04 base composition (`supralinux-base`)
- [x] Inventory the first Plasma 6 package/KCM surface available in Ubuntu 26.04; audit remains iterative
- [ ] Freeze the exact `supralinux-desktop` dependency set after C4 evidence
- [x] Keep XWayland present for legacy X11 application compatibility in the Wayland desktop baseline
- [x] Add Ubuntu 26.04 package-build/APT-resolution CI gate
- [x] Add isolated clean Ubuntu 26.04 rootfs installation gate
- [x] Pass the clean-rootfs gate and record its resulting package set
- [x] Build and pass the first real bootable VM validation harness (C1)
- [x] Ensure SDDM reaches a working KWin Wayland greeter in the VM (C2)
- [x] Ensure the normal Plasma Wayland user session boots reliably (C3)
- [x] Validate XWayland application compatibility from inside the real Plasma Wayland session (C3)

### C4 — Feature integration certification

- [x] Define the executable C4 certification contract and subgate boundaries
- [x] C4.0 — Runtime surface/contract inventory and 100% coverage reconciliation
- [ ] C4.1 — System Settings / KWin / software-only desktop behavior
- [ ] C4.2 — Polkit / KWallet / privileged actions
- [ ] C4.3 — NetworkManager / Plasma-NM / VPN
- [ ] C4.4 — PipeWire / WirePlumber / Plasma audio
- [ ] C4.5 — Bluetooth / BlueDevil software path + hardware classification
- [ ] C4.6 — Flatpak / portal routing
- [ ] C4.7 — Screenshot / screencast / repeated screen sharing
- [ ] C4.8 — KRDP / RDP integration
- [ ] C4.9 — Printing / CUPS / virtual IPP job lifecycle
- [ ] C4.10 — UDisks / Solid / removable media
- [ ] C4.11 — Samba / KIO / KIO-FUSE
- [ ] C4.12 — PowerDevil / power/platform integration
- [ ] C4.13 — Locale / Plasma+Qt translations / XDG directories
- [ ] C4.14 — Accessibility
- [ ] C4.15 — Auxiliary integration / direct-dependency closure

The historical feature checkboxes below remain as product-level outcomes. They close only when their owning C4 subgate has provided the required evidence:

- [ ] Validate Polkit integration
- [ ] Validate NetworkManager integration
- [ ] Validate PipeWire/audio integration
- [ ] Validate portals and screen sharing
- [ ] Validate KRDP/KRDC integration where shipped
- [ ] Validate Bluetooth
- [ ] Validate printing baseline
- [ ] Classify scanning correctly according to whether Aurora exposes a scanner workflow
- [ ] Validate removable-media handling
- [ ] Validate Samba/network-share UX
- [ ] Classify archive/file-format support against the current exposed baseline; final everyday archive app capability remains Phase 5
- [ ] Validate language/locale/XDG directory behavior
- [ ] Validate power management and suspend/resume within C4 VM scope
- [ ] Validate Flatpak desktop integration

**Phase 1 exit criterion:** Plasma remains close to upstream and every feature SupraLINUX exposes in the baseline works without requiring the user to discover missing packages. Hardware-only claims remain explicitly separated until representative hardware testing.

## Phase 2 — SupraLINUX packaging

Development prototypes exist for `supralinux-base`, `supralinux-desktop`, `supralinux-settings`, and `supralinux-snap-policy`; the checkboxes below mean release-ready/frozen packages, not merely that a development directory exists.

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
- [ ] Scanner application/workflow decision if desired as an out-of-box capability
- [ ] Other everyday desktop capabilities

## Phase 6 — Quality and hardware validation

- [ ] Intel graphics
- [ ] AMD graphics
- [ ] NVIDIA graphics
- [ ] laptops
- [ ] Wi-Fi
- [ ] Bluetooth peripherals/audio
- [ ] audio hardware
- [ ] suspend/resume on representative systems
- [ ] multi-monitor
- [ ] HiDPI
- [ ] touchpad/touchscreen/tablet/controller where supported
- [ ] SMART-capable storage
- [ ] hybrid-GPU/sensor/platform integration where claimed
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
