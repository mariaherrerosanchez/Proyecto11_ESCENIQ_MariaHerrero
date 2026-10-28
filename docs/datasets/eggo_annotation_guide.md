# Guía de anotación YOLO — Eggo

**Clase única:** `0 = eggo`  
**Estado:** guía para una prueba piloto; no valida ni crea anotaciones automáticamente.

Esta guía se aplica a los 50 PNG inventariados y auditados para Eggo. Los originales permanecen fuera del repositorio y deben abrirse en una herramienta gráfica de anotación que exporte texto YOLO. No asignar todavía ningún `split` y no alterar el manifiesto de procedencia ni el contrato de `DatasetRecord`.

## Formato YOLO

Cada imagen tendrá, cuando se autorice la anotación, un archivo `.txt` homónimo con una línea por instancia:

```text
class_id x_center y_center width height
```

Las cuatro coordenadas son números decimales normalizados entre 0 y 1. Si la caja visible en píxeles es `(x_min, y_min, x_max, y_max)` y la imagen mide `W × H`:

```text
x_center = ((x_min + x_max) / 2) / W
y_center = ((y_min + y_max) / 2) / H
width    = (x_max - x_min) / W
height   = (y_max - y_min) / H
```

No redondear píxeles antes de normalizar. Revisar visualmente que la caja permanezca dentro de la imagen, que ancho y alto sean positivos y que la primera columna sea siempre `0`. La infraestructura existente valida estos requisitos con `validate_yolo_label()`; no acepta clases fuera del catálogo oficial.

Ejemplo **solo de propuesta piloto**, para `2026-10-23_10h24_28.png` (1.234 × 928 px) y la caja `(28, 143, 1199, 830)`:

```text
0 0.497164 0.524246 0.948947 0.740302
```

La persona anotadora debe confirmar la caja en la herramienta gráfica antes de guardar un TXT.

## Política de cajas

1. Delimitar el envase completo cuando se vea completo, incluidos laterales visibles y perspectiva; no recortar la caja al logotipo o a la foto del gofre.
2. Para un envase o logotipo parcialmente oculto o cortado por el borde, delimitar solo la extensión que realmente se ve. No reconstruir su tamaño fuera de la imagen ni detrás de una oclusión.
3. Anotar un logotipo Eggo aislado y legible si no forma parte de un envase que ya se está anotando.
4. Anotar cada envase distinguible por separado en lineales, composiciones o anuncios. Una caja por instancia, aunque sean del mismo sabor o diseño.
5. No superponer la caja de un logotipo con la caja del envase que lo contiene. El logotipo pertenece ya a esa instancia de envase.
6. No anotar gofres, platos, comida genérica, personajes ni texto que no sea un logotipo Eggo reconocible.
7. Marcar para revisión —sin decidir unilateralmente— el desenfoque intenso, un objeto muy pequeño, una marca parcialmente legible o una caja que se confunda con otra.
8. Mantener `0` como único identificador. Distintos diseños, sabores, formatos históricos y variantes de packaging siguen siendo `eggo`, no clases nuevas.

## Casos difíciles y criterio de decisión

| Situación | Decisión |
| --- | --- |
| Envase frontal, lateral o en perspectiva | Una sola caja ajustada al contorno exterior visible del envase. |
| Envase parcialmente oculto | Una caja sobre la parte visible, sin extenderla sobre la oclusión. |
| Envase en el borde de la imagen | Anotar la porción reconocible visible. |
| Varios envases separados | Una caja por envase distinguible. |
| Lineal con cajas parcialmente solapadas | Anotar cada caja que pueda individualizarse; llevar a revisión las que no tengan límites claros. |
| Logo aislado (rótulo, anuncio o gráfica) | Una caja propia solo si es reconocible y no está ya contenido en una caja de envase. |
| Gofre sin marca | No anotar. |
| Imagen borrosa o logo demasiado pequeño | No inventar una caja: señalarla como `needs_review` y decidir con una segunda revisión. |

Evitar cajas excesivamente holgadas con mucho fondo, así como cajas que corten una parte visible del envase. Si dos personas discrepan, conservar la imagen como pendiente y registrar la decisión antes de continuar la tanda.

## Prueba piloto propuesta

La muestra combina casos nítidos, diseño histórico, instancias múltiples y una escena difícil. Todas las coordenadas siguientes son **propuestas en píxeles `(x_min, y_min, x_max, y_max)`**, revisadas visualmente; no son etiquetas aprobadas ni se han escrito en archivos YOLO.

| Imagen | Dimensiones | Cobertura | Motivo y propuesta |
| --- | ---: | --- | --- |
| `2026-10-23_10h24_28.png` | 1234 × 928 | 1 envase | Envase limpio y grande. Propuesta: `(28, 143, 1199, 830)`. Sirve de referencia para el ajuste al packaging completo. |
| `2026-10-23_10h29_55.png` | 931 × 565 | 1 envase | Diseño histórico y encuadre con borde oscuro. Propuesta: `(19, 40, 930, 524)`. Confirma que la variante visual sigue siendo clase 0. |
| `2026-10-23_10h28_48.png` | 980 × 595 | 9 envases | Lineal complejo con múltiples productos y recortes. Propuestas: `(0,0,357,148)`, `(364,0,674,148)`, `(678,0,980,148)`, `(0,155,356,289)`, `(366,155,674,289)`, `(679,155,980,289)`, `(41,381,360,540)`, `(368,381,669,540)`, `(678,381,980,540)`. Revisión obligatoria de límites e instancias parcialmente visibles. |
| `2026-10-23_10h32_53.png` | 1512 × 792 | 4 envases + 1 logo aislado | Composición publicitaria que prueba la regla de varias instancias y logo no contenido en envase. Propuestas de envases: `(14,29,878,535)`, `(907,0,1512,332)`, `(936,352,1477,590)`, `(378,480,987,753)`; logo aislado: `(1093,585,1502,783)`. |
| `2026-10-23_10h30_25.png` | 603 × 515 | 1 envase visible | Fotograma borroso, señalado por la auditoría. Propuesta de la extensión visible: `(285,323,581,484)`. Debe recibir revisión de una segunda persona antes de incluirse. |

## Resultado de la revisión piloto (provisional)

Se han materializado las 17 propuestas en TXT YOLO **provisionales**, fuera del repositorio y fuera del dataset definitivo:

- `C:\ESCENIQ_Datasets\Eggo\piloto\labels\` contiene cinco TXT homónimos.
- `C:\ESCENIQ_Datasets\Eggo\piloto\previews\` contiene cinco PNG con cajas numeradas para inspección humana.

Las cinco etiquetas se validaron con `validate_yolo_label()`: todas sus líneas usan clase `0`, coordenadas normalizadas en `[0, 1]` y dimensiones positivas. Esta validación es sintáctica; no certifica que el borde de cada caja sea correcto.

Decisiones de la revisión:

- `2026-10-23_10h24_28.png`: 1 caja de envase moderno.
- `2026-10-23_10h29_55.png`: 1 caja de envase histórico.
- `2026-10-23_10h28_48.png`: 9 cajas de envases individualizables. Los tres recortes adicionales de la fila inferior se mantienen sin anotar: muestran una fracción demasiado limitada para establecer con fiabilidad el envase y sus límites. Requieren segunda revisión a escala completa si se plantean incluir.
- `2026-10-23_10h32_53.png`: 4 cajas de envase y 1 caja de logotipo aislado; no se duplicó ningún logo incluido en un envase.
- `2026-10-23_10h30_25.png`: 1 caja alrededor de la porción visible del envase. La imagen sigue marcada para revisión debido al desenfoque.

Las previsualizaciones y los TXT sirven para discusión y corrección, no convierten las anotaciones en aceptadas ni autorizan su incorporación a `datasets/esceniq/`.

## Cómo ejecutar la prueba piloto

1. Abrir solo estas cinco imágenes en una herramienta de etiquetado gráfica configurada con una única categoría: `0`, `eggo`.
2. Usar las propuestas y previsualizaciones como referencia, no como importación automática. Ajustar cada caja sobre la imagen original a escala completa.
3. Los TXT provisionales se encuentran en `C:\ESCENIQ_Datasets\Eggo\piloto\labels\`; corregirlos solo tras inspeccionar el PNG original y mantenerlos fuera de `datasets/esceniq/labels/` mientras no exista aprobación. No tocar los PNG.
4. Solicitar una segunda revisión para las 17 cajas, con atención reforzada a las nueve del lineal, al logo aislado y al fotograma borroso. Revisar específicamente los tres recortes inferiores que se dejaron sin anotar.
5. Una vez aprobadas, validar el formato con `validate_yolo_label()` y comprobar visualmente la superposición caja-imagen. Solo entonces decidir si se incorporan al flujo de preparación del dataset.
6. No crear `train`, `val` o `test` hasta que se conozcan fuente, licencia y `group_id` reales de los originales.

## Pendientes de revisión humana

- Aprobación o ajuste de todas las 17 cajas piloto propuestas.
- Decisión sobre el umbral de legibilidad/tamaño mínimo para los productos pequeños y borrosos; la auditoría identificó ocho imágenes con lado mínimo menor de 400 px.
- Confirmación de que en lineales se anotarán todas las instancias individualizables con el mismo criterio.
- Procedencia, URL, licencia/permiso y agrupación real por fuente o clip de las 50 imágenes. Estos campos siguen siendo `unknown`/`unverified`/provisionales en el manifiesto.
- Ninguna de estas decisiones autoriza aún la anotación masiva, el movimiento de imágenes, la separación de conjuntos ni el entrenamiento.

## Lotes posteriores al piloto: estado de revisión

El lote posterior al piloto se mantiene fuera del repositorio. Los TXT, PNG de previsualización, manifiestos y datos de corrección no pertenecen al dataset definitivo ni se versionan con el código.

- **Lote provisional inicial:** 45 imágenes, 72 cajas propuestas y 22 casos marcados para revisión por lineales, cartones desplegados, instancias múltiples, recortes, baja definición o desenfoque.
- **Lote corregido:** 6 imágenes se excluyeron provisionalmente por ser cartones desplegados; permanecen 39 imágenes activas con 66 cajas provisionales.
- **Piloto independiente:** 5 imágenes y 17 cajas provisionales, conservadas aparte y sin modificación durante la corrección del lote de 45.
- **Total candidato:** 44 imágenes (39 del lote corregido + 5 del piloto), todas pendientes de aprobación visual definitiva antes de cualquier incorporación al dataset.
- `2026-10-23_10h46_10.png` conserva estado `policy_review`: es una valla publicitaria y requiere una decisión humana explícita sobre su inclusión.

Los resultados siguen sujetos a revisión humana, especialmente lineales, escenas borrosas, productos solapados y objetos parcialmente visibles. Esta tanda no autoriza particiones, entrenamiento ni publicación de datos.

## Regenerar localmente el lote corregido

`scripts/revise_eggo_annotations.py` no contiene coordenadas ni identificadores de imágenes. Requiere un JSON local, fuera del repositorio, con tres claves: `excluded` (archivo y justificación), `revised_boxes` (archivo y cajas normalizadas `xyxy`) y `review_overrides` (estado u observación opcionales).

Ejemplo, usando rutas configurables de tu entorno:

```powershell
python scripts/revise_eggo_annotations.py \
  --originals <directorio-originales> \
  --source <directorio-anotaciones-provisionales> \
  --corrections C:\ESCENIQ_Datasets\Eggo\revision_corrections.json \
  --output <directorio-de-salida-vacío>
```

El script rechaza una salida existente, valida las cajas con `validate_yolo_label()`, genera una previsualización por etiqueta activa y contrasta los hashes de los originales. No debe ejecutarse sobre el lote ya validado salvo que se autorice una regeneración separada.
