# Plasma Integration Matrix — Ubuntu 26.04 LTS

Status: **research-backed candidate matrix; clean Ubuntu 26.04 validation pending**.

This is the acceptance map for Aurora's first goal: an upstream-like Plasma desktop where every shipped capability has its backend, permissions and integration present.

A package being installed is not a pass. A row passes only when its real user workflow works.

## Test status vocabulary

- `RESEARCHED`: package/backend path identified from Ubuntu/KDE metadata.
- `PENDING-VM`: can be tested in the first clean VM/system.
- `PENDING-HW`: credible validation needs representative hardware.
- `PASS`: acceptance flow completed successfully.
- `FAIL`: defect discovered; must be tracked/fixed.

## Core/session

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-CORE-001 | Plasma desktop starts | `plasma-desktop`, `plasma-workspace` | Login reaches a usable Plasma desktop without missing-shell errors | PENDING-VM |
| AUR-CORE-002 | Wayland primary session | `plasma-session-wayland`, KWin Wayland | Session reports Wayland; normal apps/window management work | PENDING-VM |
| AUR-CORE-003 | X11 app compatibility under Wayland | `xwayland` via KWin dependency | Representative X11 app starts and behaves normally | PENDING-VM |
| AUR-CORE-004 | SDDM login | `sddm`, `sddm-theme-breeze` | Login/logout/switch-user path works reliably | PENDING-VM |
| AUR-CORE-005 | Privileged desktop actions | `polkit-kde-agent-1` | Privileged System Settings actions show KDE auth dialog and succeed | PENDING-VM |
| AUR-CORE-006 | KWallet login integration | `libpam-kwallet5` | Normal password login unlocks wallet without redundant password prompt | PENDING-VM |

## Display, input and KWin

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-KWIN-001 | Display configuration | `kscreen`, KWin | Change resolution/scaling/orientation and persist | PENDING-VM |
| AUR-KWIN-002 | Global animation speed | `kcm_animations`, KWin | Setting visibly changes timing and persists | PENDING-VM |
| AUR-KWIN-003 | Desktop effects | `kcm_kwin_effects`, KWin effects | Enable/disable/configure representative effects | PENDING-VM |
| AUR-KWIN-004 | Virtual desktops | `kcm_kwin_virtualdesktops` | Add/remove/reorder/switch and persist | PENDING-VM |
| AUR-KWIN-005 | Window decorations | `kcm_kwindecoration`, Breeze/KWin | Change supported decoration options and apply live | PENDING-VM |
| AUR-KWIN-006 | Window rules | `kcm_kwinrules` | Create a rule and verify matching on Wayland | PENDING-VM |
| AUR-KWIN-007 | Xwayland controls | `kcm_kwinxwayland` | Policy changes apply without breaking normal Xwayland apps | PENDING-VM |
| AUR-KWIN-008 | Window behavior | `kcm_kwinoptions` | Focus/placement/action settings persist and work | PENDING-VM |
| AUR-KWIN-009 | Screen edges | `kcm_kwinscreenedges` | Configured edge action triggers reliably | PENDING-VM |
| AUR-KWIN-010 | Task switcher | `kcm_kwintabbox` | Alt-Tab and selected layout/behavior work | PENDING-VM |
| AUR-INPUT-001 | Keyboard layouts/options | Plasma keyboard KCM + `xkb-data` | Add/switch layout; compose/options work under Wayland | PENDING-VM |
| AUR-INPUT-002 | Mouse settings | Plasma/KWin input stack | Common pointer settings apply under Wayland | PENDING-VM |
| AUR-INPUT-003 | Touchpad | Plasma/KWin/libinput path | Tap/scroll/speed controls work on real touchpad | PENDING-HW |
| AUR-INPUT-004 | Touchscreen/tablet | Plasma/KWin input path | Device detected and relevant settings work | PENDING-HW |

## Storage, power and hardware

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-HW-001 | Removable media | `udisks2`, Solid | Insert/mount/eject removable storage from Plasma/Dolphin | PENDING-VM |
| AUR-HW-002 | Device automount settings | Plasma automounter + UDisks | Change policy and verify device behavior | PENDING-VM |
| AUR-HW-003 | Power management | `powerdevil`, `upower` | Profiles/idle/suspend controls are actionable and persist | PENDING-VM |
| AUR-HW-004 | Battery/brightness | PowerDevil hardware path | Battery and brightness controls work on laptop hardware | PENDING-HW |
| AUR-HW-005 | SMART disk health | `plasma-disks` | SMART-capable drive status is visible and meaningful | PENDING-HW |
| AUR-HW-006 | Bluetooth | `bluedevil`, `bluez`, PipeWire Bluetooth | Pair device; reconnect; audio profile when applicable | PENDING-HW |

## Audio and media plumbing

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-AUDIO-001 | Desktop audio | `plasma-pa`, `pipewire-audio` | Playback works; volume/mute/device selection work | PENDING-VM |
| AUR-AUDIO-002 | Audio routing | PipeWire/WirePlumber | Move stream between available sinks/sources | PENDING-VM |
| AUR-AUDIO-003 | Bluetooth audio | BlueZ + PipeWire Bluetooth | Pair headset and use expected output/input profiles | PENDING-HW |

## Networking and sharing

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-NET-001 | Ethernet | `plasma-nm`, NetworkManager | Connect/disconnect/status/change connection | PENDING-VM |
| AUR-NET-002 | Wi-Fi | `plasma-nm`, NetworkManager | Scan/connect/forget/reconnect secured Wi-Fi | PENDING-HW |
| AUR-NET-003 | OpenVPN | `network-manager-openvpn` | Import/create profile and establish tunnel from Plasma-NM | PENDING-VM |
| AUR-NET-004 | OpenConnect | `network-manager-openconnect` | Create/connect supported OpenConnect profile | PENDING-VM |
| AUR-NET-005 | Browse SMB share | KIO/`kio-extras`, Samba client libs | Browse and open remote SMB share in Dolphin | PENDING-VM |
| AUR-NET-006 | Create SMB share | `kdenetwork-filesharing`, `samba` | Share folder from Dolphin and access from another client | PENDING-VM |
| AUR-NET-007 | KIO access from non-KIO apps | `kio-fuse` | Open supported remote KIO resource in conventional local-path app | PENDING-VM |

## Printing

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-PRINT-001 | Printer configuration | `print-manager`, CUPS | Add/remove/configure printer through Plasma UI | PENDING-VM |
| AUR-PRINT-002 | Driverless discovery | CUPS/OpenPrinting stack | Discover compatible network/virtual target | PENDING-VM |
| AUR-PRINT-003 | Job lifecycle | CUPS + Print Manager | Submit, view, cancel job; useful error state on failure | PENDING-VM |

## Flatpak, portals and Wayland capture

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-FLAT-001 | Flatpak runtime | `flatpak` | Install/run/remove a test Flatpak | PENDING-VM |
| AUR-FLAT-002 | Flatpak permission KCM | `kde-config-flatpak` | App permissions shown and edits affect app behavior | PENDING-VM |
| AUR-PORTAL-001 | KDE file chooser portal | `xdg-desktop-portal`, `xdg-desktop-portal-kde` | Sandboxed app receives working KDE file chooser | PENDING-VM |
| AUR-PORTAL-002 | Screen capture | KWin screenshot/screencast + PipeWire + KDE portal | Representative Wayland capture workflow succeeds | PENDING-VM |
| AUR-PORTAL-003 | Screen sharing | KWin + PipeWire + KDE portal + client | Select screen/window and stream it in supported client | PENDING-VM |
| AUR-PORTAL-004 | GTK/portal fallback | KDE portal; possible GTK fallback | Representative GTK/Flatpak apps behave correctly; determine if GTK backend is needed | PENDING-VM |

## Remote desktop

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-RDP-001 | KRDP settings KCM | `krdp` | KCM loads, persists config and reports actionable state | PENDING-VM |
| AUR-RDP-002 | KRDP physical-session path | KRDP + KWin/PipeWire/Wayland | Connect from external RDP client and obtain usable session | PENDING-VM |
| AUR-RDP-003 | KRDP virtual-session path | KRDP virtual-monitor/session support | External client gets requested virtual desktop and clean lifecycle | PENDING-VM |
| AUR-RDP-004 | KDE RDP client | `krdc` | Connect to known-good RDP server | PENDING-VM |

## Localization

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-L10N-001 | Installer-selected locale before first login | locale stack + installer | `$LANG`/locale correct before first graphical session | PENDING-VM |
| AUR-L10N-002 | Plasma/Qt translation | Plasma language packages + Qt translations | Core desktop and Qt UI use selected supported language | PENDING-VM |
| AUR-L10N-003 | XDG user directories | `xdg-user-dirs` | Desktop/Documents/etc. created in selected locale where translation exists | PENDING-VM |
| AUR-L10N-004 | Language-change migration | future Supra workflow | Existing populated directories are never silently renamed/lost | FUTURE |

## Accessibility

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-A11Y-001 | AT-SPI runtime | `at-spi2-core` | Accessibility bus/runtime available in Plasma session | PENDING-VM |
| AUR-A11Y-002 | Screen reader | `orca`, `speech-dispatcher` | User can start reader and navigate representative Plasma/Qt UI | PENDING-VM |
| AUR-A11Y-003 | Visual accessibility effects | Plasma/KWin | Zoom/invert/color-related exposed controls work as documented | PENDING-VM |

## Software management and Snap policy

| ID | Capability | Candidate packages/backends | Acceptance | Status |
|---|---|---|---|---|
| AUR-SW-001 | Snap blocked by default | planned Supra policy package | `snapd` cannot be silently installed while policy is active | DESIGN |
| AUR-SW-002 | Snap unblock is reversible | planned Supra policy package | Disable/remove policy; `snapd` can then be installed normally | DESIGN |
| AUR-SW-003 | Temporary Discover without Snap | `plasma-discover` + PackageKit/Flatpak/fwupd | Install Discover without Snap backend or snapd under Supra policy | BLOCKED by policy implementation |

## Explicitly unresolved / not claimed yet

The following are not considered supported merely because packages exist:

- firewall KCM/backend
- Thunderbolt authorization
- Plasma Vaults
- fingerprint authentication
- KDE Connect as a default app
- browser integration
- Supra Store / custom updater
- recovery and backup

They move into this matrix when SupraLINUX explicitly chooses to ship/claim them.

## First clean-system gate

The first `supralinux-desktop` VM/system pass is not allowed to end with “desktop boots, good enough”. Every `PENDING-VM` item above must become either:

- `PASS`, or
- `FAIL` with a reproducible defect and planned fix.

Hardware-only items remain pending until representative hardware is tested.
