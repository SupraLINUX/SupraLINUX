# Instrucciones de proyecto: SupraLINUX

## Objetivo y autoridades

SupraLINUX integra el KDE estable oficial más nuevo que resulte compatible con
Ubuntu 26.04 LTS mínimo y con las aplicaciones y proyectos del contrato de
compatibilidad. Ubuntu aporta la plataforma; no selecciona el escritorio.

KDE upstream define su código, funciones, dependencias y correcciones. Qt Project
define Qt. SupraLINUX selecciona, compila, empaqueta, prueba y distribuye el punto
compatible. No se propone mantener un fork de KDE o Qt ni desarrollar sus propios
parches de seguridad; debe detectar e integrar las correcciones que publique
upstream. Las adaptaciones de packaging e integración se documentan.

Reutilizar Qt de Ubuntu cuando satisfaga los requisitos de KDE. Una versión Qt
más nueva requiere evidencia de compatibilidad; el número de versión por sí solo
no prueba que sea compatible o incompatible. Si una transición no pasa el
contrato, conservar el KDE estable más nuevo ya compatible. Beta/RC no son
canónicos por defecto. Verificar upstream antes de seleccionar otra release y
fijar los inputs de cada campaña; no cambiar la selección durante un build.

Mantener el sistema mutable, basado en .deb, APT y dpkg. La recuperación prevista
usa Btrfs, Snapper, hooks APT y un entorno de recuperación.

## Estado, evidencia y continuidad

Al iniciar, verificar repositorio, rama, HEAD y manifests vivos. Consultar
`docs/status/current.md` para encontrar el gate actual. Un handoff orienta; no
sustituye la comprobación. Las instrucciones contienen políticas permanentes;
versiones, autorizaciones, IDs, hashes y resultados viven en el repositorio.

La evidencia histórica cerrada es inmutable. Reutilizarla si sus inputs y alcance
siguen siendo aplicables. Un cambio relevante exige revalidar sólo la parte
afectada, conservando los resultados anteriores. Los validators históricos
comprueban su evidencia; el lifecycle actual valida su propio estado y gate.

Continuar por los pasos autorizados hasta completar el objetivo o encontrar un
bloqueo real. Evitar polling sin información nueva, pero seguir ejecuciones
activas cuando su resultado sea necesario para terminar el trabajo. Registrar
run/job IDs, SHA y próximo paso cuando una ejecución deba quedar pendiente.

## Compilación e integración

Las VMs de SupraLINUX usan SLIRP dentro de QEMU, sin crear redes libvirt,
bridges, TAP, DHCP ni rutas en el host y sin usar direcciones o MAC de la LAN.
Bloquear redes privadas externas dentro del guest y activar su enlace sólo tras
instalar los controles de aislamiento. Las nuevas VMs no limitan la velocidad
de Internet: ambos valores de tráfico en cero significan ausencia de topes,
nunca una conexión bloqueada. Los topes positivos anteriores se conservan sólo
para reproducción histórica. Certificar el cambio con un probe pequeño de
Internet/aislamiento y cleanup antes de un preflight nuevo; no hacer pruebas de
saturación. Verificar TSO/GSO desactivados en el host
e1000e que presentó hangs; esta mitigación reversible requiere revalidación tras
cada reinicio. No ejecutar los builders históricos de golden/lifecycle que aún
requieren la red libvirt retirada: primero adaptar y certificar ese transporte.
Las imágenes golden/milestone selladas y la evidencia anterior se preservan.
No instalar paquetes, añadir firewalls ni modificar servicios/configuración de
red de la PC del usuario sin permiso específico para esa acción. La autorización
general para desarrollar la distro no sustituye ese permiso. Usar las herramientas
ya instaladas. Los controles de red propuestos se ejecutan sólo dentro de la VM
desechable; la mitigación de la NIC del host la aplica el usuario.

Resolver el DAG, ejecutar independientes por nivel, alimentar dependientes sólo
con artifacts PASS elegibles y reintentar únicamente el nodo o closure afectado.
Usar runners y validators genéricos; no crear infraestructura nueva por cada
Attempt. Certificar un mecanismo nuevo con una prueba pequeña antes del paquete
investigado. Dos incidentes INFRA_INVALID consecutivos del mismo mecanismo
exigen detener los retries, diagnosticar y certificar la reparación.

Un package Attempt comienza cuando inicia una ejecución válida de sbuild o
equivalente. Planning, materialización y validación no consumen Attempts. Separar
el resultado de compilación, los tests, la infraestructura y la validación de
evidencia. BLOCKED e INFRA_INVALID nunca se convierten en package FAIL.

Cada PASS declara versión, inputs, entorno, alcance y evidencia. Hosted Ubuntu
26.04 es preflight; la evidencia release-relevant usa KVM Ubuntu 26.04
autoritativo y entornos sbuild limpios. Certificar el runner y una muestra no
equivale a certificar todos los paquetes. amd64 es la arquitectura inicial.

## Artifacts, cachés y compatibilidad

Verificar SHA-256, identidad del source, versión Debian y arquitectura antes de
reutilizar un artifact. No sustituir evidencia de la versión actual por un PASS
de otra versión. Conservar fuentes, .deb, .changes, .buildinfo y logs fuera de la
retención temporal de GitHub Actions, con índice de hashes y recuperación
verificada. Documentar cualquier falta heredada sin inventar sus archivos.

Los snapshots milestone aceleran la ejecución. Se crean tras un cierre PASS útil,
son caché y pueden reconstruirse desde artifacts y manifests. No preinstalar
dependencias que oculten Build-Depends faltantes. Registrar los inputs del rootfs
y mirrors/suites/timestamps; cuando cambien, revisar la aplicabilidad de la caché.
La campaña final desde cero verifica reproducibilidad.

El contrato de compatibilidad cubre instalación y actualización con Ubuntu y
SupraLINUX habilitados, resolución APT, dependencias, ABI, plugins y aplicaciones
representativas. Preservar epoch y metadatos Debian cuando corresponda, comprobar
precedencia con dpkg y APT y evitar transiciones parciales del stack.

Inventariar upstream completo y definir explícitamente el perfil del producto.
Las funciones del perfil seleccionado deben funcionar con sus dependencias.
Inventario y disponibilidad no obligan a instalar perfiles móviles o de TV en el
escritorio; ninguna exclusión de build/install se introduce silenciosamente.

## Publicación y herramientas

Ejecutar los checks baratos antes de CI costoso. El router automático admite
trabajo actual; las campañas cerradas quedan manuales/reutilizables. Cambios no
relacionados no cancelan builds válidos de otro SHA.

Usar el conector GitHub autorizado para consultar y publicar commits atómicos.
En el host autorizado, los scripts pueden usar gh/API autenticada para transportar
artifacts. No mostrar tokens. Verificar las rutas locales; no tocar checkouts de
otros proyectos por semejanza de nombre.

Los cambios y tests necesarios para avanzar están autorizados. El merge final y
la publicación stable requieren sus gates y confirmación explícita. Mantener la
PR en draft mientras queden gates relevantes. Testing tampoco recibe un paquete
sólo por compilar: necesita los controles de packaging y tests de su fase.
