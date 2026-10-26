# Manifiesto de procedencia — Eggo

Los manifiestos se generan con `scripts/generate_eggo_manifest.py` a partir de una carpeta local de originales. El script solo lee los PNG y no crea anotaciones ni modifica, renombra, mueve, convierte o elimina los originales.

```powershell
$env:PYTHONPATH = "src"
python scripts/generate_eggo_manifest.py <ruta-a-originales-eggo>
```

## Archivos generados

- `datasets/esceniq/manifests/eggo_source_manifest.csv`: inventario ampliado para la revisión humana. `source_path` es relativo a una raíz configurable de originales y por ello no divulga una ruta local personal.
- `datasets/esceniq/manifests/eggo_dataset_records_pending.csv`: proyección estricta al contrato CSV de `DatasetRecord`: `image_path`, `label_path`, `class_ids`, `source`, `group_id`, `split`, `license`.

La política existente de `datasets/esceniq/.gitignore` ignora `manifests/*`. Por tanto, estos dos CSV quedan deliberadamente como artefactos locales y no se incluirán en Git de forma accidental; el script, las pruebas y esta guía sí permiten reproducirlos.

El CSV de `DatasetRecord` es estructuralmente válido mediante `read_manifest()`/`validate_manifest()`, pero todavía no puede superar `validate_manifest_paths()`: los originales no se han copiado ni enlazado dentro de la estructura de dataset, y las etiquetas `labels/*.txt` no existen porque la anotación está pendiente. Esa validación corresponde al paso posterior, una vez autorizada la preparación física y creadas las etiquetas.

## Correspondencia de campos

| Manifiesto ampliado | DatasetRecord | Decisión |
| --- | --- | --- |
| `source_path` | `image_path` | Ruta relativa, `originales/<archivo>`. |
| `class_id=0`, `brand=eggo` | `class_ids=0` | Clase oficial de US-001. |
| `source_type` | `source` | `google_images_capture`. |
| `group_id` | `group_id` | `provisional-unresolved-source`; no afirma una fuente independiente ni común. |
| `split` | `split` | Vacío; no hay partición asignada. |
| `license=unverified` | `license` | No se presenta como licencia verificada. |

`source_url=unknown` expresa que no se conoce la URL original, no una URL inferida. Los `image_id` se derivan de los primeros 16 caracteres de SHA-256, por lo que son estables respecto al contenido; el SHA-256 completo se conserva aparte.

## Estados y revisión humana

Todas las filas tienen `annotation_status=pending`. Las incidencias del informe de auditoría se trasladan a `notes`. `review_status=needs_review` identifica imágenes con lado mínimo menor de 400 px, relación de aspecto fuera de la banda operativa o revisión visual prioritaria; las restantes permanecen en `pending`.

Todos los registros usan de forma deliberada el mismo grupo provisional. No debe ejecutarse la separación por grupos hasta que una persona revise procedencia, campañas o clips y sustituya ese marcador por grupos de fuente reales y trazables. También permanecen pendientes en las 50 imágenes: URL/origen original, licencia o permiso, agrupación real y decisión de aptitud para anotación de las imágenes señaladas en la auditoría.
