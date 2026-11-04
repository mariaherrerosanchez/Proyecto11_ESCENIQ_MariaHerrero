# Demo local — Coca-Cola experimental

Esta guía demuestra el flujo real de ESCENIQ con el piloto monoclase de Coca-Cola. No distribuye pesos, vídeos, datasets ni resultados supuestos.

## Preparación privada

1. Usa un vídeo MP4 autorizado y reservado que no se haya utilizado para entrenar ni seleccionar el modelo.
2. Conserva el peso local fuera del repositorio. En el equipo de demostración puede estar en:

   ~~~text
   C:\ESCENIQ_Datasets\CocaCola_training_runs\cocacola_yolo11n_pilot_e50_img640_b8_s42\weights\best.pt
   ~~~

3. Comprueba que existe antes de abrir la aplicación:

   ~~~powershell
   Test-Path 'C:\ESCENIQ_Datasets\CocaCola_training_runs\cocacola_yolo11n_pilot_e50_img640_b8_s42\weights\best.pt'
   ~~~

4. Opcionalmente, separa los artefactos de demo del perfil habitual:

   ~~~powershell
   $env:ESCENIQ_DATABASE_PATH = 'C:\ESCENIQ_Demo\esceniq.sqlite3'
   $env:ESCENIQ_EVIDENCE_DIRECTORY = 'C:\ESCENIQ_Demo\evidences'
   ~~~

   Estas rutas son locales y no deben añadirse a Git. La aplicación guarda SQLite y JPEGs anotados; nunca guarda el vídeo original.

## Guion de aproximadamente cinco minutos

1. **0:00–0:30 — Contexto.** Abre Inicio y explica que ESCENIQ es análisis local de presencia visual de marca mediante muestras de vídeo. Indica que la demo usa un piloto experimental monoclase, no un detector multiclase validado.
2. **0:30–1:15 — Configuración.** En **Analizar vídeo**, sube el MP4 reservado. Selecciona **Coca-Cola experimental (1 clase)**, confirma la ruta local a best.pt, usa umbral 0,25 e intervalo 1,0 s. Explica que 0 = coca-cola es específico del piloto y no sustituye el catálogo oficial.
3. **1:15–2:30 — Inferencia.** Ejecuta el análisis. Muestra el progreso y que el vídeo no abandona el equipo. Si falta el peso o el MP4, muestra el error claro y corrige la ruta, sin sustituirlo por datos simulados.
4. **2:30–3:30 — Evidencias y exposición.** Enseña los fotogramas anotados, timestamp, confianza y estado **«Detección automática — sin verificar»**. Ajusta el filtro visual si ayuda a revisar cajas. Explica que segundos, porcentaje y apariciones son estimaciones derivadas del intervalo de muestreo.
5. **3:30–4:20 — Resultados y CSV.** Abre **Resultados**, muestra los parámetros que generaron las métricas y descarga el CSV solo si existen filas reales.
6. **4:20–5:00 — Persistencia y límites.** Abre **Biblioteca**, recupera el análisis sin repetir YOLO y muestra las evidencias JPEG guardadas. Cierra indicando falsos positivos/negativos posibles, ausencia de verificación humana automática y que el modelo multiclase de cinco marcas sigue pendiente.

## Comprobaciones finales

- Confirma que la Biblioteca conserva los parámetros, detecciones, exposiciones y JPEGs tras reiniciar Streamlit.
- Si una evidencia falta o está corrupta, Biblioteca debe avisar y mantener el análisis y sus métricas.
- No presentes una detección como validada por una persona ni una ausencia como prueba de que la marca no aparece.
