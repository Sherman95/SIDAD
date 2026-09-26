import pytest
from src.agent.tool_registry import get_default_registry
from src.agent.critic import Critic
from src.agent.mock_llm import MockLLMProvider
from src.agent.orchestrator import Orchestrator
from src.evaluation.static_pipeline import StaticPipeline
from src.evaluation.evaluator import Evaluator
from src.agent.state import AgentState
import json
import os

def get_base_state():
    return AgentState(
        user_request="test",
        input_dataset_path="data/raw/ventas_test.csv",
        current_goal="test",
        max_iterations=15
    )

def test_static_pipeline_executes():
    registry = get_default_registry()
    pipe = StaticPipeline(registry, "standard")
    state = get_base_state()
    evaluator = Evaluator(pipe)
    metric = evaluator.run_scenario("test_static", state, "static")
    assert metric.status == "SUCCESS"
    assert metric.iterations > 0

def test_agent_pipeline_executes():
    registry = get_default_registry()
    critic = Critic()
    llm = MockLLMProvider(scenario="standard")
    pipe = Orchestrator(llm=llm, registry=registry, critic=critic)
    state = get_base_state()
    evaluator = Evaluator(pipe)
    metric = evaluator.run_scenario("test_agent", state, "mock_agent")
    assert metric.status == "SUCCESS"
    assert metric.iterations > 0

def test_metrics_generation_and_report():
    import run_comparison
    # Corre una version en miniatura
    run_comparison.run_experiment()
    assert os.path.exists("docs/comparison_report.json")
    with open("docs/comparison_report.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "aggregate_metrics" in data
    assert "static" in data["aggregate_metrics"]
    assert "agent_mock" in data["aggregate_metrics"]
    assert data["aggregate_metrics"]["static"]["success_rate"] >= 0.0

def test_scenario_isolation():
    registry = get_default_registry()
    pipe1 = StaticPipeline(registry, "invalid_arguments")
    state1 = get_base_state()
    evaluator1 = Evaluator(pipe1)
    m1 = evaluator1.run_scenario("test_iso_1", state1, "static")
    assert m1.status == "FAILED"

    pipe2 = StaticPipeline(registry, "standard")
    state2 = get_base_state()
    evaluator2 = Evaluator(pipe2)
    m2 = evaluator2.run_scenario("test_iso_2", state2, "static")
    assert m2.status == "SUCCESS"
