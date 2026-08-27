# SupraLINUX — Project Rules and Product Contract

This file is the authoritative, living set of rules for SupraLINUX. Any architectural, product, UX, packaging, security, repository, recovery, compatibility, localization, or quality decision that becomes a project rule MUST be recorded here in the same change that implements or adopts it.

Status labels used below:
- **ACCEPTED**: current project rule.
- **PROVISIONAL**: direction agreed in principle but implementation details are still open.
- **FUTURE**: intentional roadmap item; do not let it distort the first functional baseline.

## 1. Identity

- **ACCEPTED** Brand name: `SupraLINUX`.
- **ACCEPTED** System ID: `supralinux`.
- **ACCEPTED** Package prefix: `supralinux-*`.
- **ACCEPTED** GitHub organization: `SupraLINUX`.
- **ACCEPTED** Primary project domain: `supralinux.com`.
- **ACCEPTED** Primary brand color: RGB `#51A2DA`; RGBA `#51A2DAFF`.
- **ACCEPTED** Do not alternate technical naming with `Supra Linux`, `SupraLinux`, `Supralinux`, `SLinux`, or other spellings.

## 2. Base system

- **ACCEPTED** Base distribution: Ubuntu 26.04 LTS.
- **ACCEPTED** Initial architecture: amd64.
- **ACCEPTED** Package management: DEB + APT.
- **ACCEPTED** Kernel: Ubuntu kernel.
- **ACCEPTED** Mesa: Ubuntu packages.
- **ACCEPTED** NVIDIA driver infrastructure: Ubuntu packages and mechanisms.
- **ACCEPTED** Do not fork the kernel, Mesa, Qt, Plasma, systemd, APT, NetworkManager, PipeWire, or similar foundational components without a documented technical need.
- **ACCEPTED** SupraLINUX is derived from Ubuntu base/minimal, not from Ubuntu Desktop and not from `kubuntu-desktop`.

## 3. KDE Plasma baseline

- **ACCEPTED** Desktop environment: KDE Plasma.
- **ACCEPTED** Desktop-session policy: Wayland only. SupraLINUX does not ship or expose a Plasma X11 desktop session in the default system.
- **ACCEPTED** `plasma-session-x11`, `startplasma-x11`, and the Plasma X11 session desktop entry must be absent from the default Aurora baseline.
- **ACCEPTED** Xorg components may be installed when required by non-user-session infrastructure such as the current SDDM greeter. Their presence does not make an X11 desktop session supported or selectable.
- **ACCEPTED** XWayland may be present so legacy X11 applications can run inside the Plasma Wayland session. XWayland compatibility is not an X11 desktop-session mode.
- **ACCEPTED** Initial goal: the most vanilla Plasma experience practical, while making every selected and exposed Plasma feature work end-to-end.
- **ACCEPTED** The first milestone is integration and completeness, not visual differentiation.
- **ACCEPTED** Do not modify/fork Plasma merely to make SupraLINUX look different. SupraLINUX should develop on top of Plasma using supported extension and integration mechanisms.
- **ACCEPTED — Feature completeness rule:** if a feature/control is exposed to the user in the shipped Plasma experience, its required backend/dependencies must be present and the feature must be tested. Do not ship visible controls that fail because a dependency or backend was omitted.
- **ACCEPTED** Examples of completeness areas include remote desktop, Flatpak permissions integration, networking, audio, Bluetooth, printing, archive/file-format support, network shares, portals, language support, power management, removable media, and other features presented by the desktop.

## 4. Applications and user-ready baseline

- **ACCEPTED** SupraLINUX must be useful immediately after installation. Avoid both bloatware and artificial minimalism that forces users to research/install obvious basics.
- **ACCEPTED** Common everyday capabilities should work out of the box: web browsing, office documents, PDF handling, archives, common media codecs, music/video playback, common network sharing, and other broadly expected desktop tasks.
- **ACCEPTED** Common archive formats, including RAR extraction, are part of the intended baseline, subject to redistribution/license review for any non-free component.
- **ACCEPTED** KDE applications are preferred for the vanilla baseline when they are suitable, but being a KDE application is not by itself a reason to ship it.
- **PROVISIONAL** Intended later defaults include Google Chrome as browser, JOPDF for PDF editing, LibreOffice for office work, and selected media/network utilities. Every third-party proprietary application must pass a redistribution/license review before it can be included in an ISO or SupraLINUX repository.
- **ACCEPTED** Do not ship hundreds of applications, large collections of tweaks, or opaque post-install scripts merely to appear feature-rich.

## 5. Flatpak and Snap

- **ACCEPTED** Flatpak is supported and integrated into the desktop.
- **ACCEPTED** Snap is blocked by default and is not installed by default.
- **ACCEPTED** The default Snap block is owned by the reversible `supralinux-snap-policy` package rather than by ISO-only shell edits.
- **ACCEPTED** While the policy is active it must prevent both `snapd` and Plasma Discover's Snap backend from being installed automatically through APT.
- **ACCEPTED** SupraLINUX may later expose a user-facing control that removes the Snap block. Removing the block must not itself install Snap.
- **ACCEPTED** Once the user explicitly removes the block, normal APT behavior may install `snapd` if the user chooses packages/actions that require it.
- **ACCEPTED** The Snap policy must be implemented transparently and reversibly, not through brittle ad-hoc scripts.

## 6. SupraLINUX packages

Initial package split:

- `supralinux-base`
- `supralinux-desktop`
- `supralinux-settings`
- `supralinux-release`
- `supralinux-artwork`
- `supralinux-default-apps`
- `supralinux-flatpak`
- `supralinux-snap-policy`
- `supralinux-installer`
- `supralinux-welcome`
- `supralinux-meta`

Rules:

- **ACCEPTED** `supralinux-desktop` is the declarative selection/integration layer for the chosen Plasma desktop and its required backends.
- **ACCEPTED** `supralinux-settings` owns SupraLINUX defaults, not one-off shell modifications.
- **ACCEPTED** `supralinux-release` owns system identity/version metadata such as `/etc/os-release` and related release information.
- **ACCEPTED** `supralinux-artwork` owns wallpapers, logo assets, SDDM, Plymouth, GRUB, splash, avatars, installer branding, and related visual assets.
- **ACCEPTED** `supralinux-snap-policy` owns the default reversible APT policy that blocks Snap without patching APT and without installing Snap when the policy is removed.
- **ACCEPTED** Any setting or package selection that must survive rebuilds belongs in Git and/or a DEB package.

## 7. Ubuntu and SupraLINUX repositories

- **ACCEPTED** Installed systems use Ubuntu repositories and SupraLINUX repositories together.
- **ACCEPTED** Ubuntu remains the source for the vast majority of base packages, security updates, kernel, Mesa, Qt, KDE packages, libraries, and drivers.
- **ACCEPTED** SupraLINUX repositories contain only SupraLINUX-owned packages and intentional overrides/backports.
- **ACCEPTED** Do not mirror/copy Ubuntu packages into the SupraLINUX repository without a concrete reason.
- **ACCEPTED** Initial SupraLINUX channels: `stable` and `testing`, initially with a simple `main` component.
- **ACCEPTED** An Ubuntu-derived package override must document: why the fork/override exists, what differs from Ubuntu, maintenance responsibility, and the condition under which the override can be removed.
- **ACCEPTED** Do not give every package from the SupraLINUX origin a blanket priority that accidentally overrides Ubuntu. Intentional overrides must be explicit through package versions and/or scoped APT pinning.
- **PROVISIONAL** Public repository endpoint: `repo.supralinux.com`, hosted on SupraLINUX infrastructure and served as signed static APT repository content.

## 8. Installer, locale, and filesystems

- **ACCEPTED** Installer: Calamares with SupraLINUX configuration and branding.
- **ACCEPTED** First installer scope: language, keyboard, timezone, partitioning, user, bootloader, installation.
- **ACCEPTED** The language/locale selected in the installer must be fully established before the user's first graphical session starts.
- **ACCEPTED** Locale generation, Plasma/Qt translations, language support packages, and XDG user-directory localization are part of installation completeness, not optional post-install repair work.
- **ACCEPTED** `xdg-user-dirs` must be present and functional. On first login, standard directories such as Desktop, Documents, Downloads, Music, Pictures, Videos, Templates, and Public Share must be created/configured according to the user's selected locale when translations exist.
- **ACCEPTED** SupraLINUX must test that a clean install in each officially supported installation language produces correctly localized XDG user directories and a consistent `$LANG`/locale state before first use.
- **ACCEPTED** Do not blindly run `xdg-user-dirs-update --force` on every login. Directory creation/migration must preserve user data and user choices.
- **FUTURE** If the user changes language after installation, SupraLINUX should provide a safe, explicit migration path for localized XDG user-directory names rather than silently renaming populated folders.
- **ACCEPTED** Default filesystem for the first release: ext4.
- **FUTURE** Btrfs, snapshots, subvolumes, rollback, and advanced recovery can be added only after the complete design and failure modes are understood.

## 9. Reproducibility and ISO

- **ACCEPTED** The ISO is an output artifact, not the source of truth.
- **ACCEPTED** A clean build environment must be able to clone the project and reproduce the system/ISO through documented automation.
- **ACCEPTED** Do not rely on Cubic, manual chroot edits, undocumented hand edits, or remembered command sequences as part of a release build.
- **ACCEPTED** Desired build interface: a documented build command/script producing an ISO and cryptographic checksum.
- **ACCEPTED** Every persistent change must be represented in Git, packaging, or declarative build configuration.

## 10. Git and development model

- **ACCEPTED** The source repository is public during pre-alpha development to support transparent development and public CI.
- **ACCEPTED** Public repository visibility does not mean SupraLINUX has a supported release, supported ISO, stable APT repository, or release-ready software.
- **ACCEPTED** Public visibility without an explicit software license does not itself grant an open-source license; project licensing must be deliberately selected before public release.
- **ACCEPTED** Initial repository model: monorepo.
- **ACCEPTED** Primary branches: `main` for known-good state and `development` for active integration; feature branches may be used for larger work.
- **ACCEPTED** Do not split into many repositories until a component has a real independent lifecycle.

## 11. UX direction

- **ACCEPTED** Initial UX should stay close to upstream/vanilla Plasma until functionality is complete and tested.
- **PROVISIONAL** Animation timing and motion should later be tuned toward a polished, smooth feel comparable in pacing and consistency to macOS, without gimmicky effects or visual novelty for its own sake.
- **FUTURE** SupraLINUX may develop its own Control Center, software store, application launcher/menu, clock/taskbar widget, and other desktop components.
- **ACCEPTED** These future components should build on public/supported KDE, Qt, Linux desktop, D-Bus, KConfig, XDG, Flatpak, PackageKit/APT, and related interfaces where appropriate rather than forking Plasma unnecessarily.

## 12. Inter-application architecture

- **ACCEPTED** SupraLINUX-owned applications must not communicate by undocumented file poking or private implementation coupling when a stable interface is appropriate.
- **ACCEPTED** Cross-app/system functionality should use documented, versioned interfaces such as D-Bus APIs, stable schemas, systemd user/system services, XDG conventions, and supported KDE/Qt APIs as appropriate.
- **ACCEPTED** App configuration, data, cache, and state should follow XDG conventions unless a platform API requires otherwise.
- **ACCEPTED** APIs/schemas intended for other SupraLINUX components must be versioned and documented.
- **ACCEPTED** Compatibility between SupraLINUX applications is a product requirement, not an accidental side effect.

## 13. Backup, restore, and recovery roadmap

- **FUTURE** SupraLINUX should provide a polished backup/restore experience capable of restoring user data, desktop personalization, application selections, and supported application/system state after reinstall/reset.
- **FUTURE** Backup targets should be able to include local/external storage and network/cloud-compatible storage such as Nextcloud/WebDAV where practical.
- **FUTURE** Sensitive secrets/credentials must be handled explicitly and securely; the project must not claim to restore literally everything unless it can do so safely and reliably.
- **FUTURE** SupraLINUX should provide a user-facing `Reset system`/recovery mechanism with at least a factory-reset/reinstall path and an option to preserve user data when technically safe.
- **FUTURE** Recovery should support locally cached signed recovery media/image and may later support downloading a signed recovery image online.
- **ACCEPTED** Recovery images, manifests, and metadata must be authenticated/signed before use.

## 14. Security and release integrity

Before public release the project MUST have:

- **ACCEPTED** Signed APT repository metadata/packages as appropriate.
- **ACCEPTED** Signing keys protected and separated from the public web-serving container/infrastructure.
- **ACCEPTED** HTTPS for public repository delivery.
- **ACCEPTED** SHA-256 or stronger published checksums for ISO artifacts.
- **ACCEPTED** A documented, explicit promotion process from testing to stable.
- **ACCEPTED** Stable publication must not happen automatically merely because CI builds successfully.
- **ACCEPTED** Secure Boot work should initially rely on Ubuntu kernel/shim/GRUB mechanisms instead of introducing a custom kernel/signing stack.

## 15. Quality contract

- **ACCEPTED** The core product goal is a highly integrated, complete Plasma desktop, not merely a customized theme.
- **ACCEPTED** A feature visible in the shipped UI is considered incomplete until its dependencies, permissions, backend, happy path, and common failure path have been tested.
- **ACCEPTED** The project must maintain explicit test coverage/checklists for desktop integration areas before public release.
- **ACCEPTED** Prefer root-cause integration fixes and package dependencies over user-facing instructions that say “install package X manually” for functionality SupraLINUX claims to ship.
- **ACCEPTED** Do not hide missing dependencies behind first-run setup chores. Features intended as part of the base experience should already work after installation.
- **ACCEPTED** Localization is part of quality. A release is not considered correctly integrated if the installer says one language while the first session, user directories, formats, or core Plasma/Qt UI are left partially in another language because required locale/translation setup was missing or ran in the wrong order.
- **ACCEPTED** CI that performs real package installation must use an isolated disposable environment/rootfs rather than mutating the hosted runner into something that could hide missing base dependencies.

## 16. Versioning

- **ACCEPTED** Use three-part technical versions: `MAJOR.MINOR.PATCH`.
- **ACCEPTED** Patch releases (`1.0.1`, `1.0.2`, ...) are bug/security/integration fixes within a release line.
- **ACCEPTED** Minor releases (`1.1.0`, `1.2.0`, ...; public UI may show `1.1`, `1.2`) are meaningful feature/integration releases that remain on the same Ubuntu LTS base when practical.
- **ACCEPTED** Major releases (`2.0.0`, `3.0.0`, ...) normally correspond to a new Ubuntu LTS base or another compatibility/architecture boundary significant enough to justify a new generation.
- **ACCEPTED** A marketing codename identifies a major/base generation. The codename does not replace the numeric version used by packaging/update logic.
- **ACCEPTED** Generation 1 codename: `Aurora`.
- **ACCEPTED** Generation 1 base: Ubuntu 26.04 LTS.
- **ACCEPTED** Initial release identity: `SupraLINUX 1.0.0 - Aurora`.
- **ACCEPTED** Public branding may emphasize `SupraLINUX <major.minor> - <codename>` while diagnostics, package metadata, support tools, and release metadata retain the full technical version.
- **ACCEPTED** Version numbers do not “run out”: `1.9` may be followed by `1.10`, `1.11`, etc.

## 17. Scope discipline

Do not make these first-release goals unless a concrete need appears:

- custom kernel
- custom Mesa
- Plasma fork
- custom Qt
- new package manager
- new init system
- new filesystem
- full custom updater
- large application suite without clear user value

The first objective is a vanilla, complete, reliable Plasma system on Ubuntu LTS. Product-specific SupraLINUX applications and deeper UX changes come after that baseline is proven.
