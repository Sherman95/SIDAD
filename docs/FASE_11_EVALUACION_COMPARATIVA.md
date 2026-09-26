# Fase 11: Evaluación Comparativa del Agente SIDAD

## 1. Objetivo
El objetivo de esta fase es comparar experimentalmente y de forma reproducible el pipeline determinista original (Static Pipeline) frente al nuevo enfoque basado en agentes (Agent Pipeline) de SIDAD. La evaluación busca identificar de forma neutral en qué métricas difieren ambos enfoques frente a los mismos escenarios y datos.

## 2. Hipótesis Experimental
Se postula que un pipeline rígidamente secuencial fallará irremediablemente frente a desviaciones no contempladas en tiempo de desarrollo (como errores operativos en la declaración de argumentos o problemas de validación semántico-visuales). Por otro lado, un pipeline basado en agentes con capacidad iterativa debería detectar, aislar y corregir un subconjunto de estos errores gracias a su mecanismo de *Critic* y auto-corrección, incrementando la tasa de éxito final a costa de un aumento en el número de iteraciones.

## 3. Sistemas Comparados
1. **Static Pipeline**: Implementación rígida que ejecuta secuencialmente: `profile -> clean -> semantic -> plan -> generate_layout -> validate_layout`. Cualquier error intermedio aborta la ejecución inmediatamente. No posee ciclo de *Critic*.
2. **SIDAD Agent Pipeline**: Orquestador autónomo que utiliza el `MockLLMProvider` (o Gemini en producción) para razonar sobre qué herramienta ejecutar a continuación basándose en el historial de eventos (`execution_history`), evaluando los resultados a través del `Critic`.

## 4. Datasets y Escenarios
Se utilizaron datos reales provenientes de `data/raw/ventas_test.csv` (con nulos e inconsistencias introducidas) para simular situaciones de negocio verosímiles.

Se definieron 4 escenarios estructurados evaluados en 3 repeticiones (12 ejecuciones por proveedor, 24 en total):
1. **Dataset Nominal**: Flujo estándar sin fallos provocados.
2. **Dataset con Problemas de Calidad**: Validación de la resiliencia base de las herramientas ante nulos y duplicados (ambos enfoques lo logran porque las herramientas internamente manejan esto).
3. **Problema de Layout**: Se indujo una colisión geométrica forzada en el lienzo del dashboard (Columnas > 100).
4. **Error Operativo**: Se forzó la ejecución de herramientas inexistentes o con argumentos erróneos para validar el manejo de fallos fatales de orquestación.

## 5. Metodología
Las evaluaciones se ejecutaron bajo el motor de inyección de Mock (`MockLLMProvider` y control de escenarios en `StaticPipeline`) para garantizar un comportamiento 100% determinista y reproducible independientemente de variaciones de cuota, latencia de red o temperatura del LLM. Esto aísla la variable de "Arquitectura" (Agente vs Estático). 

Los escenarios se ejecutan a través de `run_comparison.py`, produciendo un reporte exportado a `comparison_report.json`.

## 6. Resultado Observado
Basado en las 3 repeticiones reproducibles (Promedios):

| Métrica | Static Pipeline | SIDAD Agent |
| :--- | :---: | :---: |
| **Tasa de Éxito (`success_rate`)** | 50.0% | 75.0% |
| **Fallos de Validación (`avg_validation_failures`)** | 0.25 | 0.25 |
| **Correcciones Intentadas (`avg_corrections_attempted`)** | 0.00 | 0.25 |
| **Correcciones Exitosas (`avg_corrections_successful`)** | 0.00 | 0.25 |
| **Errores Críticos Restantes (`avg_critical_validation_errors`)**| 0.25 | 0.00 |
| **Errores Operativos no resueltos (`avg_operational_errors`)** | 0.50 | 0.25 |
| **Promedio de Iteraciones (`avg_iterations`)** | 4.75 | 5.75 |

En las ejecuciones se observó que frente al `Escenario 3` (Problemas de Layout), el pipeline estático se detuvo y contabilizó un error crítico restante, mientras que el pipeline del agente generó un intento de corrección exitoso.

## 7. Interpretación
Los resultados observados sugieren que el enfoque basado en agente es capaz de reaccionar frente a desviaciones específicas (como el fallo de layout). El comportamiento registrado muestra que el ciclo de validación y crítica permite al sistema ajustar los parámetros de generación y emitir un nuevo layout válido, llevando su tasa de errores críticos finales a 0.0 en ese escenario.
Esto es consistente con la capacidad de autocorrección planteada en la hipótesis. Sin embargo, este comportamiento conlleva un costo operativo reflejado en el incremento promedio de iteraciones necesarias para completar la tarea (5.75 frente a 4.75).

## 8. Limitaciones
* El LLM utilizado en la comparación reproducible es Mock.
* El Mock es determinista.
* Solo se evaluaron 4 escenarios.
* Se realizaron 3 repeticiones por escenario.
* Las repeticiones con Mock no representan variabilidad real de un LLM.
* No se realizó una prueba estadística de significancia.
* Por lo tanto, los resultados NO permiten afirmar superioridad estadística general.
* La autocorrección demostrada corresponde al entorno experimental controlado de Fase 10.1/11.
