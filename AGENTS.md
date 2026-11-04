# Instrucciones para Codex — ESCENIQ

## Antes de actuar
1. Leer `specs/MASTER_SPEC.md`, `specs/FUNCTIONAL_SPEC.md` y `specs/TECHNICAL_SPEC.md`.
2. Identificar la US asignada y confirmar criterios de aceptación y alcance.
3. 3. Comprobar `git status -sb` antes de modificar archivos.
   - Trabajar únicamente en la rama que la usuaria haya creado y seleccionado.
   - Se permiten ramas `feature/...` para funcionalidades y `docs/...` para documentación, especificaciones y scripts relacionados con su mantenimiento.
   - No crear ni cambiar ramas automáticamente.
   - Si existen archivos modificados o sin seguimiento, comprobar si pertenecen al trabajo previsto. No considerarlos automáticamente un error.
   - Detenerse si hay cambios inesperados, riesgo de sobrescritura o dudas sobre la rama autorizada.
   - Para esta tarea inicial, la rama `docs/initial-specs` está expresamente autorizada y los archivos `AGENTS.md`, `README_START_HERE.md`, `scripts/` y `specs/` son archivos nuevos previstos.

## Límites de autonomía
- **No ejecutar** `git commit`, `git push`, `git merge`, `git rebase`, `git branch -d/-D`, `gh pr create` ni `gh issue close`.
- No crear PR ni cambiar estados de GitHub sin autorización explícita.
- No borrar ramas, archivos de usuario, vídeos, datasets o artefactos de entrenamiento.
- No subir clips de películas/series, datos privados ni pesos cuya redistribución no esté autorizada.
- No introducir nuevas dependencias o servicios de pago sin justificarlo.

## Calidad
- Python modular, Clean Code, nombres descriptivos, funciones de responsabilidad clara, sin duplicación innecesaria.
- Priorizar tests de cálculo temporal, mapeo de marcas, errores y persistencia; TDD pragmático, sin ciclos RED triviales.
- Documentar decisiones relevantes en Markdown, sin comentarios redundantes.
- No presentar mocks como inferencia real ni inventar métricas de entrenamiento.
- Una clase por marca; variantes visuales dentro de la misma clase; deduplicar exposición por marca y muestra.
- Validar las tareas con comandos concretos y reportar resultados y limitaciones.

## Entrega de cada US
Explicar archivos modificados, pruebas ejecutadas, criterios satisfechos, riesgos y comandos sugeridos para que la usuaria revise y gestione manualmente Git/GitHub.
