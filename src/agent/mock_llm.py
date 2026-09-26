from src.agent.llm_provider import LLMProvider, Decision
from src.agent.state import AgentState

class MockLLMProvider(LLMProvider):
    """
    Motor de razonamiento simulado. 
    Observa el estado real (Pydantic models) y decide la siguiente herramienta lógicamente.
    Permite probar el ciclo de decisión, validación y corrección sin consumir una API.
    """
    def __init__(self, simulate_fail=False, scenario="standard"):
        # Si simulate_fail es True, el layout se genera intencionalmente corrupto para disparar el critic
        self.simulate_fail = simulate_fail
        self.scenario = scenario
        self.has_failed_once = False

    def predict_next_action(self, state: AgentState, available_tools: list[dict]) -> Decision:
        if self.scenario == "tool_error":
            return Decision(tool_name="tool_inexistente", arguments={}, operational_reason="Simulando herramienta falsa")
        if self.scenario == "invalid_arguments":
            return Decision(tool_name="clean_dataset", arguments={"bad_arg": 1}, operational_reason="Simulando argumentos falsos")
        if self.scenario == "anti_loop":
            return Decision(tool_name="profile_dataset", arguments={"file_path": "data/raw/ventas_test.csv"}, operational_reason="Bucle infinito")

        # Lógica de decisión dinámica basada en los artefactos presentes en AgentState
        
        # 1. ¿Tenemos el perfilado?
        if not state.dataset_profile:
            return Decision(
                tool_name="profile_dataset",
                arguments={"file_path": state.input_dataset_path},
                operational_reason="Se ejecutó el perfilado para identificar tipos de datos, valores faltantes y posibles anomalías."
            )
            
        # 2. ¿Hubo limpieza? (Asumimos que la limpia si detecta problemas, lo cual sabemos que hay)
        if len(state.transformation_logs) == 0:
            actions = [
                {"action": "remove_duplicates"},
                {"action": "fill_nulls", "column": "categoria", "value": "Desconocido"},
                {"action": "fill_nulls", "column": "cantidad", "value": "1"}
            ]
            return Decision(
                tool_name="clean_dataset",
                arguments={"input_path": state.input_dataset_path, "output_path": "data/processed/ventas_limpio.csv", "actions": actions},
                operational_reason="Se decidió limpiar nulos de categoría y duplicados basados en el perfilado. No se imputan fechas por seguridad analítica."
            )
            
        # 3. ¿Tenemos modelo semántico?
        if not state.semantic_project:
            return Decision(
                tool_name="build_semantic_model",
                arguments={"diagnostic_json": state.dataset_profile.model_dump_json()},
                operational_reason="Se construyó el modelo semántico para abstraer Dimensiones, Métricas y sugerir KPIs."
            )
            
        # 4. ¿Tenemos Plan de Dashboard?
        if not state.dashboard_plan:
            return Decision(
                tool_name="create_dashboard_plan",
                arguments={"semantic_project_json": state.semantic_project.model_dump_json()},
                operational_reason="Se planificó la estructura lógica de páginas y gráficos del Dashboard."
            )
            
        # 5. ¿Tenemos Layout Generado?
        if not state.report_layout:
            columns = 2
            # Simulamos un fallo (Layout corrupto) la primera vez
            if (self.simulate_fail or self.scenario == "validation_failure" or self.scenario == "self_correction_success") and not self.has_failed_once:
                columns = 100 # Esto causará over-saturation o solapamientos garantizados
                self.has_failed_once = True
                reason = "Generando maquetación inicial con 100 columnas (Probablemente falle la UX)."
                if self.scenario == "validation_failure":
                    # For self_correction_success we want it to recover. For validation_failure we might want it to stop?
                    # The prompt didn't specify exactly, but simulate_fail causes it to fail once.
                    pass
            else:
                reason = "Generando maquetación física basada en las páginas planificadas."
                
            return Decision(
                tool_name="generate_layout",
                arguments={"dashboard_plan_json": state.dashboard_plan.model_dump_json(), "columns": columns},
                operational_reason=reason
            )
            
        # 6. Evaluar el veredicto del Critic (Self-Correction)
        if state.critic_verdicts and any(v.status == "FAIL" for v in state.critic_verdicts):
            # El LLM reacciona al fallo del Critic
            return Decision(
                tool_name="generate_layout",
                arguments={"dashboard_plan_json": state.dashboard_plan.model_dump_json(), "columns": 2},
                operational_reason="Corrección: Se regenera el Layout con 2 columnas tras detectar solapamientos/saturación por el Critic."
            )

        # 7. ¿Está validado?
        if not state.validation_report:
            return Decision(
                tool_name="validate_layout",
                arguments={"layout_json": state.report_layout.model_dump_json()},
                operational_reason="Ejecutando validación de AABB y reglas heurísticas sobre el lienzo visual."
            )
            
        # 8. Si todo está perfecto, terminamos
        return Decision(
            tool_name="finish",
            arguments={},
            operational_reason="El dataset fue procesado, modelado, planificado y validado exitosamente sin errores críticos remanentes."
        )
