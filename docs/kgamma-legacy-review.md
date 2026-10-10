# KGamma legacy integration review

KGamma remains in the upstream inventory. Its reviewed packaging proposal has
not been admitted for execution or package acceptance. This note records a
local diagnosis of Ubuntu's installed module, not an authoritative package gate.

With Ubuntu `kgamma 6.6.4-0ubuntu1`, the actual installed QWidget KCM passes the
supported-backend checks: RGB/master sliders, limits, Defaults, six calibration
patterns, rendering and private configuration save/load/reload. When the private
XF86VidMode shim reports no gamma support, the module shows the diagnostic and
no sliders, but still advertises Defaults. Invoking that exposed action terminates
the D-Bus wrapper with exit code 139. The supported control exits successfully.
The harness uses its own Xvfb display and a private D-Bus configuration without
service activation; core dumps are disabled and all owned processes are reaped.
No host display, global Xorg writer or privileged helper is exercised.

Static inspection of the signed `6.7.5` source finds the same unsafe path:
`KGamma::defaults()` accesses `xf86cfgbox` and `syncbox` outside the
`GammaCorrection` guard. The constructor creates those widgets only when gamma
support is available. The release's `kcmkgamma/kgamma.cpp` is byte-identical to
the official `Plasma/6.7` file at commit
`55e72f4f80848f86b3694b593dea574997a431a2`, SHA-256
`9228cfb507ad6ed9ba1b3615dc392e67eaa4ca2f6c5d1344a457027b754cf420`.
This supports a candidate compatibility concern; the candidate itself has not
been executed in this case. See the
[pinned official source](https://invent.kde.org/plasma/kgamma/-/blob/55e72f4f80848f86b3694b593dea574997a431a2/kcmkgamma/kgamma.cpp).

KDE retired the master branch content on 2026-06-03. The official README
identifies `Plasma/6.7` as the last maintained branch and describes KGamma's X11
scope. This does not remove the pinned stable release from SupraLINUX's inventory.
See the
[official retirement README](https://invent.kde.org/plasma/kgamma/-/blob/c969f9cb83d60d79ebb0514291861be908e213be/README.md)
and [commit](https://invent.kde.org/plasma/kgamma/-/commit/c969f9cb83d60d79ebb0514291861be908e213be).

The diagnosis, harness, original logs, Ubuntu module/SDK inputs and pinned
upstream file are retained in
`.artifacts/plasma-6.7.5/diagnostics/kgamma-unsupported-defaults-ubuntu-20261006/complete-diagnosis.zip`,
SHA-256 `6a04e28923f10f514b1beb931f559292d81500b3052325669b0411b40bcbe82f`.
Restoration of the evidence hash closure from an empty directory passed locally.
The public diagnosis metadata and logs live under
`manifests/evidence/plasma/diagnostics/kgamma-unsupported-defaults-ubuntu-20261006/`.

Keep KGamma pending product/integration review and preserve its native
`X-KDE-OnlyShowOnQtPlatforms=xcb` boundary. Do not hide the issue by treating an
expected crash as quality PASS or introducing an unreviewed upstream fork.
Physical calibration and full desktop integration remain separate gates.
Independent Plasma packages can continue through their own reviews and gates.
