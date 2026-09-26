# Fase 7: Validación Visual

## 1. Introducción
Construir un dashboard visualmente deficiente derrota el propósito del análisis de datos. En el paradigma de Agentes Autónomos, no basta con generar un reporte; es indispensable garantizar que la interfaz resultante sea utilizable antes de presentarla al usuario final (Sección 18 del Contexto Maestro). 

## 2. Decisiones Arquitectónicas
- **Validación Determinista (Bounding Boxes):** Dado que en el MVP no disponemos de un entorno de renderizado con un Critic visual humano o basado en Computer Vision (Multimodal LLM), se optó por un enfoque algorítmico robusto. La clase `LayoutValidator` evalúa el `ReportLayout` de forma matemática, inspeccionando las posiciones (`x`, `y`) y dimensiones (`width`, `height`) de cada elemento.
- **Detección de Colisiones (AABB):** Se implementó el algoritmo de cajas delimitadoras (Axis-Aligned Bounding Box) para encontrar superposiciones entre gráficos, previniendo errores graves de maquetación.
- **Reglas Heurísticas de UX/UI:**
  1. Prevención de Ilegibilidad: Elementos extremadamente pequeños son marcados como Error.
  2. Detección de Desbordamiento (Overflow): Gráficos que superan el tamaño máximo del lienzo (1280x720).
  3. Desperdicio de Espacio: Si menos del 20% de la página está siendo utilizado, se lanza un Warning para sugerir al Agente Planner un rediseño de la jerarquía visual.

## 3. Lógica Implementada
1. El Agente somete su plano maestro (`ReportLayout`) al `LayoutValidator`.
2. El validador escanea secuencialmente página por página y compara cada componente contra todos los demás.
3. Se devuelve un objeto estricto `ValidationReport` que indica `is_valid` y un listado de problemas. En la **Fase 8**, este reporte alimentará el componente de Self-Correction para generar bucles de auto-mejora sin intervención humana.
