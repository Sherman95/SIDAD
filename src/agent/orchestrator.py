import json
from src.agent.state import AgentState, ActionRecord
from src.agent.tool_registry import ToolRegistry
from src.agent.llm_provider import LLMProvider
from src.agent.critic import Critic

# Parsers para inyectar la salida JSON de las tools en los modelos Pydantic del Estado
from src.models.profiling import DiagnosticResult, DatasetProfile
from src.models.semantic_model import SemanticProject
from src.models.dashboard import DashboardPlan
from src.models.report_layout import ReportLayout
from src.agent.validator import ValidationReport

class Orchestrator:
    """
    Cerebro Central del Agente SIDAD.
    Mantiene un bucle dinámico (ReAct): Razonamiento -> Ejecución -> Observación -> Crítica -> Corrección.
    """
    def __init__(self, llm: LLMProvider, registry: ToolRegistry, critic: Critic):
        self.llm = llm
        self.registry = registry
        self.critic = critic

    def run(self, state: AgentState) -> AgentState:
        while state.status == "IN_PROGRESS":
            # 1. Guardrail: Límite de Iteraciones
            if state.iteration_count >= state.max_iterations:
                state.status = "FAILED"
                state.pending_issues.append(f"Se superó el límite máximo de iteraciones ({state.max_iterations}).")
                break

            # 2. Guardrail: Detección de bucles (Loop Infinito)
            if len(state.execution_history) >= 3:
                last_3 = state.execution_history[-3:]
                # Si falló 3 veces seguidas en la misma herramienta
                if all(a.is_error for a in last_3) and last_3[0].tool_name == last_3[1].tool_name == last_3[2].tool_name:
                    state.status = "FAILED"
                    state.pending_issues.append(f"Bucle atascado detectado en herramienta: {last_3[0].tool_name}.")
                    break

            # 3. Toma de Decisión (El LLM observa el estado y los errores previos)
            available_tools = self.registry.get_available_tools_info()
            decision = self.llm.predict_next_action(state, available_tools)

            # 4. Condición de Parada Explícita
            if decision.tool_name == "finish":
                # Guardrail: Solo terminar si no hay errores críticos pendientes y tenemos el layout
                if not state.report_layout:
                    self._record_error(state, "finish", "No se puede finalizar. Falta el Report Layout.", decision.operational_reason)
                    continue
                if any(v.status == "FAIL" for v in state.critic_verdicts):
                    self._record_error(state, "finish", "No se puede finalizar con errores de Critic pendientes.", decision.operational_reason)
                    continue
                
                state.status = "SUCCESS"
                break

            # 5. Ejecución Segura
            is_error, result_str = self.registry.execute(decision.tool_name, decision.arguments)
            
            # 6. Registro de Acción en el Historial (Trazabilidad)
            record = ActionRecord(
                step=state.iteration_count + 1,
                tool_name=decision.tool_name,
                arguments=decision.arguments,
                operational_reason=decision.operational_reason,
                result_summary=result_str[:250] + ("..." if len(result_str) > 250 else ""),
                is_error=is_error
            )
            state.execution_history.append(record)
            state.last_tool_result = record.result_summary

            # 7. Si fue exitoso, parsear el output hacia el Estado Tipado
            if not is_error:
                self._update_state_from_tool(state, decision.tool_name, result_str)

            # 8. Fase de Crítica (Self-Correction loop)
            state.critic_verdicts = self.critic.evaluate(state)
            
            # Limpieza del Validation Report para la siguiente iteración si el critic falló,
            # obligando a re-validar tras la corrección.
            if any(v.status == "FAIL" for v in state.critic_verdicts) and state.validation_report:
                 state.validation_report = None # Invalida el caché

            state.iteration_count += 1

        return state

    def _record_error(self, state, tool_name, error_msg, reason):
        record = ActionRecord(
            step=state.iteration_count + 1,
            tool_name=tool_name,
            arguments={},
            operational_reason=reason,
            result_summary=error_msg,
            is_error=True
        )
        state.execution_history.append(record)
        state.iteration_count += 1

    def _update_state_from_tool(self, state: AgentState, tool_name: str, result_json: str):
        """Traduce la salida JSON determinista de la herramienta a la Memoria del Agente (AgentState)"""
        try:
            if tool_name == "profile_dataset":
                # El profiler devuelve un DiagnosticResult completo (profile + errors)
                state.dataset_profile = DiagnosticResult.model_validate_json(result_json)
            elif tool_name == "clean_dataset":
                import json
                from src.models.transformations import TransformationLog
                logs_json = json.loads(result_json)
                state.transformation_logs = [TransformationLog(**l) for l in logs_json] 
            elif tool_name == "build_semantic_model":
                state.semantic_project = SemanticProject.model_validate_json(result_json)
            elif tool_name == "create_dashboard_plan":
                state.dashboard_plan = DashboardPlan.model_validate_json(result_json)
            elif tool_name == "generate_layout":
                state.report_layout = ReportLayout.model_validate_json(result_json)
            elif tool_name == "validate_layout":
                state.validation_report = ValidationReport.model_validate_json(result_json)
        except Exception as e:
            # Si el JSON no matchea Pydantic, se registra el error
            self._record_error(state, tool_name, f"Fallo parseando salida a Pydantic: {str(e)}", "Internal Parse Error")
