# FASE 8: ORQUESTACIÓN E INTELIGENCIA (EL CEREBRO)

## 1. Objetivo
Transformar el conjunto de herramientas deterministas (Fases 1 a 7) en un Agente Inteligente autónomo. En lugar de ejecutar las herramientas en un orden secuencial estricto (pipeline), un modelo de lenguaje (LLM) decidirá dinámica y cíclicamente qué herramienta usar en función del estado de los datos.

## 2. Arquitectura de Orquestación

Se implementó un patrón de **Grafo de Estado Cíclico** (Cyclic State Graph) y **Self-Correction**.

### Componentes principales:
1. **AgentState (`src/agent/state.py`)**:
   - Mantiene el contexto global de la ejecución.
   - Almacena artefactos intermedios: `dataset_profile`, `transformation_logs`, `semantic_project`, `dashboard_plan`, `report_layout`, y los `critic_verdicts`.
   - Controla el límite de iteraciones (`max_iterations`).

2. **LLMProvider (`src/agent/llm_provider.py`)**:
   - Interfaz abstracta que define el contrato `predict_next_action`.
   - Devuelve un objeto estructurado `Decision` (Pydantic), con el nombre de la herramienta y sus argumentos.
   - Implementación simulada inicial: `MockLLMProvider` (útil para pruebas deterministas sin consumir cuotas de API).

3. **ToolRegistry (`src/agent/tool_registry.py`)**:
   - Actúa como la interfaz de seguridad y ejecución entre el Orquestador y las herramientas.
   - Inspecciona las firmas de las funciones (`inspect.signature`) para inyectar los argumentos generados por el LLM.
   - Posee **Guardrails** como la prevención de sobreescritura de la carpeta `data/raw/` y la detección de herramientas o argumentos inexistentes.

4. **Critic (`src/agent/critic.py`)**:
   - El evaluador interno del agente. 
   - Transforma los reportes de validación (ej. solapamientos del layout de Fase 7) en un `CriticVerdict`.
   - Si la validación falla, el Critic emite un `FAIL` con una acción recomendada para el LLM.

5. **Orchestrator (`src/agent/orchestrator.py`)**:
   - Es el bucle infinito controlado (hasta `max_iterations`).
   - Sigue el flujo: `LLM -> Decision -> ToolRegistry -> Tool -> State -> Critic -> Loop`.
   - Implementa un mecanismo de **Anti-Loop**: Si el LLM propone la misma herramienta y argumentos idénticos que fallaron en el paso anterior repetidas veces, el bucle se detiene para evitar ciclos infinitos.

## 3. Flujo de Decisión

El flujo ya no es rígido. El LLM puede decidir:
- Perfilar -> Limpiar -> Perfilar (para ver si la limpieza fue exitosa).
- Planificar -> Maquetar -> Validar -> Maquetar de nuevo (Self-Correction tras error visual).

## 4. Estado de Implementación
- **Estado**: COMPLETADO Y ESTABILIZADO.
- **Validación**: Probado exitosamente mediante el modo simulación (`MockLLMProvider`).
