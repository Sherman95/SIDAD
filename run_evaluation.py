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
    
    # Import and register tools
    from src.agent.tool_registry import get_default_registry
    registry = get_default_registry()
    
    # Monkey patch wrap_generate_layout for evaluation purposes to actually respect columns argument
    # so we can force a validation failure
    original_wrap_generate_layout = registry._tools["generate_layout"][1]
    
    def eval_wrap_generate_layout(dashboard_plan_json: str, columns: int = 2) -> str:
        res = original_wrap_generate_layout(dashboard_plan_json)
        import json
        data = json.loads(res)
        # Si las columnas son 100, forzamos dimensiones gigantes para que colisionen
        if columns > 10:
            for page in data.get("pages", []):
                for p_vis in page.get("placed_visuals", []):
                    pos = p_vis.get("position", {})
                    pos["width"] = 9999
                    pos["height"] = 9999
        return json.dumps(data)
        
    registry._tools["generate_layout"] = (registry._tools["generate_layout"][0], eval_wrap_generate_layout)
    
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
    
    print("\n===========================================")
    print(" INICIANDO BATERÍA DE EVALUACIÓN (FASE 10) ")
    print("===========================================\n")
    
    # Base state generator
    def get_state(name: str, max_iter: int = 15):
        return AgentState(user_request=name, input_dataset_path="data/raw/ventas_test.csv", current_goal=name, max_iterations=max_iter)

    scenarios = [
        {"name": "1. standard_success", "scenario": "standard", "simulate_fail": False, "max_iter": 15},
        {"name": "2. tool_error", "scenario": "tool_error", "simulate_fail": False, "max_iter": 2},
        {"name": "3. invalid_arguments", "scenario": "invalid_arguments", "simulate_fail": False, "max_iter": 2},
        {"name": "4. max_iterations", "scenario": "standard", "simulate_fail": False, "max_iter": 2},
        {"name": "5. anti_loop", "scenario": "anti_loop", "simulate_fail": False, "max_iter": 10},
        {"name": "6. validation_failure", "scenario": "validation_failure", "simulate_fail": True, "max_iter": 6}, # Will fail because max iter 6 is exactly right before finish, actually cycle takes 8.
        {"name": "7. self_correction_success", "scenario": "self_correction_success", "simulate_fail": True, "max_iter": 15},
        {"name": "8. finish_success", "scenario": "standard", "simulate_fail": False, "max_iter": 15}
    ]

    for s in scenarios:
        if provider_name == "mock":
            orchestrator.llm = MockLLMProvider(simulate_fail=s["simulate_fail"], scenario=s["scenario"])
        st = get_state(s["name"], s["max_iter"])
        evaluator.run_scenario(s["name"], st, provider=provider_name)
    
    # Exportar métricas finales
    evaluator.export_report()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ejecutar Batería de Evaluación")
    parser.add_argument("--provider", type=str, choices=["mock", "gemini"], default="mock", help="Proveedor de LLM a usar para la evaluación.")
    args = parser.parse_args()
    
    run_evaluation(args.provider)
