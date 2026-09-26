import json
import time
from typing import List, Dict, Any
from pydantic import BaseModel
from src.agent.state import AgentState
from src.agent.orchestrator import Orchestrator

class EvaluationMetric(BaseModel):
    scenario_name: str
    provider: str
    status: str
    iterations: int
    tools_used: int
    validation_failures: int
    corrections_attempted: int
    corrections_successful: int
    critical_validation_errors: int
    operational_errors: int
    final_pending_issues: list[str]
    execution_time_seconds: float
    provider_error: str = "NONE"

class Evaluator:
    """
    Framework de evaluación experimental para comparar el rendimiento
    del Agente SIDAD en diferentes escenarios de datos.
    """
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.metrics: List[EvaluationMetric] = []

    def run_scenario(self, scenario_name: str, initial_state: AgentState, provider: str = "mock") -> EvaluationMetric:
        print(f"\n[Evaluator] Ejecutando escenario: {scenario_name}")
        start_time = time.time()
        
        final_state = self.orchestrator.run(initial_state)
        
        end_time = time.time()
        
        # Calcular métricas precisas
        validation_failures = 0
        corrections_attempted = 0
        corrections_successful = 0
        in_correction_mode = False
        
        for action in final_state.execution_history:
            if action.tool_name == "validate_layout":
                res_str = str(action.result_summary).lower()
                # Orchestrator truncates to 250 chars, so json.loads will likely fail
                # But 'is_valid": false' will be in the first few chars
                is_false = '"is_valid":false' in res_str.replace(" ", "")
                
                if action.is_error or is_false:
                    validation_failures += 1
                    in_correction_mode = True
                else:
                    if in_correction_mode:
                        corrections_successful += 1
                        in_correction_mode = False
            elif action.tool_name == "generate_layout" and in_correction_mode:
                corrections_attempted += 1

        # Separación de errores remanentes
        critical_validation_errors = len([v for v in final_state.critic_verdicts if v.status == "FAIL"])
        operational_errors = len(final_state.pending_issues)
        
        # Determinar fallos de proveedor (ej. Quota limit)
        quota_errors = [a for a in final_state.execution_history if a.tool_name == "LLM_QUOTA_ERROR"]
        provider_err = "NONE"
        if quota_errors:
            provider_err = "LLM_QUOTA_ERROR"
        elif "límite máximo" in str(final_state.pending_issues):
            provider_err = "MAX_ITERATIONS"
        elif "Bucle atascado" in str(final_state.pending_issues):
            provider_err = "ANTI_LOOP"
            
        metric = EvaluationMetric(
            scenario_name=scenario_name,
            provider=provider,
            status=final_state.status,
            iterations=final_state.iteration_count,
            tools_used=len(final_state.execution_history),
            validation_failures=validation_failures,
            corrections_attempted=corrections_attempted,
            corrections_successful=corrections_successful,
            critical_validation_errors=critical_validation_errors,
            operational_errors=operational_errors,
            final_pending_issues=final_state.pending_issues,
            execution_time_seconds=round(end_time - start_time, 2),
            provider_error=provider_err
        )
        
        self.metrics.append(metric)
        print(f"[Evaluator] Finalizado: {metric.status} en {metric.execution_time_seconds}s")
        return metric

    def export_report(self, filepath: str = "docs/evaluation_report.json"):
        report = [m.model_dump() for m in self.metrics]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)
        print(f"\n[Evaluator] Reporte experimental exportado a {filepath}")
