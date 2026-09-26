# Fase 4: Planificación de Dashboard

## 1. Introducción
Una de las innovaciones principales de este agente inteligente es la automatización de la capa visual. En lugar de limitarse a exportar datos procesados, el sistema es capaz de abstraer, estructurar y planificar una propuesta visual completa (Páginas, Gráficos, Ejes, KPIs) antes de interactuar con cualquier motor de BI como Power BI.

## 2. Decisiones Arquitectónicas
- **Desacoplamiento Visual:** Implementamos los modelos `DashboardPlan`, `DashboardPage` y `VisualElement` (`src/models/dashboard.py`). Esto asegura que el diseño del reporte sea completamente agnóstico de la tecnología de presentación. 
- **Planificación Heurística y Determinista:** A través del `DashboardPlanner`, el sistema analiza el `SemanticProject` (creado en la Fase 3). Emplea lógicas heurísticas (ej. "Si hay una fecha y una métrica, propone un gráfico de líneas; si hay varias dimensiones categóricas, propone filtros y gráficos de barras top-N") para pre-construir el reporte. 
- **Estructuración Jerárquica:** Organiza los análisis por páginas (Ej. Resumen Ejecutivo vs. Análisis Detallado) priorizando las Cards/KPIs en la vista de alto nivel y Tablas/Pie Charts en vistas de detalle.

## 3. Lógica Implementada
1. Toma como input el modelo dimensional y los KPIs inferidos.
2. Decide automáticamente cuántas páginas generar.
3. Elige el tipo de gráfico ideal (`VisualType`) basado en los tipos de datos (X e Y).
4. Asigna descripciones para cada gráfico, manteniendo la trazabilidad ("Por qué se eligió este visual").
5. Entrega una estructura serializable (JSON) que un futuro componente de integración podrá traducir directamente a la API de Power BI.
