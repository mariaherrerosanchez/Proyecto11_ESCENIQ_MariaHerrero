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

Para las pruebas:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
```
