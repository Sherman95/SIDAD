# Fase 6: Generación Automática de Páginas y Visuales

## 1. Introducción
Mientras que la Fase 4 estructuró "qué" mostrar (El Plan Analítico), la Fase 6 resuelve el "cómo" y "dónde" mostrarlo. Para cumplir el objetivo de automatizar de extremo a extremo la construcción del dashboard, el sistema debe tomar decisiones sobre la arquitectura visual y experiencia de usuario (UX/UI Analítica).

## 2. Decisiones Arquitectónicas
- **Aislamiento de Lógica (Layout Engine):** Se creó el modelo `ReportLayout` que abstrae un lienzo físico (Canvas) con coordenadas absolutas (`x`, `y`, `width`, `height`). Esto evita acoplar el diseño conceptual del reporte con el motor gráfico final.
- **Deducción de Diseño Espacial:** La herramienta `ReportGenerator` implementa heurísticas deterministas clásicas de diseño de dashboards:
  1. Reserva espacio en la cabecera para títulos y filtros globales (`slicers`).
  2. Identifica los indicadores clave (`VisualType.CARD`) y los agrupa en una cuadrícula (grid) horizontal en la parte superior, dado que son la métrica principal.
  3. Distribuye uniformemente los gráficos restantes (Barras, Líneas, etc.) en un arreglo de 2 columnas. Si hay un número impar de gráficos, el último ocupa el ancho completo para evitar vacíos visuales.
- **Resolución Estándar:** Se adoptó la resolución estándar de la industria 16:9 (`1280x720` píxeles) como lienzo de trabajo, garantizando proporciones coherentes antes de exportar.

## 3. Lógica Implementada
1. Iteración sobre cada página del `DashboardPlan`.
2. Asignación secuencial de coordenadas y dimensiones (`PlacedVisual`) mediante cálculos matemáticos relativos al lienzo.
3. Empaquetado final en un objeto tipado (Pydantic), preparado para ser renderizado por una librería de front-end (ej. React/Next.js) o inyectado en el `report.json` de un PBIP de Power BI.
