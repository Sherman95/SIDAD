import argparse
from src.agent.state import AgentState
from src.agent.tool_registry import ToolRegistry
from src.agent.orchestrator import Orchestrator
from src.agent.critic import Critic
from src.agent.mock_llm import MockLLMProvider
from src.agent.gemini_provider import GeminiLLMProvider
from src.evaluation.evaluator import Evaluator
from dotenv import load_dotenv
import os

def run_evaluation(provider_name: str):
    load_dotenv()
    
    # Setup base components
    from src.agent.tool_registry import get_default_registry
    registry = get_default_registry()
    critic = Critic()
    
    if provider_name == "gemini":
        print("Instanciando proveedor Gemini...")
        llm = GeminiLLMProvider(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        )
    else:
        print("Instanciando proveedor Mock determinista...")
        llm = MockLLMProvider()

    orchestrator = Orchestrator(llm=llm, registry=registry, critic=critic)
    evaluator = Evaluator(orchestrator)
    
    # Definir Casos de Prueba Académicos
    # Escenario 1: Flujo ideal simulado (o real)
    sc_1 = AgentState(
        user_request="Analiza mis ventas y genera un reporte",
        input_dataset_path="data/raw/ventas_test.csv",
        current_goal="Crear un pipeline completo"
    )
    
    # Escenario 2: Límite de iteraciones (sólo para Mock simulando fallos infinitos, si es real probaremos el dataset)
    sc_2 = AgentState(
        user_request="Analiza ventas. Fallo simulado.",
        input_dataset_path="data/raw/ventas_test.csv",
        current_goal="Forzar bucle de error",
        max_iterations=3
    )
    
    print("\n===========================================")
    print(" INICIANDO BATERÍA DE EVALUACIÓN (FASE 10) ")
    print("===========================================\n")
    
    # En un entorno real de tesis, aquí se cargarían N datasets con diferentes calidades
    evaluator.run_scenario("Escenario 1: Dataset estándar", sc_1)
    
    # Modificamos el proveedor mock para forzar fallo en el Escenario 2 si aplica
    if provider_name == "mock":
        orchestrator.llm = MockLLMProvider(simulate_fail=True)
    evaluator.run_scenario("Escenario 2: Prueba de estrés / Max Iterations", sc_2)
    
    # Exportar métricas finales
    evaluator.export_report()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar Batería de Evaluación")
    parser.add_argument("--provider", type=str, choices=["mock", "gemini"], default="mock", help="Proveedor de LLM a usar para la evaluación.")
    args = parser.parse_args()
    
    run_evaluation(args.provider)
