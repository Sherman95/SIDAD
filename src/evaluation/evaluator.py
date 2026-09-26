import json
import time
from typing import List, Dict, Any
from pydantic import BaseModel
from src.agent.state import AgentState
from src.agent.orchestrator import Orchestrator

class EvaluationMetric(BaseModel):
    scenario_name: str
    status: str
    iterations: int
    tools_used: int
    corrections_made: int
    critical_errors: int
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

    def run_scenario(self, scenario_name: str, initial_state: AgentState) -> EvaluationMetric:
        print(f"\n[Evaluator] Ejecutando escenario: {scenario_name}")
        start_time = time.time()
        
        final_state = self.orchestrator.run(initial_state)
        
        end_time = time.time()
        
        # Calcular métricas
        corrections = len([v for v in final_state.critic_verdicts if v.status == "FAIL"])
        critical_errors = len(final_state.pending_issues)
        
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
            status=final_state.status,
            iterations=final_state.iteration_count,
            tools_used=len(final_state.execution_history),
            corrections_made=corrections,
            critical_errors=critical_errors,
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
