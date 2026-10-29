# Piloto de entrenamiento YOLO — Eggo

## Propósito y alcance

Este experimento comprueba el flujo local de preparación, entrenamiento y evaluación de YOLO para la clase única `0 = eggo`. Es un piloto técnico: no sustituye el modelo oficial de ESCENIQ, que debe contener exactamente `eggo`, `coca_cola`, `pepsi`, `fedex` y `wilson`.

Los PNG, etiquetas, pesos, clips y artefactos de ejecución permanecen fuera del repositorio. No se publican debido a la procedencia y licencias no verificadas de las imágenes originales.

## Datos y partición

La fuente de anotación fue el JSON de revisión humana definitivo, generado localmente con la galería de revisión. Contenía 44 imágenes aprobadas y 83 cajas YOLO válidas de clase `0`.

| Split | Imágenes | Cajas |
| --- | ---: | ---: |
| Entrenamiento | 31 | 61 |
| Validación | 7 | 14 |
| Test | 6 | 8 |
| Total | 44 | 83 |

Las seis imágenes de cartones desplegados quedaron excluidas. La partición se generó de forma determinista con semilla `42`, pero es una división por imagen, no por fuente: no se puede garantizar independencia de origen porque las URL, campañas y clips originales son desconocidos.

## Configuración reproducible

| Parámetro | Valor |
| --- | --- |
| Pesos iniciales | `yolo11n.pt` local |
| Épocas solicitadas | 50 |
| Épocas ejecutadas | 26; parada temprana con paciencia 15 |
| Tamaño de imagen | 640 |
| Batch | 4 |
| Semilla | 42 |
| Dispositivo | GPU NVIDIA RTX 5070 Laptop |
| Python | 3.12.13 |
| PyTorch | 2.11.0+cu128 |
| Ultralytics | 8.4.191 |

El entrenamiento se ejecutó sobre la raíz absoluta configurable del dataset piloto, sin modificar sus PNG o TXT. Los pesos `best.pt` y `last.pt`, el `args.yaml`, las curvas y los registros se conservaron en un directorio local externo de resultados.

## Resultados reales

La validación usada para seleccionar el mejor peso produjo:

| Split | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| Validación | 1.00000 | 0.14286 | 0.47508 | 0.10998 |
| Test final | 0.0691 | 0.5000 | 0.0881 | 0.0196 |

El test se mantuvo fuera del entrenamiento y de la selección del peso. Tras la evaluación final se usó también para una inspección diagnóstica con `conf=0.25`, `iou=0.45` e `imgsz=640`; por ello queda consumido y no debe usarse para ajustar hiperparámetros ni seleccionar otro modelo.

## Diagnóstico

La inferencia diagnóstica sobre las seis imágenes de test produjo 51 detecciones para ocho instancias anotadas. Persistieron falsos positivos y cajas superpuestas, incluidas algunas de confianza alta. El comportamiento no revela un fallo confirmado de NMS ni de la configuración de una sola clase: se utilizó NMS con `iou=0.45` y el modelo expone únicamente `{0: "eggo"}`.

La hipótesis principal es sobreajuste y desplazamiento de distribución: el entrenamiento contiene solo 31 imágenes y 61 cajas, con diversidad limitada y numerosos envases que ocupan una fracción muy grande del fotograma. Las anotaciones aprobadas son sintácticamente válidas, pero las cajas grandes y escenas con múltiples instancias merecen revisión cualitativa adicional antes de ampliar datos.

## Limitaciones y siguiente trabajo

- Es un detector experimental de una sola marca; no reconoce ni descarta Coca-Cola, Pepsi, FedEx o Wilson.
- El volumen es muy pequeño y la procedencia, licencia y agrupación por fuente no están verificadas.
- La separación no asegura independencia por vídeo, campaña o fuente.
- Las métricas de test no son una estimación fiable de generalización y ese test no debe reutilizarse para ajuste.
- No se deben desplegar ni presentar las detecciones como reconocimiento fiable de marca.

Antes de reentrenar, se necesita un nuevo conjunto de evaluación independiente, más ejemplos variados y negativos difíciles, trazabilidad de origen/licencia y revisión visual focalizada de cajas grandes y escenas densas. El futuro modelo oficial deberá entrenarse y evaluarse con las cinco clases del catálogo ESCENIQ.
