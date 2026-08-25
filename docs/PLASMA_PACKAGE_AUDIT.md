# Plasma Package Audit — Ubuntu 26.04 LTS

Status: **Phase 1 research in progress. No dependency list is frozen until clean-VM validation.**

Purpose: determine the smallest complete package composition that gives SupraLINUX an upstream-like KDE Plasma desktop in which every shipped/exposed feature has its backend and integration present.

This is not a copy of `kubuntu-desktop`. Kubuntu is used as a reference because its metapackage exposes many integration packages that the minimal Plasma metapackage does not pull in by itself.

## Source references

Primary research sources for this phase are Ubuntu 26.04 (`resolute`) and `resolute-updates` package metadata. Metadata must be rechecked before freezing a release because updates can change versions and dependency relationships.

Key package families inspected so far include:

- `kde-plasma-desktop`, `plasma-desktop`, `plasma-workspace`
- `kwin-common`, `kwin-wayland`
- `plasma-nm`, NetworkManager VPN plugins
- `xdg-desktop-portal-kde`
- `print-manager`, CUPS/OpenPrinting
- `kdenetwork-filesharing`, Samba
- `kde-config-sddm`, `kde-config-gtk-style`
- `plasma-disks`
- accessibility stack (`at-spi2-core`, `orca`, `speech-dispatcher`)
- `plasma-discover` and its optional backends

## 1. Minimal Plasma reference

Ubuntu's `kde-plasma-desktop` metapackage is intentionally minimal. It currently depends on a small desktop/application core including Plasma, a session, storage and power components. For SupraLINUX this is useful as a lower-bound reference, not as our final desktop definition. It does not by itself express the complete feature set we intend to ship.

## 2. Core desktop — candidate REQUIRED set

These packages/areas are strong candidates for the first `supralinux-desktop` dependency set because they form the desktop itself or provide integration that SupraLINUX intends to expose by default.

| Area | Candidate package(s) | Reason | Status |
|---|---|---|---|
| Plasma shell/workspace | `plasma-desktop`, `plasma-workspace` | Core desktop | research confirmed; VM pending |
| Wayland session | `plasma-session-wayland` | Primary session; pulls matching KWin Wayland | research confirmed; VM pending |
| System Settings | `systemsettings` | Main configuration UI during vanilla phase | research confirmed; VM pending |
| Default visual integration | `breeze`, `frameworkintegration6`, `plasma-integration` | Upstream-like Qt/Plasma integration | research confirmed; VM pending |
| GTK visual integration | `breeze-gtk-theme`, `kde-config-gtk-style` | Cross-toolkit coherence | promoted to candidate baseline |
| Authentication UI | `polkit-kde-agent-1` | Required for privileged desktop actions | research confirmed; VM pending |
| Display manager | `sddm`, `sddm-theme-breeze`, `kde-config-sddm` | Login and its official KCM must be functional | promoted to candidate baseline |
| Storage/removable media | `udisks2` | Backend for storage/removable-device integration | research confirmed; VM pending |
| Power | `upower`, `powerdevil` | Power/battery controls must work | research confirmed; VM pending |
| Displays | `kscreen` | Monitor hotplug/display settings | research confirmed; VM pending |
| Screen locking | `kde-config-screenlocker` | Screen-locking KCM | promoted to candidate baseline |
| System information | `kinfocenter` | Plasma/KDE system information surface | promoted to candidate baseline |
| System monitoring backend | `ksystemstats` | Backend for Plasma monitoring surfaces | promoted to candidate baseline |
| Audio UI | `plasma-pa` | Plasma volume/device UI | research confirmed; VM pending |
| Audio stack | `pipewire-audio` | Ubuntu desktop PipeWire composition | research confirmed; VM pending |
| Bluetooth UI/backend | `bluedevil`, `bluez` | Complete Plasma Bluetooth path | research confirmed; VM pending |
| Networking UI/backend | `plasma-nm`, `network-manager` | Wi-Fi/Ethernet connection management | research confirmed; VM pending |
| Common VPN backends | `network-manager-openvpn`, `network-manager-openconnect` | Useful Plasma-NM VPN workflows | promoted to candidate baseline |
| Portals | `xdg-desktop-portal`, `xdg-desktop-portal-kde` | Wayland/sandbox/file-picker/screen-sharing integration | research confirmed; VM pending |
| XDG user dirs | `xdg-user-dirs` | Correct localized standard home directories | installer test pending |
| Keyboard data | `xkb-data` | Keyboard layout configuration | research confirmed; VM pending |
| Qt translations | `qt6-translations-l10n` | Core Qt localization | locale matrix pending |
| File/network abstraction | `kio6`, `kio-fuse`, `kio-extras` | KDE protocol/device support and non-KIO app interoperability | promoted to candidate baseline |
| KWallet login integration | `libpam-kwallet5` | Avoid unnecessary wallet password prompts | research confirmed; PAM test pending |

## 3. KWin and Plasma KCM surface

The detailed KCM inventory lives in `docs/KCM_AUDIT.md`. Important package-level conclusions:

- `plasma-desktop` installs a large set of KCMs directly, including accessibility, activities, file search, input, shortcuts, session, automount, spell checking and desktop paths.
- `kwin-common` installs the KWin KCMs for animation speed, effects, scripts, virtual desktops, decorations, rules, Xwayland, virtual keyboard, window behavior, screen edges, task switching and touchscreen edges.
- KWin also ships the screenshot and screencast plugins used in the Wayland capture/sharing path.

Therefore “Plasma launches” is not a meaningful completeness test. Every visible surface requires an acceptance test.

## 4. Feature-completeness decisions promoted into the current candidate

### Flatpak

Candidate hard baseline:

- `flatpak`
- `kde-config-flatpak`

Reason: Flatpak is a first-class SupraLINUX application layer, so its Plasma permissions KCM should not be missing.

### Remote Desktop

Candidate hard baseline:

- `krdp`

`krdc` remains a recommendation for now because the server KCM is part of the desktop integration contract while the client application is a user-facing application choice. This classification can change after clean-VM testing.

### Printing

Candidate hard baseline:

- `print-manager`
- `cups`
- `cups-client`
- `cups-filters`

`cups-filters` in Ubuntu 26.04 includes the OpenPrinting filter stack and driverless-printing support through its dependencies. The clean-system test must cover discovery, adding/removing printers, queues and an actual job path.

### Network sharing

Candidate hard baseline:

- `kdenetwork-filesharing`
- `samba`
- `kio-extras`

`kdenetwork-filesharing` depends on Samba common tooling, but the Samba server itself is only suggested upstream. SupraLINUX explicitly wants folder sharing to work rather than merely show an action, so the current candidate includes `samba` until testing proves a better split.

### VPN

Candidate hard baseline:

- `network-manager-openvpn`
- `network-manager-openconnect`

These are core NetworkManager plugins, not the GNOME editor packages. Plasma-NM provides the desktop UI. Additional protocols remain optional until there is a concrete product/support decision.

### Accessibility

Candidate hard baseline:

- `at-spi2-core`
- `orca`
- `speech-dispatcher`

This is intentionally broader than a minimal Plasma install. The accessibility KCM exposes screen-reader-related behavior; shipping the UI while omitting the usable runtime would violate SupraLINUX's completeness rule. The exact startup/toggle integration still requires a real session test.

### SMART disk health

Candidate hard baseline:

- `plasma-disks`

It is an official Plasma integration for SMART-capable devices. It remains subject to hardware/VM validation and can be demoted if it proves inappropriate for the base image.

### GTK application coherence

Candidate hard baseline:

- `breeze-gtk-theme`
- `kde-config-gtk-style`

SupraLINUX will use non-Qt applications where they are the right application. A vanilla Plasma baseline should therefore make GTK applications visually coherent and expose the supported Plasma GTK configuration surface.

## 5. Discover / PackageKit / Snap interaction — important open issue

Ubuntu 26.04's `plasma-discover` package contains the PackageKit backend and depends on `packagekit`, so it can serve APT software without a separate PackageKit backend package.

However, Ubuntu's `plasma-discover` also **recommends `plasma-discover-backend-snap`**. APT installs recommendations by default. Blindly adding Discover to `supralinux-desktop` could therefore pull in the Snap backend and undermine SupraLINUX's accepted “Snap blocked by default” rule.

Current decision:

- do **not** add `plasma-discover` to the hard `supralinux-desktop` dependency set yet;
- design and implement the SupraLINUX Snap policy first;
- after the policy can safely block `snapd`/the Snap backend while remaining reversible, re-evaluate a temporary Discover baseline with:
  - PackageKit/APT
  - Flatpak backend
  - fwupd backend
  - update notifier
  - **no Snap backend**

Discover is temporary product infrastructure anyway; SupraLINUX intends to replace it later with Supra Store. That future plan is not a reason to ship a broken or policy-violating store during Aurora development.

## 6. Portal backend question — OPEN

Kubuntu installs both `xdg-desktop-portal-kde` and `xdg-desktop-portal-gtk`. SupraLINUX will not copy this blindly.

Before freeze:

1. enumerate interfaces implemented by the KDE portal backend shipped in Ubuntu 26.04;
2. identify interfaces for which a fallback backend is actually required;
3. test representative Qt, GTK and Flatpak applications under Plasma Wayland;
4. include `xdg-desktop-portal-gtk` only if it provides necessary compatibility without stealing interfaces that KDE should own.

## 7. Deliberately unresolved capabilities

These remain outside the hard candidate until policy/testing is adequate:

| Capability | Package(s) | Reason not yet hard baseline |
|---|---|---|
| Firewall KCM | `plasma-firewall` + UFW or firewalld | Must choose a firewall policy/backend before exposing it |
| Thunderbolt | `plasma-thunderbolt` + backend | Requires physical-device authorization testing |
| Plasma Vaults | `plasma-vault` + crypto backends | Requires complete create/open/close/recovery test design |
| Fingerprint | `libpam-fprintd` / `fprintd` | Changes auth stack; hardware validation required |
| KDE Connect | `kdeconnect` | Strong product candidate, but not a hidden transitive requirement |
| Browser integration | `plasma-browser-integration` | Wait for browser/default-app policy |
| Firmware UI | `fwupd` + UI integration | Backend is useful, but user-facing update surface is coupled to store/updater decision |

## 8. Explicit non-inheritance from Kubuntu

The following are NOT automatically inherited:

- `kubuntu-settings-desktop`
- Kubuntu wallpapers/branding/Plymouth themes
- `plasma-distro-release-notifier`
- `plasma-discover-backend-snap`
- `snapd`
- Firefox's Ubuntu Snap transition package
- games and discretionary applications
- Ubuntu/Kubuntu-specific helpers that do not serve SupraLINUX's architecture
- duplicate applications merely because Kubuntu recommends them

Every inherited-looking package needs a SupraLINUX reason.

## 9. Dependency-chain confirmations

- `plasma-session-wayland` pulls the matching KWin Wayland/session relationship; SupraLINUX should express the session rather than hard-code unnecessary internal version relationships.
- `kwin-wayland` depends on `xwayland`, so X11 application compatibility under the Wayland session is already included by the Ubuntu package chain.
- `pipewire-audio` pulls the normal desktop PipeWire/Pulse compatibility, WirePlumber and Bluetooth-audio pieces. Prefer this abstraction unless SupraLINUX later needs a different composition.
- Ubuntu 26.04 retains the historical package name `libpam-kwallet5` for the current KWallet PAM integration.
- `kio-extras` materially expands KIO protocol/device support, including SMB-related client support; it has been promoted from `Recommends` to the candidate hard baseline because SupraLINUX intends common network/file protocols to work out of the box.

## 10. Current metapackage state

The development package is now `0.1.0~dev2`. It remains explicitly UNRELEASED and experimental.

The current candidate is intentionally broader than a minimal KDE install because its purpose is to create a **complete test surface**. After the first clean Ubuntu 26.04 installation we can remove packages that are redundant, inappropriate or already guaranteed transitively—but only after proving that removal does not make a promised capability incomplete.

`SupraLINUX 1.0.0 - Aurora` remains the first public distribution identity. Development package versions must not imply release readiness.

## 11. Next audit steps

- assign test IDs to every KCM and major desktop capability;
- audit Wayland capture/screen-sharing end-to-end;
- audit KRDP physical and virtual session behavior;
- audit the KDE portal interface set and GTK fallback question;
- design the reversible Snap blocking package/policy;
- build `supralinux-desktop` in a clean Ubuntu 26.04 build environment;
- install it on a clean Ubuntu base and turn every missing/failed feature into a tracked defect;
- only then begin reducing/refining the candidate dependency set.
