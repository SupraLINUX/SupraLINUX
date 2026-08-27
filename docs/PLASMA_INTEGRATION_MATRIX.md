# Plasma Integration Matrix — Ubuntu 26.04 LTS / Aurora C4

Status: **C4 executable contract defined; execution pending**.

This is the canonical capability inventory for Aurora's first integration milestone. `docs/C4_CERTIFICATION.md` defines how these rows are executed, evidenced and certified.

A package being installed is not a pass. A KCM opening is not a pass. A capability passes only when the shipped user workflow reaches its real backend and the resulting state is observed.

## Status vocabulary

Execution status:

- `PREREQUISITE-CERTIFIED` — already covered by accepted C1/C2/C3 evidence.
- `PENDING-C4` — in automated C4 scope and not yet executed.
- `PASS-C4` — automated C4 acceptance passed.
- `FAIL-C4` — reproducible integration defect.
- `BLOCKED-UPSTREAM` — reproduced upstream blocker with evidence.
- `NOT-EXPOSED` — intentionally not part of the current Aurora Plasma baseline.
- `FUTURE` — deliberately deferred product work.

Hardware status:

- `NOT-REQUIRED`
- `VIRTUALIZED-ONLY`
- `PENDING-HW`
- `HW-PASS`

## C1-C3 prerequisites

| ID | Capability | Evidence owner | Status |
|---|---|---|---|
| AUR-CORE-001 | Plasma desktop starts | C3 acceptance | PREREQUISITE-CERTIFIED |
| AUR-CORE-002 | Wayland primary session | C3 acceptance | PREREQUISITE-CERTIFIED |
| AUR-CORE-003 | X11 app compatibility under Wayland | C3 acceptance | PREREQUISITE-CERTIFIED |
| AUR-CORE-004 | SDDM KWin Wayland greeter | C2 acceptance | PREREQUISITE-CERTIFIED |

These rows are not reopened by C4 unless a later product change creates a documented regression scope.

## C4.0 — Surface and contract inventory

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-COVER-001 | Every shipped System Settings KCM has an owner/test row | KService/KPlugin metadata + dpkg ownership | software | zero unknown in-scope KCMs | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-002 | Every shipped KWin configuration surface has an owner/test row | installed KWin plugins/KCM metadata | software | zero unknown in-scope KWin surfaces | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-003 | External desktop integrations exposed by Plasma/Dolphin are mapped | installed plugins/actions + package ownership | software | zero unknown integration surfaces | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-004 | Direct `supralinux-desktop` dependencies are justified or explicitly pending | dpkg/apt metadata + matrix mapping | software | every direct dependency maps to a capability/policy | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-005 | Portal routing is inventoried | XDG portal descriptors/config + D-Bus | software | installed backends and effective routing recorded | PENDING-C4 | NOT-REQUIRED |

## C4.1 — System Settings / KWin / desktop software behavior

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-KCM-001 | Accessibility KCM surface is mapped | Plasma/KWin accessibility config | software + HW split | every exposed control mapped to C4.14 or HW follow-up | PENDING-C4 | PENDING-HW |
| AUR-KCM-002 | Activities create/switch/remove and persist | Plasma Activities service | software | real lifecycle works and returns to baseline | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-003 | File Search/Baloo controls affect indexing state | Baloo config/service | software | enable/disable/config change reflected by backend | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-004 | Desktop paths reflect XDG user dirs | `user-dirs.dirs` + KCM | software | KCM and XDG state agree | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-005 | Game controller KCM is not a dead surface | input/game controller stack | hardware | KCM inventoried; representative controller deferred | PENDING-C4 | PENDING-HW |
| AUR-KCM-006 | Background-services KCM lists actionable installed services | KDED/systemd/D-Bus | software | representative toggle changes actual service state | PENDING-C4 | NOT-REQUIRED |
| AUR-INPUT-001 | Keyboard layouts/options | KWin/libxkbcommon/xkb-data | software | add/switch layout; option works and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-007 | Global shortcuts | KGlobalAccel/KWin | software | representative shortcut persists and triggers action | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-008 | System Settings landing/navigation | System Settings plugin discovery | software | all mapped modules discoverable without broken entries | PENDING-C4 | NOT-REQUIRED |
| AUR-INPUT-002 | Mouse settings | KWin/libinput | virtualized | representative supported setting reaches backend | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-KCM-009 | Plasma Search/KRunner plugin controls | KRunner config | software | enable/disable reflected in search behavior | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-010 | Session behavior | Plasma session management | software | representative setting persists and is consumed | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-011 | Splash configuration | Plasma look-and-feel/splash config | software | supported selection applies/persists without stale entry | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-012 | Qt Quick settings | Plasma/Qt config | software | representative setting produces documented runtime state | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-013 | Recent files/privacy behavior | KActivities/recent-doc state | software | state changes as configured and can be cleared | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-014 | Workspace behavior | Plasma/KWin config | software | representative setting is consumed and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-015 | Spell checking | Sonnet dictionaries/providers | software | supported locale has usable provider/dictionary | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-016 | KRunner settings | KRunner config | software | plugin/config lifecycle works | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-001 | Display configuration | KScreen/KWin | virtualized | virtual output resolution/scaling change applies and persists | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-KWIN-002 | Global animation speed | KWin | software | setting changes authoritative KWin config and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-003 | Desktop effects | KWin effects | software | representative effect enable/disable/config works | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-004 | Virtual desktops | KWin virtual desktop API/config | software | add/switch/remove/persist; KWin stays stable | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-005 | Window decorations | KWin decoration plugin/config | software | supported option applies live and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-006 | Window rules | KWin rules | software | rule matches representative Wayland window and is removable | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-007 | XWayland controls | KWin XWayland policy | software | policy change is reflected without breaking baseline compatibility | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-008 | Window behavior | KWin options | software | representative focus/placement/action option works | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-009 | Screen edges | KWin screen-edge config | virtualized | configured edge action triggers and cleans up | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-KWIN-010 | Task switcher | KWin TabBox | software | Alt-Tab works with selected layout/behavior | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-011 | KWin scripts | KWin scripting | software | discover/enable/disable representative script lifecycle | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-012 | Virtual keyboard | KWin input method + `plasma-keyboard` | virtualized | enable/disable path registers usable virtual keyboard | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-INPUT-003 | Touchpad | KWin/libinput | hardware | KCM inventory only in C4; physical controls deferred | PENDING-C4 | PENDING-HW |
| AUR-INPUT-004 | Touchscreen/tablet | KWin/libinput/tablet stack | hardware | KCM inventory only in C4; physical validation deferred | PENDING-C4 | PENDING-HW |

## C4.2 — Privilege and secrets integration

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-CORE-005 | Privileged desktop actions use Plasma Polkit agent | polkit + `polkit-kde-agent-1` | privileged | real privileged action challenges, succeeds with authorization, fails/cancels safely | PENDING-C4 | NOT-REQUIRED |
| AUR-CORE-006 | KWallet login integration | PAM + KWallet | privileged/session | password login unlocks wallet without redundant prompt; secret write/read/relogin path works | PENDING-C4 | NOT-REQUIRED |
| AUR-PRIV-001 | Date/time privileged helper path | timedate/system helper + Polkit | privileged | reversible privileged timezone/time-related action reaches backend | PENDING-C4 | NOT-REQUIRED |
| AUR-PRIV-002 | SDDM configuration privileged write path | `kde-config-sddm` helper + Polkit | privileged | reversible test setting writes through supported helper without corrupting C2 baseline | PENDING-C4 | NOT-REQUIRED |

## C4.3 — Networking and VPN

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-NET-001 | Ethernet | Plasma-NM + NetworkManager D-Bus | virtualized | create/activate/connect/disconnect/reconnect controlled NIC profile | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-NET-002 | Wi-Fi | Plasma-NM + NetworkManager | hardware | software surface mapped; secured Wi-Fi deferred to representative hardware | PENDING-C4 | PENDING-HW |
| AUR-NET-003 | OpenVPN | Plasma-NM + `network-manager-openvpn` | external fixture | controlled local tunnel establishes and carries traffic | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-004 | OpenConnect | Plasma-NM + `network-manager-openconnect` | external fixture | controlled supported tunnel establishes and carries traffic | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-008 | Mobile broadband surface justified | Plasma-NM + ModemManager | hardware/virtualized | exposed state is mapped; real modem path deferred unless faithful fixture exists | PENDING-C4 | PENDING-HW |
| AUR-NET-009 | Radio/rfkill state integration | kernel rfkill + NM/BlueDevil | virtualized/HW | software state propagates correctly; physical radios deferred | PENDING-C4 | PENDING-HW |

## C4.4 — Audio

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-AUDIO-001 | Desktop audio | Plasma-PA + PipeWire/WirePlumber | virtualized | real playback stream; volume/mute/device state changes reach backend | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-AUDIO-002 | Audio routing | PipeWire/WirePlumber | virtualized | stream moves between available fixture endpoints | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-AUDIO-003 | Bluetooth audio | BlueZ + PipeWire Bluetooth | hardware | physical headset profiles/connectivity deferred | PENDING-C4 | PENDING-HW |

## C4.5 — Bluetooth

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-HW-006 | Bluetooth adapter/control path | BlueDevil + BlueZ `Adapter1` | virtualized + HW | virtual HCI enable/disable/discovery state propagates end-to-end | PENDING-C4 | PENDING-HW |
| AUR-BT-002 | Peripheral pairing/reconnect | BlueDevil + BlueZ `Device1` | hardware | representative physical pairing/reconnect later | PENDING-C4 | PENDING-HW |

## C4.6 — Flatpak and portal routing

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-FLAT-001 | Flatpak runtime | Flatpak | software | local test Flatpak install/run/remove succeeds | PENDING-C4 | NOT-REQUIRED |
| AUR-FLAT-002 | Flatpak permissions KCM | `kde-config-flatpak` + Flatpak overrides/permissions | software | permission change alters sandbox behavior and is restored | PENDING-C4 | NOT-REQUIRED |
| AUR-PORTAL-001 | KDE file chooser portal | XDG portal broker + KDE backend | software | sandboxed app receives functional KDE chooser path | PENDING-C4 | NOT-REQUIRED |
| AUR-PORTAL-004 | GTK portal fallback is justified and does not steal KDE interfaces | portal routing config + D-Bus | software | effective routing matches documented policy | PENDING-C4 | NOT-REQUIRED |

## C4.7 — Capture and sharing

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-PORTAL-002 | Wayland screenshot/capture | KWin + portal + PipeWire as applicable | software/virtualized | representative capture returns valid image/stream without leak | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-PORTAL-003 | Wayland screen sharing | KWin + PipeWire + KDE portal + client | external-client | real stream plus clean close for >=30 repeated cycles per selected path | PENDING-C4 | VIRTUALIZED-ONLY |

## C4.8 — Remote desktop

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-RDP-001 | KRDP settings | KRDP KCM/config | software | KCM state persists and maps to actionable server state | PENDING-C4 | NOT-REQUIRED |
| AUR-RDP-002 | KRDP existing/physical-session path | KRDP + KWin/PipeWire/Wayland | external-client | external RDP client obtains usable authenticated session and clean disconnect | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-RDP-003 | KRDP virtual-session/monitor path | KRDP virtual monitor/session | external-client | requested virtual desktop lifecycle works end-to-end | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-RDP-004 | KDE RDP client (`krdc`) | KRDC | application decision | certify only if promoted into shipped baseline | PENDING-C4 | NOT-REQUIRED |

## C4.9 — Printing

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-PRINT-001 | Printer configuration | Print Manager + CUPS | virtualized | add/configure/remove controlled IPP target | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-PRINT-002 | Driverless discovery | CUPS/OpenPrinting + virtual IPP Everywhere target | virtualized | target discovered/usable driverlessly | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-PRINT-003 | Job lifecycle | CUPS + Print Manager | virtualized | fixture receives job; queue/status/cancel/failure path work | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-SCAN-001 | Scanning | none exposed in current baseline | product decision | no scanner UI/app is currently claimed by Aurora Plasma baseline | NOT-EXPOSED | PENDING-HW |

## C4.10 — Storage/removable media

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-HW-001 | Removable media | Solid + UDisks2 | virtualized | hotplug/mount/read-write/unmount/eject lifecycle works | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-HW-002 | Device automount settings | Plasma automounter + UDisks2 | virtualized | policy change changes attach/login behavior and is restored | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-HW-005 | SMART disk health | `plasma-disks` + SMART backend | hardware | package/surface justified; meaningful physical SMART validation later | PENDING-C4 | PENDING-HW |

## C4.11 — Samba / KIO

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-NET-005 | Browse/read/write SMB share | KIO SMB + Samba client libs | external fixture | controlled remote share browsed/read/written successfully | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-006 | Create local SMB share | KDE file sharing + Samba usershare/server | external-client | share created through shipped integration and accessed externally | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-007 | KIO resource in non-KIO app | KIO-FUSE | external fixture | remote resource exposed through conventional local path | PENDING-C4 | NOT-REQUIRED |

## C4.12 — Power/platform integration

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-HW-003 | Power management | PowerDevil + UPower/systemd | virtualized | representative policy/action works; suspend/resume where supported; Plasma remains healthy | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-HW-004 | Battery/brightness | PowerDevil hardware path | hardware | physical laptop controls later | PENDING-C4 | PENDING-HW |
| AUR-POWER-005 | Power profiles dependency is justified | `power-profiles-daemon` + PowerDevil/platform | virtualized/HW | available profile path behaves correctly or dependency is demoted later | PENDING-C4 | PENDING-HW |
| AUR-PLATFORM-001 | Ambient/orientation sensor integration is justified | `iio-sensor-proxy` | hardware | exposed capability mapped; representative sensor later | PENDING-C4 | PENDING-HW |
| AUR-PLATFORM-002 | Hybrid-GPU integration dependency is justified | `switcheroo-control` | hardware | exposed capability mapped; representative hybrid GPU later | PENDING-C4 | PENDING-HW |

## C4.13 — Locale/language/XDG directories

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-L10N-001 | Locale established before first Plasma login | locale stack + test pre-login setup | software | clean user first session has requested locale | PENDING-C4 | NOT-REQUIRED |
| AUR-L10N-002 | Plasma/Qt translation | Plasma language support + Qt translations | software | representative core UI uses selected supported language | PENDING-C4 | NOT-REQUIRED |
| AUR-L10N-003 | XDG user directories | `xdg-user-dirs` | software | clean first login creates/configures localized dirs consistently | PENDING-C4 | NOT-REQUIRED |
| AUR-L10N-004 | Language-change migration | future explicit workflow | future | populated directories never silently renamed/lost | FUTURE | NOT-REQUIRED |
| AUR-L10N-005 | Installer-selected language end-to-end | Calamares + locale stack | Phase 4 | installer not implemented yet; no C4 claim | FUTURE | NOT-REQUIRED |

C4 initially exercises at least `en_US.UTF-8` and `es_AR.UTF-8`; the full supported-language matrix belongs to installer/release work.

## C4.14 — Accessibility

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-A11Y-001 | AT-SPI runtime | AT-SPI bus/runtime | software | accessibility bus usable in Plasma session | PENDING-C4 | NOT-REQUIRED |
| AUR-A11Y-002 | Screen reader | Orca + Speech Dispatcher + AT-SPI | software | representative Plasma/Qt UI can be observed/navigated and speech path is usable | PENDING-C4 | NOT-REQUIRED |
| AUR-A11Y-003 | Visual accessibility effects | Plasma/KWin | software | representative exposed zoom/invert/color controls affect backend state | PENDING-C4 | NOT-REQUIRED |

## C4.15 — Auxiliary integration / direct-dependency closure

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-AUX-001 | System information | KInfoCenter | software | representative modules return meaningful data without broken backend | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-002 | System monitoring backend | KSystemStats | software | backend starts/serves representative metrics when requested | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-003 | GTK appearance integration | Breeze GTK + KDE GTK KCM | software | representative GTK settings/theme path is coherent and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-004 | Crash handling | DrKonqi | software | controlled non-critical test crash reaches usable crash-handling path without destabilizing session | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-005 | SSH askpass | `ksshaskpass` | software | supported askpass invocation returns/cancels correctly in session | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-006 | Pinentry Qt | `pinentry-qt` | software | controlled pinentry request is usable/cancellable in graphical session | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-007 | Plasma virtual keyboard package is justified | `plasma-keyboard` + KWin | virtualized | covered by AUR-KWIN-012; no dead direct dependency | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-AUX-008 | ModemManager direct dependency is justified | ModemManager | hardware | mapped to mobile-broadband surface or later demoted | PENDING-C4 | PENDING-HW |
| AUR-AUX-009 | rfkill direct dependency is justified | kernel rfkill | hardware/virtualized | mapped to radio-control capability or later demoted | PENDING-C4 | PENDING-HW |
| AUR-AUX-010 | `plasma-disks` direct dependency is justified | SMART backend | hardware | mapped to AUR-HW-005 or later demoted | PENDING-C4 | PENDING-HW |

## Software management / Snap policy

These resolver-policy capabilities were implemented before C4 and are not reopened as feature work unless package resolution changes.

| ID | Capability | Evidence owner | Status |
|---|---|---|---|
| AUR-SW-001 | Snap blocked by default | package/rootfs/C1-C3 policy assertions | PREREQUISITE-CERTIFIED |
| AUR-SW-002 | Snap policy is reversible | resolver-policy tests | PREREQUISITE-CERTIFIED |
| AUR-SW-003 | Discover can resolve under policy without Snap backend | package-resolution CI | PREREQUISITE-CERTIFIED |

Discover remains outside the current hard desktop dependency set until its product role is deliberately chosen.

## Explicitly unresolved / not currently claimed

The following do not become supported merely because Ubuntu packages exist:

- firewall KCM/backend;
- Thunderbolt authorization;
- Plasma Vaults;
- fingerprint authentication;
- KDE Connect as a default application;
- browser integration;
- scanner application/workflow;
- archive/RAR application workflow;
- Supra Store/custom updater;
- recovery/backup.

Archive/RAR capability remains a Phase 5 out-of-box application decision unless C4.0 discovers a current shipped user surface that makes it part of the Plasma baseline.

## Matrix execution rule

C4.0 is the guard against silent coverage gaps. Before feature subgates are accepted, the runtime inventory must prove that every currently exposed in-scope Plasma/KWin/integration surface maps to this matrix or to an explicit exclusion/hardware classification.

After C4 is complete, this matrix becomes evidence for re-evaluating and then freezing the exact `supralinux-desktop` dependency set. Package reduction is not a C4 design input; it is an evidence-driven result.
