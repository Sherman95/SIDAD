import json
import os
import re
from functools import lru_cache
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from src.models.dashboard import (
    DashboardPage,
    DashboardPlan,
    SemanticFieldKind,
    SemanticFieldRef,
    VisualBindings,
    VisualElement,
    VisualType,
)
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
from src.tools.dashboard.planner import DashboardPlanner


def _column(
    name: str,
    role: ColumnRole,
    data_type: SemanticDataType,
) -> SemanticColumn:
    return SemanticColumn(name=name, role=role, data_type=data_type)


def _semantic_project() -> SemanticProject:
    table = SemanticTable(
        name="Sales",
        table_type=TableType.FACT,
        columns=[
            _column("sale_date", ColumnRole.DATE, SemanticDataType.DATETIME),
            _column("category", ColumnRole.DIMENSION, SemanticDataType.STRING),
            _column("region", ColumnRole.DIMENSION, SemanticDataType.STRING),
            _column("amount", ColumnRole.METRIC, SemanticDataType.DECIMAL),
        ],
    )
    return SemanticProject(
        tables=[table],
        kpis=[
            KPI(
                name="Total Amount",
                description="Total sales amount",
                aggregation_type="Sum",
                base_column="amount",
                base_table="Sales",
                dax_suggestion="SUM('Sales'[amount])",
            )
        ],
    )


def _field(field: str, kind: SemanticFieldKind) -> SemanticFieldRef:
    return SemanticFieldRef(table="Sales", field=field, kind=kind)


def _complete_plan() -> DashboardPlan:
    return DashboardPlan(
        theme="Corporate Light",
        pages=[
            DashboardPage(
                name="Executive Summary",
                objective="Validate PBIR content and semantic bindings",
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
                        kpi_ref="Total Amount",
                    ),
                    VisualElement(
                        title="Details",
                        type=VisualType.TABLE,
                        bindings=VisualBindings(
                            values=[
                                _field("category", SemanticFieldKind.COLUMN),
                                _field("Total Amount", SemanticFieldKind.MEASURE),
                            ]
                        ),
                    ),
                    VisualElement(
                        title="Share by Region",
                        type=VisualType.PIE_CHART,
                        x_axis="region",
                        y_axis="Total Amount",
                    ),
                    VisualElement(
                        title="Region Filter",
                        type=VisualType.SLICER,
                        x_axis="region",
                    ),
                ],
                slicers=["sale_date"],
            ),
            DashboardPage(
                name="Detail",
                objective="Second page for ordering",
                visuals=[
                    VisualElement(
                        title="Raw Amount",
                        type=VisualType.TABLE,
                        x_axis="amount",
                    )
                ],
            ),
        ],
    )


def _layout(plan: DashboardPlan):
    return ReportGenerator(plan).generate_layout()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _visual_payloads(report_dir: Path) -> list[dict]:
    return [
        _load_json(path)
        for path in sorted(report_dir.glob("definition/pages/*/visuals/*/visual.json"))
    ]


def test_pbir_generates_required_tree_page_order_and_all_visual_types(tmp_path: Path):
    output = tmp_path / "export"
    provider = PowerBIProvider(project_name="SalesReport")
    plan = _complete_plan()

    assert provider.deploy_dashboard(
        plan,
        str(output),
        _semantic_project(),
        _layout(plan),
    )

    report_dir = output / "SalesReport.Report"
    definition_dir = report_dir / "definition"
    assert (report_dir / "definition.pbir").is_file()
    assert (definition_dir / "version.json").is_file()
    assert (definition_dir / "report.json").is_file()
    assert (definition_dir / "pages" / "pages.json").is_file()

    pages = _load_json(definition_dir / "pages" / "pages.json")
    assert pages["$schema"] == provider.PBIR_PAGES_SCHEMA
    assert len(pages["pageOrder"]) == 2
    assert pages["activePageName"] == pages["pageOrder"][0]
    assert all(re.fullmatch(r"[0-9a-f]{20}", page_id) for page_id in pages["pageOrder"])

    page_payloads = [
        _load_json(definition_dir / "pages" / page_id / "page.json")
        for page_id in pages["pageOrder"]
    ]
    assert [page["displayName"] for page in page_payloads] == [
        "Executive Summary",
        "Detail",
    ]
    assert all(page["$schema"] == provider.PBIR_PAGE_SCHEMA for page in page_payloads)

    visual_payloads = _visual_payloads(report_dir)
    visual_types = {payload["visual"]["visualType"] for payload in visual_payloads}
    assert visual_types == {
        "cardVisual",
        "clusteredBarChart",
        "lineChart",
        "tableEx",
        "pieChart",
        "slicer",
    }
    assert len(visual_payloads) == 8
    assert all(payload["$schema"] == provider.PBIR_VISUAL_SCHEMA for payload in visual_payloads)
    assert all(re.fullmatch(r"[0-9a-f]{20}", payload["name"]) for payload in visual_payloads)
    assert all("z" in payload["position"] for payload in visual_payloads)
    assert all("tabOrder" in payload["position"] for payload in visual_payloads)


def test_pbir_resolves_columns_measures_table_fields_and_aggregation(tmp_path: Path):
    plan = _complete_plan()
    plan.pages[1].visuals.append(
        VisualElement(
            title="Aggregated Column",
            type=VisualType.BAR_CHART,
            x_axis="category",
            y_axis="amount",
        )
    )
    output = tmp_path / "export"
    PowerBIProvider(project_name="SalesReport").deploy_dashboard(
        plan,
        str(output),
        _semantic_project(),
        _layout(plan),
    )

    payloads = _visual_payloads(output / "SalesReport.Report")
    by_title = {}
    for payload in payloads:
        title_literal = payload["visual"]["visualContainerObjects"]["title"][0][
            "properties"
        ]["text"]["expr"]["Literal"]["Value"]
        by_title[title_literal.strip("'")] = payload

    card_projection = by_title["Total Amount"]["visual"]["query"]["queryState"][
        "Data"
    ]["projections"][0]
    assert card_projection["field"]["Measure"]["Property"] == "Total Amount"
    assert card_projection["queryRef"] == "Sales.Total Amount"

    bar_state = by_title["Amount by Category"]["visual"]["query"]["queryState"]
    assert bar_state["Category"]["projections"][0]["field"]["Column"]["Property"] == (
        "category"
    )
    assert bar_state["Y"]["projections"][0]["field"]["Measure"]["Property"] == (
        "Total Amount"
    )

    table_values = by_title["Details"]["visual"]["query"]["queryState"]["Values"][
        "projections"
    ]
    assert [projection["queryRef"] for projection in table_values] == [
        "Sales.category",
        "Sales.Total Amount",
    ]

    aggregate = by_title["Aggregated Column"]["visual"]["query"]["queryState"][
        "Y"
    ]["projections"][0]
    assert aggregate["queryRef"] == "Sum(Sales.amount)"
    assert aggregate["field"]["Aggregation"]["Function"] == 0


def test_pbir_ids_are_stable_across_output_directories(tmp_path: Path):
    plan = _complete_plan()
    semantic = _semantic_project()
    provider = PowerBIProvider(project_name="Stable")
    first = tmp_path / "first"
    second = tmp_path / "second"

    layout = _layout(plan)
    provider.deploy_dashboard(plan, str(first), semantic, layout)
    provider.deploy_dashboard(plan, str(second), semantic, layout)

    first_report = first / "Stable.Report" / "definition"
    second_report = second / "Stable.Report" / "definition"
    assert _load_json(first_report / "pages" / "pages.json") == _load_json(
        second_report / "pages" / "pages.json"
    )
    assert [payload["name"] for payload in _visual_payloads(first / "Stable.Report")] == [
        payload["name"] for payload in _visual_payloads(second / "Stable.Report")
    ]


def test_pbir_rejects_missing_and_ambiguous_references(tmp_path: Path):
    provider = PowerBIProvider(project_name="Invalid")
    missing_measure = DashboardPlan(
        pages=[
            DashboardPage(
                name="Page",
                objective="",
                visuals=[
                    VisualElement(
                        title="Missing",
                        type=VisualType.CARD,
                        kpi_ref="Does Not Exist",
                    )
                ],
            )
        ]
    )
    with pytest.raises(ValueError, match="Does Not Exist"):
        provider.deploy_dashboard(
            missing_measure,
            str(tmp_path / "missing"),
            _semantic_project(),
            _layout(missing_measure),
        )

    semantic = _semantic_project()
    semantic = semantic.model_copy(
        update={
            "tables": [
                *semantic.tables,
                SemanticTable(
                    name="Targets",
                    table_type=TableType.DIMENSION,
                    columns=[
                        _column(
                            "category",
                            ColumnRole.DIMENSION,
                            SemanticDataType.STRING,
                        )
                    ],
                ),
            ]
        }
    )
    ambiguous_column = DashboardPlan(
        pages=[
            DashboardPage(
                name="Page",
                objective="",
                visuals=[
                    VisualElement(
                        title="Ambiguous",
                        type=VisualType.BAR_CHART,
                        x_axis="category",
                        y_axis="Total Amount",
                    )
                ],
            )
        ]
    )
    with pytest.raises(ValueError, match="ambigua"):
        provider.deploy_dashboard(
            ambiguous_column,
            str(tmp_path / "ambiguous"),
            semantic,
            _layout(ambiguous_column),
        )


def test_pbir_removes_stale_pages_visuals_and_legacy_report(tmp_path: Path):
    output = tmp_path / "export"
    provider = PowerBIProvider(project_name="Stale")
    plan = _complete_plan()
    semantic = _semantic_project()
    provider.deploy_dashboard(plan, str(output), semantic, _layout(plan))

    report_dir = output / "Stale.Report"
    pages_dir = report_dir / "definition" / "pages"
    pages = _load_json(pages_dir / "pages.json")
    first_page = pages_dir / pages["pageOrder"][0]
    initial_visual_dirs = {
        path.name for path in (first_page / "visuals").iterdir() if path.is_dir()
    }
    stale_page = pages_dir / "stale-page"
    stale_visual = first_page / "visuals" / "stale-visual"
    stale_page.mkdir()
    stale_visual.mkdir()
    (report_dir / "report.json").write_text("{}", encoding="utf-8")

    reduced_plan = DashboardPlan(
        pages=[
            DashboardPage(
                name="Executive Summary",
                objective="Validate PBIR content and semantic bindings",
                visuals=[plan.pages[0].visuals[0]],
            )
        ]
    )
    provider.deploy_dashboard(
        reduced_plan,
        str(output),
        semantic,
        _layout(reduced_plan),
    )

    remaining_pages = _load_json(pages_dir / "pages.json")["pageOrder"]
    remaining_visual_dirs = {
        path.name
        for path in (pages_dir / remaining_pages[0] / "visuals").iterdir()
        if path.is_dir()
    }
    assert not stale_page.exists()
    assert not stale_visual.exists()
    assert len(remaining_visual_dirs) == 1
    assert remaining_visual_dirs < initial_visual_dirs
    assert not (report_dir / "report.json").exists()


def test_pbir_requires_semantic_project_for_non_empty_plan(tmp_path: Path):
    with pytest.raises(ValueError, match="semantic es obligatorio"):
        PowerBIProvider().deploy_dashboard(
            _complete_plan(),
            str(tmp_path / "export"),
        )


def test_dashboard_planner_populates_table_with_real_multi_field_bindings():
    plan = DashboardPlanner(_semantic_project()).generate_plan()

    table_visual = next(
        visual
        for page in plan.pages
        for visual in page.visuals
        if visual.type == VisualType.TABLE
    )

    assert table_visual.bindings is not None
    assert [field.field for field in table_visual.bindings.values] == [
        "sale_date",
        "category",
        "region",
        "amount",
    ]
    assert all(field.table == "Sales" for field in table_visual.bindings.values)


def test_pbir_files_use_documented_official_schema_versions(tmp_path: Path):
    output = tmp_path / "export"
    provider = PowerBIProvider(project_name="Schemas")
    plan = _complete_plan()
    provider.deploy_dashboard(
        plan,
        str(output),
        _semantic_project(),
        _layout(plan),
    )
    report_dir = output / "Schemas.Report"
    definition_dir = report_dir / "definition"

    assert _load_json(report_dir / "definition.pbir")["$schema"] == provider.PBIR_SCHEMA
    assert _load_json(definition_dir / "version.json") == {
        "$schema": provider.PBIR_VERSION_SCHEMA,
        "version": "2.0.0",
    }
    assert _load_json(definition_dir / "report.json")["$schema"] == (
        provider.PBIR_REPORT_SCHEMA
    )
    assert _load_json(definition_dir / "pages" / "pages.json")["$schema"] == (
        provider.PBIR_PAGES_SCHEMA
    )


@pytest.mark.skipif(
    os.getenv("SIDAD_VALIDATE_ONLINE_PBIR_SCHEMAS") != "1",
    reason="requiere acceso explicito a los schemas oficiales de Microsoft",
)
def test_generated_pbir_validates_against_live_official_schemas(tmp_path: Path):
    jsonschema = pytest.importorskip("jsonschema")
    referencing = pytest.importorskip("referencing")
    output = tmp_path / "export"
    plan = _complete_plan()
    PowerBIProvider(project_name="LiveSchemas").deploy_dashboard(
        plan,
        str(output),
        _semantic_project(),
        _layout(plan),
    )

    @lru_cache(maxsize=None)
    def fetch_schema(uri: str) -> dict:
        request = Request(uri, headers={"User-Agent": "SIDAD-PBIR-schema-validation"})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def retrieve(uri: str):
        return referencing.Resource.from_contents(fetch_schema(uri))

    registry = referencing.Registry(retrieve=retrieve)
    report_dir = output / "LiveSchemas.Report"
    json_paths = [
        report_dir / "definition.pbir",
        *sorted((report_dir / "definition").rglob("*.json")),
    ]
    for path in json_paths:
        payload = _load_json(path)
        schema = fetch_schema(payload["$schema"])
        validator_class = jsonschema.validators.validator_for(schema)
        validator_class.check_schema(schema)
        validator_class(schema, registry=registry).validate(payload)
