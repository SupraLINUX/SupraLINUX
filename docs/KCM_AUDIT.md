# Plasma System Settings KCM Audit — Aurora

Status: **initial package-surface inventory; backend/test mapping still in progress**.

Purpose: enumerate System Settings modules that become visible through the selected Plasma packages so SupraLINUX can apply its quality rule: a visible setting is not considered complete until its backend, permissions, integration, and tests are known.

## 1. KCMs shipped directly by `plasma-desktop` in Ubuntu 26.04

The Ubuntu 26.04 `plasma-desktop` package currently installs these System Settings modules/plugins:

| KCM/plugin | Functional area | SupraLINUX audit target |
|---|---|---|
| `kcm_access` | Accessibility | Verify required accessibility services and screen-reader path |
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

## 2. Additional KCM surfaces already known from related Plasma packages

| Package | Visible/related surface | Current state |
|---|---|---|
| `kscreen` | Display configuration / HDR calibration / display OSD | Candidate hard dependency; VM test pending |
| `powerdevil` | Power management, battery/brightness and mobile power | Candidate hard dependency; VM test pending |
| `kde-config-flatpak` | Flatpak application permissions | Candidate hard dependency because Flatpak is first-class |
| `krdp` | Remote Desktop settings/server | Candidate hard dependency; full Wayland RDP test required |
| `plasma-nm` | Network connections | Candidate hard dependency; Wi-Fi/Ethernet/VPN matrix pending |
| `bluedevil` | Bluetooth | Candidate hard dependency; BlueZ + PipeWire Bluetooth tests pending |
| `polkit-kde-agent-1` | Authentication dialogs | Integration dependency rather than conventional KCM |
| `xdg-desktop-portal-kde` | Portal integration | Integration dependency; screen sharing/file picker tests pending |
| `sddm-theme-breeze` + SDDM | Login experience | Initial upstream-like login baseline |

## 3. First KCM quality classes

Each module will eventually receive one of these test classifications:

- **Software-only:** can be fully exercised in a VM (e.g. workspace, splash, search, activities).
- **Virtualizable:** needs a VM device/service but is automatable (e.g. removable storage, some networking, audio).
- **Hardware-assisted:** needs representative physical hardware for a credible claim (e.g. touchpad, touchscreen, tablet, fingerprint, Bluetooth peripherals).
- **Privileged/system:** requires explicit testing of Polkit/PAM/system service behavior (e.g. clock, SDDM, networking, power helpers).
- **External-client:** requires another application/device/client to prove the path (e.g. KRDP, network sharing, printing).

A module is not “done” because System Settings opens without crashing.

## 4. Immediate implications for the metapackage

The current `supralinux-desktop` development package already declares the baseline components for Wayland, SDDM/Breeze, Polkit, UDisks, PowerDevil, KScreen, PipeWire, Bluetooth, networking, portals, localized XDG user directories, KIO, KWallet PAM, Flatpak permissions and KRDP.

This is intentionally a first candidate. The audit will still decide whether items such as printing, Samba sharing, VPN plugins, accessibility runtime components, firmware updates, disk health, GTK integration, KDE Connect and other Plasma-visible features move into the hard baseline.

## 5. Next pass

1. Enumerate KWin KCMs from `kwin-common` and map them to the Wayland session.
2. Enumerate external KCMs introduced by every candidate dependency.
3. Identify settings whose UI exists but needs an optional backend/package to become useful.
4. Add one test case ID per visible module to `PLASMA_INTEGRATION_MATRIX.md`.
5. Use the resulting matrix as the acceptance checklist for the first clean Ubuntu 26.04 + `supralinux-desktop` VM.
