# Distribución oficial candidata — Arch atómico
Objetivo: experiencia integrada tipo macOS, control de stack y actualización coherente, sin convertir SupraDesktop en dependencia de Arch. Nombre de distro y relación con SupraLINUX actual pendientes de decisión. No migrar proyecto existente. Estado PROPOSED; no imagen ni prototipo.
## Diseño inicial
Arch x86-64, snapshot coherente de repositorios, PKGBUILD propios, imagen versionada y firmada, raíz protegida de solo lectura, datos persistentes, kernel LTS candidato, firmware y drivers por imagen, Wayland/XWayland. Flatpak, AppImage/AppDir, SupraBundle opcional; AUR integrado, restringido o instalado por capas del sistema bajo consentimiento; sin APT/dpkg ni proveedor .deb oficial. Pacman en build y staging, no actualización in-place habitual. Distro no obliga a usar IA.
## Documentos
- [Despliegues y rollback](DEPLOYMENT.md)
- [Construcción, seguridad y releases](BUILD_RELEASE.md)
- [Applications y AUR](APPLICATIONS_AUR.md)
- [Kernel y extensiones](KERNEL_EXTENSIONS.md)
- [Instalador, datos y hardware](INSTALLER_HARDWARE.md)
- [Puertas D00–D12](VALIDATION.md)
## Referencias primarias
[Arch Archive](https://wiki.archlinux.org/title/Arch_Linux_Archive), [partial upgrades](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported), [Arkdep](https://github.com/arkanelinux/arkdep), [RAUC](https://rauc.readthedocs.io/en/latest/using.html), [sysupdate](https://www.freedesktop.org/software/systemd/man/latest/systemd-sysupdate.html). Revisión documental 2026-11-24, no pruebas realizadas.

## Aclaraciones aceptadas del mantenedor
SupraDesktop y la distribución oficial son proyectos diferenciados, con interfaces portables y sin dependencia obligatoria de Arch para el escritorio. No se ha creado otro repositorio ni migrado SupraLINUX. La UX se dirige primero a personas poco experimentadas: operaciones visuales, comprensibles, accesibles, con progreso real, cancelación y recuperación. Conservar libertad avanzada de instalación de paquetes Arch/AUR en un despliegue personalizado. v4l2loopback es ejemplo de módulo bajo demanda, no requisito de imagen base. El riesgo de AUR debe explicarse sin bloquear su uso legítimo. Decisión de backend delegada, sujeta a pruebas.
## Profundización
- [Comparativa de backends](BACKEND_EVALUATION.md)
- [SupraLayers: capas y transacciones](PACKAGE_LAYERING.md)
- [Confianza, firma y arranque](TRUST_BOOT.md)
- [Datos, configuración y recuperación](STATE_RECOVERY.md)
- [Entrega, deltas y seguridad de releases](DELIVERY_SECURITY.md)
- [Experiencia de usuario](USER_EXPERIENCE.md)
- [GPU, CUDA y gaming](GPU_COMPATIBILITY.md)
- [Matriz de investigación ampliada](DEEP_VALIDATION.md)
Todas las elecciones concretas son PROPOSED y pruebas NOT_RUN.

## Revisión de implementación
[Auditoría de código Arkdep y estrategia de adaptación](ARKDEP_SOURCE_REVIEW.md), [frontend Calamares](INSTALLER_FRONTEND.md), [prototipos y pruebas de decisión](PROTOTYPE_GATES.md). El mantenedor ratifica congelación coherente, cifrado LUKS2, recuperación offline, Beginner First y adaptación visual del instalador. Backend todavía no seleccionado; no crear fork hasta validar brecha y licencia. Calamares upstream se trasladó a Codeberg.

## Laboratorio y hardware
[Infraestructura y trust](RELEASE_LAB.md), [hardware y firmware](HARDWARE_FIRMWARE.md). fwupd/LVFS como adaptador opcional, no flasher propio. [Fronteras de repositorios](../architecture/REPOSITORY_BOUNDARIES.md).
