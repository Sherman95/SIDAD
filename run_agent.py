import os
from src.agent.state import AgentState
from src.agent.tool_registry import get_default_registry
from src.agent.mock_llm import MockLLMProvider
from src.agent.critic import Critic
from src.agent.orchestrator import Orchestrator

def print_observability_report(state: AgentState):
    print("\n=== REPORTE DE OBSERVABILIDAD DE EJECUCIÓN ===")
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

def run_tests():
    print("=== INICIANDO TESTS DE FASE 8 (ORQUESTADOR) ===\n")
    
    registry = get_default_registry()
    critic = Critic()
    
    # 1. Test Ejecución Completa con Self-Correction (Mock simulando fallo en layout)
    print("\n--- TEST 1: Ciclo Completo con Autocorrección ---")
    llm = MockLLMProvider(simulate_fail=True)
    orchestrator = Orchestrator(llm=llm, registry=registry, critic=critic)
    
    state = AgentState(
        user_request="Analiza este dataset de ventas y prepara un dashboard ejecutivo.",
        input_dataset_path=os.path.join("data", "raw", "ventas_test.csv"),
        current_goal="Crear dashboard validado libre de colisiones"
    )
    
    final_state = orchestrator.run(state)
    print_observability_report(final_state)
    assert final_state.status == "SUCCESS", "El agente no logró llegar al final exitosamente tras la corrección."
    
    # 2. Test Guardrails: Intento de modificar data/raw directamente
    print("\n--- TEST 2: Protección RAW ---")
    is_error, res = registry.execute("clean_dataset", {"input_path": "data/raw/data.csv", "output_path": "data/raw/data_mod.csv", "actions": []})
    print(f"Resultado: {res}")
    assert is_error and "Error de Seguridad" in res, "La protección RAW falló."
    
    # 3. Test Límite de iteraciones
    print("\n--- TEST 3: Max Iterations ---")
    state_inf = AgentState(
        user_request="Loop test",
        input_dataset_path="mock.csv",
        current_goal="Loop test",
        max_iterations=2
    )
    llm_inf = MockLLMProvider(simulate_fail=True)
    orch_inf = Orchestrator(llm=llm_inf, registry=registry, critic=critic)
    final_inf = orch_inf.run(state_inf)
    print(f"Status Final: {final_inf.status}")
    assert final_inf.status == "FAILED" and "Se superó el límite máximo" in final_inf.pending_issues[0], "Max iterations no abortó."

if __name__ == "__main__":
    run_tests()
