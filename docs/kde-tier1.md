# KDE Frameworks 6.30 — Tier 1

Status: **29-node source set fixed; 7 hosted package PASS; 22 package nodes pending; 0 current FAIL; 0 BLOCKED**

Last reviewed: **2026-09-14**

## Authority and scope

Tier membership and source requirements come from KDE upstream.

SupraLINUX selecciona KDE Frameworks **6.30.0**.

Ubuntu Resolute proporciona plataforma, dependencias generales y compatibilidad.

Ubuntu y Debian son referencias técnicas de packaging.

No seleccionan la versión KDE de SupraLINUX.

Frameworks 6.30 requiere Qt >= **6.9.0**.

Ubuntu Resolute Qt **6.10.2** sigue como proveedor candidato.

Su hosted preflight está PASS.

La certificación final del proveedor sigue pendiente.

## Prerequisito

Extra CMake Modules sigue siendo el root del build-system.

- paquete `extra-cmake-modules 6.30.0-0supralinux3`;
- run `34694951158`;
- artifact `10298635300`;
- `.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- estado **PASS**;
- downstream eligible.

## Conjunto Tier 1

El manifest contiene exactamente 29 nodos.

`attica`, `bluez-qt`, `karchive`, `kcalendarcore`, `kcodecs`, `kconfig`, `kcoreaddons`, `kdbusaddons`, `kglobalaccel`, `kguiaddons`, `kholidays`, `ki18n`, `kidletime`, `kirigami`, `kitemmodels`, `kitemviews`, `kplotting`, `kquickcharts`, `syntax-highlighting`, `ktexttemplate`, `kuserfeedback`, `kwidgetsaddons`, `kwindowsystem`, `modemmanager-qt`, `networkmanager-qt`, `prison`, `solid`, `sonnet`, `threadweaver`.

Cada nodo permanece fijado a KDE 6.30.0.

Cada source SHA-256 permanece fijado al valor KDE publicado.

Un nodo Tier 1 no depende de otro Framework KDE.

Todos dependen únicamente del root ECM dentro del DAG KDE.

## Evidencia de referencia

- provider availability: run `34700048774`, artifact `10299608166`;
- source packaging reference: run `34701132721`, artifact `10299579234`;
- binary-contract reference: run `34704117024`, artifact `10301282501`;
- generic packaging tree: run `34708030450`, artifact `10301938362`.

Estos gates son referencias no autoritativas.

No promueven estado por sí solos.

## PASS actuales

### Attica

`6.30.0-0supralinux2`.

Run `34706416753`.

Artifact `10301851297`.

Tests `6/6` PASS.

Consumer smoke PASS.

Downstream eligible.

### KCodecs

`6.30.0-0supralinux4`.

Run `34716761551`.

Job `103615297758`.

Artifact `10305050385`.

Artifact SHA-256 `d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45`.

Tests `8/8` PASS.

Lintian, ABI y consumer smoke PASS.

### KDBusAddons

`6.30.0-0supralinux3`.

Run `34713034164`.

Job `103605147881`.

Artifact `10304340428`.

Tests `3/3` PASS.

Full package gate PASS.

### ThreadWeaver

`6.30.0-0supralinux3`.

Run `34713034164`.

Job `103605147772`.

Artifact `10303986419`.

Tests `8/8` PASS.

Full package gate PASS.

### KTextTemplate

`6.30.0-0supralinux3`.

Run `34884764702`.

Job `104112549851`.

Artifact `10363863115`.

Artifact SHA-256 `7b9d0390ed90c882f4b7ad1993924e722bfb7ad35238c2ced52bbd5809555bc9`.

Tests `10/10` PASS.

Lintian error gate PASS.

Consumer smoke PASS.

SONAME `libKF6TextTemplate.so.6`.

### KArchive

`6.30.0-0supralinux4`.

Run `34884764702`.

Job `104112549742`.

Artifact `10364726750`.

Artifact SHA-256 `0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e`.

Tests `5/5` PASS.

Lintian error gate PASS.

Consumer smoke PASS.

SONAME `libKF6Archive.so.6`.

### KHolidays

`6.30.0-0supralinux4`.

Run `34884764702`.

Job `104112549858`.

Artifact `10364169061`.

Artifact SHA-256 `62186f3d6d0c856fed7b055ae917ceec0b6cdf216b37b93e22126bf3ebc8f37a`.

Tests `8/8` PASS.

Lintian error gate PASS.

Consumer smoke PASS.

SONAME `libKF6Holidays.so.6`.

## KCodecs ABI/symbol policy

Ubuntu 6.24 tenía una referencia de símbolos obsoleta para KDE 6.30.

Todavía exigía dos constructores `KCharsets` ya eliminados.

SupraLINUX usa Debian 6.28 como baseline técnico más cercano.

KDE 6.30 emite 15 símbolos internos por `std::format`.

Se conservan como `(optional=toolchain)`.

Su versión mínima es upstream `6.30.0`.

No se usa una revisión Debian como versión mínima.

## Batch 2 ABI y packaging

KTextTemplate conserva una transformación ABI determinística revisada.

KArchive empaqueta `KF6Archive.pc` dentro del paquete de desarrollo.

KHolidays conserva 36 símbolos públicos nuevos del calendario hebreo.

Esos símbolos tienen mínimo upstream `6.30.0`.

KHolidays declara `python3:any` para su transformación de símbolos.

Los tres paquetes `-doc` preservan nombres Debian-family.

Actualmente no contienen QCH.

No se afirma documentación QCH inexistente.

## Gate Lintian Batch 2

El gate rechaza `Lintian: fail` informado por `sbuild`.

También valida `.dsc` y `.changes` conjuntamente.

Preserva los `.ddeb` referenciados por `.changes`.

Workflow `34884049556` descubrió la omisión inicial de `.ddeb`.

Ese run es fallo de infraestructura, no FAIL de paquetes.

Workflow `34884764702` valida la remediación completa.

## Estados actuales

- PASS: **7**;
- pending: **22**;
- current FAIL: **0**;
- BLOCKED: **0**.

Un nodo sólo es FAIL tras un intento real por causa propia.

BLOCKED queda reservado para un nodo no intentado por un FAIL predecesor.

Los FAIL históricos permanecen como evidencia después de un PASS posterior.

## CI scope

La selección de CI debe depender de inputs realmente consumidos.

Cambios de estado, evidencia o documentación no deben recompilar un PASS.

Un fallo del selector o del harness no crea un FAIL del paquete.

## Próximo trabajo

Selecciona otro grupo independiente entre los 22 nodos pendientes.

Mantén explícitos símbolos, contratos binarios, features opcionales y tests.

Mantén el PR #1 en Draft.
