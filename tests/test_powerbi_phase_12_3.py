import json
from pathlib import Path

import pytest

from src.agent.validator import LayoutValidator
from src.models.dashboard import (
    DashboardPage,
    DashboardPlan,
    SemanticFieldKind,
    SemanticFieldRef,
    VisualBindings,
    VisualElement,
    VisualType,
)
from src.models.report_layout import Position
from src.models.semantic_model import (
    ColumnRole,
    KPI,
    SemanticColumn,
    SemanticDataType,
    SemanticProject,
    SemanticTable,
    TableType,
)
from src.tools.bi.powerbi_provider import PowerBIProvider
from src.tools.dashboard.generator import ReportGenerator


def _semantic_project() -> SemanticProject:
    return SemanticProject(
        tables=[
            SemanticTable(
                name="Sales",
                table_type=TableType.FACT,
                columns=[
                    SemanticColumn(
                        name="sale_date",
                        role=ColumnRole.DATE,
                        data_type=SemanticDataType.DATETIME,
                    ),
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
                objective="Exercise every supported layout family",
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
                    VisualElement(
                        title="Amount Trend",
                        type=VisualType.LINE_CHART,
                        x_axis="sale_date",
                        y_axis="Total Amount",
                    ),
                    VisualElement(
                        title="Amount Share",
                        type=VisualType.PIE_CHART,
                        x_axis="category",
                        y_axis="Total Amount",
                    ),
                    VisualElement(
                        title="Details",
                        type=VisualType.TABLE,
                        bindings=VisualBindings(
                            values=[
                                SemanticFieldRef(
                                    table="Sales",
                                    field="category",
                                    kind=SemanticFieldKind.COLUMN,
                                ),
                                SemanticFieldRef(
                                    table="Sales",
                                    field="Total Amount",
                                    kind=SemanticFieldKind.MEASURE,
                                ),
                            ]
                        ),
                    ),
                    VisualElement(
                        title="Category Filter",
                        type=VisualType.SLICER,
                        x_axis="category",
                    ),
                ],
                slicers=["sale_date"],
            )
        ]
    )


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _visual_payloads(report_dir: Path) -> list[dict]:
    return [
        _load_json(path)
        for path in sorted(report_dir.glob("definition/pages/*/visuals/*/visual.json"))
    ]


def _payload_title(payload: dict) -> str:
    literal = payload["visual"]["visualContainerObjects"]["title"][0][
        "properties"
    ]["text"]["expr"]["Literal"]["Value"]
    return literal.strip("'")


def test_report_generator_is_deterministic_valid_and_type_aware():
    plan = _plan()
    first = ReportGenerator(plan).generate_layout()
    second = ReportGenerator(plan).generate_layout()

    assert first.model_dump() == second.model_dump()
    assert len(first.pages) == 1
    page = first.pages[0]
    assert (page.canvas_width, page.canvas_height) == (1280, 720)
    assert len(page.placed_visuals) == 7
    assert len({visual.visual_ref for visual in page.placed_visuals}) == 7
    assert {visual.z_index for visual in page.placed_visuals} == set(range(7))
    assert {visual.tab_order for visual in page.placed_visuals} == set(range(7))
    assert LayoutValidator().validate(first).is_valid

    positions = {
        (
            visual.position.x,
            visual.position.y,
            visual.position.width,
            visual.position.height,
        )
        for visual in page.placed_visuals
    }
    assert len(positions) == len(page.placed_visuals)
    for placed in page.placed_visuals:
        position = placed.position
        assert position.x + position.width <= page.canvas_width
        assert position.y + position.height <= page.canvas_height
        assert position.width >= ReportGenerator.MIN_WIDTH_BY_TYPE[placed.visual.type]
        assert position.height >= ReportGenerator.MIN_HEIGHT_BY_TYPE[placed.visual.type]
        if placed.visual.type == VisualType.CARD:
            assert position.height == ReportGenerator.CARD_HEIGHT
        elif placed.visual.type == VisualType.SLICER:
            assert position.height == ReportGenerator.SLICER_HEIGHT
        else:
            assert position.height >= ReportGenerator.BODY_MIN_HEIGHT


def test_provider_translates_layout_and_keeps_ids_independent_of_positions(
    tmp_path: Path,
):
    plan = _plan()
    semantic = _semantic_project()
    first_layout = ReportGenerator(plan).generate_layout()
    second_layout = first_layout.model_copy(deep=True)
    body = [
        visual
        for visual in second_layout.pages[0].placed_visuals
        if visual.visual.type not in {VisualType.CARD, VisualType.SLICER}
    ]
    body[0].position, body[1].position = body[1].position, body[0].position
    second_layout.pages[0].placed_visuals.reverse()

    provider = PowerBIProvider(project_name="LayoutReport")
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    provider.deploy_dashboard(plan, str(first_output), semantic, first_layout)
    provider.deploy_dashboard(plan, str(second_output), semantic, second_layout)

    first_report = first_output / "LayoutReport.Report"
    second_report = second_output / "LayoutReport.Report"
    first_payloads = _visual_payloads(first_report)
    second_payloads = _visual_payloads(second_report)
    assert _load_json(
        first_report / "definition" / "pages" / "pages.json"
    )["pageOrder"] == ["3ff31b369e3d5345996a"]
    assert {payload["name"] for payload in first_payloads} == {
        "9f4ddaf234bc5275b7d3",
        "aadeb8a926cf50ada508",
        "d513f39a18805f83a23d",
        "641cb5d73d4f5aeba50a",
        "b9cde160b35a530090c9",
        "7fa9cb9665cd558bb06b",
        "56589e4e24205309bba1",
    }
    assert {payload["name"] for payload in first_payloads} == {
        payload["name"] for payload in second_payloads
    }
    assert {
        (payload["name"], tuple(payload["position"].values()))
        for payload in first_payloads
    } != {
        (payload["name"], tuple(payload["position"].values()))
        for payload in second_payloads
    }

    expected_by_title = {
        placed.visual.title: {
            "x": placed.position.x,
            "y": placed.position.y,
            "height": placed.position.height,
            "width": placed.position.width,
            "z": placed.z_index,
            "tabOrder": placed.tab_order,
        }
        for placed in first_layout.pages[0].placed_visuals
    }
    for payload in first_payloads:
        assert payload["position"] == expected_by_title[_payload_title(payload)]

    page_id = _load_json(
        first_report / "definition" / "pages" / "pages.json"
    )["pageOrder"][0]
    page_payload = _load_json(
        first_report / "definition" / "pages" / page_id / "page.json"
    )
    assert (page_payload["width"], page_payload["height"]) == (1280, 720)


def test_provider_rejects_missing_or_ambiguous_visual_association(tmp_path: Path):
    plan = _plan()
    semantic = _semantic_project()
    provider = PowerBIProvider(project_name="InvalidAssociation")

    missing_layout = ReportGenerator(plan).generate_layout()
    missing_layout.pages[0].placed_visuals.pop()
    with pytest.raises(ValueError, match="Falta layout para visuales"):
        provider.deploy_dashboard(
            plan,
            str(tmp_path / "missing"),
            semantic,
            missing_layout,
        )

    ambiguous_layout = ReportGenerator(plan).generate_layout()
    ambiguous_layout.pages[0].placed_visuals.append(
        ambiguous_layout.pages[0].placed_visuals[0].model_copy(deep=True)
    )
    with pytest.raises(ValueError, match="ambigua"):
        provider.deploy_dashboard(
            plan,
            str(tmp_path / "ambiguous"),
            semantic,
            ambiguous_layout,
        )


def test_provider_requires_layout_for_non_empty_plan(tmp_path: Path):
    with pytest.raises(ValueError, match="report_layout es obligatorio"):
        PowerBIProvider().deploy_dashboard(
            _plan(),
            str(tmp_path / "missing-layout"),
            _semantic_project(),
        )


@pytest.mark.parametrize("invalid_kind", ["overlap", "overflow"])
def test_provider_rejects_aabb_overlap_and_overflow(
    tmp_path: Path,
    invalid_kind: str,
):
    plan = _plan()
    layout = ReportGenerator(plan).generate_layout()
    first, second = layout.pages[0].placed_visuals[:2]
    if invalid_kind == "overlap":
        second.position = first.position.model_copy(deep=True)
        expected_message = "Superposición"
    else:
        second.position = Position(x=1200, y=20, width=250, height=100)
        expected_message = "Overflow"

    with pytest.raises(ValueError, match=expected_message):
        PowerBIProvider(project_name="InvalidAABB").deploy_dashboard(
            plan,
            str(tmp_path / invalid_kind),
            _semantic_project(),
            layout,
        )
