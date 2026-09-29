import json
import time
from src.agent.state import AgentState, ActionRecord
from src.agent.tool_registry import ToolRegistry
from src.models.profiling import DiagnosticResult
from src.models.semantic_model import SemanticProject
from src.models.dashboard import DashboardPlan
from src.models.report_layout import ReportLayout
from src.agent.validator import ValidationReport
from src.models.transformations import TransformationLog

class StaticPipeline:
    """
    Representa el flujo rígido tradicional (sin agente).
    Ejecuta las herramientas en un orden hardcodeado y se detiene si hay un error o si la validación falla.
    No hay Critic ni Self-Correction.
    """
    def __init__(self, registry: ToolRegistry, scenario: str = "standard"):
        self.registry = registry
        self.scenario = scenario

    def _record(self, state: AgentState, tool_name: str, arguments: dict, is_error: bool, result_str: str, reason: str):
        record = ActionRecord(
            step=state.iteration_count + 1,
            tool_name=tool_name,
            arguments=arguments,
            operational_reason=reason,
            result_summary=result_str[:250] + ("..." if len(result_str) > 250 else ""),
            is_error=is_error
        )
        state.execution_history.append(record)
        state.last_tool_result = record.result_summary
        state.iteration_count += 1

    def run(self, state: AgentState) -> AgentState:
        state.status = "IN_PROGRESS"
        
        # 1. Profile
        tool = "profile_dataset"
        args = {"file_path": state.input_dataset_path}
        
        if self.scenario == "tool_error":
            # Forzamos error operativo simulado
            tool = "tool_inexistente"
            args = {}
            
        if self.scenario == "invalid_arguments":
            args = {"bad_arg": 1}
            
        is_err, res = self.registry.execute(tool, args)
        self._record(state, tool, args, is_err, res, "Ejecución estática: Perfilado")
        if is_err:
            state.status = "FAILED"
            state.pending_issues.append(f"Error operativo en {tool}")
            return state
            
        try:
            state.dataset_profile = DiagnosticResult.model_validate_json(res)
        except:
            state.status = "FAILED"
            state.pending_issues.append("Error parseando perfil")
            return state

        # 2. Clean
        tool = "clean_dataset"
        actions = [
            {"action": "remove_duplicates"},
            {"action": "fill_nulls", "column": "categoria", "value": "Desconocido"}
        ]
        # Inyectar problema de dataset en Escenario 2 
        # (Aunque el dataset ya puede tener problemas, Static Pipeline igual ejecuta esto rígidamente)
        args = {"input_path": state.input_dataset_path, "output_path": "data/processed/ventas_limpio_static.csv", "actions": actions}
        
        is_err, res = self.registry.execute(tool, args)
        self._record(state, tool, args, is_err, res, "Ejecución estática: Limpieza")
        if is_err:
            state.status = "FAILED"
            state.pending_issues.append("Error operativo en clean_dataset")
            return state
        state.processed_dataset_path = args["output_path"]
        try:
            logs_json = json.loads(res)
            state.transformation_logs = [TransformationLog(**l) for l in logs_json]
        except:
            pass

        # 3. Semantic Model
        tool = "build_semantic_model"
        args = {
            "diagnostic_json": state.dataset_profile.model_dump_json(),
            "source_path": state.processed_dataset_path,
        }
        is_err, res = self.registry.execute(tool, args)
        self._record(state, tool, args, is_err, res, "Ejecución estática: Modelado")
        if is_err:
            state.status = "FAILED"
            state.pending_issues.append("Error operativo en build_semantic_model")
            return state
        state.semantic_project = SemanticProject.model_validate_json(res)

        # 4. Dashboard Plan
        tool = "create_dashboard_plan"
        args = {"semantic_project_json": state.semantic_project.model_dump_json()}
        is_err, res = self.registry.execute(tool, args)
        self._record(state, tool, args, is_err, res, "Ejecución estática: Planificación")
        if is_err:
            state.status = "FAILED"
            state.pending_issues.append("Error operativo en create_dashboard_plan")
            return state
        state.dashboard_plan = DashboardPlan.model_validate_json(res)

        # 5. Generate Layout
        tool = "generate_layout"
        columns = 2
        if self.scenario in ["validation_failure", "layout_problem"]:
            columns = 100
        args = {"dashboard_plan_json": state.dashboard_plan.model_dump_json(), "columns": columns}
        is_err, res = self.registry.execute(tool, args)
        self._record(state, tool, args, is_err, res, "Ejecución estática: Maquetación")
        if is_err:
            state.status = "FAILED"
            state.pending_issues.append("Error operativo en generate_layout")
            return state
        state.report_layout = ReportLayout.model_validate_json(res)

        # 6. Validate Layout
        tool = "validate_layout"
        args = {"layout_json": state.report_layout.model_dump_json()}
        is_err, res = self.registry.execute(tool, args)
        self._record(state, tool, args, is_err, res, "Ejecución estática: Validación")
        if is_err:
            state.status = "FAILED"
            state.pending_issues.append("Error operativo en validate_layout")
            return state
        
        state.validation_report = ValidationReport.model_validate_json(res)
        
        if not state.validation_report.is_valid:
            state.status = "FAILED"
            state.pending_issues.append("Fallo de validación detectado por pipeline rígido (sin capacidad de corrección)")
            return state
            
        state.status = "SUCCESS"
        return state
