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

La aplicación separa cuatro modos de inferencia:

- **Prueba técnica:** acepta un modelo local de clases genéricas, conserva sus nombres originales y nunca los presenta como marcas ESCENIQ.
- **Eggo experimental (1 clase):** acepta exclusivamente el mapa `0=eggo`. Sugiere una ruta local editable al peso piloto; si falta, el error no afecta a los otros modos. Es un detector experimental de una sola marca, con rendimiento limitado: sus estimaciones no son adecuadas para uso comercial y no detectar Eggo no permite afirmar que no existan otras marcas.
- **Coca-Cola experimental (1 clase):** acepta exclusivamente el mapa `0=coca-cola`. Sugiere una ruta local editable al peso piloto de Coca-Cola; su identificador `0` es propio de este peso y **no** cambia el catálogo oficial, donde Coca-Cola es `1=coca_cola`. Es un detector experimental con falsos positivos observados; sus estimaciones no son adecuadas para uso comercial y no detectar Coca-Cola no permite afirmar que no aparezca en el vídeo.
- **ESCENIQ (cinco marcas oficiales):** exige exactamente `0=eggo`, `1=coca_cola`, `2=pepsi`, `3=fedex`, `4=wilson`. Si no coincide, la ejecución se detiene antes de procesar el vídeo.

## Modelos e IA

La sección **Modelos e IA** distingue los detectores experimentales de los validados: Coca-Cola y Eggo son pilotos monoclase locales; la prueba técnica no identifica marcas; el catálogo multiclase de cinco marcas es un objetivo y no declara un peso completo entrenado. La pantalla explica YOLO, las métricas de detección y exposición, el efecto del umbral y del muestreo, y las limitaciones de falsos positivos, falsos negativos e iluminación. No muestra métricas de Coca-Cola porque el repositorio no contiene una evaluación independiente verificable de ese piloto.

## Evidencias visuales

Al terminar un análisis, la misma pantalla muestra una galería de hasta 24 fotogramas positivos distribuidos temporalmente a lo largo del vídeo. Un **umbral visual de confianza**, cuyo mínimo es el umbral usado en la inferencia, permite ocultar cajas de baja confianza sin cambiar las detecciones, métricas ni exposición originales. También puede ocultarse el texto de las etiquetas. Cada evidencia muestra un resumen compacto con timestamp, número de cajas visibles y estado de revisión.

La galería no vuelve a procesar el vídeo ni invoca YOLO al cambiar estos filtros: conserva en `st.session_state` el resultado y una única imagen JPEG base, sin anotaciones, por evidencia; las cajas se dibujan temporalmente para cada vista. Las imágenes están limitadas a 960×540 px, permanecen solo en memoria durante la sesión y se descartan al seleccionar otro vídeo.

Todas las evidencias indican **«Detección automática — sin verificar»**. En los modos experimentales de Eggo y Coca-Cola se muestra además un aviso para revisar posibles falsos positivos; la interfaz no presenta ninguna detección como validada por una persona.

## Estimación de exposición

El servicio `esceniq.analytics.calculate_exposure` acepta resultados del modo ESCENIQ y de los modos experimentales de Eggo y Coca-Cola, pero rechaza la prueba técnica. Cada muestra positiva representa el intervalo desde su timestamp hasta el timestamp más el intervalo configurado, limitado por la duración real del vídeo. Los intervalos solapados de una misma marca se fusionan; un hueco entre ellos inicia otra aparición. Por ello son estimaciones dependientes del muestreo, no una medición continua exacta. Las marcas simultáneas se calculan de forma independiente y sus porcentajes pueden sumar más de 100 %.

## Persistencia local

Cada inferencia completada se guarda automáticamente en SQLite con vídeo, modo, modelo, parámetros, detecciones y exposiciones reales. La base no almacena el vídeo original ni las evidencias visuales. Por defecto se crea en `%LOCALAPPDATA%\ESCENIQ\esceniq.sqlite3`; puede configurarse antes de iniciar Streamlit con `ESCENIQ_DATABASE_PATH`. Un error de SQLite muestra una advertencia, pero conserva el resultado de la sesión actual.

En **Biblioteca** se listan los análisis del más reciente al más antiguo. Al abrir uno se recuperan directamente de SQLite sus parámetros, detecciones y métricas de exposición, sin volver a ejecutar YOLO. Las evidencias JPEG no se persisten: el historial lo indica explícitamente en lugar de reconstruirlas o simularlas.

## Exportación CSV

En **Resultados**, un análisis con marcas agregadas ofrece **Descargar CSV**. El archivo usa UTF-8 con BOM y separador `;` para abrirse correctamente en Excel en español. Incluye por marca el vídeo seleccionado, detecciones, muestras positivas, exposición estimada, porcentaje, apariciones, modelo, umbral e intervalo de muestreo. La descarga reutiliza el resultado actual y su exposición ya calculada; no vuelve a ejecutar YOLO. Si no existen marcas agregadas o se trata de una prueba técnica, no se ofrece CSV.

Los análisis guardados que incluyen exposición por marca ofrecen la misma descarga desde **Biblioteca**, reutilizando los datos persistidos.

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
