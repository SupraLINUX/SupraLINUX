# Plasma Package Audit — Ubuntu 26.04 LTS

Status: **Phase 1 research in progress. No dependency list is frozen until clean-VM validation.**

Purpose: determine the smallest complete package composition that gives SupraLINUX an upstream-like KDE Plasma desktop in which every shipped/exposed feature has its backend and integration present.

This is not a copy of `kubuntu-desktop`. Kubuntu is used as a reference because its metapackage exposes many integration packages that the minimal Plasma metapackage does not pull in by itself.

## Source references

Primary research sources for this phase are Ubuntu 26.04 (`resolute`) package metadata:

- https://packages.ubuntu.com/resolute/kde-plasma-desktop
- https://packages.ubuntu.com/resolute/kubuntu-desktop
- https://packages.ubuntu.com/resolute/plasma-desktop
- https://packages.ubuntu.com/resolute/plasma-workspace
- https://packages.ubuntu.com/resolute/kwin-common
- https://packages.ubuntu.com/resolute/xdg-desktop-portal-kde
- https://packages.ubuntu.com/resolute/plasma-firewall

Package metadata must be rechecked before freezing a release because `resolute-updates` can change versions/dependencies.

## 1. Minimal Plasma reference

Ubuntu's `kde-plasma-desktop` metapackage is intentionally minimal. It currently depends on:

- `kde-baseapps`
- `plasma-desktop`
- `plasma-session-wayland` or `plasma-session-x11`
- `plasma-workspace`
- `udisks2`
- `upower`

For SupraLINUX this is useful as a lower-bound reference, not as our final desktop definition. It does not by itself express the complete feature set we intend to ship.

## 2. Core desktop — candidate REQUIRED set

These packages/areas are strong candidates for the first `supralinux-desktop` dependency set because they form the desktop itself or provide integration that SupraLINUX intends to expose by default.

| Area | Candidate package(s) | Reason | Status |
|---|---|---|---|
| Plasma shell/workspace | `plasma-desktop`, `plasma-workspace` | Core desktop | research confirmed; VM pending |
| Wayland session | `plasma-session-wayland`, `kwin-wayland` | Primary SupraLINUX session | research confirmed; VM pending |
| System Settings | `systemsettings` | Main configuration UI during vanilla phase | research confirmed; VM pending |
| Default visual integration | `breeze`, `frameworkintegration6`, `plasma-integration` | Upstream-like Qt/Plasma integration | research confirmed; VM pending |
| Authentication UI | `polkit-kde-agent-1` | Required for privileged desktop actions | research confirmed; VM pending |
| Storage/removable media | `udisks2` | Backend for storage/removable-device integration | research confirmed; VM pending |
| Power | `upower`, `powerdevil` | Power/battery controls must work | research confirmed; VM pending |
| Displays | `kscreen` | Monitor hotplug/display settings | research confirmed; VM pending |
| Screen locking | `kde-config-screenlocker` | Screen-locking KCM | research confirmed; VM pending |
| System information | `kinfocenter` | Plasma/KDE system information surface | research confirmed; VM pending |
| System monitoring backend | `ksystemstats` | Backend for Plasma system-monitoring surfaces | research confirmed; VM pending |
| Audio UI | `plasma-pa` | Plasma volume/device UI | research confirmed; VM pending |
| Audio stack | `pipewire`, `pipewire-audio`, `wireplumber` | Standard desktop audio/session stack | research confirmed; VM pending |
| Bluetooth UI | `bluedevil` | KDE Bluetooth stack | research confirmed; VM pending |
| Bluetooth backend | `bluez`, `libspa-0.2-bluetooth` | Backend + PipeWire Bluetooth audio | research confirmed; VM pending |
| Networking UI | `plasma-nm` | Plasma network UI | research confirmed; VM pending |
| Networking backend | `network-manager`, Wi-Fi backend packages | Actual network management | research confirmed; VM pending |
| Portals | `xdg-desktop-portal`, `xdg-desktop-portal-kde` | Wayland/sandbox/file-picker/screen-sharing integration | research confirmed; VM pending |
| XDG user dirs | `xdg-user-dirs` | Correct localized standard home directories | research confirmed; installer test pending |
| Keyboard data | `xkb-data` | Keyboard layout configuration | research confirmed; VM pending |
| Qt translations | `qt6-translations-l10n` | Core Qt localization | research confirmed; locale matrix pending |
| File/network abstraction | `kio6`, `kio-fuse` | KDE file/network access and non-KIO app interoperability | research confirmed; VM pending |

This table is deliberately conservative: a package is not promoted to final REQUIRED simply because Kubuntu depends on it.

## 3. Plasma-owned KCM surface already identified

The Ubuntu `plasma-desktop` file list shows that the package itself provides System Settings modules for, among other areas:

- accessibility
- activities
- Baloo file search
- desktop paths
- game controllers
- KDE background services
- keyboard
- shortcuts
- mouse
- Plasma search
- session behavior
- splash screen
- tablets/touchpad/touchscreen
- workspace behavior
- clock/date-related UI
- device automount
- spell checking

`kwin-common` provides additional KWin/System Settings modules including:

- animation speed
- desktop effects
- KWin scripts
- virtual desktops
- window decorations
- window rules
- Xwayland controls
- virtual keyboard
- window behavior/options
- screen edges
- task/window switcher
- touchscreen edges

Every visible module in the installed baseline must eventually have a test entry in `PLASMA_INTEGRATION_MATRIX.md`.

## 4. Feature-completeness candidates

These packages are not necessarily part of the immutable core, but they correspond to capabilities that fit SupraLINUX's “everything exposed works” goal and should be audited for inclusion.

| Capability | Candidate package(s) | Notes |
|---|---|---|
| Flatpak | `flatpak`, `kde-config-flatpak` | First-class SupraLINUX application layer; permissions KCM should be present |
| Remote desktop server | `krdp` | Supplies KRDP server and Plasma KCM; end-to-end Wayland test required |
| Remote desktop client | `krdc` | KDE client; useful baseline candidate |
| Printing | `print-manager`, `cups`, `cups-client`, `cups-filters` | UI without CUPS backend is not acceptable |
| Network sharing | `kdenetwork-filesharing`, Samba/KIO backend packages | Must support real share creation/browsing, not just a visible action |
| VPN | NetworkManager plugins such as OpenVPN/OpenConnect where appropriate | Plasma NM should not advertise unusable workflows |
| SDDM configuration | `kde-config-sddm`, `sddm`, `sddm-theme-breeze` | Audit what is appropriate to expose in the vanilla phase |
| GTK appearance integration | `kde-config-gtk-style`, `breeze-gtk-theme` | Helps non-Qt apps fit the desktop |
| Firmware updates | `fwupd`, signed integration where applicable | Candidate for complete hardware maintenance UX |
| SMART disk health | `plasma-disks` | Plasma-visible disk-health integration |
| Thunderbolt | `plasma-thunderbolt` plus its backend | Include only if the full authorization workflow works |
| Plasma Vaults | `plasma-vault` and encryption backends | Include only after complete create/open/close/recovery tests |
| Firewall KCM | `plasma-firewall` plus exactly one supported firewall backend | The KCM recommends UFW or firewalld; SupraLINUX must pick/test a policy before shipping this surface |
| KDE Connect | `kdeconnect` | Strong desktop-integration candidate; not required merely because KDE provides it |
| Browser integration | `plasma-browser-integration` plus browser extension path | Audit after browser policy is finalized |
| Fingerprint | `libpam-fprintd`/`fprintd` integration | Hardware-dependent test track required before claiming support |
| Accessibility | `at-spi2-core`, screen reader stack where applicable | Accessibility KCM must not expose dead controls |

## 5. Portal backend question — OPEN

Kubuntu 26.04 depends on both `xdg-desktop-portal-kde` and `xdg-desktop-portal-gtk`. SupraLINUX will not copy this blindly.

Action before freeze:

1. enumerate portal interfaces implemented by the KDE backend shipped in Ubuntu 26.04;
2. identify any interfaces for which a fallback backend is required;
3. test GTK and Flatpak applications under Plasma Wayland;
4. include `xdg-desktop-portal-gtk` only if it provides necessary fallback behavior or compatibility.

## 6. Explicit non-inheritance from Kubuntu

The following categories found in `kubuntu-desktop` are NOT automatically inherited by SupraLINUX:

- `kubuntu-settings-desktop`
- Kubuntu wallpapers/branding/Plymouth themes
- `plasma-distro-release-notifier` as a Kubuntu/Ubuntu release policy component
- `plasma-discover-backend-snap`
- `snapd`
- Firefox's Ubuntu Snap transition package
- games and discretionary applications
- Ubuntu/Kubuntu-specific helpers that do not serve SupraLINUX's architecture
- duplicate remote-desktop clients simply because Kubuntu recommends them

Any such package requires its own SupraLINUX justification.

## 7. Important first conclusions

1. Installing only a minimal Plasma metapackage is insufficient for SupraLINUX's product contract.
2. Kubuntu's dependency list is useful as a discovery map because it exposes integration packages that are easy to miss, but it contains many policy/application choices SupraLINUX does not want.
3. The correct approach is to build our own dependency set from Plasma-visible capabilities outward: UI -> backend -> permissions -> session integration -> test.
4. `supralinux-desktop` should contain desktop/integration capability dependencies; discretionary end-user applications should remain separable in `supralinux-default-apps` where practical.
5. Snap-related dependencies must be explicitly excluded from the default composition.

## 8. Next audit steps

Before freezing `debian/control` for `supralinux-desktop`:

- enumerate every System Settings module installed by candidate packages;
- map each external KCM to its backend;
- audit network/VPN packages;
- audit printing and Samba sharing end-to-end dependencies;
- audit PipeWire, screen capture, screen sharing and KRDP paths on Wayland;
- audit KWallet/PAM/session integration;
- audit accessibility dependencies;
- decide the portal fallback policy;
- distinguish desktop capability packages from default application packages;
- then install the candidate dependency set in a clean Ubuntu 26.04 base VM and record every missing/broken surface.

Only after the clean-VM pass should `supralinux-desktop` move from a candidate dependency list to a release-controlled metapackage.
