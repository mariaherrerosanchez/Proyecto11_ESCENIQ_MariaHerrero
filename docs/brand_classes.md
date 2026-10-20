# Clases de marca oficiales

`src/esceniq/vision/brand_classes.py` es la única fuente de verdad para las clases YOLO de ESCENIQ. Su orden no debe cambiar: los pesos y las anotaciones lo utilizan para interpretar cada identificador.

| ID | Clase YOLO | Marca de reporte | Variantes visuales incluidas |
|---:|---|---|---|
| 0 | `eggo` | Eggo | Logotipo y envases |
| 1 | `coca_cola` | Coca-Cola | Coca-Cola, Coke y New Coke |
| 2 | `pepsi` | Pepsi | Pepsi y Pepsi Perfect |
| 3 | `fedex` | FedEx | Diferentes soportes del logotipo |
| 4 | `wilson` | Wilson | Logotipo completo y W aislada inequívoca |

## Reutilización

Usar `yolo_names()` para crear el campo `names` del futuro `data.yaml`, o `render_yolo_names_yaml()` para obtener su bloque YAML. Antes de entrenar o evaluar, `validate_yolo_names()` debe confirmar que el mapa del dataset coincide exactamente con el oficial. `brand_name_for_yolo_id()` normaliza una detección a su marca de reporte; `yolo_id_for_brand_name()` solo acepta nombres oficiales, no variantes.

Las variantes son ejemplos de anotación de una misma clase, no clases nuevas. Una aparición ambigua —por ejemplo, una W sin identificación inequívoca de Wilson— no debe etiquetarse como la marca sin evidencia visual suficiente. La definición del catálogo no garantiza que el modelo aprenda una variante: requiere ejemplos representativos durante el entrenamiento.
