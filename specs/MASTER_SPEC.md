# ESCENIQ — MASTER_SPEC

**Versión:** 1.2 · **Fecha:** 16/10/2026 · **Entrega objetivo:** 03/11/2026  
**Producto:** ESCENIQ · **Lema:** «Cada aparición cuenta»  
**Estado:** Especificación inicial para revisión; no implica implementación completada.

## 1. Visión
ESCENIQ es una aplicación local de análisis de vídeo mediante visión artificial que identifica marcas previamente entrenadas y estima su exposición temporal en pantalla. Está orientada a product placement y presencia de marca en películas, series, anuncios, vídeos musicales y otros contenidos audiovisuales.

**Propuesta de valor:** convertir apariciones visuales detectadas en métricas consultables, evidencias e informes reproducibles.

### 1.1 Alcance y limitaciones
- La primera versión **no reconoce cualquier marca**: solo las clases contempladas por el modelo entrenado.
- Distinguir **detección de un logotipo/producto entrenado** de una afirmación general de reconocimiento de marcas.
- No se promete identificación perfecta, medición de audiencia, valoración económica ni reconocimiento semántico de productos no entrenados.
- Los vídeos de demostración se mantienen locales y fuera del repositorio; revisar permisos de uso y distribución.

## 2. Objetivos de entrega
1. Modelo YOLO entrenado/ajustado y evaluado para un conjunto pequeño de clases, con datos y métricas documentados.
2. Flujo funcional: cargar MP4 → analizar → visualizar detecciones → calcular exposición por marca.
3. Persistencia de análisis y resultados en SQLite, consulta de historial y exportación CSV.
4. Repositorio GitHub, tablero Kanban, instrucciones reproducibles, pruebas, demo y presentación técnica.
5. Interfaz Streamlit con identidad ESCENIQ, priorizando estabilidad sobre ornamentación.

## 3. Prioridades y puertas de calidad

| Nivel | Alcance | Condición para avanzar |
|---|---|---|
| P0 — MVP núcleo | Modelo real, carga MP4, inferencia, bounding boxes, segundos y porcentajes por marca | Demo de extremo a extremo validada con vídeo reservado |
| P1 — MVP entregable | SQLite, historial, CSV, evidencias, tests, documentación y demo preparada | Persistencia y exportación contrastadas con resultados del análisis |
| P2 — Mejoras | Línea temporal interactiva, comparativas, panel ampliado de métricas, ajustes visuales | P0 y P1 estables |
| P3 — Evolución | Alta de clases y reentrenamiento desde la UI | Fuera de alcance salvo tiempo sobrante |

**Regla:** no comenzar P2/P3 a costa de la calidad de P0/P1. Docker es deseable para reproducibilidad, pero no debe bloquear una demo local funcional.

## 4. Usuarios y recorrido principal
Usuario: analista, docente o persona interesada en presencia visual de marcas.

1. Abre ESCENIQ.
2. Sube un archivo MP4 local.
3. Revisa modelo activo, umbral de confianza y frecuencia de muestreo.
4. Ejecuta el análisis y observa progreso/errores claros.
5. Consulta marcas detectadas, duración de exposición y porcentaje del vídeo, junto con fotogramas anotados.
6. Guarda el resultado y, en P1, recupera análisis históricos y exporta CSV.

## 5. Pantallas

| Pantalla | Función | Prioridad |
|---|---|---|
| Inicio | Resumen, acceso a análisis y últimos trabajos | P1 (versión mínima posible en P0) |
| Analizar vídeo | Carga MP4, parámetros, ejecución y estado | P0 |
| Resultados | Tabla de marcas, duración, %, visualizaciones y evidencias | P0; línea temporal avanzada P2 |
| Biblioteca | Historial de análisis y reapertura | P1 |
| Informes | Exportación CSV y evidencias | P1 |
| Modelos e IA | Modelo activo, clases, dataset, entrenamiento y evaluación documentados | P1 básico; ampliación P2 |
| Configuración | Tema, confianza, muestreo, modelo y rutas/preferencias | Parámetros P0; ampliación P2 |

El selector de tema **claro/oscuro** debe ser accesible desde todas las pantallas. Persistencia de la preferencia cuando sea viable, sin comprometer el MVP.

## 6. Identidad visual
- Marca: **ESCENIQ**; diferenciar cromáticamente **IQ**.
- Símbolo: **Q con motivo de diafragma de cámara** (dirección creativa aprobada; pendiente de arte final vectorial).
- Color de acento: **turquesa**; base azul noche/blanco según tema.
- Tipografía preferida: **Inter** o alternativa sans-serif compatible.
- Estilo: cinematográfico, limpio, profesional, tecnológico.
- Lema: **«Cada aparición cuenta»**.
- El verde lima puede reservarse para indicadores secundarios, sin desplazar al turquesa.
- No asumir registro de marca ni disponibilidad legal del nombre sin comprobación formal.

## 7. Arquitectura

```text
Streamlit (UI)
    │
    ▼
Servicios Python (orquestación del análisis)
    ├── OpenCV: lectura de vídeo, FPS, fotogramas, timestamps
    ├── Ultralytics YOLO: inferencia con modelo entrenado
    ├── Normalización de clases → marcas
    ├── Agregación temporal por marca
    ├── Evidencias y exportación CSV
    └── Persistencia SQLite
Archivos locales: modelos, vídeos temporales, capturas, artefactos
```

**Stack:** Python, Ultralytics YOLO, OpenCV, Streamlit, SQLite, pytest; Docker opcional P1/P2. **No** se introduce React/FastAPI salvo necesidad posterior justificada.

### 7.1 Organización lógica sugerida
- `app/`: páginas y componentes Streamlit.
- `src/esceniq/vision/`: carga, inferencia y anotación.
- `src/esceniq/analytics/`: agrupación de marcas y exposición.
- `src/esceniq/storage/`: persistencia y repositorios.
- `src/esceniq/reports/`: exportación.
- `training/`: scripts/configuración de entrenamiento y evaluación.
- `tests/`: unitarios e integración.
- `docs/`: metodología, datasets, resultados y demo.
- `models/` y `data/`: artefactos locales según tamaño/licencias, no subir automáticamente a Git.

## 8. Estrategia de datos y entrenamiento
- Catálogo objetivo: **cinco clases YOLO** (`eggo`, `coca_cola`, `pepsi`, `fedex`, `wilson`), una por marca. Priorizar primero Eggo y Coca-Cola para validar el flujo completo; ampliar progresivamente a Pepsi, FedEx y Wilson según resultados del entrenamiento.
- Registrar origen, licencia/permiso, volumen y calidad de imágenes.
- Anotar cajas delimitadoras por clase; documentar herramienta y formato YOLO.
- Separar entrenamiento, validación y test evitando fotogramas casi idénticos del mismo clip entre conjuntos. Preferir separación por vídeo/fuente.
- Registrar semilla, pesos de partida, hiperparámetros, épocas, tamaño de imagen, clases, versiones y hardware.
- Evaluar precision, recall, mAP@50, mAP@50:95 y ejemplos de falsos positivos/negativos; publicar **valores reales**, nunca supuestos.
- Mantener un clip de demostración/prueba no usado para entrenar ni seleccionar el modelo.
- **Variantes dentro de la misma clase:** Coca-Cola / Coke / New Coke → `coca_cola`; Wilson completo / W aislada → `wilson`; Pepsi Perfect → `pepsi`. También incluir variaciones de Eggo y FedEx. Las variantes son apariencias anotadas dentro de una misma clase, **no clases adicionales**. No asumir que YOLO aprende variantes sin ejemplos representativos.

## 9. Semántica de exposición
- **Unidad de reporte:** marca comercial, no instancia ni clase individual.
- Una marca presente en un fotograma cuenta **una sola vez**, aunque existan varias cajas o clases asociadas a ella.
- Dos marcas presentes simultáneamente acumulan exposición cada una: sus porcentajes **pueden sumar más del 100 %**.
- Porcentaje por marca = `100 × segundos_estimados_de_presencia / duración_total_del_vídeo`.
- Duración total obtenida de metadatos válidos del vídeo, contrastados con FPS y número de fotogramas; gestionar metadatos ausentes/incorrectos.
- Para el MVP, inferencia por **muestreo periódico de fotogramas**. Cada muestra representa un intervalo temporal definido y limitado al final del vídeo; el tiempo es una **estimación dependiente de la frecuencia de muestreo**, no precisión continua garantizada.
- No multiplicar tiempo por número de detecciones ni por confianza.
- Guardar la frecuencia de muestreo, umbral y versión del modelo con cada análisis.
- La confianza es un umbral de filtrado, **no** una probabilidad calibrada de que una marca aparezca.

## 10. Modelo de datos mínimo
- `videos`: id, nombre original, duración, FPS, dimensiones, huella opcional, fecha de análisis.
- `models`: id, identificador de versión, ruta local, clases, métricas/referencia de evaluación.
- `analyses`: id, video_id, model_id, umbral, intervalo_muestreo, estado, inicio/fin, errores.
- `detections`: id, analysis_id, timestamp, frame_index, clase, marca, confianza, bbox, evidencia opcional.
- `brand_exposures`: analysis_id, marca, segundos, porcentaje, muestras_positivas.

Guardar rutas relativas/configurables cuando sea posible. Definir política de limpieza de vídeos temporales y evitar persistir material protegido innecesariamente.

## 11. Requisitos no funcionales
- Ejecución local en Windows, sin dependencia obligatoria de servicios de pago.
- Mensajes claros para MP4 corrupto, vídeo vacío, FPS inválido, modelo inexistente, falta de espacio y fallos de inferencia.
- No subir vídeos privados a servicios externos por defecto.
- Código modular, nombres expresivos, responsabilidad única, evitar duplicación y sobreingeniería.
- Pruebas significativas, logs útiles, reproducibilidad y README con pasos verificables.
- Control de versiones en ramas de funcionalidad; la persona usuaria gestiona ramas, commits, pushes, PR y merges manualmente.

## 12. Riesgos y mitigaciones
| Riesgo | Mitigación |
|---|---|
| Dataset insuficiente o sesgado | Reducir clases; priorizar ejemplos variados y test independiente |
| Logotipos pequeños, oclusión, motion blur | Documentar limitaciones y mostrar errores reales |
| Vídeos largos o GPU limitada | Muestreo configurable, clips cortos para demo y límites de tamaño |
| Exposición mal calculada | Tests con secuencias sintéticas y solapamientos |
| Demasiadas pantallas | P0 en una ruta clara; ampliar navegación tras validación |
| Problemas con licencias | No publicar clips/datasets/pesos sin verificar derechos |
| Docker consume tiempo | Ejecutable local documentado como ruta de respaldo |

## 13. Criterio global de aceptación
Una persona puede iniciar ESCENIQ siguiendo el README, analizar un MP4 con un modelo entrenado, ver cajas y etiquetas reales, obtener segundos/porcentajes coherentes por marca y consultar evidencias. En P1, además, el análisis se recupera desde SQLite y se exporta a CSV. La presentación distingue métricas reales, datos ilustrativos y limitaciones.

## 14. Entregables
- Repositorio GitHub público con código, instrucciones, pruebas y documentación (sin vídeos privados).
- GitHub Project Kanban con épicas/historias y trazabilidad.
- Modelo/artefactos disponibles de manera legal y reproducible, o instrucciones claras para obtenerlos.
- Demostración local preparada con vídeo de prueba.
- Presentación técnica: problema, dataset, arquitectura, entrenamiento, evaluación, resultados, riesgos y mejoras.

## 15. Decisiones pendientes antes de implementar
1. **Resuelto:** catálogo de cinco marcas y variantes; validar disponibilidad de imágenes etiquetables por clase.
2. Dataset y protocolo de etiquetado.
3. Intervalo de muestreo predeterminado y límite de duración/tamaño de archivo.
4. Versión exacta de Python, YOLO y dependencias tras prueba de compatibilidad.
5. Diseño final de tablas y política de conservación de evidencias.

Estas decisiones deben resolverse con un experimento técnico temprano, no bloquear la planificación completa.

## 16. Clips de referencia confirmados
- *Stranger Things*: Eggo y Coca-Cola (incluye Coke/New Coke).
- *Regreso al futuro II*: Pepsi (incluye Pepsi Perfect).
- *Náufrago*: FedEx y Wilson (logotipo completo y W).
- Los clips están descargados y recortados **localmente**; no subirlos al repositorio.
- Evitar fuga entre entrenamiento y test: reservar secuencias/fuentes independientes, no dividir fotogramas casi idénticos aleatoriamente.
