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

Para una prueba técnica, selecciona el modo **Prueba técnica** e indica la ruta de pesos locales: las detecciones conservarán sus clases genéricas y nunca se mostrarán como marcas ESCENIQ. Para el modo **ESCENIQ**, los pesos deben exponer exactamente este mapa: `0=eggo`, `1=coca_cola`, `2=pepsi`, `3=fedex`, `4=wilson`. Si no coincide, la ejecución se detiene antes de procesar el vídeo.

## Estimación de exposición

El servicio `esceniq.analytics.calculate_exposure` acepta exclusivamente resultados del modo ESCENIQ. Cada muestra positiva representa el intervalo desde su timestamp hasta el timestamp más el intervalo configurado, limitado por la duración real del vídeo. Los intervalos solapados de una misma marca se fusionan; un hueco entre ellos inicia otra aparición. Por ello son estimaciones dependientes del muestreo, no una medición continua exacta. Las marcas simultáneas se calculan de forma independiente y sus porcentajes pueden sumar más de 100 %.

Para las pruebas:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
```
