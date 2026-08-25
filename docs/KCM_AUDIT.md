# Plasma System Settings KCM Audit — Aurora

Status: **package-surface inventory in progress; backend/test mapping still requires clean-system validation**.

Purpose: enumerate System Settings modules that become visible through the selected Plasma packages so SupraLINUX can apply its quality rule: a visible setting is not considered complete until its backend, permissions, integration, and tests are known.

## 1. KCMs shipped directly by `plasma-desktop` in Ubuntu 26.04

The Ubuntu 26.04 `plasma-desktop` package currently installs these System Settings modules/plugins:

| KCM/plugin | Functional area | SupraLINUX audit target |
|---|---|---|
| `kcm_access` | Accessibility | Verify AT-SPI and screen-reader path, not only the visual KCM |
| `kcm_activities` | Plasma Activities | Create/switch/remove activity; persistence across login |
| `kcm_baloofile` | File Search / Baloo | Verify Baloo backend, indexing controls and status |
| `kcm_desktoppaths` | User paths | Verify XDG directories and localization consistency |
| `kcm_gamecontroller` | Game controllers | Detect supported controller; avoid dead UI on normal systems |
| `kcm_kded` | Background services | Verify listed services match installed KDED components |
| `kcm_keyboard` | Keyboard | Layouts, compose, model/options and Wayland behavior |
| `kcm_keys` | Shortcuts | Global shortcuts must persist and reach KGlobalAccel/KWin |
| `kcm_landingpage` | System Settings landing page | Basic module discovery/navigation |
| `kcm_mouse` | Mouse | Pointer/input settings through supported Wayland path |
| `kcm_plasmasearch` | Plasma Search | KRunner/search plugin enable/disable behavior |
| `kcm_smserver` | Session | Login/logout/session-restore behavior |
| `kcm_splashscreen` | Plasma splash | Upstream baseline works; later Supra artwork can replace it |
| `kcm_tablet` | Drawing tablet | Hardware-dependent validation track |
| `kcm_touchpad` | Touchpad | Hardware-dependent validation; Wayland behavior |
| `kcm_touchscreen` | Touchscreen | Hardware-dependent validation track |
| `kcm_workspace` | Workspace behavior | Verify settings are actually consumed by Plasma/KWin |
| `kcm_clock` | Date/time | Verify timezone/time backend and privileged helper path |
| `kcm_device_automounter` | Removable media automount | UDisks/Solid path and per-device behavior |
| `kcm_qtquicksettings` | Qt Quick settings | Validate expected runtime effect |
| `kcm_recentFiles` | Recent files | Privacy/history behavior and persistence |
| `kcm_solid_actions` | Device actions | Solid integration and action dispatch |
| `kcmspellchecking` | Spell checking | Verify dictionaries/providers are available for supported locales |
| `kcm_krunnersettings` | KRunner settings | Plugin list and configuration behavior |

The same package also installs accessibility configuration schemas for bell, color-blindness correction, invert, keyboard, mouse, screen reader, shake cursor and zoom/magnifier behavior. These must be audited as actual capabilities rather than assuming that the KCM file alone guarantees a working backend.

## 2. KWin KCM surface from `kwin-common`

Ubuntu 26.04's `kwin-common` file list confirms these System Settings modules. They are part of the Wayland desktop surface and therefore each requires an Aurora acceptance test.

| KCM/plugin | Functional area | Acceptance focus |
|---|---|---|
| `kcm_animations` | Global animation speed | Setting changes KWin animation timing and persists |
| `kcm_kwin_effects` | Desktop Effects | Enable/disable/configure supported effects without stale entries |
| `kcm_kwin_scripts` | KWin scripts | Discovery, enable/disable and configuration lifecycle |
| `kcm_kwin_virtualdesktops` | Virtual desktops | Add/remove/reorder/switch and persistence |
| `kcm_kwindecoration` | Window decorations | Breeze baseline, decoration settings and live application |
| `kcm_kwinrules` | Window rules | Create/edit/delete rules and verify Wayland application matching |
| `kcm_kwinxwayland` | Xwayland controls | Changes affect Xwayland policy without breaking compatibility |
| `kcm_virtualkeyboard` | Virtual keyboard | Backend selection and on-screen keyboard path when enabled |
| `kcm_kwinoptions` | Window management behavior | Focus, placement, titlebar/window actions and persistence |
| `kcm_kwinscreenedges` | Screen edges | Trigger actions reliably and preserve configuration |
| `kcm_kwintabbox` | Task/window switcher | Layout/behavior selection and Alt-Tab operation |
| `kcm_kwintouchscreen` | Touchscreen edges | Hardware-assisted touch edge validation |

The same package ships KWin screencast and screenshot plugins plus effect configuration plugins. This matters because Wayland capture/sharing is not just a portal package problem: KWin, PipeWire and the portal backend all participate in the path.

## 3. External KCM/integration surfaces selected for the current candidate baseline

| Package(s) | Visible/related surface | Current candidate policy |
|---|---|---|
| `kscreen` | Displays / HDR calibration / display OSD | Hard dependency candidate |
| `powerdevil` | Power management, battery, brightness | Hard dependency candidate |
| `kde-config-screenlocker` | Screen locking | Hard dependency candidate |
| `kde-config-sddm` + `sddm` | Login screen configuration | Hard dependency candidate; privileged write path must be tested |
| `kde-config-flatpak` + `flatpak` | Flatpak permissions | Hard dependency candidate because Flatpak is first-class |
| `krdp` | Remote Desktop settings/server | Hard dependency candidate; full Wayland RDP test required |
| `plasma-nm` + NetworkManager | Network connections | Hard dependency candidate |
| `bluedevil` + BlueZ | Bluetooth | Hard dependency candidate |
| `print-manager` + CUPS | Printers | Hard dependency candidate; real print/discovery path required |
| `kdenetwork-filesharing` + Samba | Dolphin folder sharing | Hard dependency candidate; share creation and remote access required |
| `kde-config-gtk-style` + Breeze GTK | GTK application appearance | Hard dependency candidate for cross-toolkit coherence |
| `plasma-disks` | SMART disk health | Hard dependency candidate; requires SMART-capable hardware/virtual disk tests |
| `polkit-kde-agent-1` | Authentication dialogs | Integration dependency rather than conventional KCM |
| `xdg-desktop-portal-kde` | Portals | File picker, open/save, screen sharing and sandbox integration |
| `libpam-kwallet5` | Wallet unlock at login | PAM/session integration; no duplicate password prompt in normal flow |
| `at-spi2-core`, `orca`, `speech-dispatcher` | Accessibility / screen reader | Candidate baseline so accessibility controls do not point to a missing runtime |

## 4. Network/VPN integration decision for the first candidate

`plasma-nm` exposes VPN creation/import workflows when matching NetworkManager plugins exist. The first Aurora candidate now includes:

- `network-manager-openvpn`
- `network-manager-openconnect`

These cover two widely used VPN families without installing GNOME-specific editor packages. Additional protocols (L2TP, WireGuard-specific UI paths, VPNC, SSTP, strongSwan, etc.) remain an audit item. The rule is not “install every VPN plugin”; it is “do not present a workflow as supported unless its backend is present and tested”.

## 5. Printing and network-sharing completeness

The first candidate now treats these as baseline desktop capabilities rather than optional cleanup after installation:

### Printing

- `print-manager`
- `cups`
- `cups-client`
- `cups-filters`

Acceptance must cover at least driverless/local discovery, add/remove printer, queue visibility, test-page/job path, cancellation and useful failure reporting.

### Samba sharing

- `kdenetwork-filesharing`
- `samba`
- `kio-extras`

`kdenetwork-filesharing` itself depends on Samba common tools, but a real share server requires the Samba server stack. Aurora therefore tests both directions separately:

1. browse/open SMB shares from Dolphin;
2. create a local folder share from Dolphin and access it from another machine/client.

## 6. First KCM quality classes

Each module receives one or more test classifications:

- **Software-only:** can be fully exercised in a VM (workspace, splash, search, activities, many KWin options).
- **Virtualizable:** needs a VM device/service but is automatable (removable storage, networking, audio, printing to a virtual target).
- **Hardware-assisted:** needs representative physical hardware for a credible claim (touchpad, touchscreen, tablet, fingerprint, Bluetooth peripherals, SMART, Thunderbolt).
- **Privileged/system:** explicitly tests Polkit/PAM/system service behavior (clock, SDDM, networking, power helpers, sharing).
- **External-client:** requires another application/device/client (KRDP, Samba sharing, printing, KDE Connect).

A module is not “done” because System Settings opens without crashing.

## 7. Deliberately unresolved surfaces

These remain outside the current hard baseline until their policy and complete backend path are decided:

- `plasma-firewall`: requires choosing and supporting a firewall backend; do not ship a dead KCM.
- `plasma-thunderbolt`: requires backend and physical-device validation.
- `plasma-vault`: requires encryption backend selection plus create/open/close/recovery tests.
- fingerprint/PAM: `libpam-fprintd` exists, but auth-stack changes require hardware testing before becoming default.
- KDE Connect: strong candidate, but should be accepted as a product/default-app choice rather than accidentally inherited.
- browser integration: wait for the browser/default-app policy.
- Discover: temporary use is attractive, but its Ubuntu package recommends the Snap backend; it cannot enter the hard baseline until the SupraLINUX Snap-block policy safely neutralizes that recommendation.

## 8. Immediate next pass

1. assign stable test IDs to every visible Plasma/KWin/external KCM;
2. audit the complete Wayland screen capture/share path (KWin -> PipeWire -> portal -> client);
3. audit KRDP end-to-end and distinguish physical-session vs virtual-session behavior;
4. audit portal interfaces and whether `xdg-desktop-portal-gtk` is actually needed as fallback;
5. build `supralinux-desktop` on a clean Ubuntu 26.04 environment;
6. install it into a clean base system and use the integration matrix as the defect list.
