# Preparación del dataset YOLO

La plantilla versionada está en `datasets/esceniq/`. Conserva `data.yaml` y directorios vacíos; imágenes, etiquetas y manifiestos reales están ignorados por Git. Las rutas son relativas, por lo que la estructura funciona en Windows, Docker y Ultralytics.

```text
datasets/esceniq/
  images/{train,val,test}/
  labels/{train,val,test}/
  manifests/
  data.yaml
```

## Anotaciones y procedencia

Cada línea YOLO sigue `class_id x_center y_center width height`: coordenadas normalizadas entre 0 y 1, y ancho y alto positivos. Un `.txt` vacío es válido para una imagen negativa. Cada imagen requiere un `.txt` homónimo, aunque esté vacío; no se aceptan etiquetas sin imagen.

Crear un `DatasetRecord` por imagen con rutas relativas, `class_ids`, fuente, licencia y `group_id`. El grupo representa vídeo, clip o fuente que no puede repartirse entre conjuntos. `write_manifest()` y `read_manifest()` guardan un CSV UTF-8 portable; `validate_manifest_paths()` comprueba sus archivos sin depender de rutas absolutas.

## División sin fugas

`split_records_by_group()` asigna grupos completos con una semilla configurable; por defecto usa 70 % train, 15 % val, 15 % test y semilla 42. Devuelve advertencias cuando una clase no alcanza los tres conjuntos. Pasar clips reservados mediante `demo_groups` hace que el proceso los rechace: deben quedar fuera de entrenamiento, validación, test y selección del modelo.

Las variantes Eggo/envases, Coca-Cola/Coke/New Coke, Pepsi/Pepsi Perfect, soportes FedEx y Wilson/W inequívoca pertenecen a las cinco clases de US-001, nunca a clases nuevas. No anotar una variante ambigua sin evidencia visual suficiente. Documentar fuente y licencia antes de incorporar imágenes propias o datasets externos; no subir contenido sin permisos ni clips de demostración.

## Configuración y validación

`data.yaml` se genera conceptualmente con `render_data_yaml()` y se valida con `validate_data_yaml_text()`. Ambos consumen `yolo_names()` de US-001, sin duplicar la definición de clases. `validate_dataset_files()` detecta estructura incompleta, pares faltantes y etiquetas YOLO inválidas.

Desde Git Bash en Windows:

```bash
export PYTHONPATH=src
python -m unittest discover -s tests -v
python -c "from pathlib import Path; from esceniq.dataset.preparation import validate_dataset_files, validate_data_yaml_text; root = Path('datasets/esceniq'); validate_dataset_files(root); validate_data_yaml_text((root / 'data.yaml').read_text(encoding='utf-8')); print('Dataset válido')"
```
