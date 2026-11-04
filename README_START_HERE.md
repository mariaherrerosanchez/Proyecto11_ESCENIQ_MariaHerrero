# ESCENIQ — paquete inicial de documentación

**Este paquete se copia a la raíz del repositorio**, no se ejecuta desde la carpeta de descargas.

## Contenido
- `specs/MASTER_SPEC.md`: visión, alcance, arquitectura, identidad y catálogo de cinco marcas.
- `specs/FUNCTIONAL_SPEC.md`: 20 historias de usuario, prioridades y aceptación.
- `specs/TECHNICAL_SPEC.md`: clases, algoritmo temporal, persistencia y tests.
- `AGENTS.md`: instrucciones permanentes para Codex.
- `scripts/create_github_issues.sh` + `scripts/sync_issues.py`: vista previa y creación idempotente por identificador de las 20 US en el repositorio y Project #3.
- `scripts/set_issue_status.sh`: cambio de estado usando IDs reales de GitHub Projects (se necesita consultar IDs primero).

## Secuencia recomendada
1. En Git Bash, dentro del repositorio, crear **manualmente** la rama `docs/initial-specs` desde `dev` y comprobar `git status -sb`.
2. Copiar `specs/`, `scripts/` y `AGENTS.md` a la raíz del repositorio.
3. Revisar los documentos y ejecutar `bash scripts/create_github_issues.sh` (**solo vista previa**, no modifica GitHub).
4. Tras confirmar las historias, ejecutar `bash scripts/create_github_issues.sh --apply` para crearlas y asociarlas al Project #3.
5. Revisar cambios, hacer commit y push **manualmente** cuando corresponda. El script de issues no hace commits, pushes ni merges.

**Aviso:** el script `--apply` sí crea/actualiza etiquetas y crea issues en GitHub; usarlo solo después de revisar la vista previa. Si se interrumpe, se puede reejecutar: detecta historias existentes por identificador US.

Los vídeos y datasets locales no deben copiarse al repositorio. No subir material audiovisual de terceros sin derechos de redistribución.
