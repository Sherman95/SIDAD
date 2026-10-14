# Fase 12.4: exportación Power BI integrada en el agente

## Objetivo y estado

La Fase 12.4 incorpora la materialización del proyecto Power BI al flujo
determinista y al ciclo del agente:

```text
SemanticProject + DashboardPlan + ReportLayout validado
                          |
                          v
                 export_to_powerbi
                          |
                          v
                   PowerBIProvider
                          |
                          v
                 PBIP + TMDL + PBIR
```

**FASE 12.4 IMPLEMENTADA, VALIDADA AUTOMÁTICAMENTE Y VERIFICADA END-TO-END EN POWER BI DESKTOP.**

La fase reutiliza la generación ya verificada de 12.1A, 12.2 y 12.3. No
duplica serialización TMDL/PBIR, resolución de bindings, cálculo de layout ni
generación de IDs.

## Contrato de la herramienta

`export_to_powerbi` está registrada en `ToolRegistry` y recibe:

- `semantic_project_json`: serialización de `SemanticProject`;
- `dashboard_plan_json`: serialización de `DashboardPlan`;
- `report_layout_json`: serialización de `ReportLayout`;
- `output_path`: directorio de salida absoluto o relativo a una base explícita;
- `project_name`: nombre seguro del artefacto Power BI;
- `source_base_path`: directorio absoluto y estable para resolver rutas.

El wrapper valida los JSON con sus modelos Pydantic antes de invocar el
servicio tipado. El servicio interno consume directamente `SemanticProject`,
`DashboardPlan` y `ReportLayout` y retorna `PowerBIExportResult`:

```text
success
project_path
semantic_model_path
report_path
generated_files
message
errors
```

Las rutas exitosas son absolutas. `generated_files` enumera el `.pbip` y todos
los archivos materializados dentro de los artefactos `.SemanticModel` y
`.Report`.

## Precondiciones y seguridad

Antes de escribir se exige:

- presencia y deserialización válida de los tres modelos de dominio;
- al menos una tabla semántica con tipos exportables;
- dataset CSV real y existente por cada tabla;
- asociaciones completas y no ambiguas entre plan y layout;
- bindings resolubles contra el modelo semántico;
- validación AABB sin errores de tamaño, overflow ni solapamiento;
- nombre de proyecto válido;
- directorio de salida válido y distinto de la raíz del sistema y de la raíz
  del proyecto;
- una ruta relativa contenida en `source_base_path`, sin escape mediante
  `..`;
- salida fuera de `data/raw` y que no contenga un dataset fuente.

Las precondiciones se evalúan antes de crear el directorio de salida. Un fallo
esperado produce un `PowerBIExportResult(success=false)` con errores claros y
`ToolRegistry` lo marca como error operativo.

## Independencia del working directory

`AgentState.project_base_path` define el contexto estable del flujo. Las rutas
de entrada, limpieza y exportación se resuelven con
`AgentState.resolve_project_path`; una ruta absoluta se conserva y una ruta
relativa se resuelve contra esa base, no contra el CWD del proceso.

`PowerBIProvider` conserva su base estable por módulo cuando no recibe una base
explícita. Las pruebas ejecutan tanto la herramienta como el agente desde un
CWD ajeno y verifican que se encuentran el dataset y la salida correctos.

## Integración del flujo

### AgentState

Conserva:

- el contexto `project_base_path`;
- `powerbi_output_path` y `powerbi_project_name`;
- el resultado tipado en `powerbi_export`.

Cuando se reemplaza el modelo semántico, el plan o el layout, se invalidan los
artefactos descendientes. Una nueva validación también invalida una exportación
anterior para impedir que el estado declare éxito con artefactos obsoletos.

### ToolRegistry

Registra `export_to_powerbi`, convierte los tres JSON a modelos Pydantic y
serializa `PowerBIExportResult`. Un resultado con `success=false` se propaga con
`is_error=true`.

### Orchestrator y proveedores LLM

El guardrail de `finish` ahora exige simultáneamente:

1. `ReportLayout` presente;
2. `ValidationReport.is_valid=true`;
3. ausencia de fallos del `Critic`;
4. `PowerBIExportResult.success=true`.

`MockLLMProvider` invoca la exportación después de validar. El prompt de Gemini
expone el estado de exportación y, cuando corresponde, proporciona los
argumentos serializados exactos. Un error de exportación queda en
`AgentState.powerbi_export`, se añade a `pending_issues` y finaliza el flujo como
`FAILED`.

### StaticPipeline y script

`StaticPipeline` añade la exportación como séptimo paso y solo declara `SUCCESS`
si el resultado tipado es exitoso. `run_powerbi.py` ejecuta el mismo servicio
tipado en vez de llamar directamente a los dos métodos de despliegue.

## Pruebas automatizadas

`tests/test_powerbi_phase_12_4.py` cubre:

- registro y schema de la herramienta;
- exportación completa desde modelos tipados y serializados;
- contrato y rutas de `PowerBIExportResult`;
- rechazo individual de modelos ausentes;
- rechazo de layout AABB inválido;
- rechazo de dataset inexistente;
- rechazo de salida relativa insegura;
- independencia del CWD;
- integración en `StaticPipeline`;
- integración completa con `MockLLMProvider` y `Orchestrator`;
- bloqueo de `finish` antes de una exportación exitosa;
- persistencia y propagación de errores en `AgentState`.

Las suites de 12.1A, 12.2 y 12.3 permanecen como regresión obligatoria.

## Evidencia de validación manual en Power BI Desktop

La validación end-to-end se realizó sobre el proyecto generado mediante
`ToolRegistry.export_to_powerbi`. Power BI Desktop confirmó:

- apertura correcta de `SIDAD.pbip`;
- carga correcta del modelo `FACT_DATA`;
- 2 páginas: `Resumen Ejecutivo` y `Análisis Detallado`;
- 12 visuales correctamente generados;
- cuatro KPI con datos y medidas reales;
- slicers de fecha, producto y categoría;
- funcionamiento de `cardVisual`, `lineChart`, `clusteredBarChart`, `pieChart`
  y `tableEx`;
- bindings contra columnas y medidas reales;
- datos procesados visibles, incluidos los 7 registros de la tabla;
- posiciones y dimensiones correctas;
- ausencia de solapamientos y overflow visibles;
- conservación de páginas, visuales, bindings, layout e IDs deterministas;
- generación end-to-end realizada mediante `ToolRegistry.export_to_powerbi`;
- persistencia exitosa de `PowerBIExportResult` en `AgentState`;
- finalización correcta del agente únicamente después de validar el layout y
  completar la exportación.

## Limitaciones y fuera de alcance

- La herramienta no abre Power BI Desktop ni ejecuta procesos GUI.
- No añade styling avanzado, temas materializados, bookmarks o interacciones.
- No modifica el algoritmo de layout, los bindings, los IDs ni la
  serialización validada en fases anteriores.
- El exportador actual continúa limitado a particiones CSV, conforme al alcance
  de 12.1A.
