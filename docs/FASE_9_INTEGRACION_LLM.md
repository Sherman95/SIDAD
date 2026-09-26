# FASE 9 y 9.1: INTEGRACIÓN CON GEMINI LLM Y AUDITORÍA

## 1. Objetivo
Reemplazar el motor simulado (`MockLLMProvider`) por el modelo real cognitivo de **Google Gemini** mediante su API oficial, dotando al sistema SIDAD de una toma de decisiones real, adaptativa y basada en lenguaje natural.

## 2. Implementación de Gemini Provider (`src/agent/gemini_provider.py`)

Se construyó el adaptador `GeminiLLMProvider` utilizando la librería oficial `google-genai`.

### Características:
- **Zero-Shot & Few-Shot Prompting**: El Agente recibe un prompt dinámico (`_build_prompt`) que inyecta todo el `AgentState` serializado (resumen del perfilado, cantidad de errores, historial de transformaciones, y artefactos actuales).
- **JSON Force output**: Gemini fue restringido algorítmicamente para responder *exclusivamente* con una estructura JSON coincidente con el modelo `Decision` de Pydantic. Se omitieron llamadas a funciones (Function Calling) directas complejas debido a las restricciones de la API actual, optando por validación de esquemas JSON robusta.
- **Protección de Credenciales**: Se utiliza `python-dotenv` para leer la llave desde el archivo `.env` local, el cual se excluyó del control de versiones (`.gitignore`).

## 3. Auditoría y Endurecimiento (Fase 9.1)

Durante las pruebas se detectaron y corrigieron vulnerabilidades operativas en relación al trato con un LLM real:
1. **Control de Cuota (Error 429)**: Al utilizar el Free-Tier de Gemini, el agente puede agotar sus llamadas. Se construyó un recolector de excepciones que categoriza el estado como `LLM_QUOTA_ERROR`, rompiendo el ciclo sanamente (FAILED) sin activar inútilmente el mecanismo Anti-Loop del orquestador.
2. **Contexto Rico**: El modelo Gemini inicializaba limpiezas a ciegas. Se enriqueció el constructor de prompts para que Gemini pueda "ver" cuántos nulos y duplicados reportó el Profiler de la Fase 1.
3. **Mecanismo de Parada (`finish`)**: Se inyectó una "herramienta virtual" llamada `finish` en el prompt. Gemini es instruido a utilizarla únicamente cuando la última iteración del layout resultó en `PASS` por parte de los heurísticos de validación.
4. **Self-Correction Comprobado**: Mediante el `MockLLMProvider` se aisló y demostró algorítmicamente que el Orquestador es capaz de detenerse tras una maquetación corrupta, el Critic reporta el `FAIL`, y en el siguiente ciclo el LLMProvider genera una decisión correctiva en base a este veredicto.

## 4. Reportes de Observabilidad
El `run_agent.py` evolucionó a una CLI robusta que permite inyectar `--provider mock` o `--provider gemini`. Al finalizar, se despliega un reporte exhaustivo:
- Iteraciones utilizadas vs máximas.
- Ratio de fallos críticos.
- Herramientas ejecutadas en orden cronológico con sus justificaciones cognitivas.
- Errores operativos subyacentes.

## 5. Estado de Implementación
- **Estado**: COMPLETADO Y ESTABILIZADO.
- **Validación**: El Pipeline principal fue comprobado; Gemini generó decisiones precisas (`profile` -> `clean` con parámetros correctos) antes de detenerse controladamente por límite de peticiones de capa gratuita.
