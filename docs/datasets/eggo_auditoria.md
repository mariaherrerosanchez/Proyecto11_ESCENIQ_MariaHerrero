# Auditoría de calidad — colección Eggo

**Fecha de auditoría:** 23/10/2026  
**Origen auditado (solo lectura):** `C:\ESCENIQ_Datasets\Eggo\originales\`  
**Clase prevista:** `0` (`eggo`)  
**Alcance:** control técnico local y revisión visual preliminar. No se han creado anotaciones, entrenado modelos, ni modificado, movido, renombrado o eliminado imágenes originales.

## Resumen de calidad

La carpeta existe y contiene **50 imágenes válidas**, pero hay una discrepancia con el inventario esperado: **las 50 son archivos PNG, no JPG**. Esta diferencia no impide preparar un dataset YOLO, aunque debe reflejarse en el manifiesto y en las decisiones de conversión posteriores si se desea un formato uniforme.

Todas las imágenes abren y se decodifican con Pillow. Son PNG RGBA, sin EXIF, con DPI embebido cercano a 144 × 144. El conjunto ocupa **62.813.320 bytes (59,9 MiB)**. El tamaño de archivo va de 176.546 B a 4.753.003 B (mediana: 1.041.710,5 B); las dimensiones van de 275 × 274 a 1.649 × 1.238 px (mediana: 721,5 × 636,5 px).

La variedad visual es buena para una primera colección: aparecen envases individuales, distintos sabores y diseños, lineales de supermercado, composición publicitaria y fotogramas/estética de anuncios históricos. En la revisión visual realizada, el producto o logotipo Eggo es apreciable en la colección. Hay, no obstante, varias imágenes con producto pequeño, desenfoque, baja resolución o una escena de vídeo que requieren confirmar que el objeto anotado conserve suficiente detalle para la finalidad del detector.

## Comprobaciones técnicas

| Control | Resultado |
| --- | --- |
| Carpeta de origen | Existe |
| Archivos de imagen | 50 PNG; 0 JPG/JPEG |
| Apertura/verificación y carga completa | 50/50 correctas |
| Formato y modo | PNG / RGBA en 50/50 |
| Hash SHA-256 exacto | 0 grupos de duplicados |
| Hash perceptual dHash | 0 pares con distancia de Hamming <= 10 |
| Revisión visual local | Realizada mediante hoja de contacto; no usa inferencia ni servicios externos |

El dHash es útil para detectar copias muy próximas, pero no prueba que no existan escenas relacionadas, recortes distintos o fotogramas próximos del mismo vídeo. Como contraste adicional se calcularon firmas perceptuales de baja frecuencia; los resultados cercanos se explican por fondos claros, cajas amarillas y composición de producto, y no se clasifican automáticamente como duplicados.

## Imágenes con incidencias o revisión recomendada

### Resolución limitada

Se marca como umbral preventivo un lado mínimo menor de 400 px. No son archivos defectuosos, pero conviene comprobar el tamaño efectivo del envase/logotipo antes de anotar:

- `2026-10-23_10h25_42.png` — 713 × 398 px.
- `2026-10-23_10h26_08.png` — 709 × 372 px.
- `2026-10-23_10h26_28.png` — 700 × 391 px.
- `2026-10-23_10h27_08.png` — 491 × 306 px.
- `2026-10-23_10h32_21.png` — 689 × 392 px; revisión visual: escena/anuncio con desenfoque.
- `2026-10-23_10h34_39.png` — 557 × 363 px.
- `2026-10-23_10h38_08.png` — 275 × 274 px; la menor del conjunto.
- `2026-10-23_10h38_55.png` — 402 × 353 px; incluye un diseño monocromo de baja definición.

### Relaciones de aspecto fuera de la banda habitual

La banda usada como aviso es menor de 0,75 o mayor de 1,90; no se trata de un error de decodificación.

- `2026-10-23_10h26_08.png` — 1,906 (apaisada).
- `2026-10-23_10h32_53.png` — 1,909 (apaisada).
- `2026-10-23_10h35_52.png` — 0,680 (vertical).
- `2026-10-23_10h42_07.png` — 0,696 (vertical).

### Calidad visual y encuadre: revisión humana prioritaria

- `2026-10-23_10h30_25.png`, `2026-10-23_10h31_31.png`, `2026-10-23_10h32_21.png`, `2026-10-23_10h33_16.png`, `2026-10-23_10h36_55.png`, `2026-10-23_10h43_50.png`, `2026-10-23_10h45_12.png`, `2026-10-23_10h45_37.png`, `2026-10-23_10h46_44.png` y `2026-10-23_10h47_28.png` contienen aspecto de fotograma/anuncio o desenfoque visible. Son valiosas para robustez si la caja sigue siendo identificable; descartar o mantenerlas debe depender del tamaño real de la caja y de la política de calidad de anotación.
- `2026-10-23_10h31_05.png`, `2026-10-23_10h34_16.png`, `2026-10-23_10h34_59.png`, `2026-10-23_10h35_26.png`, `2026-10-23_10h35_52.png`, `2026-10-23_10h36_10.png`, `2026-10-23_10h37_19.png`, `2026-10-23_10h37_47.png`, `2026-10-23_10h39_35.png`, `2026-10-23_10h39_57.png`, `2026-10-23_10h41_44.png` y `2026-10-23_10h42_33.png` son imágenes verticales/casi cuadradas o de composición editorial. Mantenerlas puede mejorar diversidad, pero conviene vigilar que no dominen una futura partición.

## Duplicados

No existen duplicados exactos: los 50 SHA-256 son únicos.

No se identificaron grupos de posibles duplicados visuales con dHash y umbral de distancia <= 10 sobre 64 bits. Por tanto, no hay grupos que requieran deduplicación automática. Esto **no** sustituye agrupar manualmente por fuente o clip antes de dividir train/val/test: varias imágenes tienen apariencia de anuncios o secuencias de vídeo y podrían proceder de una misma fuente aunque su composición no sea un duplicado visual.

## Candidatas para anotación

Las 50 imágenes son candidatas iniciales porque contienen representación visible de la marca/producto Eggo en la revisión visual. Para empezar con una primera tanda de mayor calidad técnica, priorizar las imágenes de envase/publicidad nítida y lineal, excluyendo temporalmente las incidencias de resolución limitada y desenfoque indicadas arriba.

En la anotación, usar exclusivamente la clase `0` (`eggo`) y dibujar una caja por cada envase/logotipo que cumpla la política que se defina. Las variantes de producto y diseño siguen siendo una sola clase, de acuerdo con US-001. Las imágenes con varios envases, lineales o packaging desplegado necesitan una decisión consistente: anotar cada instancia visible o solo las instancias suficientemente legibles; esa política debe documentarse antes de etiquetar en lote.

## Recomendaciones

1. Registrar para cada archivo su fuente, licencia/permiso y un `group_id` de origen antes de integrarlo en el dataset.
2. Revisar manualmente los fotogramas/anuncios y asignar el mismo `group_id` a los que procedan del mismo clip o campaña; no dividir un mismo grupo entre entrenamiento, validación y test.
3. Definir un criterio escrito de tamaño mínimo y visibilidad de la caja. Evaluar primero las ocho imágenes con lado mínimo inferior a 400 px y los recortes borrosos.
4. Anotar una muestra piloto que incluya packshots, lineales, envases múltiples, escenas y publicidad. Validar las cajas sobre la imagen antes de escalar.
5. No convertir ni recomprimir los originales durante la auditoría. Si posteriormente se decide normalizar de PNG a JPG, conservar los originales y dejar trazabilidad de la conversión; hacerlo tras fijar la política de transparencia/fondo y no como sustitución destructiva.
6. Ampliar fuentes y condiciones visuales de manera autorizada: oclusión, distancia, escala pequeña, luz difícil y ángulos variados. Cincuenta imágenes son apropiadas para comenzar la anotación, pero insuficientes por sí solas para evaluar la cobertura final de una clase de detección.

## Limitaciones

- No se ha entrenado ni ejecutado un modelo, ni se han generado etiquetas.
- La presencia de Eggo se ha revisado visualmente de forma preliminar; no equivale a validar cajas, licencia, autenticidad, fuente o idoneidad de cada instancia a nivel de píxel.
- Los hashes perceptuales no detectan de forma fiable todas las relaciones semánticas, fotogramas del mismo clip o variantes de recorte.
- No se han inspeccionado derechos de uso ni metadatos de procedencia; los PNG no contienen EXIF útil para resolverlos.
- Los umbrales de resolución y aspecto son avisos operativos para revisión, no reglas universales de exclusión.
