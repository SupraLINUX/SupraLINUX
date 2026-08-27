# Plasma System Settings KCM Audit — Aurora

Status: **initial package-surface inventory established; C4.0 runtime coverage reconciliation pending**.

Purpose: enumerate System Settings modules that become visible through the selected Plasma packages so SupraLINUX can enforce its quality rule: a visible setting is not complete until its backend, permissions, integration and test owner are known.

This document is a research/input inventory. The canonical executable capability IDs and statuses live in `docs/PLASMA_INTEGRATION_MATRIX.md`; the execution contract lives in `docs/C4_CERTIFICATION.md`.

## 1. KCMs shipped directly by `plasma-desktop` in Ubuntu 26.04

The audited Ubuntu 26.04 package surface includes these System Settings modules/plugins:

| KCM/plugin | Functional area | C4 acceptance focus |
|---|---|---|
| `kcm_access` | Accessibility | AT-SPI/screen-reader/visual accessibility paths, with hardware split where needed |
| `kcm_activities` | Plasma Activities | Create/switch/remove and persistence |
| `kcm_baloofile` | File Search / Baloo | Backend state, indexing controls and status |
| `kcm_desktoppaths` | User paths | XDG directories and localization consistency |
| `kcm_gamecontroller` | Game controllers | Surface ownership in C4; representative physical controller later |
| `kcm_kded` | Background services | Listed services correspond to installed/actionable backends |
| `kcm_keyboard` | Keyboard | Layouts/options and Wayland behavior |
| `kcm_keys` | Shortcuts | Global shortcut persistence and actual trigger path |
| `kcm_landingpage` | System Settings landing page | Module discovery/navigation and no broken entries |
| `kcm_mouse` | Mouse | Supported settings reach KWin/libinput path |
| `kcm_plasmasearch` | Plasma Search | KRunner/search plugin enable/disable behavior |
| `kcm_smserver` | Session | Representative login/logout/session-setting behavior |
| `kcm_splashscreen` | Plasma splash | Upstream baseline configuration lifecycle |
| `kcm_tablet` | Drawing tablet | Runtime surface inventory; representative hardware later |
| `kcm_touchpad` | Touchpad | Runtime surface inventory; representative hardware later |
| `kcm_touchscreen` | Touchscreen | Runtime surface inventory; representative hardware later |
| `kcm_workspace` | Workspace behavior | Settings actually consumed by Plasma/KWin |
| `kcm_clock` | Date/time | Timezone/time backend and privileged helper/Polkit path |
| `kcm_device_automounter` | Removable-media automount | UDisks/Solid behavior with hot-plug fixture |
| `kcm_qtquicksettings` | Qt Quick settings | Expected runtime effect |
| `kcm_recentFiles` | Recent files | Privacy/history behavior and cleanup |
| `kcm_solid_actions` | Device actions | Solid integration/action dispatch |
| `kcmspellchecking` | Spell checking | Dictionaries/providers for supported C4 locales |
| `kcm_krunnersettings` | KRunner settings | Plugin list/configuration lifecycle |

The same package exposes accessibility schemas for bell, color-blindness correction, invert, keyboard, mouse, screen reader, shake cursor and zoom/magnifier behavior. C4.0 must reconcile the installed runtime surface rather than assuming this static list remains complete after Ubuntu/KDE updates.

## 2. KWin KCM surface from `kwin-common`

The audited Ubuntu 26.04 KWin surface includes:

| KCM/plugin | Functional area | C4 acceptance focus |
|---|---|---|
| `kcm_animations` | Global animation speed | Change/persistence and KWin health |
| `kcm_kwin_effects` | Desktop Effects | Representative effect lifecycle |
| `kcm_kwin_scripts` | KWin scripts | Discovery/enable/disable/configuration lifecycle |
| `kcm_kwin_virtualdesktops` | Virtual desktops | Add/remove/switch/persistence |
| `kcm_kwindecoration` | Window decorations | Supported setting applies live/persists |
| `kcm_kwinrules` | Window rules | Wayland application matching |
| `kcm_kwinxwayland` | XWayland controls | Policy changes without breaking intended compatibility |
| `kcm_virtualkeyboard` | Virtual keyboard | KWin input-method path with `plasma-keyboard` |
| `kcm_kwinoptions` | Window management behavior | Representative focus/placement/action settings |
| `kcm_kwinscreenedges` | Screen edges | Trigger and persistence |
| `kcm_kwintabbox` | Task/window switcher | Layout/behavior and Alt-Tab operation |
| `kcm_kwintouchscreen` | Touchscreen edges | Surface inventory plus later hardware validation |

KWin also ships screenshot/screencast plugins. C4 therefore treats Wayland capture/sharing as a KWin + PipeWire + portal/client path, not merely a portal-package check.

## 3. External KCM/integration surfaces in the current candidate

| Package(s) | Visible/related surface | Current C4 treatment |
|---|---|---|
| `kscreen` | Displays / HDR/display OSD | C4.1 virtual-output test; physical multi-monitor/HDR later |
| `powerdevil` | Power/battery/brightness | C4.12; hardware capability split |
| `kde-config-screenlocker` | Screen locking | inventory plus applicable software/session behavior |
| `kde-config-sddm` + `sddm` | Login screen configuration | privileged write path in C4.2; preserve C2 greeter baseline |
| `kde-config-flatpak` + `flatpak` | Flatpak permissions | C4.6 real sandbox behavior |
| `krdp` | Remote Desktop settings/server | C4.8 end-to-end external-client tests |
| `plasma-nm` + NetworkManager | Network connections | C4.3 |
| `bluedevil` + BlueZ | Bluetooth | C4.5 virtual HCI software path + physical follow-up |
| `print-manager` + CUPS | Printers | C4.9 virtual IPP job lifecycle |
| `kdenetwork-filesharing` + Samba | Dolphin folder sharing | C4.11 external SMB client |
| `kde-config-gtk-style` + Breeze GTK | GTK appearance | C4.15 |
| `plasma-disks` | SMART disk health | C4.10/C4.15 justification + hardware follow-up |
| `polkit-kde-agent-1` | Authentication dialogs | C4.2 real privileged action |
| `xdg-desktop-portal-kde` | Portals | C4.6/C4.7 |
| `xdg-desktop-portal-gtk` | Portal compatibility fallback | C4.6 routing evidence; keep/remove decision after test |
| `libpam-kwallet5` | Wallet unlock at login | C4.2 password-login flow |
| `at-spi2-core`, `orca`, `speech-dispatcher` | Accessibility / screen reader | C4.14 |

## 4. Network/VPN integration

The current candidate includes:

- `network-manager-openvpn`
- `network-manager-openconnect`

These remain candidates because Plasma-NM exposes corresponding workflows. C4.3 must prove real controlled tunnels and traffic; plugin presence alone is insufficient.

Additional VPN protocols are not automatically claimed. The rule remains: do not present a workflow as supported unless its backend is present and tested.

## 5. Printing and network-sharing completeness

### Printing

Current product candidates:

- `print-manager`
- `cups`
- `cups-client`
- `cups-filters`

C4.9 must exercise a real virtual IPP job path, queue state, cancellation and failure behavior.

### Samba sharing

Current product candidates:

- `kdenetwork-filesharing`
- `samba`
- `kio-extras`
- `kio-fuse`

C4.11 tests both remote SMB consumption and creation of a local share through the shipped KDE integration, with an external client verifying access.

## 6. C4 test classes

Each surface receives one or more classes:

- **Software-only** — fully automatable in a real Plasma VM session.
- **Virtualizable** — requires a VM device/service fixture but can be automated credibly.
- **Hardware-assisted** — requires representative physical hardware for the hardware claim.
- **Privileged/system** — explicitly tests Polkit/PAM/system service behavior.
- **External-client** — requires another process/guest/client role outside the tested server/session.

Hardware status is separate from C4 execution status. A virtualized software stack may be `PASS-C4` while physical validation remains `PENDING-HW`.

## 7. Deliberately unresolved / not currently claimed

These remain outside the hard baseline until policy and complete backend paths are chosen:

- `plasma-firewall` — no supported firewall backend policy selected;
- `plasma-thunderbolt` — physical authorization testing required;
- `plasma-vault` — crypto backend and lifecycle/recovery design required;
- fingerprint/PAM — auth-stack and hardware testing required;
- KDE Connect — product/default-app decision;
- browser integration — waits for browser/default-app policy;
- scanner workflow — no scanner UI/app is currently exposed by the baseline;
- archive/RAR workflow — Phase 5 application capability unless C4.0 discovers a current exposed surface.

Discover is resolver-safe under the implemented Snap policy, but remains outside the hard `supralinux-desktop` baseline until its product role is deliberately chosen.

## 8. Immediate C4 work

The old “first clean-system pass” is complete and must not be repeated as if it were pending. The next sequence is now:

1. implement C4.0 runtime surface discovery;
2. generate a versioned coverage manifest from the known matrix IDs;
3. compare runtime-discovered KCM/KWin/integration surfaces against that manifest;
4. fail on any unknown in-scope exposed surface;
5. only after C4.0 is green, implement C4.1;
6. let later C4 failures drive package/configuration changes one isolated defect at a time;
7. after all C4 subgates close, re-evaluate and freeze the exact dependency set.

Do not add or remove product packages merely to make this static audit list look tidy before C4.0 establishes the actual runtime surface.
