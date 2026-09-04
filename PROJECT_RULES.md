# SupraLINUX — Project Rules and Product Contract

This file is the authoritative, living set of rules for SupraLINUX. Any architectural, product, UX, packaging, security, repository, recovery, compatibility, localization, or quality decision that becomes a project rule MUST be recorded here in the same change that implements or adopts it.

Status labels used below:
- **ACCEPTED**: current project rule.
- **PROVISIONAL**: direction agreed in principle but implementation details are still open.
- **FUTURE**: intentional roadmap item; do not let it distort the first functional baseline.
- **REJECTED**: explicitly excluded from the current product architecture/baseline unless a later documented decision reopens it with new evidence.

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
- **ACCEPTED** Qt remains owned by Ubuntu unless a separately documented architecture decision proves that replacing it is necessary.
- **ACCEPTED** Wayland runtime, systemd, PipeWire, NetworkManager and comparable base-platform infrastructure remain owned by Ubuntu unless a separately documented architecture decision proves that an override is necessary.
- **ACCEPTED** Do not fork the kernel, Mesa, Qt, Plasma, systemd, APT, NetworkManager, PipeWire, or similar foundational components without a documented technical need.
- **ACCEPTED** Rebuilding or backporting an unmodified official KDE release as a DEB does not by itself constitute a Plasma fork. Source patches beyond packaging/integration must be individually justified and documented.
- **ACCEPTED** SupraLINUX is derived from Ubuntu base/minimal, not from Ubuntu Desktop and not from `kubuntu-desktop`.

## 3. KDE Plasma baseline

- **ACCEPTED** Desktop environment: KDE Plasma.
- **ACCEPTED** User desktop-session policy: SupraLINUX ships and exposes Plasma on Wayland as the supported desktop session; a selectable Plasma X11 desktop session is not part of the default Aurora baseline.
- **ACCEPTED** `plasma-session-x11`, `startplasma-x11`, and the Plasma X11 session desktop entry must be absent from the default Aurora baseline.
- **ACCEPTED — X11 compatibility rule:** the Wayland desktop-session policy is not a policy to purge X11 technology. XWayland, X11 libraries, protocols, utilities, and other compatibility components required by applications or Plasma features must remain available when they are needed for a complete and comfortable desktop. Do not remove working functionality merely for architectural purity.
- **ACCEPTED** XWayland is part of the intended Aurora baseline so legacy X11 applications can run inside the Plasma Wayland session.
- **ACCEPTED** Aurora's current SDDM greeter baseline uses KWin Wayland and is configured by `supralinux-settings`; the greeter path must be validated independently from the user Plasma session.
- **ACCEPTED** Initial goal: the most vanilla Plasma experience practical, while making every selected and exposed Plasma feature work end-to-end.
- **ACCEPTED** The first milestone is integration and completeness, not visual differentiation.
- **ACCEPTED** Do not modify/fork Plasma merely to make SupraLINUX look different. SupraLINUX should develop on top of Plasma using supported extension and integration mechanisms.
- **ACCEPTED — KDE release policy:** SupraLINUX seeks the newest official stable KDE release that is technically compatible with the Aurora Ubuntu LTS platform. SupraLINUX is not automatically limited to the KDE version frozen in Ubuntu 26.04, but beta, RC, git/master and otherwise experimental KDE builds are not product candidates.
- **ACCEPTED — Promotion rule:** a newer KDE release never enters the supported product automatically. It must pass reproducible package builds, dependency closure, clean installation, upgrade, rollback, boot/session regression, runtime-surface reconciliation and applicable functional certification before promotion from testing to stable.
- **ACCEPTED — Platform boundary:** a newer KDE release is not by itself sufficient reason to replace Ubuntu's Qt, Wayland runtime, Mesa, kernel or other foundational platform layers. Crossing that boundary requires a separate architecture decision and its own qualification evidence.
- **PROVISIONAL — Aurora KDE stack candidate:** evaluate KDE Frameworks 6.29.x with Plasma/KWin 6.7.4 on Ubuntu 26.04 LTS using Ubuntu Qt 6.10.2. This is a qualification target, not yet the accepted Aurora release stack.
- **PROVISIONAL — KDE Gear policy:** KDE Gear is evaluated independently after the Plasma/Frameworks stack is qualified, with preference for the newest official stable release compatible with Aurora and subject to the same packaging, integration and certification discipline.
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
- **ACCEPTED** Ubuntu remains the source for the vast majority of base packages, security updates, kernel, Mesa, Qt, libraries, drivers and platform services.
- **ACCEPTED** SupraLINUX repositories contain SupraLINUX-owned packages and intentional documented overrides/backports; a qualified KDE stack may therefore be supplied by SupraLINUX rather than by Ubuntu when the KDE release policy requires it.
- **ACCEPTED** Do not mirror/copy Ubuntu packages into the SupraLINUX repository without a concrete reason.
- **ACCEPTED** When practical, KDE backports should reuse official upstream release tarballs and maintained Debian/Kubuntu packaging rather than inventing unrelated packaging or installing manually into `/usr/local`.
- **ACCEPTED** KDE packages maintained by SupraLINUX must record source provenance, exact version, packaging base, SupraLINUX delta, maintenance/security responsibility, dependency rationale, upgrade/rollback behavior and removal condition.
- **ACCEPTED** Initial SupraLINUX channels: `stable` and `testing`, initially with a simple `main` component.
- **ACCEPTED** An Ubuntu-derived package override must document: why the fork/override exists, what differs from Ubuntu, maintenance responsibility, and the condition under which the override can be removed.
- **ACCEPTED** Do not give every package from the SupraLINUX origin a blanket priority that accidentally overrides Ubuntu. Intentional overrides must be explicit through package versions and/or scoped APT pinning.
- **ACCEPTED** Stable/testing repository publication is generation-based: every promoted state must have an immutable generation identity and an auditable manifest of exact Ubuntu/SupraLINUX package inputs, hashes and qualification evidence.
- **ACCEPTED** Qualification that depends on Ubuntu archive state must record an exact Ubuntu Snapshot Service timestamp or equivalently immutable Ubuntu archive identity.
- **PROVISIONAL** Public repository endpoint: `repo.supralinux.com`, hosted on SupraLINUX infrastructure and served as signed static APT repository content.
- **PROVISIONAL** Package-generation rollback will be designed and certified independently of filesystem snapshots; rollback must target explicit known repository generations and prove package/configuration transition safety.

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
- **FUTURE** Btrfs, filesystem snapshots/subvolumes, filesystem-level rollback, and advanced filesystem recovery can be added only after the complete design and failure modes are understood. They are not a prerequisite for package-generation rollback.

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
- **PROVISIONAL** TPM-backed full-disk encryption is deferred from the Aurora baseline pending a separate SupraLINUX/Calamares architecture and hardware qualification. Conflicting current Ubuntu 26.04 documentation maturity signals and known limitations must be resolved before promotion.

## 14. Security and release integrity

Before public release the project MUST have:

- **ACCEPTED** Signed APT repository metadata/packages as appropriate.
- **ACCEPTED** Signing keys protected and separated from the public web-serving container/infrastructure.
- **ACCEPTED** HTTPS for public repository delivery.
- **ACCEPTED** SHA-256 or stronger published checksums for ISO artifacts.
- **ACCEPTED** A documented, explicit promotion process from testing to stable.
- **ACCEPTED** Stable publication must not happen automatically merely because CI builds successfully.
- **ACCEPTED** Secure Boot work should initially rely on Ubuntu kernel/shim/GRUB mechanisms instead of introducing a custom kernel/signing stack.
- **ACCEPTED** If SupraLINUX overrides an Ubuntu KDE package, SupraLINUX assumes responsibility for tracking applicable upstream KDE security fixes and publishing qualified updates for the override; Ubuntu updates to the replaced binary package cannot be assumed to secure the SupraLINUX override automatically.
- **ACCEPTED** Release artifacts and maintained SupraLINUX package outputs must gain machine-readable provenance/SBOM coverage appropriate to the artifact before public release; provenance complements rather than replaces reproducible-build evidence.

## 15. Quality contract

- **ACCEPTED** The core product goal is a highly integrated, complete Plasma desktop, not merely a customized theme.
- **ACCEPTED** A feature visible in the shipped UI is considered incomplete until its dependencies, permissions, backend, happy path, and common failure path have been tested.
- **ACCEPTED** The project must maintain explicit test coverage/checklists for desktop integration areas before public release.
- **ACCEPTED** Prefer root-cause integration fixes and package dependencies over user-facing instructions that say “install package X manually” for functionality SupraLINUX claims to ship.
- **ACCEPTED** Do not hide missing dependencies behind first-run setup chores. Features intended as part of the base experience should already work after installation.
- **ACCEPTED** Localization is part of quality. A release is not considered correctly integrated if the installer says one language while the first session, user directories, formats, or core Plasma/Qt UI are left partially in another language because required locale/translation setup was missing or ran in the wrong order.
- **ACCEPTED** CI that performs real package installation must use an isolated disposable environment/rootfs rather than mutating the hosted runner into something that could hide missing base dependencies.
- **ACCEPTED** Certification evidence is version-scoped. A PASS obtained on one KDE/Qt/runtime stack must not be silently carried forward after a package-stack change that can affect the tested behavior; the applicable regression gates must run again.
- **ACCEPTED** Functional certification is organized by subsystem with explicit package-to-gate regression ownership. A changed input may reuse a PASS only when irrelevance to that gate is proven, not assumed.

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

A SupraLINUX-maintained package set for an official stable KDE release is permitted by the KDE release policy and is not itself a Plasma fork. The first objective remains a vanilla, complete, reliable Plasma system on Ubuntu LTS. Product-specific SupraLINUX applications and deeper UX changes come after that baseline is proven.

## 18. Aurora Integration Qualification contract

The detailed adopted roadmap is `docs/AURORA_INTEGRATION_QUALIFICATION_ROADMAP.md`.

- **ACCEPTED** KDE Stack Qualification remains the prerequisite for downstream Aurora Integration Qualification (AIQ). Do not mix unrelated feature work into an open KSQ gate merely because the eventual feature belongs in Aurora.
- **ACCEPTED** After KSQ, Aurora integration is certified through ordered subsystem gates covering runtime/dependency surface, install/update/rollback, display/GPU, portals/Flatpak/remote desktop, audio/Bluetooth, networking/VPN, printing/scanning/OCR, multimedia/codecs, firmware/power, accessibility/localization, diagnostics/debug evidence, recovery/encryption, and final release integrity.
- **ACCEPTED** SupraLINUX maintains a KDE LTS fix-parity review for relevant Kubuntu/Ubuntu 26.04 KDE fixes whenever SupraLINUX ships a newer maintained KDE stack. Each material fix must be proven already present, incorporated through the qualified source path, proven not applicable, or treated as an unresolved blocker where severity requires it.
- **ACCEPTED** XDG portal/Flatpak support is an end-to-end contract, including applicable file chooser, URI opening, printing, screenshot, screencast, remote desktop, notifications, device/media permissions and persistence behavior; installing Flatpak alone is not sufficient.
- **ACCEPTED** Audio/Bluetooth qualification includes A2DP and headset microphone/call profiles, reconnection, suspend/resume and routing behavior. LE Audio/BAP/LC3 remains **PROVISIONAL** until certified on representative hardware; Ubuntu PipeWire/WirePlumber remain platform owners.
- **ACCEPTED** Baseline VPN integration targets maintained NetworkManager paths including WireGuard, OpenVPN, IKEv2/strongSwan and OpenConnect where packaged/qualified. **REJECTED**: PPTP as a SupraLINUX baseline VPN because the protocol is cryptographically broken and the NetworkManager plugin is unmaintained upstream.
- **ACCEPTED** Printing/scanning is driverless-first: IPP Everywhere/AirPrint-class printing through CUPS and eSCL/AirScan/WSD scanning through qualified SANE/`sane-airscan`/`ipp-usb` integration where technically applicable. Legacy drivers remain compatibility paths, not the architecture for modern devices.
- **ACCEPTED** If a shipped application exposes OCR, officially supported installation languages must include the corresponding maintained OCR language resources where available; users must not be required to discover missing language packages after installation.
- **ACCEPTED** Accessibility completeness includes the external runtime pieces required by exposed Plasma accessibility functions, including a qualified screen-reader/speech path when that control is shipped. Missing supporting applications/backends are product dependencies, not post-install instructions.
- **ACCEPTED** Firmware updates through Ubuntu-compatible `fwupd`/LVFS integration are part of the planned complete desktop baseline when hardware supports them.
- **ACCEPTED** Ubuntu's power-profiles-daemon/UPower/PowerDevil path remains the default power-policy architecture. **REJECTED**: installing TLP or another parallel default policy manager without first proving a concrete deficiency and separately qualifying ownership/conflicts.
- **ACCEPTED** Display/GPU qualification covers representative Intel, AMD and Ubuntu NVIDIA paths, hybrid graphics, external displays, suspend/resume, fractional scaling, XWayland compatibility and mixed-DPI. HDR/ICC/VRR support is **PROVISIONAL** until the complete relevant matrix passes; feature presence alone is not certification.
- **ACCEPTED** SupraLINUX will provide a local, explicit, privacy-conscious diagnostic collection path and retain/index debug symbols/Build-IDs for SupraLINUX-owned binaries and maintained KDE overrides so released crashes remain diagnosable.
- **REJECTED** Technology-preview/experimental Plasma functionality as an Aurora product baseline merely because it exists upstream. It may be researched in isolation and reconsidered after upstream stabilization plus SupraLINUX qualification.
- **PROVISIONAL** GitHub-hosted `ubuntu-26.04` may be used for qualification experiments while GitHub labels it Public preview, but it is not accepted as final SupraLINUX release-build infrastructure until GitHub promotes it out of preview and SupraLINUX reruns the infrastructure qualification. Do not weaken AppArmor/host security, require privileged Docker or add broad outer privileges merely to force that architecture to pass.
