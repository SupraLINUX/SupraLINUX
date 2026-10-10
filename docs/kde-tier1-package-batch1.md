# KDE Frameworks 6.30 Tier 1 — package batch 1

Status: **CLOSED PASS — KCodecs, KDBusAddons and ThreadWeaver are 3/3 PASS**

Last reviewed: **2026-09-14**

## Scope

Batch 1 generalizó el hosted package path para tres nodos independientes.

- `kcodecs`;
- `kdbusaddons`;
- `threadweaver`.

Todos dependen sólo de ECM `6.30.0-0supralinux3` PASS.

KDE upstream permanece como autoridad.

Ubuntu y Debian sólo aportan referencias de packaging y compatibilidad.

## Attempt 1 — tres FAIL reales

Commit `50611225422b05803ee49d8d5fc8ff4f84a21d99`.

Run `34709829162`.

Los tres nodos fueron intentados realmente.

Un `reuse lint` inventado por SupraLINUX falló antes de los autotests.

KDE no define ese full-tree gate como requisito de build.

No se atribuye resultado de autotests KDE al intento 1.

## Attempt 2 — tests PASS, package gates FAIL

Commit `3fa96423bb01b8a7cd63a62ab5947cf7ef57b482`.

Run `34710627400`.

KCodecs alcanzó `8/8` tests PASS.

Después `dpkg-gensymbols` expuso un baseline Ubuntu 6.24 obsoleto.

KDBusAddons alcanzó `3/3` tests PASS.

Su build binario completó antes del fallo de contrato SupraLINUX.

ThreadWeaver alcanzó `8/8` tests PASS.

Su build binario completó antes del mismo fallo de contrato.

Estos siguen siendo FAIL históricos reales.

## Attempt 3

Commit `c4de13b66184cb3b84283f1c4c5f0668f577b0de`.

Run `34713034164`.

### KDBusAddons — PASS

Revisión `6.30.0-0supralinux3`.

Job `103605147881`.

Artifact `10304340428`.

Artifact SHA-256 `2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799`.

Tests **3/3 PASS**.

Lintian error gate PASS.

SONAME `libKF6DBusAddons.so.6`.

Consumer smoke PASS.

Downstream eligible.

### ThreadWeaver — PASS

Revisión `6.30.0-0supralinux3`.

Job `103605147772`.

Artifact `10303986419`.

Artifact SHA-256 `6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8`.

Tests **8/8 PASS**.

Lintian error gate PASS.

SONAME `libKF6ThreadWeaver.so.6`.

Consumer smoke PASS.

Downstream eligible.

### KCodecs — FAIL at Lintian

KCodecs compiló y pasó **8/8 tests**.

Lintian rechazó 15 símbolos internos `std::format` y Unicode.

La versión mínima generada incluía la revisión Debian.

No se ocultaron los símbolos.

Se revisaron como detalles de compiler/libstdc++.

Se conservaron como `(optional=toolchain)`.

Su mínimo upstream es `6.30.0`.

## Attempt 4 — KCodecs PASS

Commit `6c156b6a1dc0fc9e6c9e43eae90c3da86f6b0cb9`.

Run `34716761551`.

Revisión `6.30.0-0supralinux4`.

Job `103615297758`.

Artifact `10305050385`.

Artifact SHA-256 `d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45`.

Tests **8/8 PASS**.

Lintian error gate PASS.

SONAME `libKF6Codecs.so.6`.

Consumer smoke PASS.

`.buildinfo` prueba ECM `6.30.0-0supralinux3`.

Downstream eligible.

Runtime `.deb` SHA-256 `66b34b1ec140e1942d906c4e8537661bd540f959277e41de9a772e1e0956be13`.

Development `.deb` SHA-256 `87be51ba7f3ea8813e1ce61b3c6975b312db9c62d24f41e0909edb4d344f92dd`.

Data `.deb` SHA-256 `70f2197d5fa6f475d2d414ef9a13a3e885bceee73e7dcf95983f3a3313565c24`.

`.buildinfo` SHA-256 `b7b76708384495225491b58067c10547c5c29ab66282bca3371ac2069c649ff6`.

`.dsc` SHA-256 `50d5e17652c58fab76fc3c7c4e3f765e14df744487d8600bf2950e68d5403ce4`.

Rootfs SHA-256 `b0bcb87ff643d730940cbd267745cf18e868e01f64e7270d0ddeb2e348c950cf`.

## Infrastructure scope incident

Run `34716761551` seleccionó dos nodos PASS innecesariamente.

La primera fingerprint incluía metadata descriptiva no consumida.

KDBusAddons job `103615297686`.

Artifact `10305410248`.

SHA-256 `ce17097096841a500ce8b2e4f24171253b91ba1dce4a6560d0107d626eb32b1a`.

ThreadWeaver job `103615297757`.

Artifact `10304955612`.

SHA-256 `79e5393b892ae1ee3fb9a19c21e2f41bb691c7c55bf40487bb2d5de7c42fc507`.

Ambos abortaron en `campaign-validation` con `got PASS`.

No alcanzaron source-package ni `sbuild`.

Son fallos de **infrastructure scope**.

No son intentos de paquete.

No alteran los PASS anteriores.

La fingerprint corregida usa sólo inputs consumidos por el runner.

Estado, evidencia y metadata descriptiva no provocan rebuild.

## Revalidación source+binary Lintian

Después del incidente Batch 2 con `.ddeb`, se creó un lane específico para cerrar el mismo punto ciego en los PASS históricos de Batch 1.

Workflow `34892250114` sobre commit `2b0e78b67becc2ece1064816e20b9a2b9d883c47` reejecutó las mismas revisiones Debian sin incrementarlas.

El gate preserva los `.ddeb` referenciados por `.changes` y ejecuta Lintian sobre `.dsc` y `.changes`.

Los tres nodos volvieron a compilar y validar correctamente:

- KCodecs job `104137548290`, artifact `10367990559`, artifact SHA-256 `434aee54a56b91d6f7791bb02483e61522d287a7ed1920bcb0c2872d177d3ff6` — PASS;
- KDBusAddons job `104137547996`, artifact `10367472262`, artifact SHA-256 `aac536a623fb4907b89ac73f3241032fa465e43985332eaedfd0a8c699bd76d6` — PASS;
- ThreadWeaver job `104137547891`, artifact `10367666440`, artifact SHA-256 `acf24b54f72005f3068c6257216d88a47a44efca44302f6b2bed5f6a9d0d6e6c` — PASS.

Esta revalidación es evidencia adicional hosted y no sustituye los artifacts PASS canónicos originales.

Tampoco sustituye la certificación KVM/JIT autoritativa.

El registro estructurado está en `manifests/kde-tier1-batch1-lintian-revalidation.json`.

## Closure

Batch 1 permanece **3/3 PASS**.

Batch 2 cerró posteriormente **3/3 PASS**.

Junto con Attica, el estado canónico actual es **7 Tier 1 PASS**.

Quedan **22 pending**.

Hay **0 current FAIL** y **0 BLOCKED**.

La actualización global no modifica la evidencia histórica Batch 1.

El siguiente grupo puede seleccionarse entre los 22 nodos pendientes.
