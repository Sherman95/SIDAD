from pathlib import Path

import pytest

from src.agent.critic import Critic
from src.agent.llm_provider import Decision, LLMProvider
from src.agent.mock_llm import MockLLMProvider
from src.agent.orchestrator import Orchestrator
from src.agent.state import AgentState
from src.agent.tool_registry import get_default_registry
from src.agent.validator import LayoutValidator, ValidationReport
from src.evaluation.static_pipeline import StaticPipeline
from src.models.dashboard import (
    DashboardPage,
    DashboardPlan,
    VisualElement,
    VisualType,
)
from src.models.powerbi_export import PowerBIExportResult
from src.models.report_layout import ReportLayout
from src.models.semantic_model import (
    ColumnRole,
    KPI,
    SemanticColumn,
    SemanticDataType,
    SemanticProject,
    SemanticTable,
    TableType,
)
from src.tools.bi.export_service import export_to_powerbi
from src.tools.dashboard.generator import ReportGenerator


def _semantic(source_path: str) -> SemanticProject:
    return SemanticProject(
        tables=[
            SemanticTable(
                name="Sales",
                table_type=TableType.FACT,
                columns=[
                    SemanticColumn(
                        name="category",
                        role=ColumnRole.DIMENSION,
                        data_type=SemanticDataType.STRING,
                    ),
                    SemanticColumn(
                        name="amount",
                        role=ColumnRole.METRIC,
                        data_type=SemanticDataType.DECIMAL,
                    ),
                ],
                source_path=source_path,
            )
        ],
        kpis=[
            KPI(
                name="Total Amount",
                description="Total amount",
                aggregation_type="Sum",
                base_column="amount",
                base_table="Sales",
                dax_suggestion="SUM('Sales'[amount])",
            )
        ],
    )


def _plan() -> DashboardPlan:
    return DashboardPlan(
        pages=[
            DashboardPage(
                name="Overview",
                objective="Validate agent export",
                visuals=[
                    VisualElement(
                        title="Total Amount",
                        type=VisualType.CARD,
                        kpi_ref="Total Amount",
                    ),
                    VisualElement(
                        title="Amount by Category",
                        type=VisualType.BAR_CHART,
                        x_axis="category",
                        y_axis="Total Amount",
                    ),
                ],
            )
        ]
    )


def _models(project_root: Path, *, relative_source: bool = False):
    source = project_root / "data" / "processed" / "sales.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("category,amount\nA,10.5\nB,20.0\n", encoding="utf-8")
    source_value = "data/processed/sales.csv" if relative_source else str(source)
    semantic = _semantic(source_value)
    plan = _plan()
    layout = ReportGenerator(plan).generate_layout()
    return semantic, plan, layout


def _tool_args(
    semantic: SemanticProject | None,
    plan: DashboardPlan | None,
    layout: ReportLayout | None,
    output_path: str | Path,
    source_base_path: Path,
) -> dict:
    return {
        "semantic_project_json": (
            semantic.model_dump_json() if semantic is not None else None
        ),
        "dashboard_plan_json": plan.model_dump_json() if plan is not None else None,
        "report_layout_json": (
            layout.model_dump_json() if layout is not None else None
        ),
        "output_path": str(output_path),
        "project_name": "AgentReport",
        "source_base_path": str(source_base_path.resolve()),
    }


def _agent_project(project_root: Path) -> None:
    source = project_root / "data" / "raw" / "ventas_test.csv"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "id_venta,fecha,producto,categoria,cantidad,precio,ciudad\n"
        "1,2026-01-01,Laptop,Electronica,1,1200.5,Quito\n"
        "2,2026-01-02,Mouse,,2,25.0,Cuenca\n"
        "3,2026-01-03,Silla,Oficina,,150.0,Loja\n",
        encoding="utf-8",
    )


def test_export_to_powerbi_is_registered():
    tools = get_default_registry().get_available_tools_info()

    export_tool = next(tool for tool in tools if tool["name"] == "export_to_powerbi")

    assert set(export_tool["schema"]) == {
        "semantic_project_json",
        "dashboard_plan_json",
        "report_layout_json",
        "output_path",
        "project_name",
        "source_base_path",
    }


def test_typed_export_generates_complete_project_and_correct_paths(tmp_path: Path):
    semantic, plan, layout = _models(tmp_path)
    output = tmp_path / "exports" / "powerbi"

    result = export_to_powerbi(
        semantic,
        plan,
        layout,
        output,
        project_name="AgentReport",
        source_base_path=tmp_path,
    )

    assert isinstance(result, PowerBIExportResult)
    assert result.success
    assert result.errors == []
    assert result.project_path == str((output / "AgentReport.pbip").resolve())
    assert result.semantic_model_path == str(
        (output / "AgentReport.SemanticModel").resolve()
    )
    assert result.report_path == str((output / "AgentReport.Report").resolve())
    assert result.generated_files
    assert all(Path(path).is_file() for path in result.generated_files)
    assert Path(result.project_path).is_file()
    assert (Path(result.semantic_model_path) / "definition" / "model.tmdl").is_file()
    assert (Path(result.report_path) / "definition" / "pages" / "pages.json").is_file()


def test_registry_exports_from_serialized_models(tmp_path: Path):
    semantic, plan, layout = _models(tmp_path)
    registry = get_default_registry()

    is_error, payload = registry.execute(
        "export_to_powerbi",
        _tool_args(semantic, plan, layout, "exports/serialized", tmp_path),
    )
    result = PowerBIExportResult.model_validate_json(payload)

    assert not is_error
    assert result.success
    assert Path(result.project_path).is_relative_to(tmp_path)


@pytest.mark.parametrize(
    ("missing", "expected_error"),
    [
        ("semantic", "Falta SemanticProject"),
        ("plan", "Falta DashboardPlan"),
        ("layout", "Falta ReportLayout"),
    ],
)
def test_registry_rejects_missing_models(
    tmp_path: Path,
    missing: str,
    expected_error: str,
):
    semantic, plan, layout = _models(tmp_path)
    values = {"semantic": semantic, "plan": plan, "layout": layout}
    values[missing] = None

    is_error, payload = get_default_registry().execute(
        "export_to_powerbi",
        _tool_args(
            values["semantic"],
            values["plan"],
            values["layout"],
            tmp_path / "export",
            tmp_path,
        ),
    )
    result = PowerBIExportResult.model_validate_json(payload)

    assert is_error
    assert not result.success
    assert expected_error in result.errors
    assert not (tmp_path / "export").exists()


def test_export_rejects_invalid_aabb_layout_before_writing(tmp_path: Path):
    semantic, plan, layout = _models(tmp_path)
    first, second = layout.pages[0].placed_visuals
    second.position = first.position.model_copy(deep=True)
    output = tmp_path / "invalid-layout"

    result = export_to_powerbi(
        semantic,
        plan,
        layout,
        output,
        source_base_path=tmp_path,
    )

    assert not result.success
    assert any("Superposici" in error for error in result.errors)
    assert not output.exists()


def test_export_rejects_missing_dataset_before_writing(tmp_path: Path):
    semantic, plan, layout = _models(tmp_path)
    semantic.tables[0].source_path = "data/processed/missing.csv"
    output = tmp_path / "missing-source"

    result = export_to_powerbi(
        semantic,
        plan,
        layout,
        output,
        source_base_path=tmp_path,
    )

    assert not result.success
    assert any("missing.csv" in error for error in result.errors)
    assert not output.exists()


def test_export_paths_are_independent_from_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    semantic, plan, layout = _models(project_root, relative_source=True)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    is_error, payload = get_default_registry().execute(
        "export_to_powerbi",
        _tool_args(semantic, plan, layout, "exports/report", project_root),
    )
    result = PowerBIExportResult.model_validate_json(payload)

    assert not is_error
    assert result.success
    assert Path(result.project_path) == (
        project_root / "exports" / "report" / "AgentReport.pbip"
    ).resolve()
    table_tmdl = (
        Path(result.semantic_model_path)
        / "definition"
        / "tables"
        / "Sales.tmdl"
    ).read_text(encoding="utf-8")
    assert str((project_root / "data" / "processed" / "sales.csv").resolve()) in table_tmdl


def test_static_pipeline_exports_powerbi(tmp_path: Path):
    project_root = tmp_path / "static-project"
    project_root.mkdir()
    _agent_project(project_root)
    state = AgentState(
        user_request="test static export",
        input_dataset_path="data/raw/ventas_test.csv",
        current_goal="export",
        project_base_path=str(project_root.resolve()),
        powerbi_output_path="data/output/static-export",
    )

    final_state = StaticPipeline(get_default_registry()).run(state)

    assert final_state.status == "SUCCESS"
    assert final_state.powerbi_export is not None
    assert final_state.powerbi_export.success
    assert final_state.execution_history[-1].tool_name == "export_to_powerbi"


def test_mock_agent_exports_and_finishes_from_unrelated_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    project_root = tmp_path / "agent-project"
    project_root.mkdir()
    _agent_project(project_root)
    unrelated = tmp_path / "unrelated-agent-cwd"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    state = AgentState(
        user_request="create a Power BI report",
        input_dataset_path="data/raw/ventas_test.csv",
        current_goal="export",
        project_base_path=str(project_root.resolve()),
        powerbi_output_path="data/output/agent-export",
        max_iterations=15,
    )

    final_state = Orchestrator(
        llm=MockLLMProvider(),
        registry=get_default_registry(),
        critic=Critic(),
    ).run(state)

    assert final_state.status == "SUCCESS"
    assert final_state.validation_report is not None
    assert final_state.validation_report.is_valid
    assert final_state.powerbi_export is not None
    assert final_state.powerbi_export.success
    assert final_state.execution_history[-1].tool_name == "export_to_powerbi"
    assert Path(final_state.powerbi_export.project_path).is_file()


class _FinishOnlyLLM(LLMProvider):
    def predict_next_action(
        self,
        state: AgentState,
        available_tools: list[dict],
    ) -> Decision:
        return Decision(
            tool_name="finish",
            arguments={},
            operational_reason="Intento prematuro",
        )


class _ExportOnlyLLM(LLMProvider):
    def predict_next_action(
        self,
        state: AgentState,
        available_tools: list[dict],
    ) -> Decision:
        return Decision(
            tool_name="export_to_powerbi",
            arguments={
                "semantic_project_json": state.semantic_project.model_dump_json(),
                "dashboard_plan_json": state.dashboard_plan.model_dump_json(),
                "report_layout_json": state.report_layout.model_dump_json(),
                "output_path": state.resolve_project_path(state.powerbi_output_path),
                "project_name": state.powerbi_project_name,
                "source_base_path": state.resolve_project_path("."),
            },
            operational_reason="Propagar fallo de exportacion",
        )


def test_agent_cannot_finish_before_successful_export(tmp_path: Path):
    semantic, plan, layout = _models(tmp_path)
    state = AgentState(
        user_request="finish",
        input_dataset_path="data/processed/sales.csv",
        current_goal="finish",
        project_base_path=str(tmp_path.resolve()),
        semantic_project=semantic,
        dashboard_plan=plan,
        report_layout=layout,
        validation_report=ValidationReport(is_valid=True),
        max_iterations=1,
    )

    final_state = Orchestrator(
        llm=_FinishOnlyLLM(),
        registry=get_default_registry(),
        critic=Critic(),
    ).run(state)

    assert final_state.status == "FAILED"
    assert any(
        "Falta una exportacion Power BI exitosa" in action.result_summary
        for action in final_state.execution_history
    )


def test_agent_propagates_export_errors_to_state(tmp_path: Path):
    semantic, plan, layout = _models(tmp_path)
    semantic.tables[0].source_path = "data/processed/not-found.csv"
    state = AgentState(
        user_request="export",
        input_dataset_path="data/processed/not-found.csv",
        current_goal="export",
        project_base_path=str(tmp_path.resolve()),
        semantic_project=semantic,
        dashboard_plan=plan,
        report_layout=layout,
        validation_report=LayoutValidator().validate(layout),
        powerbi_output_path="exports/failure",
        max_iterations=2,
    )

    final_state = Orchestrator(
        llm=_ExportOnlyLLM(),
        registry=get_default_registry(),
        critic=Critic(),
    ).run(state)

    assert final_state.status == "FAILED"
    assert final_state.powerbi_export is not None
    assert not final_state.powerbi_export.success
    assert any("not-found.csv" in issue for issue in final_state.pending_issues)
    assert final_state.execution_history[-1].tool_name == "export_to_powerbi"
    assert final_state.execution_history[-1].is_error


def test_export_rejects_unsafe_relative_output(tmp_path: Path):
    semantic, plan, layout = _models(tmp_path)

    result = export_to_powerbi(
        semantic,
        plan,
        layout,
        "../outside",
        source_base_path=tmp_path,
    )

    assert not result.success
    assert any("escapar" in error for error in result.errors)
