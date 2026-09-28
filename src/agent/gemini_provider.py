import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

from src.agent.llm_provider import LLMProvider, Decision
from src.agent.state import AgentState

load_dotenv()

class GeminiLLMProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY no encontrada en el entorno (.env).")
            
        self.client = genai.Client(api_key=api_key)

    def predict_next_action(self, state: AgentState, available_tools: list[dict]) -> Decision:
        prompt = self._build_prompt(state, available_tools)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                ),
            )
            
            data = json.loads(response.text)
            decision = Decision.model_validate(data)
            return decision
            
        except ValidationError as ve:
            # Error controlado: Gemini devolvió algo que no matchea el schema Decision
            return Decision(
                tool_name="ERROR",
                arguments={},
                operational_reason=f"Gemini API Error: Respuesta inválida del modelo. {str(ve)}"
            )
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower() or "exhausted" in error_str.lower():
                return Decision(
                    tool_name="ERROR",
                    arguments={},
                    operational_reason=f"LLM_QUOTA_ERROR: {error_str}"
                )
            # Errores HTTP, timeout, API Key inválida, etc.
            return Decision(
                tool_name="ERROR",
                arguments={},
                operational_reason=f"LLM_API_ERROR: {error_str}"
            )

    def _build_prompt(self, state: AgentState, available_tools: list[dict]) -> str:
        prompt = f"""
Eres el Agente SIDAD (Sistema Inteligente para Automatización de Dashboards).
Tu trabajo es analizar un dataset, prepararlo, construir un modelo semántico, diseñar un dashboard, maquetarlo, validarlo visualmente y finalizar de forma inteligente.

REGLA FUNDAMENTAL: Nunca modificas archivos directamente ni ejecutas código Python directamente.
Tu única labor es decidir qué herramienta ejecutar basándote en el Estado actual del Agente. El Orchestrator ejecutará tu decisión.
Si no estás seguro de una transformación peligrosa, utiliza una estrategia segura o ignórala.

--- HERRAMIENTAS DISPONIBLES ---
{json.dumps(available_tools, indent=2)}

Además de las listadas, existe una herramienta virtual de control:
- "finish": Utilízala SOLO cuando la última validación del layout (Critic) haya sido PASS y el reporte esté listo. Si hay errores del Critic pendientes, DEBES ejecutar acciones correctivas antes de finalizar.

--- ESTADO ACTUAL DEL AGENTE ---
User Request: {state.user_request}
Current Goal: {state.current_goal}
OBLIGATORIO: La ruta del dataset de entrada que debes procesar es EXACTAMENTE: '{state.input_dataset_path.replace(chr(92), "/")}'
Iteration Count: {state.iteration_count} / {state.max_iterations}

Artefactos disponibles (Metadatos):
- Profile: {"SÍ" if state.dataset_profile else "NO"}"""
        
        if state.dataset_profile:
            prompt += f"\n  -> Filas: {state.dataset_profile.profile.row_count}, Columnas: {state.dataset_profile.profile.column_count}"
            prompt += f"\n  -> Duplicados: {state.dataset_profile.profile.duplicate_rows}"
            prompt += f"\n  -> Problemas detectados: {state.dataset_profile.problems_detected}"
            
        prompt += f"\n- Acciones de Limpieza Hechas: {len(state.transformation_logs)}"
        if state.transformation_logs:
            prompt += f"\n  -> Últimas acciones: {[log.action for log in state.transformation_logs[-3:]]}"
            
        prompt += f"""
- Modelo Semántico: {"SÍ" if state.semantic_project else "NO"}
- Plan Dashboard: {"SÍ" if state.dashboard_plan else "NO"}
- Layout Reporte: {"SÍ" if state.report_layout else "NO"}
- Validación Layout: {"SÍ" if state.validation_report else "NO"} (Válido: {state.validation_report.is_valid if state.validation_report else 'N/A'})

--- CRITIC VERDICTS PENDIENTES (Resultados de validación) ---
"""
        if state.critic_verdicts:
            for cv in state.critic_verdicts:
                prompt += f"[{cv.status}] {cv.severity}: {cv.issue} | Recomendación: {cv.recommended_action}\n"
        else:
            prompt += "No hay críticas de diseño o validaciones fallidas pendientes.\n"
            
        prompt += f"""
--- HISTORIAL DE EJECUCIÓN (Últimas 5 acciones) ---
"""
        for a in state.execution_history[-5:]:
            status = "ERROR" if a.is_error else "OK"
            prompt += f"Step {a.step} | Tool: {a.tool_name} [{status}] | Result: {a.result_summary}\n"

        prompt += """
Analiza los datos, elige inteligentemente tu próxima 'tool_name', asigna 'arguments' válidos (un diccionario con los parámetros requeridos), y explica tu 'operational_reason'.
DEBES responder EXACTAMENTE con un objeto JSON con este formato:
{
  "tool_name": "nombre_de_la_herramienta",
  "arguments": {
    "param1": "valor"
  },
  "operational_reason": "Justificación de tu decisión basada en el contexto."
}
"""
        return prompt
