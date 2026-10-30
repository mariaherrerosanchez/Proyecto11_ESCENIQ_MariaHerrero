# ESCENIQ

Computer Vision para detectar marcas en vídeos y analizar su tiempo de exposición mediante YOLO.

## Ejecutar la primera pantalla

Requiere Python 3.11 o posterior. Crear y activar un entorno virtual, instalar las dependencias y ejecutar:

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
streamlit run app.py
```

La pantalla **Analizar vídeo** valida localmente un MP4, muestra sus metadatos y permite visualizarlo. También puede ejecutar inferencia por muestreo con una ruta local a pesos YOLO: no descarga modelos ni sube el archivo a servicios externos.

La aplicación separa tres modos de inferencia:

- **Prueba técnica:** acepta un modelo local de clases genéricas, conserva sus nombres originales y nunca los presenta como marcas ESCENIQ.
- **Eggo experimental (1 clase):** acepta exclusivamente el mapa `0=eggo`. Sugiere una ruta local editable al peso piloto; si falta, el error no afecta a los otros modos. Es un detector experimental de una sola marca, con rendimiento limitado: sus estimaciones no son adecuadas para uso comercial y no detectar Eggo no permite afirmar que no existan otras marcas.
- **ESCENIQ (cinco marcas oficiales):** exige exactamente `0=eggo`, `1=coca_cola`, `2=pepsi`, `3=fedex`, `4=wilson`. Si no coincide, la ejecución se detiene antes de procesar el vídeo.

## Estimación de exposición

El servicio `esceniq.analytics.calculate_exposure` acepta resultados del modo ESCENIQ y del modo Eggo experimental, pero rechaza la prueba técnica. Cada muestra positiva representa el intervalo desde su timestamp hasta el timestamp más el intervalo configurado, limitado por la duración real del vídeo. Los intervalos solapados de una misma marca se fusionan; un hueco entre ellos inicia otra aparición. Por ello son estimaciones dependientes del muestreo, no una medición continua exacta. Las marcas simultáneas se calculan de forma independiente y sus porcentajes pueden sumar más de 100 %.

## Piloto de entrenamiento Eggo

El procedimiento, resultados y limitaciones del piloto de una sola clase están documentados en [la documentación del experimento](docs/datasets/eggo_training_pilot.md). Sus pesos y datos se mantienen fuera del repositorio. Este piloto **no** cumple aún el requisito del modelo oficial ESCENIQ de cinco marcas ni permite concluir que otras marcas estén ausentes de un vídeo.

## Revisión visual de anotaciones Eggo

La galería local de revisión no modifica imágenes ni etiquetas y deja sus resultados fuera del repositorio. En Windows:

```powershell
python scripts/review_eggo_gallery.py --dataset-root C:\ESCENIQ_Datasets\Eggo
Start-Process C:\ESCENIQ_Datasets\Eggo\revision_visual_html\eggo_review_gallery.html
```

El HTML muestra las 44 candidatas con sus cajas y deja las seis exclusiones en una sección separada. El mismo directorio contiene `eggo_review_template.csv`, con las columnas vacías `filename`, `decision` y `notes`; rellenarlo no cambia el estado del dataset ni sus etiquetas.

Haz clic en una imagen candidata para abrir el editor. Selecciona una caja para arrastrarla; usa sus controles amarillos para redimensionarla, **Añadir caja** para dibujar una nueva y **Eliminar caja seleccionada** para retirarla. Selecciona una decisión (aprobar, corregir, excluir o sin decisión) y, opcionalmente, añade notas. Los cambios permanecen exclusivamente en la memoria del navegador y el aviso superior indica los cambios pendientes.

Para conservar la revisión, pulsa **Exportar JSON de revisión**. El archivo descargado contiene solo el nombre de cada candidata, su decisión, notas y cajas YOLO normalizadas; no modifica PNG, TXT ni manifiestos. Más adelante, usa **Importar JSON** para cargarlo de nuevo en el editor y seguir revisando. Importar tampoco escribe en el dataset: vuelve a exportar el JSON cuando quieras guardar la nueva versión.

Para las pruebas:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
```
