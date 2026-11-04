# ESCENIQ — TECHNICAL_SPEC

**Versión:** 1.1 · **Referencia:** [MASTER_SPEC](MASTER_SPEC.md)

## 1. Contratos de dominio propuestos

```python
# Esquema conceptual; no es implementación final.
Detection = {
    "frame_index": int,
    "timestamp_seconds": float,
    "class_name": str,
    "brand_name": str,
    "confidence": float,
    "bbox_xyxy": tuple[float, float, float, float],
}
BrandExposure = {
    "brand_name": str,
    "estimated_seconds": float,
    "percentage_of_video": float,
    "positive_samples": int,
}
```

- Mantener separadas las responsabilidades de inferencia, normalización de marca, agregación y persistencia.
- Almacenar versión del modelo, frecuencia de muestreo, confianza y duración para reproducibilidad.

## 2. Algoritmo MVP de exposición

**Propuesta inicial:** procesar muestras en instantes `t_i` espaciados según intervalo `Δ` (por ejemplo, 1 segundo, pendiente de validar). Cada muestra representa `[t_i, min(t_i + Δ, T))`, con `T` duración total.

Para cada muestra:
1. Ejecutar YOLO y filtrar por confianza.
2. Convertir las clases detectadas a nombres de marca mediante mapa versionado.
3. Construir un **conjunto** de marcas presentes, eliminando duplicados.
4. Sumar la longitud del intervalo representado **una vez por marca**.
5. Calcular `porcentaje = 100 * segundos / T` y limitar a `[0, 100]` por marca.

Si el muestreo se realiza por índices de fotograma, calcular timestamps con la información temporal disponible y evitar acumulación de errores de redondeo. Para FPS variable, advertir limitaciones de metadatos y priorizar timestamps fiables. El método es una **aproximación**: una aparición breve entre muestras puede perderse.

### Casos de prueba obligatorios
| Caso | Entrada | Resultado esperado |
|---|---|---|
| Duplicados | 3 cajas de Coca-Cola en una muestra de 1 s | Coca-Cola = 1 s |
| Clases equivalentes | dos detecciones de variantes Coca-Cola/Coke en misma muestra | Coca-Cola = 1 s |
| Simultaneidad | Coca-Cola y Eggo en misma muestra | 1 s cada una |
| Ausencia | Ninguna detección | 0 s; tabla vacía controlada |
| Final parcial | T=2,4 s; muestras t=0,1,2 y Δ=1 | Duraciones 1+1+0,4, no 3 s |
| Duración cero | Archivo sin duración válida | Error explícito, sin división por cero |
| Porcentaje | 2 s de 10 s | 20 % |
| Cambio de umbral | Mismo vídeo, umbrales distintos | Análisis diferenciados con parámetros registrados |

## 3. Pruebas
- **Unitarias:** agregación, mapeo, porcentajes, límites de intervalos, validación de entrada.
- **Integración:** inferencia con clip pequeño, SQLite, exportación CSV.
- **End-to-end manual:** cargar clip reservado, ejecutar, inspeccionar cajas, contrastar muestras y reabrir historial.
- **ML:** conjunto de test independiente; métricas y matriz de errores documentadas.

## 4. Persistencia y archivos
- SQLite local con claves foráneas activas, migraciones sencillas si se requieren.
- Evitar guardar un frame por cada muestra si dispara el almacenamiento: limitar evidencias representativas.
- `data/`, `runs/`, `models/*.pt`, vídeos, bases SQLite y cachés deben revisarse en `.gitignore` según política de entrega.
- No registrar rutas personales ni datos privados en logs públicos.

## 5. Configuración
- Variables/rutas en archivo de configuración local o variables de entorno.
- Ajustes mínimos: modelo activo, umbral de confianza, intervalo de muestreo, directorios.
- El tema claro/oscuro requiere una solución probada en Streamlit; no asumir que cambiar CSS equivale a cambiar todos los widgets y gráficos. Priorizar accesibilidad y consistencia.

## 6. Rendimiento y fiabilidad
- Procesar secuencialmente o por lotes pequeños para evitar consumo excesivo de RAM.
- Mostrar progreso basado en fotogramas/muestras procesados cuando sea viable.
- Gestionar interrupciones y estados `pending/running/completed/failed`.
- Definir tamaño máximo de carga y longitud recomendada tras prueba con equipo real.
- Si falla GPU, documentar ejecución CPU o error claro, según compatibilidad del modelo.

## 7. Reproducibilidad
- Fijar versiones tras validación local de Python, Ultralytics, OpenCV y Streamlit.
- README con comandos de entorno, entrenamiento (si datos accesibles), ejecución, tests y limitaciones.
- Conservar resultados reales de entrenamiento y evaluación, fecha, dataset y parámetros.
- Docker es una mejora condicionada a la estabilidad del MVP y compatibilidad del entorno.

## 8. Seguridad y legalidad
- Validar extensiones y decodificación real; no confiar solo en nombre de archivo.
- Evitar ejecutar comandos construidos con nombres de archivos del usuario.
- Mantener los vídeos locales y fuera del repositorio.
- Comprobar derechos de redistribución de datasets, clips y pesos antes de publicarlos.

## 9. Configuración inicial de clases
```yaml
names:
  0: eggo
  1: coca_cola
  2: pepsi
  3: fedex
  4: wilson
```
La asignación de índices es una propuesta que deberá coincidir exactamente con `data.yaml` y los pesos entrenados. Todas las variantes visuales de una marca comparten clase. Para Wilson, incluir ejemplos de la W aislada y el logotipo completo; para Coca-Cola, Coke y New Coke. No asumir que ver el objeto sin logotipo equivale a reconocer la marca.
