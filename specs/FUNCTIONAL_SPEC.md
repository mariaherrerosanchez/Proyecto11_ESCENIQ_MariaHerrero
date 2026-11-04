# ESCENIQ — FUNCTIONAL_SPEC

**Versión:** 1.2 · **Referencia:** [MASTER_SPEC](MASTER_SPEC.md) · **Entrega objetivo:** 03/11/2026

## Historias de usuario y aceptación

### Épica E1 — Datos y modelo (P0)

### US-001 — Definir clases y mapa de marcas
**Prioridad:** P0  
**Épica:** E1 — Datos y modelo

#### Historia de usuario
Como desarrolladora, quiero un catálogo versionado de clases YOLO y marcas para agrupar detecciones correctamente.

#### Alcance funcional
El catálogo contiene solo `eggo`, `coca_cola`, `pepsi`, `fedex` y `wilson`. Coca-Cola/Coke/New Coke pertenecen a `coca_cola`, Pepsi Perfect a `pepsi` y el logo Wilson completo o W a `wilson`; las desconocidas no se atribuyen a ninguna marca.

#### Criterios de aceptación
- [ ] El catálogo contiene exactamente las cinco clases y coincide con `data.yaml` y los pesos activos.
- [ ] Las variantes se documentan dentro de su clase, sin crear clases adicionales.
- [ ] Una clase desconocida no altera las exposiciones ni se asigna a una marca.
- [ ] El mapa está versionado y es ampliable sin cambiar equivalencias existentes.

#### Dependencias
No tiene dependencias funcionales previas.

#### Definición de terminado
Catálogo, equivalencias y tratamiento de desconocidas documentados y probados.

#### Fuera de alcance
Reconocer marcas ajenas al catálogo inicial.

### US-002 — Preparar dataset y separación
**Prioridad:** P0  
**Épica:** E1 — Datos y modelo

#### Historia de usuario
Como desarrolladora, quiero datos anotados y conjuntos independientes para entrenar y evaluar sin fugas.

#### Alcance funcional
Se registran procedencia, licencia o permiso, fuente, clase y calidad. Las cajas YOLO se validan; entrenamiento, validación y test se separan por vídeo o fuente cuando existan fotogramas relacionados. El clip de demo queda reservado.

#### Criterios de aceptación
- [ ] Cada conjunto dispone de procedencia y recuentos por clase documentados.
- [ ] Las anotaciones YOLO se validan contra la imagen y las clases permitidas.
- [ ] Fotogramas de un mismo clip o fuente no se mezclan entre particiones.
- [ ] Test y clip de demo no participan en entrenamiento ni selección del modelo.
- [ ] Las variantes disponibles se anotan en la clase de su marca.

#### Dependencias
US-001.

#### Definición de terminado
Partición reproducible, manifiesto de datos y control de fugas revisados.

#### Fuera de alcance
Publicar datos o clips sin derechos verificados.

### US-003 — Entrenar y evaluar YOLO
**Prioridad:** P0  
**Épica:** E1 — Datos y modelo

#### Historia de usuario
Como desarrolladora, quiero un modelo YOLO real, evaluado y reproducible.

#### Alcance funcional
El entrenamiento usa exclusivamente el conjunto de entrenamiento. La validación se usa para ajustar hiperparámetros y seleccionar el modelo; el test independiente se reserva para la evaluación final tras esa selección. Se conservan semilla, configuración, versión y partición del dataset, pesos iniciales y finales, hiperparámetros, épocas, tamaño, clases, versiones y hardware. La evaluación final conserva precision, recall, mAP@50 y mAP@50:95 globales y por clase, además de ejemplos reales de aciertos y errores. El clip de demostración queda fuera de entrenamiento, validación, selección y evaluación.

#### Criterios de aceptación
- [ ] Los pesos seleccionados se cargan para inferencia local.
- [ ] Entrenamiento, validación y test independiente se identifican por separado, y solo la validación interviene en el ajuste y la selección del modelo.
- [ ] La evaluación final conserva métricas reales globales y por cada una de las cinco clases: precision, recall, mAP@50 y mAP@50:95.
- [ ] El registro reproducible reúne configuración de entrenamiento, versión y partición del dataset, semilla, pesos iniciales y finales, e información de entorno suficiente para repetir la ejecución.
- [ ] La evaluación conserva aciertos, falsos positivos y falsos negativos representativos del test independiente.
- [ ] El clip reservado de demostración no interviene en entrenamiento, validación, selección ni evaluación del modelo.

#### Dependencias
US-001 y US-002.

#### Definición de terminado
Modelo ejecutable, evaluación final independiente con métricas globales y por clase, y registro suficiente para reproducir la ejecución.

#### Fuera de alcance
Prometer reconocimiento perfecto o modificar el protocolo de partición independiente definido en US-002.

### Épica E2 — Análisis (P0)

### US-004 — Cargar MP4
**Prioridad:** P0  
**Épica:** E2 — Análisis

#### Historia de usuario
Como usuaria, quiero seleccionar un vídeo MP4 local para analizarlo.

#### Alcance funcional
Se valida extensión y decodificación, y se obtienen nombre, duración, FPS, dimensiones y fotogramas cuando sean válidos. El archivo permanece local.

#### Criterios de aceptación
- [ ] Un MP4 decodificable muestra sus metadatos básicos antes de analizarse.
- [ ] Archivo inválido, corrupto, vacío o con FPS/duración inválidos produce un error accionable.
- [ ] Se contrastan duración, FPS y número de fotogramas cuando existen.
- [ ] El vídeo no se publica ni se transfiere fuera del equipo por defecto.

#### Dependencias
US-003.

#### Definición de terminado
Carga local validada y errores de entrada cubiertos por pruebas.

#### Fuera de alcance
Otros formatos y carga desde servicios cloud.

### US-005 — Ejecutar inferencia
**Prioridad:** P0  
**Épica:** E2 — Análisis

#### Historia de usuario
Como usuaria, quiero analizar fotogramas con el modelo activo para obtener detecciones trazables.

#### Alcance funcional
La inferencia procesa muestras a intervalo configurable, filtra por confianza y conserva índice, timestamp, clase, marca, confianza y caja. Muestra progreso y estados de ejecución.

#### Criterios de aceptación
- [ ] El umbral seleccionado se aplica y se registra con el análisis.
- [ ] Cada detección conserva timestamp, fotograma, clase, marca, confianza y bbox.
- [ ] El progreso informa de muestras o fotogramas procesados cuando es viable.
- [ ] Modelo inexistente o fallo de inferencia deja un error claro, nunca un análisis completado.
- [ ] Se guardan versión de modelo e intervalo de muestreo.

#### Dependencias
US-001, US-003 y US-004.

#### Definición de terminado
Inferencia local trazable, con estados y fallos verificados.

#### Fuera de alcance
Procesamiento distribuido o inferencia continua garantizada.

### US-006 — Ver evidencias visuales
**Prioridad:** P0  
**Épica:** E2 — Análisis

#### Historia de usuario
Como usuaria, quiero ver fotogramas con cajas y etiquetas para comprobar detecciones.

#### Alcance funcional
Se muestran fotogramas realmente analizados, con caja, marca, confianza y timestamp, vinculados a su análisis de origen.

#### Criterios de aceptación
- [ ] Cada evidencia muestra caja, marca y timestamp de la muestra correspondiente.
- [ ] Etiquetas y cajas son legibles y no ocultan innecesariamente la detección.
- [ ] La evidencia se relaciona con una detección y análisis reales.
- [ ] Sin detecciones se muestra estado vacío, nunca imágenes simuladas.

#### Dependencias
US-005.

#### Definición de terminado
Evidencias reales renderizadas y contrastables con las detecciones.

#### Fuera de alcance
Generar evidencias ficticias o retocadas para aparentar detecciones.

### US-007 — Calcular exposición por marca
**Prioridad:** P0  
**Épica:** E2 — Análisis

#### Historia de usuario
Como usuaria, quiero conocer segundos y porcentaje de presencia por marca.

#### Alcance funcional
Cada muestra representa desde su timestamp hasta el siguiente intervalo o el final. Se normaliza a marca y se deduplica por marca y muestra: varias cajas cuentan una vez; marcas simultáneas acumulan independientemente y sus porcentajes pueden superar el 100 %.

#### Criterios de aceptación
- [ ] Varias detecciones de una marca en una muestra aportan una sola vez el intervalo.
- [ ] Marcas distintas simultáneas reciben cada una la duración del intervalo.
- [ ] El último intervalo se limita a la duración real del vídeo.
- [ ] Se informa `segundos estimados` y `100 × segundos / duración_total`.
- [ ] Duración cero o inválida provoca error explícito, sin división por cero.
- [ ] El tiempo no se multiplica por cajas ni por confianza.

#### Dependencias
US-001, US-004 y US-005.

#### Definición de terminado
Pruebas superadas para duplicados, equivalencias, simultaneidad, ausencia y tramo final.

#### Fuera de alcance
Medición continua exacta entre muestras o audiencia.

### US-008 — Mostrar resultados
**Prioridad:** P0  
**Épica:** E2 — Análisis

#### Historia de usuario
Como usuaria, quiero consultar un resumen de marcas detectadas para interpretar el análisis.

#### Alcance funcional
Resultados presenta por marca segundos estimados, porcentaje, muestras positivas, parámetros y evidencias, distinguiendo completado, vacío y fallo.

#### Criterios de aceptación
- [ ] La tabla muestra marca, segundos, porcentaje y muestras positivas.
- [ ] Los valores coinciden con la agregación y los parámetros son visibles.
- [ ] Sin detecciones se comunica un estado vacío sin métricas inventadas.
- [ ] Un fallo muestra su error y no se confunde con un resultado vacío.

#### Dependencias
US-006 y US-007.

#### Definición de terminado
Resumen contrastado con detecciones y exposiciones.

#### Fuera de alcance
Línea temporal avanzada o comparativas.

### Épica E3 — Persistencia e informes (P1)

### US-009 — Guardar análisis en SQLite
**Prioridad:** P1  
**Épica:** E3 — Persistencia e informes

#### Historia de usuario
Como usuaria, quiero conservar análisis para revisarlos después.

#### Alcance funcional
SQLite guarda vídeo, modelo, análisis, detecciones y exposiciones con relaciones consistentes, parámetros, estados y errores.

#### Criterios de aceptación
- [ ] Un análisis completado guarda parámetros, detecciones y exposiciones relacionados.
- [ ] Las claves foráneas impiden exposiciones sin análisis asociado.
- [ ] Modelo, umbral e intervalo permiten reproducir el contexto.
- [ ] Un fallo se registra o revierte consistentemente, sin resultados parciales engañosos.

#### Dependencias
US-005 y US-007.

#### Definición de terminado
Persistencia probada con análisis correcto y fallido.

#### Fuera de alcance
Base de datos compartida o sincronización cloud.

### US-010 — Consultar biblioteca
**Prioridad:** P1  
**Épica:** E3 — Persistencia e informes

#### Historia de usuario
Como usuaria, quiero listar y abrir análisis anteriores para revisar el historial.

#### Alcance funcional
La biblioteca ordena análisis, abre detalle y avisa si vídeo o evidencia ya no existen sin alterar sus métricas.

#### Criterios de aceptación
- [ ] El historial muestra fecha, vídeo, estado y modelo o parámetros identificables.
- [ ] El orden de lista está documentado y es estable.
- [ ] Al abrir se recuperan exposiciones y parámetros guardados.
- [ ] Un archivo ausente avisa claramente y no borra ni falsea el historial.

#### Dependencias
US-009.

#### Definición de terminado
Historial y reapertura validados sobre SQLite.

#### Fuera de alcance
Edición destructiva masiva del historial.

### US-011 — Exportar CSV
**Prioridad:** P1  
**Épica:** E3 — Persistencia e informes

#### Historia de usuario
Como usuaria, quiero exportar métricas por marca a CSV para reutilizarlas.

#### Alcance funcional
La exportación local incluye análisis, vídeo, marca, segundos, porcentaje, muestras, modelo, umbral e intervalo, con UTF-8 y valores idénticos a SQLite/UI.

#### Criterios de aceptación
- [ ] El CSV usa UTF-8 y cabeceras documentadas.
- [ ] Cada fila coincide con los valores persistidos y mostrados.
- [ ] Modelo, umbral e intervalo acompañan cada resultado.
- [ ] Sin detecciones se exporta el resultado documentado o se comunica que no hay filas, sin inventar datos.

#### Dependencias
US-009 y US-010.

#### Definición de terminado
CSV leído automáticamente y comparado con SQLite/UI.

#### Fuera de alcance
Servicios externos u otros formatos de informe.

### US-012 — Guardar evidencias
**Prioridad:** P1  
**Épica:** E3 — Persistencia e informes

#### Historia de usuario
Como usuaria, quiero conservar ejemplos visuales de detecciones para auditar resultados.

#### Alcance funcional
Se guardan evidencias representativas vinculadas a análisis, marca, timestamp y detección. Una política limita almacenamiento y mantiene vídeos locales.

#### Criterios de aceptación
- [ ] Cada evidencia se vincula a análisis, marca y timestamp existentes.
- [ ] La selección o límite de almacenamiento está documentado y se aplica.
- [ ] La ausencia de evidencia no altera la métrica de exposición.
- [ ] Guardar evidencias no publica vídeos ni imágenes fuera del equipo.

#### Dependencias
US-006 y US-009.

#### Definición de terminado
Evidencias recuperables y límites verificados.

#### Fuera de alcance
Guardar cada fotograma o publicar clips.

### Épica E4 — Experiencia y documentación (P1)

### US-013 — Navegar por la aplicación
**Prioridad:** P1  
**Épica:** E4 — Experiencia y documentación

#### Historia de usuario
Como usuaria, quiero localizar análisis, resultados, biblioteca y ayuda para moverme con seguridad.

#### Alcance funcional
La navegación dirige a Inicio, Analizar vídeo, Resultados, Biblioteca, Informes, Modelos e IA y Configuración según estén disponibles, sin prometer funciones inexistentes.

#### Criterios de aceptación
- [ ] Las rutas disponibles se identifican consistentemente desde la interfaz.
- [ ] Cargar, analizar y consultar resultados no contiene enlaces rotos.
- [ ] Una función no implementada se indica como no disponible, sin simular datos.
- [ ] Pantallas vacías y errores conservan textos y estados comprensibles.

#### Dependencias
US-004, US-008 y US-010.

#### Definición de terminado
Recorrido principal probado manualmente con navegación y errores.

#### Fuera de alcance
Rediseño para funciones P2/P3.

### US-014 — Consultar modelo y metodología
**Prioridad:** P1  
**Épica:** E4 — Experiencia y documentación

#### Historia de usuario
Como evaluadora, quiero conocer clases, dataset, entrenamiento y métricas para valorar el modelo.

#### Alcance funcional
La aplicación o documentación enlazada explica clases, variantes, protocolo sin fuga, modelo, configuración, métricas reales y limitaciones, distinguiendo evidencias reales de ilustraciones.

#### Criterios de aceptación
- [ ] Se identifican las cinco clases y sus variantes compartidas.
- [ ] Se describe separación por fuente o clip y test independiente.
- [ ] Las métricas tienen referencia a ejecución o artefacto de evaluación real.
- [ ] Se expresan limitaciones de muestreo, cobertura y datos sin afirmaciones no demostradas.

#### Dependencias
US-001, US-002 y US-003.

#### Definición de terminado
Metodología verificable y referencias a evidencias reales.

#### Fuera de alcance
Inventar métricas o reclamar reconocimiento general de marcas.

### US-015 — Ejecutar pruebas y demo
**Prioridad:** P1  
**Épica:** E4 — Experiencia y documentación

#### Historia de usuario
Como evaluadora, quiero reproducir un análisis siguiendo instrucciones para comprobar el producto.

#### Alcance funcional
La documentación describe instalación, ejecución, pruebas y limitaciones. La demo usa vídeo local autorizado y reservado; la presentación separa resultados reales, ejemplos y trabajo futuro.

#### Criterios de aceptación
- [ ] Las instrucciones permiten ejecutar localmente sin exigir archivos privados en el repositorio.
- [ ] Hay comandos documentados para pruebas de mapeo, exposición, errores y persistencia.
- [ ] La demo usa un clip reservado, no entrenado y no publicado sin autorización.
- [ ] La presentación comunica métricas reales, limitaciones y pendientes trazables.

#### Dependencias
US-003, US-008, US-009 y US-014.

#### Definición de terminado
Guía reproducible y demo manual validada.

#### Fuera de alcance
Distribuir material audiovisual o datos protegidos.

### US-016 — Alternar tema claro/oscuro
**Prioridad:** P1  
**Épica:** E4 — Experiencia y documentación

#### Historia de usuario
Como usuaria, quiero alternar tema claro y oscuro desde cualquier pantalla para trabajar cómodamente.

#### Alcance funcional
Un control global aplica ambos temas con contraste en textos, tablas, evidencias, gráficos y estados. La preferencia se persiste solo si es estable en Streamlit.

#### Criterios de aceptación
- [ ] El selector está disponible desde todas las pantallas principales.
- [ ] Texto, tablas, alertas y controles son legibles en ambos temas.
- [ ] El cambio no oculta métricas, evidencias ni errores.
- [ ] Si se persiste preferencia, se verifica su recuperación; si no, se documenta la limitación.

#### Dependencias
US-013.

#### Definición de terminado
Dos temas contrastados en el flujo principal.

#### Fuera de alcance
Personalización completa de paletas o temas de terceros.

### Épica E5 — Ampliaciones (P2/P3)

### US-017 — Línea temporal interactiva
**Prioridad:** P2  
**Épica:** E5 — Ampliaciones

#### Historia de usuario
Como usuaria, quiero explorar una línea temporal por marca para localizar tramos aproximados de exposición.

#### Alcance funcional
La visualización deriva tramos de muestras procesadas, identifica marca, inicio, final y duración aproximada, y comunica su dependencia del intervalo.

#### Criterios de aceptación
- [ ] Cada tramo procede de muestras y parámetros del análisis seleccionado.
- [ ] La interfaz identifica marca y límites aproximados del tramo.
- [ ] Se advierte que el muestreo no garantiza continuidad entre muestras.
- [ ] Los tramos no cambian los segundos calculados por US-007.

#### Dependencias
US-007 y US-008.

#### Definición de terminado
Línea temporal contrastada con muestras conocidas y límites documentados.

#### Fuera de alcance
Reconstrucción exacta entre muestras.

### US-018 — Comparar análisis
**Prioridad:** P2  
**Épica:** E5 — Ampliaciones

#### Historia de usuario
Como usuaria, quiero comparar análisis guardados para interpretar diferencias de exposición con contexto.

#### Alcance funcional
La comparación muestra vídeo, duración, modelo, umbral, intervalo y exposición por marca, y advierte sobre parámetros que impidan comparación directa.

#### Criterios de aceptación
- [ ] La selección identifica inequívocamente los análisis comparados.
- [ ] Duración, modelo, umbral e intervalo aparecen junto a las exposiciones.
- [ ] Una marca sin detecciones se distingue de un dato no disponible.
- [ ] Parámetros distintos generan aviso sin cambiar resultados originales.

#### Dependencias
US-009, US-010 y US-011.

#### Definición de terminado
Comparación validada con parámetros iguales y distintos.

#### Fuera de alcance
Ranking económico o inferencias de audiencia.

### US-019 — Configuración avanzada
**Prioridad:** P2  
**Épica:** E5 — Ampliaciones

#### Historia de usuario
Como usuaria, quiero gestionar rutas, exportación y preferencias ampliadas para adaptar la aplicación a mi entorno.

#### Alcance funcional
La configuración centraliza rutas, directorios de evidencias, opciones de exportación y preferencias no MVP; valida valores y evita exponer rutas personales en salidas públicas.

#### Criterios de aceptación
- [ ] Las rutas configurables se validan antes de guardar o usar.
- [ ] Un valor inválido muestra error y conserva una configuración previa funcional.
- [ ] Exportación y evidencias reflejan la configuración activa.
- [ ] No se registran rutas personales ni credenciales en salidas públicas.

#### Dependencias
US-011, US-012 y US-016.

#### Definición de terminado
Rutas válidas e inválidas verificadas y configuración documentada.

#### Fuera de alcance
Cloud, cuentas de usuario o secretos remotos.

### US-020 — Alta y reentrenamiento desde UI
**Prioridad:** P3  
**Épica:** E5 — Ampliaciones

#### Historia de usuario
Como desarrolladora, quiero gestionar altas de clases y reentrenamiento desde la interfaz para evolucionar el catálogo controladamente.

#### Alcance funcional
La futura interfaz podrá guiar anotación, validación, separación sin fuga, entrenamiento, evaluación real y activación explícita. No pertenece al MVP ni altera las cinco clases iniciales mientras no exista proceso validado.

#### Criterios de aceptación
- [ ] Una clase nueva exige nombre, ejemplos, anotaciones y licencia o permiso documentados.
- [ ] El flujo impide mezclar fotogramas relacionados entre entrenamiento, validación y test.
- [ ] Antes de activar modelo se conservan configuración, métricas reales y evidencias de evaluación.
- [ ] La activación requiere confirmación y permite identificar la versión activa.
- [ ] El MVP no expone un control de reentrenamiento funcional.

#### Dependencias
US-001, US-002, US-003 y US-014.

#### Definición de terminado
Flujo posterior al MVP validado con datos autorizados, test independiente y activación trazable.

#### Fuera de alcance
Reentrenar desde Streamlit en el MVP o activar modelos automáticamente.

## Definición de terminado común
- El alcance y criterios verificables de la historia están satisfechos.
- Se ejecutan y registran las pruebas pertinentes.
- La documentación se actualiza cuando cambia el comportamiento.
- No se presentan datos ficticios, métricas supuestas ni evidencias simuladas como reales.
- La historia no rompe P0 ni introduce dependencias o servicios innecesarios.

## Catálogo inicial y secuencia de entrega
- **Cinco clases objetivo:** Eggo, Coca-Cola, Pepsi, FedEx y Wilson.
- **Variantes:** Coca-Cola/Coke/New Coke → Coca-Cola; Wilson/W → Wilson; Pepsi Perfect → Pepsi.
- **Primera demostración P0:** Eggo y Coca-Cola en *Stranger Things*; ampliar las otras marcas sin retrasar el MVP.
- **Vídeos:** clips preparados localmente; no publicar material audiovisual de terceros.
