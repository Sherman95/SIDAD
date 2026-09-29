import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models.dashboard import DashboardPlan
from src.models.profiling import ColumnProfile, DatasetProfile
from src.models.semantic_model import (
    ColumnRole,
    KPI,
    Relationship,
    SemanticColumn,
    SemanticDataType,
    SemanticProject,
    SemanticTable,
    TableType,
)
from src.tools.bi.powerbi_provider import PowerBIProvider
from src.tools.modeling.semantic_builder import SemanticBuilder


def _column(
    name: str,
    role: ColumnRole,
    data_type: SemanticDataType,
) -> SemanticColumn:
    return SemanticColumn(name=name, role=role, data_type=data_type)


def test_semantic_builder_preserves_source_and_physical_types(tmp_path: Path):
    source = tmp_path / "ventas.csv"
    source.write_text(
        "id,fecha,cantidad,total,activo\n1,2026-01-01,3,10.5,true\n",
        encoding="utf-8",
    )
    profile = DatasetProfile(
        row_count=1,
        column_count=5,
        columns=[
            ColumnProfile(name="id", dtype="Int64", unique_count=1),
            ColumnProfile(name="fecha", dtype="String", unique_count=1),
            ColumnProfile(name="cantidad", dtype="Int64", unique_count=2),
            ColumnProfile(name="total", dtype="Float64", unique_count=3),
            ColumnProfile(name="activo", dtype="Boolean", unique_count=2),
        ],
    )

    project = SemanticBuilder(profile).build_project(source_path=source)
    table = project.tables[0]

    assert table.source_path == str(source)
    assert [column.data_type for column in table.columns] == [
        SemanticDataType.INTEGER,
        SemanticDataType.DATETIME,
        SemanticDataType.INTEGER,
        SemanticDataType.DECIMAL,
        SemanticDataType.BOOLEAN,
    ]
    assert next(column for column in table.columns if column.name == "cantidad").role == (
        ColumnRole.METRIC
    )
    assert any(kpi.name == "Total Cantidad" for kpi in project.kpis)
    assert not project.relationships
    assert all(kpi.base_table == table.name for kpi in project.kpis)


@pytest.mark.parametrize(
    ("column_name", "dtype", "expected_role"),
    [
        ("id", "Int64", ColumnRole.KEY),
        ("id_venta", "Int64", ColumnRole.KEY),
        ("producto_id", "Int64", ColumnRole.KEY),
        ("ventaId", "Int64", ColumnRole.KEY),
        ("IDVenta", "Int64", ColumnRole.KEY),
        ("identificador_cliente", "Int64", ColumnRole.KEY),
        ("cantidad", "Int64", ColumnRole.METRIC),
        ("ciudad", "String", ColumnRole.DIMENSION),
    ],
)
def test_semantic_builder_detects_keys_only_from_identifier_tokens(
    column_name: str,
    dtype: str,
    expected_role: ColumnRole,
):
    profile = DatasetProfile(
        row_count=3,
        column_count=1,
        columns=[ColumnProfile(name=column_name, dtype=dtype, unique_count=3)],
    )

    column = SemanticBuilder(profile).build_project().tables[0].columns[0]

    assert column.role == expected_role


def test_semantic_project_rejects_invalid_relationship_endpoint():
    fact = SemanticTable(
        name="Fact",
        table_type=TableType.FACT,
        columns=[_column("dimension_id", ColumnRole.KEY, SemanticDataType.INTEGER)],
    )

    with pytest.raises(ValidationError, match="tabla destino 'Dim'"):
        SemanticProject(
            tables=[fact],
            relationships=[
                Relationship(
                    from_table="Fact",
                    from_column="dimension_id",
                    to_table="Dim",
                    to_column="id",
                )
            ],
        )


def test_powerbi_provider_generates_tmdl_with_real_sources_and_relationships(
    tmp_path: Path,
):
    fact_source = tmp_path / "fact.csv"
    dimension_source = tmp_path / "dimension.csv"
    fact_source.write_text("product_id,amount\n1,10.5\n", encoding="utf-8")
    dimension_source.write_text("product_id,name\n1,Keyboard\n", encoding="utf-8")

    fact = SemanticTable(
        name="Fact Sales",
        table_type=TableType.FACT,
        columns=[
            _column("product_id", ColumnRole.KEY, SemanticDataType.INTEGER),
            _column("amount", ColumnRole.METRIC, SemanticDataType.DECIMAL),
        ],
        source_path=str(fact_source),
    )
    dimension = SemanticTable(
        name="Dim Product",
        table_type=TableType.DIMENSION,
        columns=[
            _column("product_id", ColumnRole.KEY, SemanticDataType.INTEGER),
            _column("name", ColumnRole.DIMENSION, SemanticDataType.STRING),
        ],
        primary_key="product_id",
        source_path=str(dimension_source),
    )
    project = SemanticProject(
        tables=[fact, dimension],
        relationships=[
            Relationship(
                name="Sales to Product",
                from_table="Fact Sales",
                from_column="product_id",
                to_table="Dim Product",
                to_column="product_id",
            )
        ],
        kpis=[
            KPI(
                name="Sales Amount",
                description="Total sales",
                aggregation_type="Sum",
                base_column="amount",
                base_table="Fact Sales",
                dax_suggestion="SUM('Fact Sales'[amount])",
            )
        ],
    )
    output = tmp_path / "export"
    legacy_report_dir = output / "Sales.Report"
    legacy_report_dir.mkdir(parents=True)
    (output / "model.tmdl").write_text("legacy", encoding="utf-8")
    (output / "report_spec.json").write_text("{}", encoding="utf-8")
    (legacy_report_dir / "report_spec.json").write_text("{}", encoding="utf-8")

    provider = PowerBIProvider(project_name="Sales")
    assert provider.deploy_semantic_model(project, str(output))
    assert provider.deploy_dashboard(DashboardPlan(), str(output))

    semantic_dir = output / "Sales.SemanticModel"
    definition_dir = semantic_dir / "definition"
    pbism = json.loads((semantic_dir / "definition.pbism").read_text(encoding="utf-8"))
    pbip = json.loads((output / "Sales.pbip").read_text(encoding="utf-8"))
    pbir = json.loads(
        (output / "Sales.Report" / "definition.pbir").read_text(encoding="utf-8")
    )

    assert pbism["version"] == "4.2"
    assert pbism["$schema"] == provider.PBISM_SCHEMA
    assert pbip["$schema"] == provider.PBIP_SCHEMA
    assert pbir["$schema"] == provider.PBIR_SCHEMA
    assert "byConnection" not in pbir["datasetReference"]
    assert (definition_dir / "database.tmdl").exists()
    assert not (output / "model.tmdl").exists()
    assert not (output / "report_spec.json").exists()
    assert not (legacy_report_dir / "report_spec.json").exists()

    model_tmdl = (definition_dir / "model.tmdl").read_text(encoding="utf-8")
    fact_tmdl = (definition_dir / "tables" / "Fact Sales.tmdl").read_text(
        encoding="utf-8"
    )
    dimension_tmdl = (
        definition_dir / "tables" / "Dim Product.tmdl"
    ).read_text(encoding="utf-8")
    relationships_tmdl = (definition_dir / "relationships.tmdl").read_text(
        encoding="utf-8"
    )

    assert "defaultPowerBIDataSourceVersion: powerBI_V3" in model_tmdl
    assert f'File.Contents("{fact_source.resolve()}")' in fact_tmdl
    assert 'File.Contents("data.csv")' not in fact_tmdl
    assert "Columns=1" not in fact_tmdl
    assert "Encoding = 65001" in fact_tmdl
    assert "Table.PromoteHeaders" in fact_tmdl
    assert "dataType: double" in fact_tmdl
    assert "isKey" in dimension_tmdl
    assert "relationship 'Sales to Product'" in relationships_tmdl
    assert "fromColumn: 'Fact Sales'.'product_id'" in relationships_tmdl
    assert "toColumn: 'Dim Product'.'product_id'" in relationships_tmdl


def test_powerbi_provider_generates_boolean_types_end_to_end(tmp_path: Path):
    source = tmp_path / "flags.csv"
    source.write_text("id,activo\n1,true\n", encoding="utf-8")
    table = SemanticTable(
        name="Flags",
        table_type=TableType.FACT,
        columns=[
            _column("id", ColumnRole.KEY, SemanticDataType.INTEGER),
            _column("activo", ColumnRole.DIMENSION, SemanticDataType.BOOLEAN),
        ],
        source_path=str(source),
    )
    output = tmp_path / "export"

    PowerBIProvider().deploy_semantic_model(
        SemanticProject(tables=[table]),
        str(output),
    )

    table_tmdl = (
        output / "SIDAD.SemanticModel" / "definition" / "tables" / "Flags.tmdl"
    ).read_text(encoding="utf-8")
    assert "dataType: boolean" in table_tmdl
    assert '{"activo", type logical}' in table_tmdl


def test_powerbi_provider_escapes_m_literals_without_escaping_backslashes():
    value = 'C:\\data#(archive)\\ventas "final".csv'

    encoded = PowerBIProvider._m_text(value)

    assert encoded == '"C:\\data#(#)(archive)\\ventas ""final"".csv"'
    assert "C:\\\\data" not in encoded


def test_powerbi_provider_resolves_relative_source_from_explicit_base_not_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    project_root = tmp_path / "project"
    source = project_root / "data" / "processed" / "source#(archive).csv"
    source.parent.mkdir(parents=True)
    source.write_text("id\n1\n", encoding="utf-8")
    unrelated_cwd = tmp_path / "unrelated"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)

    table = SemanticTable(
        name="Fact",
        table_type=TableType.FACT,
        columns=[_column("id", ColumnRole.KEY, SemanticDataType.INTEGER)],
        source_path="data/processed/source#(archive).csv",
    )
    output = tmp_path / "export"
    provider = PowerBIProvider(source_base_path=project_root.resolve())

    provider.deploy_semantic_model(SemanticProject(tables=[table]), str(output))

    table_tmdl = (
        output / "SIDAD.SemanticModel" / "definition" / "tables" / "Fact.tmdl"
    ).read_text(encoding="utf-8")
    expected_source = str(source.resolve()).replace("#(", "#(#)(")
    assert f'File.Contents("{expected_source}")' in table_tmdl


def test_powerbi_provider_requires_a_real_csv_and_removes_stale_relationships(
    tmp_path: Path,
):
    source = tmp_path / "source.csv"
    source.write_text("id\n1\n", encoding="utf-8")
    table = SemanticTable(
        name="Fact",
        table_type=TableType.FACT,
        columns=[_column("id", ColumnRole.KEY, SemanticDataType.INTEGER)],
        primary_key="id",
        source_path=str(source),
    )
    project = SemanticProject(tables=[table])
    output = tmp_path / "export"
    relationships_path = (
        output / "SIDAD.SemanticModel" / "definition" / "relationships.tmdl"
    )
    relationships_path.parent.mkdir(parents=True)
    relationships_path.write_text("stale", encoding="utf-8")
    stale_table_path = relationships_path.parent / "tables" / "Ghost.tmdl"
    stale_table_path.parent.mkdir()
    stale_table_path.write_text("table Ghost", encoding="utf-8")

    PowerBIProvider().deploy_semantic_model(project, str(output))
    assert not relationships_path.exists()
    assert not stale_table_path.exists()

    missing_source_project = SemanticProject(
        tables=[table.model_copy(update={"source_path": str(tmp_path / "missing.csv")})]
    )
    with pytest.raises(FileNotFoundError):
        PowerBIProvider().deploy_semantic_model(missing_source_project, str(output))
