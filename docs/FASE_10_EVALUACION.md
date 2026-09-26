# FASE 10: EVALUACIÓN EXPERIMENTAL

## 1. Objetivo
Establecer un framework de pruebas sistemático y medible para la validación académica del Agente SIDAD en el contexto de una Tesis. El objetivo es comparar cuantitativa y cualitativamente la aproximación estática (pipelines rígidos) vs el agente adaptativo.

## 2. Implementación de la Batería Experimental

Se construyó el módulo `src/evaluation/evaluator.py`, el cual provee la clase `Evaluator`. Esta clase automatiza la ejecución del orquestador a través de múltiples escenarios y recolecta métricas en tiempo de ejecución.

### Métricas de Observabilidad Académica:
- **`status`**: Indica si el pipeline logró converger (`SUCCESS`) o falló (`FAILED`).
- **`iterations`**: Cuántas iteraciones cognitivas tomó el agente para resolver el problema.
- **`tools_used`**: Número de herramientas efectivamente ejecutadas con éxito.
- **`corrections_made`**: Número de veces que el `Critic` abortó el proceso por un Layout inválido, forzando un *Self-Correction*. Demuestra la adaptabilidad del sistema.
- **`critical_errors`**: Errores no resueltos al finalizar.
- **`execution_time_seconds`**: El costo temporal (latencia).
- **`provider_error`**: Tipificación de fallos externos como límites de cuota (`LLM_QUOTA_ERROR`) o trabas cognitivas (`ANTI_LOOP`).

## 3. Uso del Framework

Se provee el script en la raíz `run_evaluation.py`, el cual levanta una batería de escenarios (`AgentState` preconfigurados) y los despacha al evaluador.

**Ejecución Simulada:**
```bash
python run_evaluation.py --provider mock
```
**Ejecución Real:**
```bash
python run_evaluation.py --provider gemini
```

El script genera un archivo `docs/evaluation_report.json` que consolida todos los datos, listos para ser injertados en Pandas, Jupyter o Power BI para la redacción de la tesis final.

## 4. Estado de Implementación
- **Estado**: COMPLETADO.
- **Validación**: Batería funcional ejecutada bajo Mock. En una etapa productiva, se inyectarán datasets variados (con distintos grados de ruido y volúmenes de datos) para enriquecer la comparativa de la tesis.
