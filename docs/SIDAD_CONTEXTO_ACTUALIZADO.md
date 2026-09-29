# CONTEXTO INTEGRAL DEL PROYECTO SIDAD (ESTADO ACTUAL)

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

Este documento centraliza todo el contexto, arquitectura, evolución y estado actual del proyecto **SIDAD** (Sistema Inteligente para el Diseño Automatizado de Dashboards), reflejando desde los requerimientos iniciales hasta la implementación de la Fase 12.1.

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

---

## 4. ESTADO ACTUAL Y FLUJO DE TRABAJO
El repositorio se encuentra estable, con pruebas automatizadas (`pytest`) pasando correctamente. El pipeline de evaluación comparativa evidencia que el Agente SIDAD puede auto-corregir errores simulados de validación y finalizar exitosamente los ciclos de las herramientas subyacentes.

### Comando Principal
`python run_powerbi.py`: Dispara el workflow estático actual sobre el dataset procesado: perfilado -> modelo semántico -> planificación -> exportación estructural PBIP/TMDL.

### Próximos Pasos de Desarrollo (Roadmap inminente):
1. **Fase 12.2:** implementar la estructura PBIR completa: `report.json`, `version.json`, `pages/`, visuales y bindings visuales.
2. **Fase 12.3:** traducir `ReportLayout -> PBIR`, incluyendo canvas, posiciones, tamaños y orden visual.
3. **Fase 12.4:** integrar `export_to_powerbi` en `ToolRegistry` y en el flujo del Agente.
4. **Fase 12.5:** validar manualmente en Power BI Desktop el dashboard completo, incluyendo páginas, visuales, bindings y layout.
