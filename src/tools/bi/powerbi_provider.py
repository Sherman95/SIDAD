import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from src.models.dashboard import DashboardPlan
from src.models.semantic_model import (
    ColumnRole,
    CrossFilterDirection,
    KPI,
    Relationship,
    SemanticDataType,
    SemanticProject,
    SemanticTable,
)
from src.tools.bi.provider import BIProvider


class PowerBIProvider(BIProvider):
    """Traduce los modelos de dominio de SIDAD a un proyecto PBIP/TMDL."""

    DEFAULT_SOURCE_BASE_PATH = Path(__file__).resolve().parents[3]

    PBIP_SCHEMA = (
        "https://developer.microsoft.com/json-schemas/fabric/pbip/"
        "pbipProperties/1.0.0/schema.json"
    )
    PBISM_SCHEMA = (
        "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/"
        "definitionProperties/1.0.0/schema.json"
    )
    PBIR_SCHEMA = (
        "https://developer.microsoft.com/json-schemas/fabric/item/report/"
        "definitionProperties/2.0.0/schema.json"
    )

    _TMDL_TYPES = {
        SemanticDataType.STRING: "string",
        SemanticDataType.INTEGER: "int64",
        SemanticDataType.DECIMAL: "double",
        SemanticDataType.DATETIME: "dateTime",
        SemanticDataType.BOOLEAN: "boolean",
    }
    _M_TYPES = {
        SemanticDataType.STRING: "type text",
        SemanticDataType.INTEGER: "Int64.Type",
        SemanticDataType.DECIMAL: "type number",
        SemanticDataType.DATETIME: "type datetime",
        SemanticDataType.BOOLEAN: "type logical",
    }

    def __init__(
        self,
        project_name: str = "SIDAD",
        compatibility_level: int = 1600,
        culture: str = "en-US",
        source_base_path: str | Path | None = None,
    ) -> None:
        self.project_name = self._validate_artifact_name(project_name)
        self.compatibility_level = compatibility_level
        self.culture = culture
        base_path = (
            self.DEFAULT_SOURCE_BASE_PATH
            if source_base_path is None
            else Path(source_base_path).expanduser()
        )
        if not base_path.is_absolute():
            raise ValueError("source_base_path debe ser una ruta absoluta")
        self.source_base_path = base_path.resolve(strict=True)
        if not self.source_base_path.is_dir():
            raise ValueError("source_base_path debe apuntar a un directorio")

    def deploy_semantic_model(self, semantic: SemanticProject, output_path: str) -> bool:
        if not semantic.tables:
            raise ValueError("El proyecto semantico debe contener al menos una tabla")

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        self._remove_if_exists(output_dir / "model.tmdl")
        semantic_model_dir = output_dir / f"{self.project_name}.SemanticModel"
        definition_dir = semantic_model_dir / "definition"
        tables_dir = definition_dir / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)

        table_filenames: dict[str, str] = {}
        for table in semantic.tables:
            table_filenames[table.name] = self._table_filename(table.name)
            self._resolve_csv_source(table)
            for column in table.columns:
                self._type_for(column.data_type, self._TMDL_TYPES, column.name)
                self._type_for(column.data_type, self._M_TYPES, column.name)

        self._write_json(
            output_dir / f"{self.project_name}.pbip",
            {
                "$schema": self.PBIP_SCHEMA,
                "version": "1.0",
                "artifacts": [
                    {"report": {"path": f"{self.project_name}.Report"}}
                ],
                "settings": {"enableAutoRecovery": True},
            },
        )
        self._write_json(
            semantic_model_dir / "definition.pbism",
            {
                "$schema": self.PBISM_SCHEMA,
                "version": "4.2",
                "settings": {"qnaEnabled": False},
            },
        )
        self._write_text(
            definition_dir / "database.tmdl",
            "\n".join(
                [
                    "database",
                    f"\tcompatibilityLevel: {self.compatibility_level}",
                    "\tcompatibilityMode: powerBI",
                    "",
                ]
            ),
        )
        self._write_text(
            definition_dir / "model.tmdl",
            self._serialize_model(semantic),
        )

        for table in semantic.tables:
            table_file = tables_dir / table_filenames[table.name]
            self._write_text(table_file, self._serialize_table(table, semantic.kpis))

        expected_table_files = set(table_filenames.values())
        for existing_table_file in tables_dir.glob("*.tmdl"):
            if existing_table_file.name not in expected_table_files:
                existing_table_file.unlink()

        relationships_path = definition_dir / "relationships.tmdl"
        if semantic.relationships:
            self._write_text(
                relationships_path,
                self._serialize_relationships(semantic.relationships),
            )
        elif relationships_path.exists():
            relationships_path.unlink()

        return True

    def deploy_dashboard(self, plan: DashboardPlan, output_path: str) -> bool:
        """Genera metadatos PBIR raiz; paginas y visuales pertenecen a la fase 12.2."""

        output_dir = Path(output_path)
        report_dir = output_dir / f"{self.project_name}.Report"
        report_dir.mkdir(parents=True, exist_ok=True)
        self._remove_if_exists(output_dir / "report_spec.json")
        self._remove_if_exists(report_dir / "report_spec.json")

        self._write_json(
            report_dir / "definition.pbir",
            {
                "$schema": self.PBIR_SCHEMA,
                "version": "4.0",
                "datasetReference": {
                    "byPath": {"path": f"../{self.project_name}.SemanticModel"}
                },
            },
        )

        return True

    def _serialize_model(self, semantic: SemanticProject) -> str:
        lines = [
            "model Model",
            f"\tculture: {self._tmdl_text(self.culture)}",
            "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
            "",
        ]
        lines.extend(f"ref table {self._identifier(table.name)}" for table in semantic.tables)
        lines.append("")
        return "\n".join(lines)

    def _serialize_table(self, table: SemanticTable, kpis: list[KPI]) -> str:
        source_path = self._resolve_csv_source(table)
        lines = [f"table {self._identifier(table.name)}", ""]

        for kpi in self._kpis_for_table(table, kpis):
            if not kpi.dax_suggestion:
                continue
            lines.extend(
                [
                    f"\tmeasure {self._identifier(kpi.name)} = {kpi.dax_suggestion}",
                    f"\t\tformatString: {self._measure_format(kpi)}",
                    "",
                ]
            )

        for column in table.columns:
            tmdl_type = self._type_for(column.data_type, self._TMDL_TYPES, column.name)
            lines.extend(
                [
                    f"\tcolumn {self._identifier(column.name)}",
                    f"\t\tdataType: {tmdl_type}",
                ]
            )
            if column.name == table.primary_key:
                lines.append("\t\tisKey")
            lines.extend(
                [
                    f"\t\tsourceColumn: {self._tmdl_text(column.name)}",
                    "\t\tsummarizeBy: "
                    + ("sum" if column.role == ColumnRole.METRIC else "none"),
                    "",
                ]
            )

        lines.extend(self._serialize_partition(table, source_path))
        lines.append("")
        return "\n".join(lines)

    def _serialize_partition(self, table: SemanticTable, source_path: Path) -> list[str]:
        type_pairs = ", ".join(
            "{" + self._m_text(column.name) + ", "
            + self._type_for(column.data_type, self._M_TYPES, column.name)
            + "}"
            for column in table.columns
        )
        return [
            f"\tpartition {self._identifier(table.name + '-Partition')} = m",
            "\t\tmode: import",
            "\t\tsource =",
            "\t\t\tlet",
            "\t\t\t\tSource = Csv.Document(",
            f"\t\t\t\t\tFile.Contents({self._m_text(str(source_path))}),",
            "\t\t\t\t\t[Delimiter = \",\", Encoding = 65001, "
            "QuoteStyle = QuoteStyle.Csv]",
            "\t\t\t\t),",
            "\t\t\t\t#\"Promoted Headers\" = Table.PromoteHeaders(",
            "\t\t\t\t\tSource, [PromoteAllScalars = true]",
            "\t\t\t\t),",
            "\t\t\t\t#\"Changed Type\" = Table.TransformColumnTypes(",
            f"\t\t\t\t\t#\"Promoted Headers\", {{{type_pairs}}}, {self._m_text(self.culture)}",
            "\t\t\t\t)",
            "\t\t\tin",
            "\t\t\t\t#\"Changed Type\"",
        ]

    def _serialize_relationships(self, relationships: list[Relationship]) -> str:
        lines: list[str] = []
        for relationship in relationships:
            relationship_name = relationship.name or str(
                uuid5(
                    NAMESPACE_URL,
                    "sidad:"
                    f"{relationship.from_table}.{relationship.from_column}->"
                    f"{relationship.to_table}.{relationship.to_column}",
                )
            )
            lines.extend(
                [
                    f"relationship {self._identifier(relationship_name)}",
                    "\tfromColumn: "
                    f"{self._identifier(relationship.from_table)}."
                    f"{self._identifier(relationship.from_column)}",
                    "\ttoColumn: "
                    f"{self._identifier(relationship.to_table)}."
                    f"{self._identifier(relationship.to_column)}",
                    "\tcrossFilteringBehavior: "
                    + (
                        "bothDirections"
                        if relationship.cross_filter_direction
                        == CrossFilterDirection.BOTH_DIRECTIONS
                        else "oneDirection"
                    ),
                ]
            )
            if not relationship.is_active:
                lines.append("\tisActive: false")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _kpis_for_table(table: SemanticTable, kpis: list[KPI]) -> list[KPI]:
        column_names = {column.name for column in table.columns}
        return [
            kpi
            for kpi in kpis
            if kpi.base_table == table.name
            or (kpi.base_table is None and kpi.base_column in column_names)
        ]

    @staticmethod
    def _measure_format(kpi: KPI) -> str:
        return "0" if kpi.aggregation_type.lower() in {"count", "distinctcount"} else "0.00"

    def _resolve_csv_source(self, table: SemanticTable) -> Path:
        if not table.source_path:
            raise ValueError(
                f"La tabla '{table.name}' no tiene source_path; no se generara una particion ficticia"
            )
        source_path = Path(table.source_path).expanduser()
        if not source_path.is_absolute():
            source_path = self.source_base_path / source_path
        source_path = source_path.resolve(strict=True)
        if source_path.suffix.lower() != ".csv":
            raise ValueError(
                f"La tabla '{table.name}' usa '{source_path.suffix}'. "
                "La exportacion 12.1A solo implementa particiones CSV"
            )
        if "\n" in str(source_path) or "\r" in str(source_path):
            raise ValueError("La ruta del dataset contiene saltos de linea no soportados")
        return source_path

    @staticmethod
    def _type_for(
        data_type: SemanticDataType,
        mapping: dict[SemanticDataType, str],
        column_name: str,
    ) -> str:
        try:
            return mapping[data_type]
        except KeyError as exc:
            raise ValueError(
                f"La columna '{column_name}' no tiene un tipo exportable: {data_type.value}"
            ) from exc

    @staticmethod
    def _identifier(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _tmdl_text(value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    @staticmethod
    def _m_text(value: str) -> str:
        escaped = value.replace("#(", "#(#)(").replace('"', '""')
        return '"' + escaped + '"'

    @staticmethod
    def _table_filename(table_name: str) -> str:
        if (
            table_name in {".", ".."}
            or table_name.endswith((" ", "."))
            or any(character in table_name for character in '<>:"/\\|?*')
        ):
            raise ValueError(
                f"El nombre de tabla '{table_name}' no puede representarse como archivo TMDL"
            )
        return f"{table_name}.tmdl"

    @staticmethod
    def _validate_artifact_name(name: str) -> str:
        if not name or any(character in name for character in '<>:"/\\|?*'):
            raise ValueError(f"Nombre de proyecto Power BI invalido: '{name}'")
        return name

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _remove_if_exists(path: Path) -> None:
        if path.exists():
            path.unlink()
