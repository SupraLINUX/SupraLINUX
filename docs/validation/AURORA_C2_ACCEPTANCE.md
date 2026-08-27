# Aurora C2 Acceptance Record

Status: **ACCEPTED / GREEN**

This record captures the first formally accepted Aurora C2 result using the current SupraLINUX SDDM/KWin Wayland greeter architecture. It supersedes any earlier C2 evidence produced while the greeter depended on Xorg.

## Accepted source state

- Repository: `SupraLINUX/SupraLINUX`
- Branch under test: `development`
- Commit: `8fbde31fb415500e1d52659c1cffbdbc853f9641`
- Commit message: `desktop: move SDDM greeter to Wayland`
- C2 workflow run: `33039513394`
- C2 job: `98409680392`
- Workflow conclusion: `success`

The same source state also passed package/APT resolution and the independent clean-rootfs gate. C1 completed successfully as a regression check after the settings/package change.

## Persistent runtime evidence

GitHub Actions artifact:

- Name: `aurora-c2-boot-diagnostics`
- Artifact ID: `9633456511`
- Artifact digest: `sha256:0f71726d0e8737f839fd760072eafc25cd4fe32b148e5dd285c965eb7bc0eaaf`

The artifact contained four files and every file was reviewed in full before C2 was accepted:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `aurora-c2-serial.log` | 83,146 bytes | `10bbb5bd11e1aea5b775cbee79d843c4dcc5f3e8045bfd3b53056625d261b11c` |
| `c2-validation.log` | 743,469 bytes | `6f0db5d7ce372b24aa59618341009ca6946784cc5759535da5e49d7213fd1580` |
| `debootstrap.log` | 15,031 bytes | `2fae459bd5957fe42032b4674909c909c5a3ae922339a85d387f70021fbb59fc` |
| `rootfs-discover-simulation.log` | 278 bytes | `25be157344b48fdd0d93e635c15c42aed7ffcb073d43f82360306692c56558e5` |

## Acceptance evidence

The serial console contains exactly:

- `1 × AURORA_C2_CHECK_START`
- `1 × AURORA_C2_SUCCESS`
- `0 × AURORA_C2_FAILURE`

The guest reached both `multi-user.target` and `graphical.target`. The SDDM user session was created before the probe emitted success, and the guest shut down normally afterward.

C2's guest probe can emit `AURORA_C2_SUCCESS` only after all of the following runtime assertions succeed:

- PID 1 is systemd;
- `graphical.target` and `multi-user.target` are active;
- emergency/rescue targets are inactive;
- `/` is read/write;
- `apt-get check` succeeds;
- SupraLINUX base/settings/desktop packages are installed;
- Plasma Wayland, KWin Wayland, XWayland, layer-shell-qt and SDDM are installed;
- Snap remains absent and blocked;
- `plasma-session-x11`, `plasmax11.desktop` and `startplasma-x11` are absent;
- Aurora's SDDM configuration selects `DisplayServer=wayland` and KWin Wayland;
- SDDM is the configured display manager;
- systemd-logind is active;
- `/dev/dri/card0` exists and `seat0` is graphical;
- `kwin_wayland` is running as the SDDM user;
- `sddm-greeter` is running as the SDDM user;
- `sddm.service` is not failed.

The complete validation log confirms `xwayland` was installed. Exact searches found no `xserver-xorg` package occurrence and no `plasma-session-x11` occurrence in the final C2 composition log. The serial console contained no runtime `Xorg` process line.

## Non-blocking shutdown warning

After `AURORA_C2_SUCCESS`, while the machine was already entering poweroff, systemd logged:

`sys-devices-virtual-misc-rfkill.device: Failed to enqueue SYSTEMD_WANTS job ... systemd-poweroff.service has 'start' job queued`

This occurs during the deliberate CI shutdown after all C2 assertions have passed. It is not a greeter, KWin, SDDM, package or boot failure and does not invalidate C2.

## Scope of this acceptance

C2 proves that the package-defined Aurora system can boot through `graphical.target` and sustain the configured **SDDM greeter on KWin Wayland** in the QEMU validation environment.

C2 does **not** prove a normal user's Plasma session yet. It also does not prove real-hardware GPU compatibility. Those belong to C3 and later hardware validation.

The next gate is C3: start a real disposable Plasma Wayland user session and validate the desktop stack, including an XWayland application-compatibility smoke test.
