# Fase 12.5: validación integral y compatibilidad de entrada

## Objetivo y estado

La Fase 12.5 valida de forma reproducible el recorrido completo de SIDAD:

```text
dataset CSV/XLSX
        |
        v
profiling -> cleaning -> CSV procesado
        |
        v
SemanticProject -> DashboardPlan -> ReportLayout
        |
        v
validación AABB -> export_to_powerbi
        |
        v
PBIP + TMDL + PBIR -> PowerBIExportResult -> AgentState
```

**FASE 12.5 IMPLEMENTADA, VALIDADA INTEGRALMENTE Y VERIFICADA END-TO-END EN POWER BI DESKTOP.**

No se añadieron formatos, visuales ni capacidades de autoría nuevas. La única
corrección funcional fue unificar la carga de CSV y XLSX que ya declaraba el
perfilador, de modo que perfilado y limpieza usen la misma política de entrada.

## Alcance de la auditoría

Se revisaron y probaron:

- `DataProfiler` y su carga física de datos;
- `DataCleaner` y el wrapper `clean_dataset` de `ToolRegistry`;
- resolución de rutas y persistencia de artefactos en `AgentState`;
- secuencia de `MockLLMProvider` y `Orchestrator`;
- `StaticPipeline` y el propósito de `run_powerbi.py`;
- construcción de `SemanticProject`, KPI y `DashboardPlan`;
- generación y validación AABB de `ReportLayout`;
- servicio tipado `export_to_powerbi` y `PowerBIProvider`;
- generación física de PBIP, TMDL y PBIR.

`run_powerbi.py` es un script de reproducción/exportación desde el CSV ya
procesado. No es el punto de ingestión raw y no se usa como evidencia de
compatibilidad XLSX. Esa compatibilidad se prueba a través del flujo real del
agente y de `ToolRegistry`.

## Corrección mínima de compatibilidad

`src/tools/data/loader.py` concentra el contrato de entrada:

- CSV se carga con Polars;
- XLSX se carga con Polars usando el motor `openpyxl`, dependencia ya declarada;
- archivos inexistentes, vacíos o con extensión no soportada fallan antes de
  construir artefactos descendientes;
- tanto el perfilador como la limpieza consumen este mismo cargador;
- `clean_dataset` siempre materializa un CSV procesado.

La normalización XLSX -> CSV procesado mantiene intacto el límite de 12.1A: las
particiones Power Query M del modelo semántico siguen leyendo fuentes CSV
reales. No se añadió una segunda serialización TMDL ni lógica especial al
`PowerBIProvider`.

## Matriz de compatibilidad comprobada

| Formato | Estado |
|---|---|
| CSV | **VALIDADO END-TO-END** |
| XLSX | **VALIDADO END-TO-END automáticamente** |
| JSON | **NO SOPORTADO** |
| Parquet | **NO SOPORTADO** |
| XLS heredado | **NO SOPORTADO** |

CSV completó las validaciones automática y manual en Power BI Desktop. El
proyecto abierto manualmente fue generado desde `data/raw/ventas_test.csv`;
por tanto, la evidencia de Desktop no se extiende a XLSX. XLSX completó el
mismo flujo end-to-end en pruebas automáticas, incluida su normalización a CSV,
pero no fue abierto específicamente en Power BI Desktop.

## Dataset y escenarios controlados

La prueba integral crea en directorios temporales dos fuentes equivalentes,
una CSV y otra XLSX. Ambas contienen:

- identificador `id_venta`;
- fecha;
- producto, categoría y ciudad;
- cantidad y precio como métricas numéricas;
- nulos en categoría y cantidad;
- una fila exactamente duplicada.

Para cada formato se verifica:

1. ingestión y perfilado de cinco filas, un duplicado y los nulos esperados;
2. preservación byte a byte del archivo raw;
3. limpieza a cuatro filas únicas, sin nulos en los campos tratados;
4. materialización del dataset procesado fuera de `data/raw`;
5. `SemanticProject` con `Total Registros`, `Total Cantidad`, `Total Precio` y
   `Promedio de Precio`;
6. `DashboardPlan` con dos páginas y doce visuales/slicers;
7. `ReportLayout` válido, sin overlap ni overflow;
8. orden obligatorio `validate_layout` antes de `export_to_powerbi`;
9. persistencia de un `PowerBIExportResult(success=true)` en `AgentState`;
10. existencia y parseo de `.pbip`, TMDL y JSON PBIR;
11. rutas absolutas originadas en la base temporal, incluso desde un CWD ajeno;
12. igualdad de IDs de páginas y visuales entre las ejecuciones CSV y XLSX.

## Errores controlados

La suite exige errores explícitos para:

- archivo inexistente;
- CSV con cabecera pero sin registros;
- JSON, Parquet y XLS heredado;
- intento de pedir a `clean_dataset` una salida procesada distinta de CSV.

El `ToolRegistry` devuelve estos fallos como errores operativos y no genera una
salida que pueda confundirse con una exportación válida.

## Evidencia automatizada

Resultados del cierre:

- Fase 12.5: `9 passed`;
- Fase 12.4: `14 passed`;
- Fase 12.3: `6 passed`;
- Fase 12.2: `8 passed, 1 skipped`;
- Fase 12.1A: `15 passed`;
- suite relevante: `55 passed, 1 skipped, 1 deselected`.

El test omitido de 12.2 consulta schemas oficiales en línea y requiere activar
explícitamente `SIDAD_VALIDATE_ONLINE_PBIR_SCHEMAS=1`. El test deseleccionado es
`test_metrics_generation_and_report`, porque reescribe el archivo excluido
`docs/comparison_report.json`.

También se ejecutan como cierre `python -m compileall src` y
`git diff --check`.

## Evidencia manual en Power BI Desktop

El flujo real del agente generó correctamente:

```text
data/output/phase_12_5_validation/
|-- SIDAD.pbip
|-- SIDAD.SemanticModel/
`-- SIDAD.Report/
```

La exportación produjo 23 archivos y conservó sin cambios el hash SHA-256 del
CSV raw. La validación manual final se realizó satisfactoriamente sobre este
proyecto, generado desde el flujo CSV. Power BI Desktop confirmó:

- apertura correcta de `SIDAD.pbip`;
- carga correcta del modelo `FACT_DATA`;
- visualización correcta de los 7 registros del dataset;
- tipos coherentes para `fecha`, `producto`, `categoria`, `cantidad`, `precio`,
  `ciudad` e `id_venta`;
- `id_venta` configurado como columna clave;
- medidas reales `Total Cantidad`, `Total Precio`, `Promedio de Precio` y
  `Total Registros`;
- existencia de las páginas `Resumen Ejecutivo` y `Análisis Detallado`;
- funcionamiento correcto de los 12 visuales generados;
- funcionamiento de cards, slicers, line chart, clustered bar chart, pie chart
  y `tableEx`;
- ausencia visible de solapamientos y overflow;
- conservación del layout generado automáticamente;
- bindings correctos contra columnas y medidas reales;
- interacción correcta de los slicers con los KPI y gráficos;
- filtrado por producto: al seleccionar `Monitor`, los KPI mostraron
  `Total Registros = 1`, `Total Cantidad = 1,00`, `Total Precio = 300,00` y
  `Promedio de Precio = 300,00`;
- visualización correcta del gráfico de evolución temporal;
- visualización correcta de la distribución por producto;
- visualización correcta del pie chart por categoría;
- tabla detallada con registros reales.

## Limitaciones

- Las entradas auditadas y soportadas son únicamente CSV y XLSX.
- XLSX se normaliza a CSV durante la limpieza; el exportador no crea
  particiones M nativas de Excel.
- Se usa la hoja que Polars selecciona por defecto; no existe todavía un
  contrato para elegir múltiples hojas, rangos o tablas de Excel.
- No se soportan libros cifrados, XLS heredado, JSON ni Parquet.
- La validación manual de Power BI Desktop corresponde al flujo CSV. XLSX está
  validado end-to-end automáticamente, pero no fue abierto específicamente en
  Desktop.
- Styling avanzado, temas, bookmarks e interacciones personalizadas siguen
  fuera de alcance.

## Estado final

**FASE 12.5 IMPLEMENTADA, VALIDADA INTEGRALMENTE Y VERIFICADA END-TO-END EN POWER BI DESKTOP.**
