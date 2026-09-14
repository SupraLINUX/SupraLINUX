# KDE stable dependency DAG

Status: **ECM root PASS; 7 Frameworks Tier 1 PASS; 22 Tier 1 pending; 0 current FAIL; 0 BLOCKED**

Last reviewed: **2026-09-14**

## Authority

KDE upstream stable define el desktop y sus requisitos.

Ubuntu 26.04 es plataforma, proveedor y objetivo de compatibilidad.

Un packaging de otra distribución sólo aporta referencia técnica.

No selecciona la versión KDE de SupraLINUX.

Snapshot seleccionado:

- Plasma 6.7.5;
- KDE Frameworks 6.30.0;
- KDE Gear 26.08.1;
- KDE-selected Qt series 6.10;
- Ubuntu Resolute Qt 6.10.2: hosted preflight PASS;
- final Qt provider certification: pending.

Ubuntu 26.04 currently carries `extra-cmake-modules` 6.24.0-0ubuntu1.

Eso es una **technical packaging reference only**.

KDE upstream 6.30.0 sigue siendo autoridad para ECM.

## Semántica DAG

- `PASS`: el gate definido fue intentado y completado.
- `FAIL`: el nodo fue intentado y falló por causa propia.
- `BLOCKED`: no se intenta porque un predecesor requerido está FAIL.
- `pending`: todavía no se intentó.

`BLOCKED` is never counted as `FAIL`.

Los FAIL históricos permanecen como evidencia tras un PASS posterior.

Un hosted PASS no sustituye la prueba KVM/JIT autoritativa.

Los tests de sistema y compatibilidad siguen siendo gates separados.

## Extra CMake Modules 6.30.0 — PASS

Source SHA-256 `22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e`.

Paquete validado `extra-cmake-modules 6.30.0-0supralinux3`.

### Historial

1. `6.30.0-0supralinux1`.
   Run `34689672632`.
   Artifact `10296512341`.
   SHA-256 `d47ac7361106ceb5f04729c1a3dcb4103b30255684e5b3f53b833edd6d4f6558`.
   Resultado **FAIL** en `dh_auto_test`.
   `BUILD_TESTING=OFF` eliminó el target Ninja esperado.

2. `6.30.0-0supralinux2`.
   Run `34690027788`.
   Job `103543538213`.
   Artifact `10296517706`.
   SHA-256 `89ef0003fd8282965a4c253bcd0150b8f040fe134ca0385d1365cd8c31808239`.
   Resultado **FAIL** en consumer smoke.
   También reveló findings de packaging.
   El consumer Qt carecía de `qtpaths6`.

3. `6.30.0-0supralinux3`.
   Run `34694951158`.
   Job `103556722010`.
   Artifact `10298635300`.
   SHA-256 `181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`.
   Resultado **PASS**.

La revisión PASS hace fatal `lintian --fail-on error`.

También incorpora metadata requerida y `qtpaths6` al consumer.

`.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`.

El ECM hosted preflight no afirma ejecutar toda la upstream test suite.

La upstream test suite completa sigue como **separate gate** de calidad.

## Tier 1 PASS

### Attica

`6.30.0-0supralinux2`.

Run `34706416753`.

Artifact `10301851297`.

Artifact SHA-256 `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`.

Tests `6/6` PASS.

Consumer smoke PASS.

### Batch 1 — 3/3 PASS

Los tres nodos dependen sólo de ECM PASS.

- KCodecs `6.30.0-0supralinux4`: PASS.
- KDBusAddons `6.30.0-0supralinux3`: PASS.
- ThreadWeaver `6.30.0-0supralinux3`: PASS.

KCodecs usa Debian 6.28 como referencia técnica de símbolos.

Quince símbolos internos toolchain tienen mínimo upstream `6.30.0`.

No usan una revisión Debian como mínimo ABI.

### Batch 2 — 3/3 PASS

Workflow final `34884764702`.

Commit `e0f4e7c48dcf7541538eb919374a3f4b6c293b75`.

- KTextTemplate `6.30.0-0supralinux3`.
  Job `104112549851`.
  Artifact `10363863115`.
  SHA-256 `7b9d0390ed90c882f4b7ad1993924e722bfb7ad35238c2ced52bbd5809555bc9`.
  Tests `10/10` PASS.
  SONAME `libKF6TextTemplate.so.6`.
  Consumer smoke PASS.

- KArchive `6.30.0-0supralinux4`.
  Job `104112549742`.
  Artifact `10364726750`.
  SHA-256 `0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e`.
  Tests `5/5` PASS.
  SONAME `libKF6Archive.so.6`.
  Consumer smoke PASS.

- KHolidays `6.30.0-0supralinux4`.
  Job `104112549858`.
  Artifact `10364169061`.
  SHA-256 `62186f3d6d0c856fed7b055ae917ceec0b6cdf216b37b93e22126bf3ebc8f37a`.
  Tests `8/8` PASS.
  SONAME `libKF6Holidays.so.6`.
  Consumer smoke PASS.

Todos superaron Lintian contra source y binary evidence.

Todos son downstream elegibles en el lane hosted.

## Incidentes de infraestructura

Run `34716761551` seleccionó dos nodos ya PASS incorrectamente.

KDBusAddons job `103615297686` abortó antes de source build.

Artifact `10305410248`.

SHA-256 `ce17097096841a500ce8b2e4f24171253b91ba1dce4a6560d0107d626eb32b1a`.

ThreadWeaver job `103615297757` abortó antes de source build.

Artifact `10304955612`.

SHA-256 `79e5393b892ae1ee3fb9a19c21e2f41bb691c7c55bf40487bb2d5de7c42fc507`.

Estos abortos no crean FAIL de paquetes.

Run `34884049556` reveló otro fallo del harness.

El gate Lintian reforzado no preservaba `.ddeb` referenciados.

Los paquetes ya habían completado build, tests y consumer smoke.

El incidente tampoco crea FAIL de paquetes.

Commit `e0f4e7c48dcf7541538eb919374a3f4b6c293b75` corrige el gate.

Run `34884764702` valida la corrección.

## Estado actual

Tier 1 queda en **7 PASS, 22 pending, 0 current FAIL, 0 BLOCKED**.

Sólo artifacts PASS retenidos pueden alimentar dependientes.

## Próxima expansión

Selecciona otro grupo independiente entre los 22 nodos pendientes.

Mantén la compilación paralela por nivel topológico.

Continúa aunque existan FAIL independientes.

No intentes nodos dependientes de un FAIL.

Mantén BLOCKED separado de FAIL.
