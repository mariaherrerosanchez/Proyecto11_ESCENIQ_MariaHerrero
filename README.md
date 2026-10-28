# ESCENIQ

Computer Vision para detectar marcas en vídeos y analizar su tiempo de exposición mediante YOLO.

## Ejecutar la primera pantalla

Requiere Python 3.11 o posterior. Crear y activar un entorno virtual, instalar las dependencias y ejecutar:

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
streamlit run app.py
```

La pantalla **Analizar vídeo** valida localmente un MP4, muestra sus metadatos y permite visualizarlo. No ejecuta inferencia YOLO, no descarga modelos y no sube el archivo a servicios externos.

Para las pruebas:

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
```
