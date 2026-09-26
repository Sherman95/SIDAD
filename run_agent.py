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

def print_observability_report(state: AgentState, provider_name: str):
    print("\n=== REPORTE DE OBSERVABILIDAD DE EJECUCIÓN ===")
    print(f"Provider: {provider_name}")
    print(f"Status: {state.status}")
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
        
    print(f"\nCorrections needed: {corrections}")
    print(f"Critical errors pending: {critical_errors}")

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
    
    print("\n--- EJECUCIÓN PRINCIPAL ---")
    orchestrator = Orchestrator(llm=llm, registry=registry, critic=critic)
    
    state = AgentState(
        user_request="Analiza este dataset de ventas y prepara un dashboard ejecutivo. Por favor, limpia nulos en la categoría usando la palabra 'Desconocido', y elimina duplicados. Luego genera un dashboard para mí.",
        input_dataset_path=os.path.join("data", "raw", "ventas_test.csv"),
        current_goal="Crear dashboard validado libre de colisiones"
    )
    
    final_state = orchestrator.run(state)
    print_observability_report(final_state, provider_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar el Agente SIDAD")
    parser.add_argument("--provider", type=str, choices=["mock", "gemini"], default="mock", help="El proveedor LLM a utilizar.")
    args = parser.parse_args()
    
    try:
        run_tests(args.provider)
    except Exception as e:
        print(f"Error crítico en la ejecución: {e}")
        sys.exit(1)
