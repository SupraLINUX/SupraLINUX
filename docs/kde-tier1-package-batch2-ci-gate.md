# KDE Frameworks 6.30 — Batch 2 CI gate evidence

Status: **remediated and validated**

Last reviewed: **2026-09-14**

## Workflow 34884049556

Usa commit `e251338e7347e47245a83a64a6ec2efa1651b4ff`.

Clasifica este workflow como fallo de infraestructura CI.

No clasifiques sus tres nodos como FAIL propios de paquetes.

Los tres paquetes completaron build, tests y consumer smoke.

### KTextTemplate

Job `104110141498`.

Artifact `10364256456`.

Artifact SHA-256 `006b1f60aa28132d1da975432f98acdb57c257430ef3aaabea4e239252edbf0d`.

Revisión `6.30.0-0supralinux3`.

Tests `10/10` PASS.

`sbuild` informó `Lintian: warn`.

Consumer smoke PASS.

El wrapper falló en `lintian-source-binary`.

### KArchive

Job `104110142062`.

Artifact `10364111842`.

Artifact SHA-256 `6208a5cb9ccf4e1dfb34248573f9cf937dc2e320165ecd811625fbf6ea7c0b5c`.

Revisión `6.30.0-0supralinux4`.

Tests `5/5` PASS.

`sbuild` informó `Lintian: warn`.

Consumer smoke PASS.

El wrapper falló en `lintian-source-binary`.

### KHolidays

Job `104110141944`.

Artifact `10364111805`.

Artifact SHA-256 `1256146d001bd6792d7844c034cf4589890e51c1e84c2371a8f893d362b1b774`.

Revisión `6.30.0-0supralinux4`.

Tests `8/8` PASS.

`sbuild` informó `Lintian: warn`.

Consumer smoke PASS.

El wrapper falló en `lintian-source-binary`.

El error anterior de `python3` ya no apareció.

## Causa raíz

Cada `.changes` referenciaba un `*-dbgsym_*.ddeb` generado.

El directorio de evidencia no contenía esos `.ddeb`.

Lintian abortaba antes de validar el paquete completo.

Ejemplo observado:

`libkf6holidays6-dbgsym_6.30.0-0supralinux4_amd64.ddeb does not exist`.

La causa pertenece al wrapper de evidencia.

No pertenece a KDE upstream.

No pertenece al packaging de los tres nodos.

No requiere incrementar revisiones Debian.

## Remediación

Commit `e0f4e7c48dcf7541538eb919374a3f4b6c293b75` corrige el wrapper.

Copia los `.ddeb` desde el directorio de salida.

Preserva sus SHA-256 en la evidencia.

Después ejecuta Lintian contra `.dsc` y `.changes`.

Mantiene además el rechazo de `Lintian: fail` desde `sbuild`.

Mantiene `dag-node.txt` ausente ante un fallo real.

## Validación final

Workflow `34884764702` valida la remediación.

Los tres nodos ejecutaron build real.

KTextTemplate job `104112549851`: PASS.

KArchive job `104112549742`: PASS.

KHolidays job `104112549858`: PASS.

Todos superaron el gate Lintian completo.

Todos superaron consumer smoke.

Todos son downstream elegibles en el lane hosted.

Esta evidencia no sustituye la prueba KVM/JIT autoritativa.
