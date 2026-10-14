# CONTEXTO INTEGRAL DEL PROYECTO SIDAD (ESTADO ACTUAL)

> **Actualización de Fase 12.3 (2026-10-14):** **FASE 12.3 IMPLEMENTADA,
> VALIDADA ESTRUCTURALMENTE Y VERIFICADA EN POWER BI DESKTOP PARA
> POSICIONAMIENTO, DIMENSIONES Y DISTRIBUCIÓN DE VISUALES PBIR.**
> `ReportLayout` se integra con PBIR mediante referencias deterministas; el
> exportador traduce `x`, `y`, `width`, `height`, `z` y `tabOrder` sin decidir
> el diseño. El layout base `1280 x 720` supera la validación AABB sin overflow,
> solapamientos ni advertencias. Power BI Desktop confirmó el canvas, la
> distribución de KPI, slicers, gráficos y tabla, la ausencia de superposiciones
> y la conservación de páginas, visuales, bindings e IDs con datos reales. El detalle está en
> [FASE_12_3_LAYOUT_PBIR.md](FASE_12_3_LAYOUT_PBIR.md).
>
> **Actualización de Fase 12.2 (2026-10-14):** **FASE 12.2 IMPLEMENTADA,
> VALIDADA ESTRUCTURALMENTE Y VERIFICADA EN POWER BI DESKTOP PARA GENERACIÓN DE
> PÁGINAS, VISUALES Y BINDINGS PBIR.** El
> exportador genera la estructura PBIR modular, paginas y visuales con IDs
> deterministas, bindings contra `SemanticProject`, resolucion explicita de
> ambiguedades y limpieza stale. Power BI Desktop confirmó 2 páginas, 12
> visuales, todos los tipos previstos, bindings con columnas y medidas reales,
> carga de datos y funcionamiento de los visuales. La superposición observada
> correspondía al placeholder que 12.3 ya sustituyó. El detalle se documenta en
> [FASE_12_2_PBIR.md](FASE_12_2_PBIR.md).
>
> **Actualizacion de Fase 12.1A (2026-09-29):** **FASE 12.1A IMPLEMENTADA,
> VALIDADA ESTRUCTURALMENTE Y VERIFICADA EN POWER BI DESKTOP PARA CARGA Y
> ACTUALIZACIÓN DEL MODELO SEMÁNTICO.** Se incorporaron tipos semanticos
> portables, procedencia real por tabla, relaciones explicitas con validacion de
> extremos, `relationships.tmdl` condicional, particiones CSV con el dataset
> procesado real y resolucion de rutas independiente del working directory. La
> verificacion manual cubrio apertura, carga y actualizacion del modelo sin
> errores. No cubre todavia paginas, visuales, bindings ni layout PBIR. El detalle
> y los limites de evidencia estan en
> [FASE_12_1A_TMDL.md](FASE_12_1A_TMDL.md).

Este documento centraliza todo el contexto, arquitectura, evolución y estado actual del proyecto **SIDAD** (Sistema Inteligente para el Diseño Automatizado de Dashboards), actualmente con la Fase 12.3 completada y validada en Power BI Desktop.

---

## 1. OBJETIVO DEL PROYECTO
Desarrollar un agente inteligente capaz de automatizar el flujo de procesamiento, análisis, modelado y visualización de datos para generar dashboards orientados al soporte de decisiones. Su objetivo es reducir drásticamente la intervención manual desde el origen de datos crudos hasta la implementación final en plataformas de Business Intelligence (específicamente Power BI), manteniendo un diseño de software escalable, determinista y auditable.

---

## 2. ARQUITECTURA DEL SISTEMA
El sistema emplea un paradigma híbrido que separa el razonamiento (LLM/Agente) de la ejecución (Herramientas deterministas) para garantizar fiabilidad.

### 2.1. Core del Agente
- **`Agent` (`src/agent/agent.py`)**: El orquestador inteligente que recibe peticiones en lenguaje natural. Implementa un bucle de razonamiento (Plan-Act-Observe) y utiliza un modelo LLM subyacente.
- **`LLMProvider` (`gemini_provider.py` y `mock_provider.py`)**: Abstracción del proveedor de inteligencia. Soporta Google Gemini Pro y un Mock determinista para pruebas reproducibles.
- **`ToolRegistry` (`src/agent/tool_registry.py`)**: Define y envuelve las funciones deterministas de Python para que el LLM pueda llamarlas con protecciones de seguridad (ej. no modificar archivos en `data/raw`).

### 2.2. Herramientas Deterministas (`src/tools/`)
Las tareas algorítmicas están encapsuladas:
- **`DataProfiler` (`data/profiler.py`)**: Analiza la calidad y estructura del dataset (nulos, duplicados, distribución, tipos).
- **`DataCleaner` (`data/cleaner.py`)**: Aplica normalización, limpieza y formateo (ej. llenar nulos, borrar duplicados) sobre DataFrames de Polars.
- **`SemanticBuilder` (`modeling/semantic_builder.py`)**: Infiere el esquema de negocio (Dimensiones vs Hechos), asigna roles a columnas y detecta posibles KPIs.
- **`DashboardPlanner` (`dashboard/planner.py`)**: Planifica la estructura narrativa del dashboard (páginas, objetivos, distribución general).
- **`ReportGenerator` (`dashboard/generator.py`)**: (Fase de layout visual) Genera coordenadas AABB y asigna tipos de visuales.
- **`PowerBIProvider` (`bi/powerbi_provider.py`)**: Exportador responsable de traducir el modelo semántico de Python a un proyecto PBIP/TMDL válido.

### 2.3. Modelos de Dominio (`src/models/`)
Definidos con Pydantic fuertemente tipados:
- **`profiling.py`**: Modelos de calidad de datos y diagnóstico.
- **`transformations.py`**: Bitácora auditable de las limpiezas realizadas.
- **`semantic_model.py`**: Entidades lógicas (Columnas, Tablas, Relaciones lógicas y KPIs).
- **`dashboard.py`**: Planes de diseño analítico (Páginas, Gráficos, Ejes).
- **`report_layout.py`**: Estructuras geométricas y espaciales del tablero.

---

## 3. HISTORIAL DE FASES IMPLEMENTADAS

### Fases 1 a 4: Preparación y Modelado
- **Fase 1 (Perfilado):** Ingesta de CSV usando Polars y generación de perfiles estadísticos (`DataProfiler`).
- **Fase 2 (Limpieza):** Generación de operaciones correctivas (`DataCleaner`) con registro de transformaciones.
- **Fase 3 (Modelado Semántico):** Análisis del esquema en estrella (Dimensiones/Hechos) a partir de los perfiles y definición de KPIs.
- **Fase 4 (Planificación de Dashboard):** Creación del `DashboardPlan` mapeando los requerimientos de negocio a páginas y visuales abstractos.

### Fases 5 a 7: Diseño Visual (Parcial/En transición)
- **Fase 5 (Abstracción BI):** Creación inicial de `BIProvider` y `PowerBIProvider`.
- **Fase 6 y 7 (Generación y Validación Visual):** Motor de cálculo geométrico (`ReportGenerator`) y validación de colisiones o superposiciones (`LayoutValidator`).

### Fases 8 y 9: Orquestación Inteligente (El Agente SIDAD)
- Implementación de la arquitectura completa del agente (Agent, ToolRegistry, GeminiProvider). Se reemplazó un flujo de scripts estáticos con un LLM capaz de invocar las herramientas de las Fases 1 a 7 de manera autónoma.

### Fases 10 y 11: Evaluación y Comparación
- **Fase 10 (Framework de Evaluación):** Se desarrolló `run_evaluation.py` para medir cuantitativamente el agente bajo métricas rigurosas (éxito de tareas, alucinación de herramientas, tiempo de ejecución, uso de tokens).
- **Fase 11 (Evaluación Comparativa):** Se introdujo un `StaticPipeline` (flujo clásico basado en scripts) y se automatizó la comparación entre el desempeño estático determinista y el desempeño autónomo del Agente SIDAD usando datos de prueba (`MockProvider`).

### Fase 12.1A: Modelo semántico Power BI (PBIP/TMDL)
- **Estado:** implementada, validada estructuralmente y verificada manualmente en Power BI Desktop para carga y actualización del modelo semántico.
- **Qué se implementó:**
  - Archivos raíz `.pbip`, `definition.pbism` y metadato raíz `definition.pbir`.
  - `database.tmdl`, `model.tmdl`, tablas modulares y `relationships.tmdl` cuando existen relaciones reales.
  - Tipos semánticos portables y traducción coherente a Power Query M y TMDL.
  - Medidas DAX automáticas, incluyendo `Total Cantidad` para el dataset validado.
  - Particiones M conectadas al CSV procesado real, sin `data.csv` ficticio y sin dependencia accidental del working directory.
- **Evidencia manual:** `SIDAD.pbip` abrió correctamente; `FACT_DATA`, columnas, tipos y medidas fueron reconocidos; la partición M leyó el CSV procesado real y la actualización terminó sin errores.
- **Límite:** esta evidencia corresponde al modelo semántico. No existe todavía un dashboard PBIR completo.

### Fase 12.2: Contenido y bindings Power BI (PBIR)
- **Estado:** implementada, validada estructuralmente y verificada en Power BI Desktop para generación de páginas, visuales y bindings PBIR.
- **Qué se implementó:**
  - Estructura modular `definition/version.json`, `report.json`, `pages/pages.json`, `page.json` y `visual.json`.
  - IDs deterministas, orden y página activa.
  - Traducción de Card, BarChart, LineChart, Table, PieChart y Slicer a tipos PBIR oficiales.
  - Bindings a columnas, medidas y agregaciones resueltos contra `SemanticProject`, con error explícito ante ambigüedad.
  - Tablas con múltiples referencias de campo y slicers declarados por página.
  - Limpieza de páginas, visuales y archivos legacy obsoletos.
  - Validación automatizada contra los schemas oficiales publicados de Microsoft.
- **Evidencia manual:** 2 páginas y 12 visuales cargaron correctamente; cards, slicers, line chart, clustered bar chart, pie chart y `tableEx` funcionaron con columnas, medidas y datos reales.
- **Frontera:** no consume `ReportLayout`, no calcula layout final y no registra `export_to_powerbi` en el agente. Las posiciones son placeholders técnicos sin `z` ni `tabOrder`.

### Fase 12.3: Layout real en Power BI (PBIR)
- **Estado:** implementada, validada estructuralmente y verificada en Power BI Desktop para posicionamiento, dimensiones y distribución de visuales PBIR.
- **Qué se implementó:**
  - Referencia `visual_ref` determinista entre `DashboardPlan` y cada `PlacedVisual`.
  - Layout reproducible para canvas `1280 x 720`, con zonas y mínimos por tipo de visual.
  - Inclusión de slicers declarados en el layout físico.
  - Traducción de `x`, `y`, `width`, `height`, `z` y `tabOrder` a `visual.json`.
  - Uso de `RenderedPage` para el tamaño real de `page.json`.
  - Fallo explícito ante asociaciones ausentes, adicionales, inconsistentes o ambiguas.
  - Validación AABB previa a la escritura para impedir overflow y solapamientos.
- **Evidencia manual:** Power BI Desktop confirmó canvas `1280 × 720`, cuatro KPI alineados, slicers correctamente distribuidos, gráficos inferiores sin solapamientos y la página `Análisis Detallado` con slicers, pie chart y tabla correctamente distribuidos. Se conservaron páginas, visuales, bindings e IDs, con datos reales y medidas funcionando.
- **Frontera:** el provider no calcula diseño; styling avanzado, temas, bookmarks, interacciones e integración con el agente permanecen fuera de alcance.

---

## 4. ESTADO ACTUAL Y FLUJO DE TRABAJO
El repositorio se encuentra estable, con pruebas automatizadas (`pytest`) pasando correctamente. El pipeline de evaluación comparativa evidencia que el Agente SIDAD puede auto-corregir errores simulados de validación y finalizar exitosamente los ciclos de las herramientas subyacentes.

### Comando Principal
`python run_powerbi.py`: Dispara el workflow estático actual sobre el dataset procesado: perfilado -> modelo semántico -> planificación -> layout -> exportación PBIP/TMDL/PBIR.

### Próximos Pasos de Desarrollo (Roadmap inminente):
1. **Fase 12.4:** integrar `export_to_powerbi` en `ToolRegistry` y en el flujo del Agente.
2. **Fase 12.5:** realizar la validación integral de cierre del dashboard completo tras las integraciones posteriores.
