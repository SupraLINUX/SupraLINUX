# Plasma Integration Matrix — Ubuntu 26.04 LTS

Status: **initial research; not yet validated in a clean SupraLINUX VM**.

This document maps Plasma-visible capabilities to the Ubuntu 26.04 packages/backends SupraLINUX must evaluate. Package existence is not enough: each row eventually needs a real clean-install test.

## Baseline composition

Ubuntu 26.04 provides `kde-plasma-desktop` as a minimal KDE Plasma metapackage. It depends on `kde-baseapps`, `plasma-desktop`, a Plasma session, `plasma-workspace`, `udisks2`, and `upower`. SupraLINUX will use this as a reference only; it will define its own composition rather than simply depending on Kubuntu's desktop metapackage.

Ubuntu 26.04 currently provides Plasma 6.6 packages, with updates in `resolute-updates`.

## Initial matrix

| Area | Ubuntu 26.04 package(s) / backend candidates | SupraLINUX intent | Validation |
|---|---|---|---|
| Core desktop | `plasma-desktop`, `plasma-workspace` | Required | pending clean VM |
| Session | `plasma-session-wayland` | Wayland is the primary session | pending clean VM |
| Display manager | `sddm`, Breeze SDDM theme/integration | Required | pending audit |
| Storage/removable media | `udisks2`, KDE Solid integration | Required | pending clean VM |
| Power backend | `upower`, `powerdevil` | All exposed power controls must work | pending clean VM |
| Network UI | `plasma-nm` + NetworkManager | Wi-Fi/Ethernet/VPN UI must have working backends | pending clean VM |
| Audio | Plasma audio integration + PipeWire stack | Volume/devices/routing must work | pending package audit |
| Bluetooth | `bluedevil` + BlueZ stack | Plasma Bluetooth UI must be complete | pending clean VM |
| Polkit | `polkit-kde-agent-1` | Required authentication agent | pending clean VM |
| Portals | `xdg-desktop-portal-kde` | Required for Wayland/sandbox integrations | pending clean VM |
| Flatpak permissions | `flatpak`, `kde-config-flatpak` | Settings KCM must work, not just appear | pending clean VM |
| Flatpak software backend | `plasma-discover-backend-flatpak` while Discover is retained | Temporary baseline until Supra Store exists | pending clean VM |
| Remote desktop server | `krdp` | If the Plasma RDP settings UI ships, KRDP must work end-to-end | pending clean VM |
| Remote desktop client | `krdc` | Candidate default KDE remote-desktop client | pending clean VM |
| Network/KIO local bridging | `kio-fuse` | Candidate for non-KIO-aware app interoperability | pending clean VM |
| Printing | Plasma print manager + CUPS stack | Printing UI must have complete backend | pending package audit |
| Network shares | KIO/Samba stack | Browse/connect/share workflows must be explicit tests | pending package audit |
| Localization | locale packages, Plasma/Qt translations, `xdg-user-dirs` | Must be correct before first graphical login | pending installer test |
| Screen capture | Spectacle/KWin/PipeWire/portal path | Wayland capture must work | pending package audit |
| Screen sharing | KWin/PipeWire/portal path | Wayland sharing must work in supported apps | pending package audit |
| Wallet | KWallet + PAM/session integration | No broken/missing wallet prompts from incomplete integration | pending package audit |

## Verified package availability from Ubuntu 26.04 repository research

The following package names have already been confirmed to exist in Ubuntu 26.04 (`resolute`):

- `plasma-desktop`
- `kde-plasma-desktop`
- `plasma-nm`
- `powerdevil`
- `bluedevil`
- `krdp`
- `krdc`
- `kde-config-flatpak`
- `plasma-discover-backend-flatpak`
- `xdg-desktop-portal-kde`
- `polkit-kde-agent-1`
- `kio-fuse`

Do not interpret this list as the final `supralinux-desktop` dependency list.

## Important discovery

`krdp` in Ubuntu 26.04 ships both `krdpserver` and a Plasma System Settings KCM. This is exactly the kind of package that can make a Plasma setting appear/disappear depending on distro composition; SupraLINUX must deliberately include and test such feature packages rather than leaving official Plasma capabilities half-present.

Likewise, `kde-config-flatpak` supplies the Flatpak permissions KCM. If SupraLINUX supports Flatpak as a first-class application layer, omitting this KCM would violate the project's integration-completeness rule.

## Next audit

Before creating the first `supralinux-desktop` control file, expand this matrix by inspecting:

1. `plasma-desktop` dependencies/recommends
2. `plasma-workspace` dependencies/recommends
3. `kde-plasma-desktop` dependency closure as a reference
4. `kubuntu-desktop` dependency closure only as a comparison/reference
5. all Plasma System Settings KCMs exposed on a clean Ubuntu-base + Plasma install
6. backend packages required by each KCM
7. which packages are hard dependencies vs SupraLINUX policy choices

Only after that audit should the first real metapackage dependency list be frozen.
