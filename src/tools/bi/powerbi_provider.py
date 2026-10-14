import json
import shutil
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from src.agent.validator import LayoutValidator
from src.models.dashboard import (
    DashboardPage,
    DashboardPlan,
    SemanticAggregation,
    SemanticFieldKind,
    SemanticFieldRef,
    VisualBindings,
    VisualElement,
    VisualType,
)
from src.models.report_layout import PlacedVisual, RenderedPage, ReportLayout
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
from src.tools.dashboard.visual_identity import (
    page_visual_instances,
    visual_fingerprint,
)


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
    PBIR_VERSION_SCHEMA = (
        "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
        "versionMetadata/1.0.0/schema.json"
    )
    PBIR_REPORT_SCHEMA = (
        "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
        "report/3.3.0/schema.json"
    )
    PBIR_PAGES_SCHEMA = (
        "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
        "pagesMetadata/1.1.0/schema.json"
    )
    PBIR_PAGE_SCHEMA = (
        "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
        "page/2.1.0/schema.json"
    )
    PBIR_VISUAL_SCHEMA = (
        "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
        "visualContainer/2.9.0/schema.json"
    )

    PBIR_DEFINITION_VERSION = "2.0.0"
    _VISUAL_TYPES = {
        VisualType.CARD: "cardVisual",
        VisualType.BAR_CHART: "clusteredBarChart",
        VisualType.LINE_CHART: "lineChart",
        VisualType.TABLE: "tableEx",
        VisualType.PIE_CHART: "pieChart",
        VisualType.SLICER: "slicer",
    }
    _AGGREGATION_FUNCTIONS = {
        SemanticAggregation.SUM: 0,
        SemanticAggregation.AVERAGE: 1,
        SemanticAggregation.DISTINCT_COUNT: 2,
        SemanticAggregation.MIN: 3,
        SemanticAggregation.MAX: 4,
        SemanticAggregation.COUNT: 5,
    }

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

    def deploy_dashboard(
        self,
        plan: DashboardPlan,
        output_path: str,
        semantic: SemanticProject | None = None,
        report_layout: ReportLayout | None = None,
    ) -> bool:
        """Traduce contenido, bindings y un ReportLayout ya calculado a PBIR."""

        if plan.pages and semantic is None:
            raise ValueError(
                "semantic es obligatorio para resolver los bindings de un DashboardPlan con paginas"
            )
        if plan.pages and report_layout is None:
            raise ValueError(
                "report_layout es obligatorio para posicionar un DashboardPlan con paginas"
            )
        self._validate_unique_page_names(plan)
        if report_layout is None:
            report_layout = ReportLayout()
        layout_pages = self._associate_layout(plan, report_layout)
        self._validate_layout(report_layout)

        output_dir = Path(output_path)
        report_dir = output_dir / f"{self.project_name}.Report"
        definition_dir = report_dir / "definition"
        pages_dir = definition_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        self._remove_if_exists(output_dir / "report_spec.json")
        self._remove_if_exists(report_dir / "report_spec.json")
        self._remove_if_exists(report_dir / "report.json")

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
        self._write_json(
            definition_dir / "version.json",
            {
                "$schema": self.PBIR_VERSION_SCHEMA,
                "version": self.PBIR_DEFINITION_VERSION,
            },
        )
        self._write_json(
            definition_dir / "report.json",
            {
                "$schema": self.PBIR_REPORT_SCHEMA,
                "themeCollection": {},
                "annotations": [
                    {"name": "sidad.theme", "value": plan.theme},
                    {"name": "sidad.phase", "value": "12.3"},
                ],
            },
        )

        page_ids = [self._page_id(page) for page in plan.pages]
        pages_metadata: dict[str, object] = {
            "$schema": self.PBIR_PAGES_SCHEMA,
            "pageOrder": page_ids,
        }
        if page_ids:
            pages_metadata["activePageName"] = page_ids[0]
        self._write_json(pages_dir / "pages.json", pages_metadata)

        expected_page_ids = set(page_ids)
        for page, page_id in zip(plan.pages, page_ids):
            rendered_page, placements = layout_pages[page.name]
            self._write_pbir_page(
                page,
                page_id,
                semantic,
                rendered_page,
                placements,
                pages_dir,
            )
        self._remove_stale_directories(pages_dir, expected_page_ids)

        return True

    @staticmethod
    def _validate_unique_page_names(plan: DashboardPlan) -> None:
        page_names = [page.name for page in plan.pages]
        if len(page_names) != len(set(page_names)):
            raise ValueError("DashboardPlan contiene nombres de pagina duplicados")

    def _associate_layout(
        self,
        plan: DashboardPlan,
        report_layout: ReportLayout,
    ) -> dict[str, tuple[RenderedPage, dict[str, PlacedVisual]]]:
        pages_by_name: dict[str, RenderedPage] = {}
        for rendered_page in report_layout.pages:
            page_name = rendered_page.page_info.name
            if page_name in pages_by_name:
                raise ValueError(
                    f"La asociacion de layout para la pagina '{page_name}' es ambigua"
                )
            pages_by_name[page_name] = rendered_page

        expected_page_names = {page.name for page in plan.pages}
        actual_page_names = set(pages_by_name)
        missing_pages = sorted(expected_page_names - actual_page_names)
        extra_pages = sorted(actual_page_names - expected_page_names)
        if missing_pages:
            raise ValueError(
                "Falta layout para las paginas: " + ", ".join(missing_pages)
            )
        if extra_pages:
            raise ValueError(
                "ReportLayout contiene paginas no declaradas en DashboardPlan: "
                + ", ".join(extra_pages)
            )

        associations: dict[
            str,
            tuple[RenderedPage, dict[str, PlacedVisual]],
        ] = {}
        for page in plan.pages:
            rendered_page = pages_by_name[page.name]
            placements: dict[str, PlacedVisual] = {}
            for placed_visual in rendered_page.placed_visuals:
                visual_ref = placed_visual.visual_ref
                if visual_ref in placements:
                    raise ValueError(
                        f"La asociacion del visual_ref '{visual_ref}' en la pagina "
                        f"'{page.name}' es ambigua"
                    )
                placements[visual_ref] = placed_visual

            expected_instances = page_visual_instances(page)
            expected_by_ref = {
                instance.visual_ref: instance for instance in expected_instances
            }
            missing_visuals = sorted(set(expected_by_ref) - set(placements))
            extra_visuals = sorted(set(placements) - set(expected_by_ref))
            if missing_visuals:
                raise ValueError(
                    f"Falta layout para visuales de la pagina '{page.name}': "
                    + ", ".join(missing_visuals)
                )
            if extra_visuals:
                raise ValueError(
                    f"ReportLayout contiene visuales no declarados en la pagina "
                    f"'{page.name}': "
                    + ", ".join(extra_visuals)
                )

            for visual_ref, instance in expected_by_ref.items():
                placed_visual = placements[visual_ref]
                if visual_fingerprint(placed_visual.visual) != instance.fingerprint:
                    raise ValueError(
                        f"La asociacion del visual_ref '{visual_ref}' en la pagina "
                        f"'{page.name}' no corresponde al visual de DashboardPlan"
                    )
            associations[page.name] = (rendered_page, placements)

        return associations

    @staticmethod
    def _validate_layout(report_layout: ReportLayout) -> None:
        validation = LayoutValidator().validate(report_layout)
        errors = [
            issue.description
            for issue in validation.issues
            if issue.level == "Error"
        ]
        if errors:
            raise ValueError("ReportLayout invalido: " + " | ".join(errors))

    def _page_id(self, page: DashboardPage) -> str:
        return uuid5(
            NAMESPACE_URL,
            f"sidad:{self.project_name}:page:{page.name}",
        ).hex[:20]

    def _visual_id(
        self,
        page_id: str,
        visual: VisualElement,
        occurrence: int,
    ) -> str:
        canonical_visual = visual_fingerprint(visual)
        return uuid5(
            NAMESPACE_URL,
            f"sidad:{self.project_name}:visual:{page_id}:{canonical_visual}:{occurrence}",
        ).hex[:20]

    def _write_pbir_page(
        self,
        page: DashboardPage,
        page_id: str,
        semantic: SemanticProject | None,
        rendered_page: RenderedPage,
        placements: dict[str, PlacedVisual],
        pages_dir: Path,
    ) -> None:
        if semantic is None:
            raise ValueError("semantic es obligatorio para generar paginas PBIR")

        page_dir = pages_dir / page_id
        visuals_dir = page_dir / "visuals"
        visuals_dir.mkdir(parents=True, exist_ok=True)
        page_annotations = [
            {
                "name": "sidad.layout",
                "value": "posicion y tamano generados por ReportLayout en Fase 12.3",
            }
        ]
        if page.objective:
            page_annotations.append({"name": "sidad.objective", "value": page.objective})
        self._write_json(
            page_dir / "page.json",
            {
                "$schema": self.PBIR_PAGE_SCHEMA,
                "name": page_id,
                "displayName": page.name,
                "displayOption": "FitToPage",
                "height": rendered_page.canvas_height,
                "width": rendered_page.canvas_width,
                "annotations": page_annotations,
            },
        )

        expected_visual_ids: set[str] = set()
        for instance in page_visual_instances(page):
            visual = instance.visual
            visual_id = self._visual_id(page_id, visual, instance.occurrence)
            expected_visual_ids.add(visual_id)
            visual_dir = visuals_dir / visual_id
            visual_dir.mkdir(parents=True, exist_ok=True)
            self._write_json(
                visual_dir / "visual.json",
                self._serialize_pbir_visual(
                    visual,
                    visual_id,
                    semantic,
                    placements[instance.visual_ref],
                ),
            )

        self._remove_stale_directories(visuals_dir, expected_visual_ids)

    def _serialize_pbir_visual(
        self,
        visual: VisualElement,
        visual_id: str,
        semantic: SemanticProject,
        placed_visual: PlacedVisual,
    ) -> dict:
        try:
            visual_type = self._VISUAL_TYPES[visual.type]
        except KeyError as exc:
            raise ValueError(f"VisualType no soportado por PBIR: {visual.type}") from exc

        bindings = self._resolve_visual_bindings(visual, semantic)
        query_state = self._query_state_for(visual.type, bindings, semantic)
        annotations = [{"name": "sidad.layout", "value": "ReportLayout Fase 12.3"}]
        if visual.description:
            annotations.append({"name": "sidad.description", "value": visual.description})

        visual_config: dict[str, object] = {
            "visualType": visual_type,
            "query": {"queryState": query_state},
        }
        if visual.title:
            visual_config["visualContainerObjects"] = {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {
                                "expr": {
                                    "Literal": {
                                        "Value": self._pbir_string_literal(visual.title)
                                    }
                                }
                            },
                        }
                    }
                ]
            }

        return {
            "$schema": self.PBIR_VISUAL_SCHEMA,
            "name": visual_id,
            "position": {
                "x": placed_visual.position.x,
                "y": placed_visual.position.y,
                "height": placed_visual.position.height,
                "width": placed_visual.position.width,
                "z": placed_visual.z_index,
                "tabOrder": placed_visual.tab_order,
            },
            "visual": visual_config,
            "annotations": annotations,
        }

    def _resolve_visual_bindings(
        self,
        visual: VisualElement,
        semantic: SemanticProject,
    ) -> VisualBindings:
        if visual.bindings is not None:
            if visual.kpi_ref:
                self._resolve_legacy_field(
                    visual.kpi_ref,
                    semantic,
                    allow_columns=False,
                    allow_measures=True,
                )
            if visual.x_axis:
                self._resolve_legacy_field(
                    visual.x_axis,
                    semantic,
                    allow_columns=True,
                    allow_measures=True,
                )
            if visual.y_axis:
                self._resolve_legacy_field(
                    visual.y_axis,
                    semantic,
                    allow_columns=True,
                    allow_measures=True,
                )
            return VisualBindings(
                category=(
                    self._validate_field_ref(visual.bindings.category, semantic)
                    if visual.bindings.category
                    else None
                ),
                values=[
                    self._validate_field_ref(field_ref, semantic)
                    for field_ref in visual.bindings.values
                ],
                series=(
                    self._validate_field_ref(visual.bindings.series, semantic)
                    if visual.bindings.series
                    else None
                ),
            )

        if visual.type == VisualType.CARD:
            value_name = visual.kpi_ref or visual.y_axis
            if not value_name:
                raise ValueError(f"El visual Card '{visual.title}' requiere una medida")
            value = self._resolve_legacy_field(
                value_name,
                semantic,
                allow_columns=False,
                allow_measures=True,
            )
            if visual.kpi_ref and visual.y_axis:
                y_value = self._resolve_legacy_field(
                    visual.y_axis,
                    semantic,
                    allow_columns=False,
                    allow_measures=True,
                )
                self._require_same_field(value, y_value, visual.title)
            return VisualBindings(values=[value])

        if visual.type in {
            VisualType.BAR_CHART,
            VisualType.LINE_CHART,
            VisualType.PIE_CHART,
        }:
            if not visual.x_axis:
                raise ValueError(f"El visual '{visual.title}' requiere x_axis")
            category = self._resolve_legacy_field(
                visual.x_axis,
                semantic,
                allow_columns=True,
                allow_measures=False,
            )
            value_name = visual.y_axis or visual.kpi_ref
            if not value_name:
                raise ValueError(f"El visual '{visual.title}' requiere y_axis o kpi_ref")
            value = self._resolve_legacy_field(
                value_name,
                semantic,
                allow_columns=True,
                allow_measures=True,
                aggregate_columns=True,
            )
            if visual.kpi_ref:
                kpi_value = self._resolve_legacy_field(
                    visual.kpi_ref,
                    semantic,
                    allow_columns=False,
                    allow_measures=True,
                )
                if visual.y_axis:
                    self._require_same_field(value, kpi_value, visual.title)
            return VisualBindings(category=category, values=[value])

        if visual.type == VisualType.TABLE:
            value_names = [
                field_name
                for field_name in (visual.x_axis, visual.y_axis, visual.kpi_ref)
                if field_name
            ]
            values: list[SemanticFieldRef] = []
            for field_name in value_names:
                resolved = self._resolve_legacy_field(
                    field_name,
                    semantic,
                    allow_columns=True,
                    allow_measures=True,
                )
                if resolved not in values:
                    values.append(resolved)
            return VisualBindings(values=values)

        if visual.type == VisualType.SLICER:
            if not visual.x_axis:
                raise ValueError(f"El visual Slicer '{visual.title}' requiere x_axis")
            category = self._resolve_legacy_field(
                visual.x_axis,
                semantic,
                allow_columns=True,
                allow_measures=False,
            )
            return VisualBindings(category=category)

        raise ValueError(f"VisualType no soportado por PBIR: {visual.type}")

    def _query_state_for(
        self,
        visual_type: VisualType,
        bindings: VisualBindings,
        semantic: SemanticProject,
    ) -> dict:
        if visual_type == VisualType.CARD:
            if not bindings.values:
                raise ValueError("Card requiere al menos una medida")
            values = [self._require_measure(field_ref) for field_ref in bindings.values]
            return {"Data": {"projections": [self._projection(ref) for ref in values]}}

        if visual_type in {
            VisualType.BAR_CHART,
            VisualType.LINE_CHART,
            VisualType.PIE_CHART,
        }:
            if bindings.category is None or not bindings.values:
                raise ValueError(f"{visual_type.value} requiere categoria y valores")
            category = self._require_column(bindings.category, "category")
            values = [self._ensure_chart_value(ref, semantic) for ref in bindings.values]
            query_state: dict[str, object] = {
                "Category": {"projections": [self._projection(category)]},
                "Y": {"projections": [self._projection(ref) for ref in values]},
            }
            if bindings.series is not None:
                series = self._require_column(bindings.series, "series")
                query_state["Series"] = {"projections": [self._projection(series)]}
            return query_state

        if visual_type == VisualType.TABLE:
            return {
                "Values": {
                    "projections": [self._projection(ref) for ref in bindings.values]
                }
            }

        if visual_type == VisualType.SLICER:
            slicer_fields = (
                [bindings.category]
                if bindings.category is not None
                else bindings.values
            )
            if len(slicer_fields) != 1:
                raise ValueError("Slicer requiere exactamente una columna")
            field_ref = self._require_column(slicer_fields[0], "slicer")
            return {"Values": {"projections": [self._projection(field_ref)]}}

        raise ValueError(f"VisualType no soportado por PBIR: {visual_type}")

    def _resolve_legacy_field(
        self,
        field_name: str,
        semantic: SemanticProject,
        *,
        allow_columns: bool,
        allow_measures: bool,
        aggregate_columns: bool = False,
    ) -> SemanticFieldRef:
        measure_matches = (
            self._measure_refs_named(field_name, semantic) if allow_measures else []
        )
        if len(measure_matches) > 1:
            raise ValueError(f"La medida '{field_name}' es ambigua entre varias tablas")
        if measure_matches:
            return measure_matches[0]

        column_matches = (
            self._column_refs_named(field_name, semantic) if allow_columns else []
        )
        if not column_matches and allow_columns:
            qualified = self._qualified_column_ref(field_name, semantic)
            if qualified is not None:
                column_matches = [qualified]
        if len(column_matches) > 1:
            tables = ", ".join(sorted(ref.table for ref in column_matches))
            raise ValueError(
                f"La columna '{field_name}' es ambigua; existe en las tablas: {tables}"
            )
        if column_matches:
            field_ref = column_matches[0]
            if aggregate_columns:
                return self._with_default_aggregation(field_ref, semantic)
            return field_ref

        expected = []
        if allow_columns:
            expected.append("columna")
        if allow_measures:
            expected.append("medida")
        raise ValueError(
            f"La referencia '{field_name}' no corresponde a ninguna {' o '.join(expected)} del SemanticProject"
        )

    def _validate_field_ref(
        self,
        field_ref: SemanticFieldRef,
        semantic: SemanticProject,
    ) -> SemanticFieldRef:
        if field_ref.kind == SemanticFieldKind.COLUMN:
            table = next(
                (table for table in semantic.tables if table.name == field_ref.table),
                None,
            )
            if table is None:
                raise ValueError(f"La tabla '{field_ref.table}' no existe")
            column = next(
                (column for column in table.columns if column.name == field_ref.field),
                None,
            )
            if column is None:
                raise ValueError(
                    f"La columna '{field_ref.table}.{field_ref.field}' no existe"
                )
            if field_ref.aggregation in {
                SemanticAggregation.SUM,
                SemanticAggregation.AVERAGE,
            } and column.data_type not in {
                SemanticDataType.INTEGER,
                SemanticDataType.DECIMAL,
            }:
                raise ValueError(
                    f"{field_ref.aggregation.value} requiere una columna numerica; "
                    f"'{field_ref.table}.{field_ref.field}' es {column.data_type.value}"
                )
            return field_ref

        matches = [
            candidate
            for candidate in self._measure_refs_named(field_ref.field, semantic)
            if candidate.table == field_ref.table
        ]
        if not matches:
            raise ValueError(
                f"La medida '{field_ref.table}.{field_ref.field}' no existe o no tiene DAX"
            )
        if len(matches) > 1:
            raise ValueError(f"La medida '{field_ref.table}.{field_ref.field}' es ambigua")
        return matches[0]

    def _measure_refs_named(
        self,
        measure_name: str,
        semantic: SemanticProject,
    ) -> list[SemanticFieldRef]:
        matches: list[SemanticFieldRef] = []
        for kpi in semantic.kpis:
            if kpi.name != measure_name:
                continue
            if not kpi.dax_suggestion:
                continue
            table_name = kpi.base_table
            if table_name is None:
                owners = [
                    table.name
                    for table in semantic.tables
                    if any(column.name == kpi.base_column for column in table.columns)
                ]
                if len(owners) != 1:
                    continue
                table_name = owners[0]
            matches.append(
                SemanticFieldRef(
                    table=table_name,
                    field=kpi.name,
                    kind=SemanticFieldKind.MEASURE,
                )
            )
        return matches

    @staticmethod
    def _column_refs_named(
        column_name: str,
        semantic: SemanticProject,
    ) -> list[SemanticFieldRef]:
        return [
            SemanticFieldRef(
                table=table.name,
                field=column.name,
                kind=SemanticFieldKind.COLUMN,
            )
            for table in semantic.tables
            for column in table.columns
            if column.name == column_name
        ]

    @staticmethod
    def _qualified_column_ref(
        value: str,
        semantic: SemanticProject,
    ) -> SemanticFieldRef | None:
        for table in semantic.tables:
            candidates = (f"{table.name}.{column.name}" for column in table.columns)
            for column, qualified_name in zip(table.columns, candidates):
                if value in {qualified_name, f"{table.name}[{column.name}]"}:
                    return SemanticFieldRef(
                        table=table.name,
                        field=column.name,
                        kind=SemanticFieldKind.COLUMN,
                    )
        return None

    def _with_default_aggregation(
        self,
        field_ref: SemanticFieldRef,
        semantic: SemanticProject,
    ) -> SemanticFieldRef:
        table = next(table for table in semantic.tables if table.name == field_ref.table)
        column = next(column for column in table.columns if column.name == field_ref.field)
        if column.role != ColumnRole.METRIC or column.data_type not in {
            SemanticDataType.INTEGER,
            SemanticDataType.DECIMAL,
        }:
            raise ValueError(
                f"La columna '{field_ref.table}.{field_ref.field}' no puede usarse "
                "como valor sin una agregacion explicita"
            )
        return field_ref.model_copy(update={"aggregation": SemanticAggregation.SUM})

    def _ensure_chart_value(
        self,
        field_ref: SemanticFieldRef,
        semantic: SemanticProject,
    ) -> SemanticFieldRef:
        if field_ref.kind == SemanticFieldKind.MEASURE or field_ref.aggregation is not None:
            return field_ref
        return self._with_default_aggregation(field_ref, semantic)

    @staticmethod
    def _require_measure(field_ref: SemanticFieldRef) -> SemanticFieldRef:
        if field_ref.kind != SemanticFieldKind.MEASURE:
            raise ValueError(
                f"'{field_ref.table}.{field_ref.field}' debe ser una medida para Card"
            )
        return field_ref

    @staticmethod
    def _require_column(
        field_ref: SemanticFieldRef,
        binding_name: str,
    ) -> SemanticFieldRef:
        if field_ref.kind != SemanticFieldKind.COLUMN or field_ref.aggregation is not None:
            raise ValueError(
                f"El binding {binding_name} requiere una columna sin agregacion"
            )
        return field_ref

    @staticmethod
    def _require_same_field(
        first: SemanticFieldRef,
        second: SemanticFieldRef,
        visual_title: str,
    ) -> None:
        if (first.table, first.field, first.kind) != (
            second.table,
            second.field,
            second.kind,
        ):
            raise ValueError(
                f"El visual '{visual_title}' declara kpi_ref y y_axis incompatibles"
            )

    def _projection(self, field_ref: SemanticFieldRef) -> dict:
        return {
            "field": self._field_expression(field_ref),
            "queryRef": self._query_ref(field_ref),
            "nativeQueryRef": field_ref.field,
            "active": True,
        }

    def _field_expression(self, field_ref: SemanticFieldRef) -> dict:
        source_ref = {"SourceRef": {"Entity": field_ref.table}}
        if field_ref.kind == SemanticFieldKind.MEASURE:
            return {
                "Measure": {
                    "Expression": source_ref,
                    "Property": field_ref.field,
                }
            }
        column_expression = {
            "Column": {
                "Expression": source_ref,
                "Property": field_ref.field,
            }
        }
        if field_ref.aggregation is None:
            return column_expression
        return {
            "Aggregation": {
                "Expression": column_expression,
                "Function": self._AGGREGATION_FUNCTIONS[field_ref.aggregation],
            }
        }

    @staticmethod
    def _query_ref(field_ref: SemanticFieldRef) -> str:
        base_ref = f"{field_ref.table}.{field_ref.field}"
        if field_ref.aggregation is None:
            return base_ref
        return f"{field_ref.aggregation.value}({base_ref})"

    @staticmethod
    def _pbir_string_literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _remove_stale_directories(parent: Path, expected_names: set[str]) -> None:
        for child in parent.iterdir():
            if child.is_dir() and child.name not in expected_names:
                shutil.rmtree(child)

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
