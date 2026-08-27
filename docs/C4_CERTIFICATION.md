# Aurora C4 — Feature Integration Certification

Status: **design accepted; implementation pending**

C1, C2 and C3 are already certified prerequisites. C4 must not reopen them unless a later product change creates a real regression risk. C4 starts from the package-defined Aurora system that already boots to a real Plasma Wayland user session with XWayland compatibility.

## 1. Purpose

C4 certifies that the Plasma features SupraLINUX exposes are functional end-to-end. A visible KCM, plasmoid, action or dialog does not pass merely because it loads. Each claimed capability must account for its frontend, backend, service/API path, permissions, runtime dependencies, happy path, common failure path and resulting state.

The canonical capability inventory lives in `docs/PLASMA_INTEGRATION_MATRIX.md`. This document defines how that inventory is executed and certified.

## 2. Non-goals

C4 does not:

- re-certify C1/C2/C3 without a regression trigger;
- freeze `supralinux-desktop` before evidence exists;
- claim broad physical-hardware support from virtual devices;
- add applications merely to make a checklist green;
- start ISO/installer, branding or C5 manual QA work;
- hide or suppress warnings instead of classifying them.

## 3. Canonical status vocabulary

Capability execution status:

- `PREREQUISITE-CERTIFIED`: already covered by an accepted earlier gate; not re-run as C4 work unless regression scope requires it.
- `PENDING-C4`: in C4 scope but not yet executed.
- `PASS-C4`: automated C4 acceptance completed successfully.
- `FAIL-C4`: reproducible product/integration defect found.
- `BLOCKED-UPSTREAM`: reproduced blocker outside SupraLINUX-owned code/package selection; evidence and upstream reference required.
- `NOT-EXPOSED`: capability is intentionally not part of the current Aurora Plasma baseline.
- `FUTURE`: explicitly deferred product work.

Hardware claim status is separate:

- `NOT-REQUIRED`: software-only capability.
- `VIRTUALIZED-ONLY`: C4 can exercise the path with a virtual fixture but makes no physical-hardware claim.
- `PENDING-HW`: representative physical hardware remains required.
- `HW-PASS`: reserved for later representative hardware certification.

A capability may therefore be `PASS-C4` and still be `PENDING-HW`.

## 4. Required matrix fields

Every C4 capability row must identify:

1. stable capability ID;
2. C4 subgate owner;
3. user-visible surface;
4. exact product claim;
5. UI package/component;
6. backend implementation;
7. relevant system/user service or unit;
8. authoritative D-Bus/API/state source where applicable;
9. product dependencies;
10. CI-only fixture dependencies;
11. test class;
12. happy-path assertion;
13. common failure-path assertion;
14. persistence requirement where relevant;
15. cleanup/rollback behavior;
16. exact PASS condition;
17. exact FAIL condition;
18. hardware follow-up status;
19. regression scope against C1/C2/C3;
20. evidence pointer after execution.

CI fixtures must never be silently promoted into product dependencies. The harness must log product package versions and fixture package versions separately.

## 5. C4 gate layout

### C4.0 — Surface and contract inventory

Goal: prove that the certification matrix covers the complete currently exposed Aurora Plasma surface before feature testing begins.

The guest inventory must collect at least:

- discoverable System Settings KCMs;
- KWin KCMs/plugins relevant to user configuration;
- selected Plasma desktop/systray surfaces with external backends;
- Dolphin/KIO integration actions relevant to shipped features;
- relevant systemd system and user units;
- relevant D-Bus names/services;
- installed XDG portal backends and effective routing configuration;
- direct `supralinux-desktop` dependencies;
- package owner and version for each discovered surface where resolvable.

The inventory is compared against a versioned coverage manifest in Git.

PASS: every discovered in-scope surface maps to a known capability row or to an explicit `NOT-EXPOSED`/hardware-only policy entry. There are zero unknown exposed surfaces.

FAIL: any in-scope visible surface has no owner/test classification, or a matrix capability claims a product surface that is not actually present without a documented reason.

C4.0 must pass before package selection changes are made for later C4 defects.

### C4.1 — System Settings / KWin / software-only desktop behavior

Covers software-only or virtualizable Plasma/KWin settings such as activities, Baloo/search, keyboard layouts, global shortcuts, workspace/session behavior, recent files, KWin animations/effects/scripts, virtual desktops, decorations, rules, XWayland policy, window behavior, screen edges and task switching.

Representative settings must be changed through supported configuration/API paths, observed in the live session, checked for persistence where appropriate and restored before the probe exits.

Hardware-specific touchpad, touchscreen, tablet and controller claims remain separate `PENDING-HW` entries even when their KCM presence is inventoried.

### C4.2 — Polkit + KWallet + privileged desktop actions

Polkit PASS requires a real privileged operation that triggers the Plasma Polkit agent, succeeds with valid authentication, does not succeed on cancel/invalid authorization, and leaves the session healthy.

KWallet PASS requires a password-based login path rather than C3 autologin, successful wallet access without an unexpected duplicate password prompt, temporary secret write/read, logout/login persistence as applicable, and cleanup.

### C4.3 — NetworkManager + Plasma-NM + VPN

Use a dedicated test NIC so destructive network assertions cannot sever the primary diagnostics path.

Ethernet must cover profile creation/activation, address acquisition, connectivity to a controlled fixture, disconnect/reconnect and state observation through NetworkManager.

OpenVPN/OpenConnect must use controlled local CI endpoints and prove actual tunnel establishment plus traffic/routing, not merely profile import or plugin discovery.

Wi-Fi and physical modem behavior remain hardware follow-up unless a sufficiently faithful kernel/VM fixture is used and explicitly documented.

### C4.4 — PipeWire + WirePlumber + Plasma audio

Use virtual audio hardware/fixtures. PASS requires a real stream, backend-visible nodes, Plasma volume/mute/device state changes reflected in PipeWire/WirePlumber, routing between available endpoints where the fixture provides them, and service stability.

`systemctl --user is-active pipewire` alone is never sufficient.

### C4.5 — Bluetooth + BlueDevil

A CI-only virtual HCI fixture such as `btvirt` may be used to prove kernel HCI → BlueZ → D-Bus → BlueDevil state propagation, adapter enable/disable and discovery lifecycle.

Pairing with representative physical peripherals and Bluetooth audio profiles remain `PENDING-HW` even if the software stack passes C4.

### C4.6 — Flatpak + portal routing

Use a locally built test Flatpak so C4 does not depend on Flathub availability.

The gate records `XDG_CURRENT_DESKTOP`, portal backend descriptors and effective routing. It must prove that KDE owns the intended Plasma-native interfaces and that GTK fallback, if installed, serves only justified compatibility paths rather than stealing KDE-specific interfaces.

Flatpak permissions must be changed through the supported permissions/override mechanisms and the sandbox behavior must demonstrably change, then be restored.

### C4.7 — Screenshot / screencast / screen sharing

Treat capture separately from generic portal activation. The test must exercise the real Wayland portal path through KWin and PipeWire, obtain a real stream, verify frame flow, close the session and ensure indicators/resources disappear.

Because `docs/UPSTREAM_BLOCKERS.md` tracks a repeated screen-sharing regression candidate, acceptance requires repeated start/share/stop cycles. The initial contract is at least 30 consecutive cycles for each selected representative client path where practical.

A one-shot success cannot certify screen sharing.

### C4.8 — KRDP / RDP

Keep server and external client roles separate. The RDP client must run outside the tested KRDP server session, either on the runner or another guest.

Cover the KRDP settings surface, existing-session/physical-session path where supported, virtual-monitor/session path where supported, authentication, usable framebuffer/input/session lifecycle and clean disconnect.

`krdc` is certified only if it remains part of the product baseline rather than merely a recommendation/application choice.

### C4.9 — Printing / CUPS

Use a controlled virtual IPP Everywhere target where possible. PASS must cover discovery or explicit addition, queue creation, a real submitted job received by the fixture, queue/job state, cancellation and a useful unavailable-printer failure path.

A running `cups.service` is not sufficient.

### C4.10 — UDisks / Solid / removable media

Use hot-pluggable virtual removable storage rather than a permanently attached fixed disk. Cover device appearance, Solid/UDisks state, mount, read/write, unmount/eject, automount policy changes, reattach behavior and cleanup with no stale mount points.

### C4.11 — Samba / KIO / KIO-FUSE

Test both directions independently:

1. Aurora browsing/reading/writing a controlled remote SMB share through KIO, including a non-KIO local-path consumer through KIO-FUSE where applicable;
2. Aurora creating a local share through the shipped KDE sharing integration and an external SMB client accessing it.

Include at least one authentication/resource failure path.

### C4.12 — Power management

PowerDevil must be tested according to capabilities exposed by the VM/platform. Cover configurable/persistent policy, an actionable idle/power path, suspend/resume where the VM can exercise it, and Plasma/KWin health after resume.

Battery, real brightness, lid switch and hardware power-profile claims remain `PENDING-HW` unless representative hardware is used.

Direct product dependencies such as `power-profiles-daemon`, `iio-sensor-proxy` and `switcheroo-control` must each be justified by an exposed capability or demoted/removed later.

### C4.13 — Locale / translations / XDG user directories

C4 does not claim installer behavior because Calamares is not yet implemented. It tests the pre-first-login mechanism with clean users whose locale is established before their first Plasma session.

At minimum exercise `en_US.UTF-8` and `es_AR.UTF-8`: `$LANG`, generated locale, Plasma/Qt translations, regional state and localized XDG user directories. User data must never be silently renamed during cleanup/migration tests.

Full installer-language coverage remains a Phase 4 gate.

### C4.14 — Accessibility

Cover AT-SPI availability, Orca startup and representative Plasma/Qt accessibility, Speech Dispatcher path, and exposed KWin accessibility controls. Installing the packages alone is insufficient; the user-facing assistive path must produce an observable result.

### C4.15 — Auxiliary integration and closure audit

Audit direct `supralinux-desktop` dependencies that do not naturally fit earlier gates, including at least:

- `modemmanager`;
- `rfkill`;
- `iio-sensor-proxy`;
- `switcheroo-control`;
- `plasma-keyboard`;
- `drkonqi`;
- `ksshaskpass`;
- `pinentry-qt`;
- `ksystemstats`;
- `kinfocenter`;
- `plasma-disks`;
- GTK style integration.

Each ends C4 as one of:

- tested and justified;
- hardware-dependent but product-justified;
- intentionally demoted/removed from the candidate dependency set.

No direct dependency may remain merely because it looked reasonable during the initial package audit.

## 6. Common PASS contract

A capability may become `PASS-C4` only when all applicable points are true:

1. shipped user surface is identified;
2. required product dependencies are present;
3. backend/service/API is available;
4. a real positive action is executed;
5. result is observed using an authoritative state source;
6. a common negative/failure path is exercised;
7. affected desktop/service components remain healthy;
8. no relevant resources are leaked;
9. test state is restored or the disposable guest is intentionally destroyed after evidence capture;
10. no relevant failed units/crashes remain unexplained;
11. package versions and targeted logs are recorded;
12. CI-only fixtures are clearly separated from product dependencies.

## 7. Failure classification

Every failure must be classified before changing packages:

- SupraLINUX dependency omission;
- SupraLINUX configuration/policy defect;
- harness/fixture defect;
- VM limitation;
- upstream Ubuntu/KDE/component defect;
- external transient infrastructure failure.

Do not change multiple product variables simultaneously when one defect can be isolated first.

## 8. Evidence contract

Each subgate uses deterministic guest markers, for example:

```text
AURORA_C4_<GATE>_STAGE=<stage>
AURORA_C4_<CAPABILITY>_PASS
AURORA_C4_<GATE>_SUCCESS
AURORA_C4_<GATE>_FAILURE:<reason>
```

The harness must require exactly one final success marker, zero failure markers and all expected capability markers for that execution set. QEMU/runner exit code alone is insufficient.

Artifacts should include, as applicable:

- serial log;
- capability result manifest;
- package/version manifest;
- relevant system/user journals;
- D-Bus/API snapshots;
- fixture logs;
- crash/failed-unit inventory;
- portal routing state;
- cleanup state.

Large VM images remain ephemeral.

## 9. Regression rule for C1-C3

C4 implementation itself does not automatically re-run C1-C3. A regression run is required when a change can plausibly affect the certified scope, for example:

- core Plasma/KWin/session package changes → C3, and C2 if greeter/session infrastructure overlaps;
- SDDM/KWin greeter configuration changes → C2 and normally C3;
- kernel/initramfs/base/systemd changes → C1 plus later affected gates;
- removing/changing XWayland/session compatibility components → C3;
- documentation-only C4 changes → no C1-C3 rerun.

The reason for every requested regression run should be documented in the corresponding change.

## 10. C4 closure rule

C4 is complete only when:

- C4.0 coverage is green;
- every current in-scope matrix capability is `PASS-C4`, `BLOCKED-UPSTREAM` with an explicit release decision, or explicitly hardware-deferred without overstating support;
- every direct `supralinux-desktop` dependency is justified by evidence or removed/demoted;
- no unknown exposed Plasma feature remains;
- known warnings/failures have classifications;
- the exact candidate dependency set is then re-evaluated and only afterward considered for freeze.

C4 completion means the automated feature-integration gate is complete. It does not replace C5 manual VM QA or later physical-hardware certification.

## 11. Current upstream/reference documentation used for the design

Recheck these before implementing each subgate because package versions/APIs can move within Ubuntu 26.04 updates:

- Ubuntu 26.04 package metadata: `https://packages.ubuntu.com/resolute/` and `https://packages.ubuntu.com/resolute-updates/`
- KDE Plasma documentation: `https://docs.kde.org/`
- KDE developer/admin documentation: `https://develop.kde.org/`
- XDG Desktop Portal documentation: `https://flatpak.github.io/xdg-desktop-portal/`
- Flatpak documentation: `https://docs.flatpak.org/`
- NetworkManager D-Bus/API documentation: `https://networkmanager.dev/docs/api/latest/`
- PipeWire documentation: `https://docs.pipewire.org/`
- WirePlumber documentation: `https://pipewire.pages.freedesktop.org/wireplumber/`
- BlueZ D-Bus APIs: `https://bluez.readthedocs.io/en/latest/`
- OpenPrinting/CUPS documentation: `https://openprinting.github.io/cups/`
- UDisks2 D-Bus API: `https://storaged.org/doc/udisks2-api/latest/`
- xdg-user-dirs: `https://www.freedesktop.org/wiki/Software/xdg-user-dirs/`

The repository acceptance records remain authoritative for the already-certified C1-C3 state.
