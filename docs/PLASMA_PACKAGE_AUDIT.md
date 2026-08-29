# Plasma Package Audit — Historical Ubuntu KDE 6.6.6 baseline

Status: **HISTORICAL / VERSION-SCOPED; package composition and C1-C3/C4.0 evidence preserved while KDE Stack Qualification is active**.

Purpose: preserve the first broad Ubuntu 26.04 Plasma package composition that gave SupraLINUX an upstream-like KDE desktop and exposed the surfaces used to build the original C4 contract. This is now a regression/reference document, not a statement that Ubuntu's KDE versions are the final Aurora release stack.

This is not a copy of `kubuntu-desktop`. Kubuntu remains an important integration and packaging reference, but SupraLINUX does not inherit Kubuntu metapackages or third-party binaries automatically. For a newer KDE stack, maintained Debian/Kubuntu packaging may be used as the packaging base only after its dependencies/deltas are audited for Resolute.

The historical runtime/executable feature status lives in:

- `docs/PLASMA_INTEGRATION_MATRIX.md`
- `docs/C4_CERTIFICATION.md`

The active architecture gate is:

- `docs/KDE_STACK_QUALIFICATION.md`

## 1. Historical validation context

The first clean Ubuntu 26.04 / KDE 6.6.6 development candidate successfully:

- built the SupraLINUX packages as DEBs;
- resolved through APT under the SupraLINUX Snap policy;
- installed in an isolated clean Resolute rootfs;
- booted through C1;
- reached a real SDDM/KWin Wayland greeter through C2;
- reached a stable real Plasma Wayland user session with XWayland compatibility through C3;
- produced an accepted C4.0 runtime-surface reconciliation.

Those results prove composition/session viability for that exact stack. They do not prove feature completeness and they do not automatically transfer to Plasma/KWin/Frameworks replacements.

## 2. Historical REQUIRED-candidate areas

The pre-qualification `supralinux-desktop` candidate intentionally remained broader than a minimal KDE installation so C4 could test the complete intended surface.

| Area | Historical candidate package(s) | C4 owner / reason |
|---|---|---|
| Plasma shell/workspace | `plasma-desktop`, `plasma-workspace` | C3 prerequisite + C4.0/C4.1 surface inventory |
| Wayland session | `plasma-session-wayland` | C3 prerequisite |
| System Settings | `systemsettings` | C4.0/C4.1 |
| Qt/Plasma visual integration | `breeze`, `frameworkintegration6`, `plasma-integration` | baseline integration |
| GTK visual integration | `breeze-gtk-theme`, `kde-config-gtk-style` | C4.15 |
| Authentication UI | `polkit-kde-agent-1` | C4.2 real privileged action |
| Display manager/config | `sddm`, `sddm-theme-breeze`, `kde-config-sddm` | C2 prerequisite + C4.2 privileged config path |
| Storage/removable media | `udisks2` | C4.10 |
| Power | `upower`, `powerdevil`, `power-profiles-daemon` | C4.12 |
| Displays | `kscreen` | C4.1 virtual output + later HW |
| Screen locking | `kde-config-screenlocker` | C4.0/C4.1/session coverage |
| System information | `kinfocenter` | C4.15 |
| System monitoring | `ksystemstats` | C4.15 |
| Audio UI | `plasma-pa` | C4.4 |
| Audio stack | `pipewire-audio` | C4.4 |
| Bluetooth | `bluedevil`, `bluez` | C4.5 + later HW |
| Networking | `plasma-nm`, `network-manager` | C4.3 |
| Common VPN backends | `network-manager-openvpn`, `network-manager-openconnect` | C4.3 controlled tunnels |
| Mobile/radio integration | `modemmanager`, `rfkill` | C4.3/C4.15 justification |
| Platform sensors/GPU | `iio-sensor-proxy`, `switcheroo-control` | C4.12/C4.15 justification + HW |
| Portals | `xdg-desktop-portal`, `xdg-desktop-portal-kde`, `xdg-desktop-portal-gtk` | C4.6/C4.7 routing evidence |
| XDG user dirs | `xdg-user-dirs` | C4.13 |
| Keyboard data | `xkb-data` | C4.1 |
| Qt translations | `qt6-translations-l10n` | C4.13 |
| File/network abstraction | `kio6`, `kio-fuse`, `kio-extras` | C4.11 |
| KWallet login integration | `libpam-kwallet5` | C4.2 |
| Flatpak | `flatpak`, `kde-config-flatpak` | C4.6 |
| Remote Desktop server | `krdp` | C4.8 |
| Printing | `print-manager`, `cups`, `cups-client`, `cups-filters` | C4.9 |
| Network sharing | `kdenetwork-filesharing`, `samba` | C4.11 |
| Accessibility | `at-spi2-core`, `orca`, `speech-dispatcher` | C4.14 |
| SMART surface | `plasma-disks` | C4.10/C4.15 + HW |
| Virtual keyboard | `plasma-keyboard` | C4.1/C4.15 |
| Crash/credential UI helpers | `drkonqi`, `ksshaskpass`, `pinentry-qt` | C4.15 |

This table captures the historical broad candidate. It is not proof that every entry must remain a hard dependency after the KDE stack and C4 are finalized.

## 3. KWin and Plasma KCM surface

The detailed historical package-derived KCM inventory remains in `docs/KCM_AUDIT.md`.

The accepted historical C4.0 gate used live discovery to compare the actual installed KCM/KWin/integration surface with a versioned coverage manifest. If a new KDE stack is adopted, C4.0 must be regenerated from that live runtime rather than editing this table to predict the result.

Static package research is therefore an input, not the final source of truth for coverage.

## 4. Feature-completeness decisions promoted into the historical candidate

### Flatpak

Historical candidate:

- `flatpak`
- `kde-config-flatpak`

Reason: Flatpak is a first-class SupraLINUX application layer. C4.6 must prove actual sandbox/permission behavior before the hard dependency classification is frozen.

### Remote Desktop

Historical hard candidate:

- `krdp`

`krdc` remained `Recommends` and must not be automatically treated as a certified baseline application. C4.8 decides whether the client remains optional or is promoted later.

### Printing

Historical candidate:

- `print-manager`
- `cups`
- `cups-client`
- `cups-filters`

C4.9 must exercise a real controlled IPP job lifecycle, not only package/service presence.

### Network sharing

Historical candidate:

- `kdenetwork-filesharing`
- `samba`
- `kio-extras`
- `kio-fuse`

C4.11 verifies both remote SMB consumption and local share creation/access. `samba` remains explicit until evidence proves a better split.

### VPN

Historical candidate:

- `network-manager-openvpn`
- `network-manager-openconnect`

C4.3 must establish real controlled tunnels and traffic. Other protocols remain unclaimed unless deliberately selected.

### Accessibility

Historical candidate:

- `at-spi2-core`
- `orca`
- `speech-dispatcher`

C4.14 determines whether the composition provides a genuinely usable assistive path or whether an additional provider/runtime is needed.

### SMART disk health

Historical candidate:

- `plasma-disks`

C4 can validate package/surface integration, but a meaningful physical SMART claim remains hardware-scoped. C4.15 may demote it if the dependency is inappropriate for the base image.

### GTK application coherence

Historical candidate:

- `breeze-gtk-theme`
- `kde-config-gtk-style`

C4.15 must prove the supported configuration path rather than assuming installation equals coherence.

## 5. Discover / PackageKit / Snap interaction — resolver issue CLOSED, product decision OPEN

The previous package-audit blocker was that Ubuntu's `plasma-discover` recommends `plasma-discover-backend-snap` and APT normally installs recommendations.

That resolver risk is no longer an implementation blocker: the shipped `supralinux-snap-policy` has been implemented and CI verifies that Discover resolves under the policy without pulling either the Snap backend or `snapd`.

This does **not** automatically promote Discover into the hard `supralinux-desktop` dependency set.

Current product decision remains:

- Snap resolver policy: implemented/validated;
- Discover baseline role: still a later product/software-management decision;
- no Snap backend in Aurora's default policy state.

Any changed dependency/recommendation graph in the candidate KDE stack must be re-audited rather than assuming the 6.6.6 resolver result is unchanged.

## 6. Portal backend question — TO BE CERTIFIED AFTER STACK QUALIFICATION

The historical `supralinux-desktop` installs both:

- `xdg-desktop-portal-kde`;
- `xdg-desktop-portal-gtk`.

This is an explicit candidate policy, not an unresolved package-presence question. `docs/PORTAL_POLICY.md` defines KDE as primary and GTK as compatibility fallback candidate.

Once C4 resumes, C4.6 must record effective routing and determine from runtime evidence whether the GTK backend is required and whether it stays out of KDE-specific interfaces.

Only after C4.6 may the GTK backend be kept or removed from the final candidate.

## 7. Deliberately unresolved capabilities

These remain outside the hard candidate until policy/testing is adequate:

| Capability | Package(s) | Reason not yet hard baseline |
|---|---|---|
| Firewall KCM | `plasma-firewall` + backend | No selected/supported firewall policy |
| Thunderbolt | `plasma-thunderbolt` + backend | Physical authorization testing required |
| Plasma Vaults | `plasma-vault` + crypto backends | Complete lifecycle/recovery design required |
| Fingerprint | `libpam-fprintd` / `fprintd` | Auth-stack + hardware validation required |
| KDE Connect | `kdeconnect` | Deliberate app/product decision |
| Browser integration | `plasma-browser-integration` | Wait for browser/default-app policy |
| Scanner workflow | scanner app/backend stack | No scanner UI/app currently exposed by baseline |
| Archive/RAR workflow | Ark/backend choices | Phase 5 capability unless runtime discovery exposes a current surface |
| Firmware UI | `fwupd` + UI | Coupled to store/updater product decision |

The new KDE stack's runtime may add/remove surfaces. Do not pre-classify those changes until KSQ-7/C4.0 discovery provides evidence.

## 8. Explicit non-inheritance from Kubuntu

The following remain NOT automatically inherited:

- `kubuntu-settings-desktop`;
- Kubuntu wallpapers/branding/Plymouth themes;
- `plasma-distro-release-notifier`;
- `plasma-discover-backend-snap`;
- `snapd`;
- Firefox Ubuntu Snap transition package;
- games and discretionary applications;
- Ubuntu/Kubuntu-specific helpers without a SupraLINUX architectural reason;
- duplicate applications merely because Kubuntu recommends them.

Using Kubuntu's maintained source packaging for a KDE source package does not mean adopting the Kubuntu desktop product. Every binary dependency and Ubuntu/Kubuntu-specific patch still needs a SupraLINUX reason.

## 9. Dependency-chain observations retained from historical research

- `plasma-session-wayland` expressed the intended Wayland session relationship and pulled the appropriate KWin Wayland/session chain in the historical baseline.
- KWin Wayland pulled XWayland compatibility; SupraLINUX intentionally retains that compatibility path.
- `pipewire-audio` is Ubuntu's desktop PipeWire abstraction and brings the normal compatibility/WirePlumber/Bluetooth-audio pieces through its dependency chain.
- Ubuntu retained the package name `libpam-kwallet5` for the audited KWallet PAM integration.
- `kio-extras` materially expanded KIO protocol/device support and remained a candidate because SupraLINUX intends common network/file protocols to work out of the box.

Every KDE-package-specific relationship must be rechecked against the candidate source packages before adoption.

## 10. Metapackage state during KDE Stack Qualification

`supralinux-desktop` on `development` remains the known historical broad candidate until the new stack is proven. The feature branch may introduce prototype packaging, but `development` must not pretend the candidate KDE stack is already accepted.

Do not reduce or expand the release dependency set merely to optimize package count during architecture qualification.

If the new stack is adopted, its regenerated C4.0 and later C4 defects may justify isolated dependency/configuration changes. After C4 closes, every direct dependency must be one of:

- tested and justified;
- hardware-dependent but product-justified;
- demoted/removed.

Only then should the exact dependency set be considered for freeze.

## 11. Immediate next steps

The previous clean-rootfs/C1-C3/C4.0 work is historical and complete for KDE 6.6.6. The active package sequence is now:

1. execute KSQ-0 source/dependency inventory in `docs/KDE_STACK_QUALIFICATION.md`;
2. build the newer KDE stack reproducibly on clean Resolute builders;
3. prove APT dependency closure, clean install, upgrade and rollback;
4. re-run C1-C3 on the candidate;
5. regenerate C4.0 and this package audit from the live candidate if it is adopted;
6. only then resume C4.1 and later feature subgates;
7. complete C4.15 direct-dependency closure on the adopted stack;
8. only then freeze/refine the final `supralinux-desktop` set.

If the KDE candidate receives a NO-GO, document why, return this baseline to current status, and resume C4.1 without rewriting the failed qualification as product history.
