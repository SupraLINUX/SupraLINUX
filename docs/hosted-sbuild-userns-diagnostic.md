# Hosted sbuild-unshare — diagnóstico aislado

El mecanismo sbuild-unshare hospedado estuvo en HOLD tras los runs 38700751372 y 38701383856, ambos INFRA_INVALID. Ese HOLD histórico se resolvió exclusivamente para la ejecución sin root dentro de Ubuntu KVM en el run 38750289548; la vía root-mode original no se declara reparada. El segundo creó un tarball buildd correctamente, pero sbuild 0.91.2ubuntu3 falló al crear la sesión de chroot sin registro --debug. No se consumió KDE Attempt.

Este workflow opt-in y activable por cambios propios de scripts/diagnose-sbuild-userns.sh recopila únicamente capacidades UID/GID, mappings de usuario normal y root, y límites del kernel en un runner GitHub-hosted Ubuntu 26.04. No altera sysctls, no inicia KVM, no reconstruye snapshots, no ejecuta sbuild y no cambia los tests DEP-8 certificados. Los PASS de namespaces son diagnósticos, NO certificación de sbuild, de invitados KVM ni de paquetes.

Antes de reparar o repetir el smoke KVM, comparar el resultado con el contexto real del invitado y reproducir el fallo concreto a escala mínima con sbuild --debug. No promover el preflight CLI Tools -3 sin build backend certificado. El fixture DEP-8 estable sigue intacto.

Fuentes: https://ubuntu.com/project/docs/contributors/setup/set-up-for-ubuntu-development/ ; https://manpages.ubuntu.com/manpages/resolute/man1/sbuild.1.html ; https://manpages.ubuntu.com/manpages/stonking/man1/newuidmap.1.html ; https://bugs.debian.org/1101753 .

## Primer resultado real (hosted runner; no invitado)

Run 38745890347 en el commit d8ba82a: recolección PASS, no certificación de sbuild.

- Ubuntu 26.04 amd64, util-linux 2.41.3-3ubuntu2.2, uidmap 1:4.17.4-2ubuntu3.
- kernel.unprivileged_userns_clone=1; apparmor_restrict_unprivileged_userns=1.
- runner: 65536 sub-UIDs y sub-GIDs; root: 0 sub-UIDs/sub-GIDs registrados.
- runner-single-id: FAIL, Operation not permitted escribiendo uid_map.
- runner-subordinate-ids: PASS; root-single-id: PASS; root-subordinate-ids: PASS.

La asimetría comprueba que la política de mapeo importa, pero NO
identifica la causa del fallo del invitado ni verifica que el backend de
sbuild haya podido abrir su sesión. Ningún paquete fue compilado.

## Segundo experimento pequeño: sbuild real fuera de KVM

Reutilizamos el mismo workflow en un runner hosted Ubuntu 26.04 sin arrancar
ninguna VM. El script scripts/probe-hosted-sbuild-backend.sh genera una fuente
Debian descartable 0.1, crea un tarball buildd con mmdebstrap --mode=root
y ejecuta sbuild --debug como root con entorno saneado. Conserva logs
limitados y verifica .deb/.changes/.buildinfo si el build termina exitoso.

El resultado distingue fallos de mmdebstrap, de sbuild y de verificación
de artifacts. Cualquier PASS sería exclusivamente de este host efímero:
no certifica la ejecución dentro del invitado KVM, el preflight -3,
compatibilidad ABI ni un KDE package Attempt.

## Resultado root-mode y comparación siguiente

Run 38747014708 (55152dd): el smoke nativo, ejecutado como root,
completó el tarball con mmdebstrap --mode=root pero sbuild --debug falló
antes del build: Fail-Stage=create-session. El log completo indica
Sbuild::ChrootRoot; no contiene la excepción/llamada de bajo nivel,
de modo que NO demuestra todavía un error de UID/GID específico.
La infraestructura KVM no intervino. El CI de ese SHA pasó (38747024726).

El siguiente experimento usa el MISMO runner y fixture genérico pero
ejecuta mmdebstrap --mode=unshare y sbuild como usuario no privilegiado,
sin sudo, para comparar con el camino recomendado por Ubuntu.
La comparación host/root vs host/user sólo diagnostica el host,
no certifica el invitado KVM ni un paquete.

## Native unprivileged PASS y verificación opt-in dentro de KVM

Run 38747868023 del SHA e219135: mmdebstrap --mode=unshare,
sbuild --chroot-mode=unshare y .deb/.changes/.buildinfo PASS en hosted
Ubuntu 26.04 como usuario no privilegiado; Repository Policy 38747880762 PASS.
No es todavía PASS del invitado.

Un evento PR labeled con la etiqueta ci:hosted-sbuild-guest inicia el job
`guest` del workflow de diagnóstico existente. Reutiliza exactamente la
clave de caché del workflow original y rechaza misses; verifica SHA-256 de
la imagen y de sus inputs antes y después. Ejecuta sobre un overlay
autopkgtest y una COPIA temporal del fixture DEP-8 estable, sin modificar
su source de Git ni reconstruir la imagen. El único guest-smoke combinado
prueba el backend en modo no root. Un error es INFRA_INVALID del mecanismo,
no FAIL de KDE ni un Package Attempt. La base QCOW2 NO se vuelve a guardar.

## Cierre de mecanismo guest unprivileged — 2026-10-15

- Commit comprobado: f1f2cb8366dc3edadc5b1d54772c13413475b608.
- Run: 38750289548, PASS; Repository Policy previo: 38750025273, PASS.
- Restauración: cache hit exacto de la base original (1.318.909.194 bytes de caché transferidos), sin reconstrucción ni resellado.
- Ensayo: Ubuntu 26.04 KVM real y un único test DEP-8 que conserva el guest-smoke de identidad y anexa en una copia temporal el smoke sbuild sin root.
- mmdebstrap --mode=unshare: rootfs=PASS.
- sbuild --chroot-mode=unshare, usuario normal: host_sbuild=PASS (dentro del invitado), archivo .deb amd64 y .changes/.buildinfo verificados por el smoke.
- autopkgtest/summary: guest-smoke PASS; sha256 8aa5951ad5bd0b763cb76c6f5a283d5fe16f6e2f4540de19d18ff4fe1f871774.
- Marca final: GUEST_SBUILD_UNSHARE_MECHANISM_PASS; NO_KDE_PACKAGE_PASS.
- Artifact de diagnóstico 11981310968: sha256:662b6b308fdd540fc352812a146dd5b4968545ade1a807a65d0d8af1c44410d1, retención temporal 30 días.
- Manifest acotado: manifests/evidence/hosted-sbuild-guest-milestone-2026-10-15.json.

La evidencia certifica la mecánica de construcción guest/UID no privilegiado con
inputs y versión registrados. **No** declara PASS de KDE CLI Tools, preflight -3,
compatibilidad Ubuntu/Qt, actualización APT, reproducibilidad de paquetes KDE
ni equivalencia con el runner autoritativo de publicación. Attempt 4 no empezó.

El error del modo root previo se reprodujo fuera de KVM en 38747014708;
la causa syscall/identidad de bajo nivel no quedó demostrada. El cambio
validado es evitar el camino root-mode para este backend y utilizar el
modo sin privilegios, **no** atribuirle una causa definitiva al error
anterior. La imagen/fixture base certificados permanecen congelados.
