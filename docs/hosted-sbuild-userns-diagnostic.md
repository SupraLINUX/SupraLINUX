# Hosted sbuild-unshare — diagnóstico aislado

El mecanismo sbuild-unshare hospedado sigue en HOLD tras los runs 38700751372 y 38701383856, ambos INFRA_INVALID. El segundo creó un tarball buildd correctamente, pero sbuild 0.91.2ubuntu3 falló al crear la sesión de chroot sin registro --debug. No se consumió KDE Attempt.

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
