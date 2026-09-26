import json
import os
import copy
from src.agent.tool_registry import get_default_registry
from src.agent.critic import Critic
from src.agent.mock_llm import MockLLMProvider
from src.agent.orchestrator import Orchestrator
from src.evaluation.static_pipeline import StaticPipeline
from src.evaluation.evaluator import Evaluator
from src.agent.state import AgentState

def get_base_state(name: str):
    return AgentState(
        user_request=name,
        input_dataset_path="data/raw/ventas_test.csv",
        current_goal=name,
        max_iterations=15
    )

def run_experiment():
    print("=== INICIANDO FASE 11: EVALUACIÓN COMPARATIVA ===")
    registry = get_default_registry()
    critic = Critic()

    # Inyección de monkey patch para escenarios de fallo de validación visual
    original_wrap_generate_layout = registry._tools["generate_layout"][1]
    def eval_wrap_generate_layout(dashboard_plan_json: str, columns: int = 2) -> str:
        res = original_wrap_generate_layout(dashboard_plan_json)
        data = json.loads(res)
        if columns > 10:
            for page in data.get("pages", []):
                for p_vis in page.get("placed_visuals", []):
                    pos = p_vis.get("position", {})
                    pos["width"] = 9999
                    pos["height"] = 9999
        return json.dumps(data)
    registry._tools["generate_layout"] = (registry._tools["generate_layout"][0], eval_wrap_generate_layout)

    # Definir escenarios
    scenarios = [
        {"name": "1_Dataset_Nominal", "scenario": "standard"},
        {"name": "2_Dataset_Calidad", "scenario": "standard"}, # Usa ventas_test.csv que ya tiene nulos
        {"name": "3_Problema_Layout", "scenario": "validation_failure"}, # En mock agent: generate_layout genera 100 columns primero
        {"name": "4_Error_Operativo", "scenario": "invalid_arguments"}
    ]

    all_metrics = []

    # Repetimos 3 veces para reproducibilidad
    REPETITIONS = 3

    for run_idx in range(REPETITIONS):
        print(f"\n--- REPETICIÓN {run_idx + 1} ---")
        
        for s in scenarios:
            scenario_id = s["scenario"]
            name = s["name"]
            
            # --- RUN STATIC PIPELINE ---
            static_pipe = StaticPipeline(registry=registry, scenario=scenario_id)
            evaluator_static = Evaluator(pipeline=static_pipe)
            state_static = get_base_state(f"{name}_static")
            metric_static = evaluator_static.run_scenario(name, state_static, provider="static")
            all_metrics.append(metric_static)

            # --- RUN AGENT PIPELINE ---
            # Para SIDAD el escenario validation_failure requiere simulate_fail para que dispare columns=100
            sim_fail = (scenario_id == "validation_failure")
            mock_llm = MockLLMProvider(simulate_fail=sim_fail, scenario=scenario_id)
            agent_pipe = Orchestrator(llm=mock_llm, registry=registry, critic=critic)
            evaluator_agent = Evaluator(pipeline=agent_pipe)
            state_agent = get_base_state(f"{name}_agent")
            metric_agent = evaluator_agent.run_scenario(name, state_agent, provider="agent_mock")
            all_metrics.append(metric_agent)

    # Exportar resultados estructurados
    report = {
        "experiment": "SIDAD Phase 11 - Comparative Evaluation",
        "repetitions": REPETITIONS,
        "scenarios": [s["name"] for s in scenarios],
        "aggregate_metrics": {},
        "runs": [m.model_dump() for m in all_metrics]
    }

    # Calcular promedios para tabla agregada
    for prov in ["static", "agent_mock"]:
        prov_metrics = [m for m in all_metrics if m.provider == prov]
        total_runs = len(prov_metrics)
        if total_runs == 0: continue
        
        successes = len([m for m in prov_metrics if m.status == "SUCCESS"])
        
        report["aggregate_metrics"][prov] = {
            "success_rate": successes / total_runs,
            "avg_validation_failures": sum(m.validation_failures for m in prov_metrics) / total_runs,
            "avg_corrections_attempted": sum(m.corrections_attempted for m in prov_metrics) / total_runs,
            "avg_corrections_successful": sum(m.corrections_successful for m in prov_metrics) / total_runs,
            "avg_critical_validation_errors": sum(m.critical_validation_errors for m in prov_metrics) / total_runs,
            "avg_operational_errors": sum(m.operational_errors for m in prov_metrics) / total_runs,
            "avg_iterations": sum(m.iterations for m in prov_metrics) / total_runs,
            "avg_execution_time": sum(m.execution_time_seconds for m in prov_metrics) / total_runs
        }

    os.makedirs("docs", exist_ok=True)
    with open("docs/comparison_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print("\n=== RESUMEN COMPARATIVO (Promedios) ===")
    print(f"{'Metric':<30} | {'Static':<10} | {'Agent':<10}")
    print("-" * 55)
    metrics_keys = [
        "success_rate", "avg_validation_failures", "avg_corrections_attempted",
        "avg_corrections_successful", "avg_critical_validation_errors",
        "avg_operational_errors", "avg_iterations", "avg_execution_time"
    ]
    stat_agg = report["aggregate_metrics"].get("static", {})
    agnt_agg = report["aggregate_metrics"].get("agent_mock", {})
    
    for k in metrics_keys:
        s_val = stat_agg.get(k, 0)
        a_val = agnt_agg.get(k, 0)
        if isinstance(s_val, float): s_val = round(s_val, 2)
        if isinstance(a_val, float): a_val = round(a_val, 2)
        print(f"{k:<30} | {s_val:<10} | {a_val:<10}")

    print("\nReporte generado en: docs/comparison_report.json")

if __name__ == "__main__":
    run_experiment()
