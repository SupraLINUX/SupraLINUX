# Instrucciones del proyecto SupraLINUX

Leer README, docs/distribution/README.md, PROTOTYPE_GATES.md y las decisiones aplicables. Los [principios canónicos](https://github.com/SupraLINUX/SupraDesktop/blob/docs/m00-import/PRINCIPLES.md) y [política upstream](https://github.com/SupraLINUX/SupraDesktop/blob/docs/m00-import/docs/development/UPSTREAM_POLICY.md) se comparten con SupraDesktop. 
- Separar desktop y distro: consumir versiones fijadas del escritorio y contratos públicos. No duplicar tokens, SDK ni acciones.
- Reutilizar, adaptar o implementar por evidencia, con atribuciones y licencias. No elegir backend definitivo sin gates.
- Raíz activa no se modifica mediante layering; paquetes efectivos por despliegue, rollback y datos persistentes. AUR libre por consentimiento; no ejecución automática.
- Beginner First: GUI clara, progreso real, opciones avanzadas, accesibilidad, confirmación de operaciones sensibles.
- No ejecutar scripts no revisados, usar claves productivas, flashear firmware ni modificar discos host durante prototipos. VM y datos descartables.
- Mantener NOT_RUN/BLOCKED/FAIL/PASS con evidencia; CI documental no es validación de runtime.
- Ramas de trabajo y PR; no fusionar main, publicar releases, migrar instalaciones ni force-push sin autorización explícita. 
- Licencia propia pendiente; auditar dependencias y recursos antes de incorporación.
