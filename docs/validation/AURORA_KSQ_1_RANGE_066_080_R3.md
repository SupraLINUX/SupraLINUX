# Aurora KSQ-1 — accepted range 066–080 on r3

Status: **ACCEPTED CHECKPOINT — KSQ-1 STILL ACTIVE / NOT CERTIFIED**

This record accepts the maintained normal source-build range 66–80 against immutable slice `20260829T022000Z-r3`. It does not satisfy the dedicated reproducibility obligation for order 68 `drkonqi`, does not certify KWallet automatic session unlock, and does not close KSQ-1.

## Predecessor

The range starts only from the independently regression-valid accepted order-65 state:

- accepted checkpoint: order `65` / `295` DEBs;
- r3 accepted-065 regression run: `33965237362`;
- artifact: `9969240177`;
- digest: `sha256:8b829f4cd81afc26c340d727561b2ea2c5438487c4e1a945ce01f1eaa940165f`;
- KWallet selection/install replay: PASS;
- KWallet automatic session unlock: **NOT CERTIFIED**.

The immutable r3 input was independently validated by run `33964782073`, artifact `9969086882`, digest `sha256:6fc4c3cae63f53d5484d1e5c168f51c01fb285af5697bc6f1f8438a2cb899907`.

## Source-build run

- workflow: `.github/workflows/ksq-native-range-066-080-r3-regression.yml`;
- run: `33973287438`;
- source HEAD: `e812059c50f8f1def9a1a18489840bbee1762231`;
- artifact: `9972463409` (`aurora-ksq-native-range-066-080-r3-regression`);
- artifact digest: `sha256:e1c9dccad9164a8e8445ff2487fc17d61c55816bfa3c22da385c336cca3feda5`;
- artifact size: `155471043` bytes;
- sources: `15/15 PASS`;
- new DEBs: `50`;
- accumulated DEBs: `345`;
- `new-debs.sha256` file SHA-256: `62003c9993b2d995913b02650cd59e89f24f044bf7762ed8f3f9407a28d79abf`;
- `build-manifest.tsv` SHA-256: `74cfee53a5898331de6bb354a46c98dc842503436adddce52238ad0876d06efa`.

The source orders are 66 `kf6-kxmlgui`, 67 `kf6-kio`, 68 `drkonqi`, 69 `kf6-baloo`, 70 `kf6-kcmutils`, 71 `kf6-knotifyconfig`, 72 `kf6-kparts`, 73 `kglobalacceld`, 74 `xdg-desktop-portal-kde`, 75 `flatpak-kcm`, 76 `kf6-knewstuff`, 77 `kinfocenter`, 78 `krdp`, 79 `plasma-disks` and 80 `systemsettings`.

The range audit proves:

- command RC `0` and tee RC `0`;
- relevant AppArmor denials `0`;
- packaging adaptations in orders 66–80: `0`;
- Docker used: `0`;
- custom AppArmor used: `0`;
- uidmap file-capability hack used: `0`;
- canonical snapshot pointer changed: `no`;
- exact accepted-065 r3 regression predecessor: PASS.

Every one of the 15 retained `.build` logs contains the maintained network-isolation proof (`NETNS_DIFFERENT`, loopback-only `/proc/net`, IPv4 route isolation and `AURORA_NATIVE_BUILD_NETWORK=isolated`) and successful sbuild status. No APT HTTP(S) acquisition event is present in those build logs. The 50 produced DEBs were independently checked against `new-debs.sha256` and their Package/Version/Architecture metadata against the binary manifest.

The historical r2 failure at order 74 is therefore resolved by the proven r3 payload-completeness correction without changing `xdg-desktop-portal-kde` or adding a packaging adaptation.

## Independent acceptance

The successful source artifact was not promoted merely because its workflow was green. A separate fail-closed acceptance consumed the exact source run and artifact identities and repeated the range/evidence checks.

- workflow: `.github/workflows/ksq-accept-066-080-r3.yml`;
- run: `33978315934`;
- acceptance HEAD: `2772d36a07722d142ed37c5fe8295d1b64d8a1d7`;
- artifact: `9972976872` (`aurora-ksq-accept-066-080-r3`);
- artifact digest: `sha256:ebd60471d9834efbb4fad9f5680c6a153000aa8b9393f4821a70ff148edc2511`;
- artifact size: `8189` bytes;
- `evidence.sha256`: PASS after independent download/extraction.

Acceptance state:

- `AURORA_KSQ_R3_066_080_ACCEPTANCE=PASS`;
- first/last order: `66/80`;
- sources: `15`;
- prior/new/accumulated DEBs: `295/50/345`;
- packaging adaptations: `0`;
- external build HTTP: `0`;
- AppArmor denials: `0`;
- Docker/custom AppArmor/uidmap-filecap hack: `0/0/0`;
- DrKonqi normal build: PASS;
- DrKonqi reproducibility certified: `no`;
- next range: `81-90`.

## Boundary

The maintained KSQ-1 checkpoint is now **order 80 / 345 DEBs**.

Order 68 `drkonqi` remains one of the six dedicated independent-rebuild nodes in the fixed `95 + 6` reproducibility contract. Its normal build PASS in this range must not be represented as reproducibility certification.

Orders 81–90 require their own local-only build and independent acceptance from this exact checkpoint. KSQ-1 remains **ACTIVE / NOT CERTIFIED** and KSQ-2 remains blocked.
