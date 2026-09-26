import os
import argparse
import sys
from typing import Optional

from src.agent.state import AgentState
from src.agent.tool_registry import get_default_registry
from src.agent.mock_llm import MockLLMProvider
from src.agent.gemini_provider import GeminiLLMProvider
from src.agent.critic import Critic
from src.agent.orchestrator import Orchestrator
from src.agent.llm_provider import Decision

def print_observability_report(state: AgentState, provider_name: str, model_name: str):
    print("\n=== SIDAD EXECUTION REPORT ===")
    print(f"Provider: {provider_name}")
    print(f"Model: {model_name}")
    
    # Determinar si hay error de cuota en history
    quota_errors = [a for a in state.execution_history if a.tool_name == "LLM_QUOTA_ERROR"]
    failure_type = "NONE"
    if state.status == "FAILED":
        if quota_errors:
            failure_type = "LLM_QUOTA_ERROR"
        elif "límite máximo" in str(state.pending_issues):
            failure_type = "MAX_ITERATIONS"
        elif "Bucle atascado" in str(state.pending_issues):
            failure_type = "ANTI_LOOP"
        else:
            failure_type = "AGENT_ERROR"
            
    print(f"\nStatus: {state.status}")
    if failure_type != "NONE":
        print(f"Failure type: {failure_type}")
        
    print(f"Iterations: {state.iteration_count} / {state.max_iterations}")
    print(f"Tools executed: {len(state.execution_history)}")
    
    corrections = len([v for v in state.critic_verdicts if v.status == "FAIL"])
    critical_errors = len(state.pending_issues)
    
    print(f"\nHistorial de Acciones:")
    for a in state.execution_history:
        status_flag = "[ERROR]" if a.is_error else "[OK]"
        print(f" {a.step:02d} {status_flag} {a.tool_name}")
        print(f"    Razón: {a.operational_reason}")
        if a.is_error:
            print(f"    Detalle: {a.result_summary}")
        
    print(f"\nCorrections: {corrections}")
    print(f"Critical errors: {critical_errors}")
    
    if failure_type != "NONE":
        print("\nProvider errors:")
        for err in quota_errors:
            print(f"- {err.operational_reason}")

def run_tests(provider_name: str):
    print(f"=== INICIANDO TESTS DE FASE 8/9 (ORQUESTADOR + {provider_name}) ===\n")
    
    registry = get_default_registry()
    critic = Critic()
    
    if provider_name == "gemini":
        llm = GeminiLLMProvider()
    else:
        llm = MockLLMProvider(simulate_fail=True)
        
    # --- PRUEBAS SOLICITADAS ---
    
    print("\n--- TEST: Decision Estructurada / API (Simulación si mock) ---")
    state_test = AgentState(
        user_request="Test decision",
        input_dataset_path="test.csv",
        current_goal="Test",
        max_iterations=2
    )
    decision = llm.predict_next_action(state_test, registry.get_available_tools_info())
    print(f"Decisión inicial: {decision.tool_name}")
    assert isinstance(decision, Decision), "No se retornó un objeto Decision válido."
    
    print("\n--- TEST: Tool inexistente ---")
    is_err, res = registry.execute("tool_that_does_not_exist", {})
    assert is_err and "no existe" in res, "No se bloqueó la tool inexistente."
    print("OK: Bloqueo de tool inexistente validado.")
    
    print("\n--- TEST: Argumentos inválidos ---")
    is_err, res = registry.execute("profile_dataset", {})
    assert is_err and "Error de Argumentos" in res, "No se validaron los argumentos requeridos."
    print("OK: Bloqueo de argumentos inválidos validado.")

    print("\n--- TEST: Protección RAW ---")
    is_error, res = registry.execute("clean_dataset", {"input_path": "data/raw/data.csv", "output_path": "data/raw/data_mod.csv", "actions": []})
    assert is_error and "Error de Seguridad" in res, "La protección RAW falló."
    print("OK: Protección de data/raw validada.")
    
    print("\n--- TEST: Límite de iteraciones ---")
    llm_inf = MockLLMProvider(simulate_fail=True)
    orch_inf = Orchestrator(llm=llm_inf, registry=registry, critic=critic)
    state_inf = AgentState(
        user_request="Loop test",
        input_dataset_path="mock.csv",
        current_goal="Loop test",
        max_iterations=2
    )
    final_inf = orch_inf.run(state_inf)
    assert final_inf.status == "FAILED" and "límite máximo" in final_inf.pending_issues[0], "Max iterations no abortó."
    print("OK: Límite de iteraciones funciona.")
    
    print("\n--- TEST: Self-Correction (Mock) ---")
    # Forzamos que el mock falle inicialemente (simulate_fail=True)
    # y que el validador AABB lo detecte como solapamiento.
    # En nuestro entorno real, ventas_test.csv no genera suficientes visuales para colisionar en 5 columnas.
    # Así que vamos a saltar directamente a probar que el LLM genera la decisión correctiva.
    # Wait, the MockLLMProvider ya lo hace en mock!
    # El problema es que en la ejecución con ventas_test.csv, el LayoutValidator no detectaba colisión.
    # Podemos inyectar un estado con validation report falso para simular el fallo.
    state_sc = AgentState(
        user_request="test", input_dataset_path="test", current_goal="test"
    )
    from src.models.profiling import DiagnosticResult, DatasetProfile
    from src.models.transformations import TransformationLog
    from src.models.semantic_model import SemanticProject
    from src.models.dashboard import DashboardPlan
    from src.models.report_layout import ReportLayout
    from src.agent.state import CriticVerdict
    
    state_sc.dataset_profile = DiagnosticResult(profile=DatasetProfile(row_count=1, column_count=1, missing_values=0, duplicate_rows=0, columns_with_nulls=[], problems_detected=[]))
    state_sc.transformation_logs = [TransformationLog(action="test", reason="test", tool_used="test", records_affected=1)]
    state_sc.semantic_project = SemanticProject(dimensions=[], facts=[], kpis=[], context="test")
    state_sc.dashboard_plan = DashboardPlan(title="test", pages=[])
    state_sc.report_layout = ReportLayout(pages=[])
    state_sc.critic_verdicts = [CriticVerdict(status="FAIL", issue="layout collision", severity="ERROR", recommended_action="regenerate_layout", reason="test")]
    
    decision_sc = llm_inf.predict_next_action(state_sc, registry.get_available_tools_info())
    assert decision_sc.tool_name == "generate_layout" and decision_sc.arguments.get("columns") == 2, "Mock no reaccionó al FAIL del Critic"
    print("OK: Self-correction LLM decision probada exitosamente.")

    print("\n--- EJECUCIÓN PRINCIPAL ---")
    orchestrator = Orchestrator(llm=llm, registry=registry, critic=critic)
    
    state = AgentState(
        user_request="Analiza este dataset de ventas y prepara un dashboard ejecutivo. Por favor, limpia nulos en la categoría usando la palabra 'Desconocido', y elimina duplicados. Luego genera un dashboard para mí.",
        input_dataset_path=os.path.join("data", "raw", "ventas_test.csv"),
        current_goal="Crear dashboard validado libre de colisiones"
    )
    
    final_state = orchestrator.run(state)
    model_nm = getattr(llm, "model_name", "mock-deterministic")
    print_observability_report(final_state, provider_name, model_nm)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar el Agente SIDAD")
    parser.add_argument("--provider", type=str, choices=["mock", "gemini"], default="mock", help="El proveedor LLM a utilizar.")
    args = parser.parse_args()
    
    try:
        run_tests(args.provider)
    except Exception as e:
        print(f"Error crítico en la ejecución: {e}")
        sys.exit(1)
