# FASE 10: INFRAESTRUCTURA DE EVALUACIÓN EXPERIMENTAL

## 1. Objetivo
Establecer una infraestructura de pruebas sistemática y medible para la validación académica del Agente SIDAD en el contexto de una Tesis. El objetivo es proporcionar un entorno controlado que permita demostrar empíricamente el comportamiento adaptativo del agente mediante escenarios de fallo y recuperación (self-correction).

## 2. Implementación de la Batería Experimental

Se construyó el módulo `src/evaluation/evaluator.py`, el cual provee la clase `Evaluator`. Esta clase automatiza la ejecución del orquestador a través de 8 escenarios deterministas configurados.

### Escenarios Implementados:
1. `standard_success`: Ejecución nominal sin errores.
2. `tool_error`: Intento de uso de una herramienta inexistente.
3. `invalid_arguments`: Intento de pase de parámetros erróneos a una herramienta.
4. `max_iterations`: Interrupción forzada por el límite de iteraciones.
5. `anti_loop`: Activación del guardrail anti-bucle por decisiones idénticas.
6. `validation_failure`: Simulación de un fallo matemático de validación (overlapping).
7. `self_correction_success`: Ejecución completa demostrando el bucle Validator(FAIL) -> Critic -> LLM -> Generación -> Validator(PASS).
8. `finish_success`: Terminación explícita del pipeline.

### Métricas Académicas:
- **`status`**: Indica si el pipeline logró converger (`SUCCESS`) o fue abortado (`FAILED`).
- **`iterations`**: Iteraciones cognitivas totales.
- **`validation_failures`**: Cantidad de ocasiones en que el validador produjo un resultado de error.
- **`corrections_attempted`**: Intentos de corrección generados por el LLM tras un fallo.
- **`corrections_successful`**: Correcciones que pasaron exitosamente la re-validación.
- **`critical_validation_errors`**: Errores matemáticos de maquetación no resueltos al finalizar.
- **`operational_errors`**: Errores técnicos del entorno (ej. Timeouts, Cuotas, Límites de iteración).
- **`execution_time_seconds`**: El costo temporal (latencia).

## 3. Uso del Framework

Se provee el script en la raíz `run_evaluation.py`.

**Ejecución Simulada (Determinista para Trazabilidad):**
```bash
python run_evaluation.py --provider mock
```

El script exporta `docs/evaluation_report.json` que consolida todos los datos.

## 4. Limitaciones Restantes
- **Sin Comparador Estático**: Actualmente, la infraestructura no incluye una función de ejecución estática (pipeline rígido) para comparar su rendimiento contra el agente.
- **Simulación Aislada**: El caso de validación visual requiere *monkey-patching* en tiempo de evaluación debido a la desconexión actual de los algoritmos de maquetación profunda con los parámetros dinámicos.
