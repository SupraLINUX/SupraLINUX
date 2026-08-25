# SupraLINUX Aurora — Upstream Integration Blockers

Status: living investigation log.

This file tracks bugs or regressions in Ubuntu/KDE/upstream components that may prevent SupraLINUX from meeting its integration contract. An upstream report is **not** automatically a SupraLINUX defect or proof that Aurora reproduces it. Every item must be reproduced on our own clean candidate before we override, patch, downgrade or pin an Ubuntu package.

## BLOCKER-CANDIDATE-001 — Repeated Wayland screen sharing may fail on Ubuntu 26.04

### Why this matters

Aurora explicitly claims a complete Wayland screen-sharing path. `AUR-PORTAL-003` therefore cannot pass merely because one share attempt succeeds.

### Current external evidence

A public Ubuntu 26.04/KDE report filed in August 2026 describes repeated screen-sharing sessions eventually failing after several start/stop cycles, leaving the Plasma recording indicator stuck. The reporter reproduced the issue with Chrome, Firefox and Brave and linked Ubuntu bug **#2163211**.

The report says downgrading `xdg-desktop-portal` from Ubuntu 26.04's 1.21.1 series to the Ubuntu 25.10/Questing 1.20.3 series avoided the failure in repeated tests. This is useful evidence for triage, **not** a SupraLINUX solution.

References:

- https://discourse.ubuntu.com/t/permanent-fix-for-screen-sharing-not-working-in-kde-firefox-brave-chrome/86057
- https://bugs.launchpad.net/ubuntu/+source/xdg-desktop-portal/+bug/2163211
- Ubuntu 26.04 package metadata currently lists `xdg-desktop-portal` 1.21.1+ds-1ubuntu3.

### SupraLINUX policy

Do **not** downgrade, hold or fork `xdg-desktop-portal` based only on the external report.

First clean-system validation must:

1. use current Ubuntu 26.04 updates;
2. run Plasma Wayland with the Aurora candidate dependency set;
3. test screen sharing with at least one Chromium-family client and one independent client where practical;
4. repeat start/share/stop for at least 30 cycles per chosen client;
5. verify the recording indicator disappears and PipeWire/portal sessions close after every cycle;
6. capture user-session logs and package versions if the failure occurs.

If Aurora reproduces the regression:

1. confirm whether the fault is `xdg-desktop-portal`, `xdg-desktop-portal-kde`, KWin, PipeWire, the browser/client, or their interaction;
2. check whether Ubuntu has already published an SRU/security update fixing it;
3. prefer an Ubuntu/upstream fix;
4. only then consider a temporary SupraLINUX override, with the normal override documentation and removal condition.

### Release effect

If reproducible and unfixed, this is a release blocker for any Aurora build that claims working Wayland screen sharing. We will not mark `AUR-PORTAL-003` as PASS with a one-shot test.
