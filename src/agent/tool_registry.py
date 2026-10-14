from pydantic import BaseModel, ValidationError
from typing import Callable, Any
import traceback
import json

class ToolDef(BaseModel):
    name: str
    description: str
    arguments_schema: dict

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[ToolDef, Callable]] = {}
        
    def register(self, name: str, description: str, schema: dict, func: Callable):
        t_def = ToolDef(name=name, description=description, arguments_schema=schema)
        self._tools[name] = (t_def, func)
        
    def get_available_tools_info(self) -> list[dict]:
        return [
            {"name": t_def.name, "description": t_def.description, "schema": t_def.arguments_schema}
            for t_def, _ in self._tools.values()
        ]
        
    def execute(self, name: str, kwargs: dict) -> tuple[bool, str]:
        """Ejecuta la herramienta y devuelve (is_error, result_json_string)"""
        # Guardrails de seguridad (Raw protection)
        if "data/raw" in str(kwargs).replace("\\", "/"):
            # Excepciones válidas: profile y clean como input_path
            if name not in ["profile_dataset", "clean_dataset"]:
                return True, "Error de Seguridad: Prohibido interactuar con data/raw/"
            if name == "clean_dataset" and "output_path" in kwargs and "data/raw" in kwargs["output_path"].replace("\\", "/"):
                return True, "Error de Seguridad: Prohibido escribir transformaciones en data/raw/"
                
        if name not in self._tools:
            return True, f"Error: Tool '{name}' no existe en el registro."
            
        _, func = self._tools[name]
        try:
            # Ejecución real de la herramienta envuelta
            res = func(**kwargs)
            if isinstance(res, BaseModel):
                result_json = res.model_dump_json()
                return not bool(getattr(res, "success", True)), result_json
            return False, res
        except TypeError as e:
            return True, f"Error de Argumentos en tool '{name}': {str(e)}"
        except Exception as e:
            return True, f"Error interno en tool '{name}': {str(e)}\n{traceback.format_exc()}"

# Wrappers para las herramientas existentes (Desacoplan la API interna)
def wrap_profile_dataset(file_path: str) -> str:
    from src.tools.data.profiler import DataProfiler
    p = DataProfiler(file_path)
    return p.profile().model_dump_json()

def wrap_clean_dataset(input_path: str, output_path: str, actions: list) -> str:
    from src.tools.data.cleaner import DataCleaner
    from src.tools.data.loader import load_tabular_dataset
    import json
    from pathlib import Path

    if Path(output_path).suffix.casefold() != ".csv":
        raise ValueError(
            "clean_dataset requiere un output_path CSV para el flujo semantico y Power BI."
        )

    df = load_tabular_dataset(input_path)
    cleaner = DataCleaner(df)
    logs = []
    for act in actions:
        if act["action"] == "remove_duplicates": 
            df, log = cleaner.remove_duplicates()
            cleaner.df = df
            logs.append(log)
        elif act["action"] == "fill_nulls": 
            df, log = cleaner.fill_nulls(act["column"], act["value"], reason="Imputación automática vía Agente")
            cleaner.df = df
            logs.append(log)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(output_path)
    return json.dumps([l.model_dump() for l in logs])

def wrap_build_semantic(diagnostic_json: str, source_path: str) -> str:
    from src.tools.modeling.semantic_builder import SemanticBuilder
    from src.models.profiling import DiagnosticResult
    diag = DiagnosticResult.model_validate_json(diagnostic_json)
    builder = SemanticBuilder(diag.profile)
    return builder.build_project(source_path=source_path).model_dump_json()

def wrap_create_planner(semantic_project_json: str) -> str:
    from src.tools.dashboard.planner import DashboardPlanner
    from src.models.semantic_model import SemanticProject
    sem = SemanticProject.model_validate_json(semantic_project_json)
    return DashboardPlanner(sem).generate_plan().model_dump_json()

def wrap_generate_layout(dashboard_plan_json: str, columns: int = 2) -> str:
    from src.tools.dashboard.generator import ReportGenerator
    from src.models.dashboard import DashboardPlan
    plan = DashboardPlan.model_validate_json(dashboard_plan_json)
    # En un caso real, el generador usaría el parámetro columns
    return ReportGenerator(plan).generate_layout().model_dump_json()

def wrap_validate_layout(layout_json: str) -> str:
    from src.agent.validator import LayoutValidator
    from src.models.report_layout import ReportLayout
    layout = ReportLayout.model_validate_json(layout_json)
    val = LayoutValidator()
    # Si detecta colisiones graves, podemos marcar que no es válido
    return val.validate(layout).model_dump_json()

def wrap_export_to_powerbi(
    semantic_project_json: str | None,
    dashboard_plan_json: str | None,
    report_layout_json: str | None,
    output_path: str,
    project_name: str = "SIDAD",
    source_base_path: str | None = None,
):
    from src.models.dashboard import DashboardPlan
    from src.models.powerbi_export import PowerBIExportResult
    from src.models.report_layout import ReportLayout
    from src.models.semantic_model import SemanticProject
    from src.tools.bi.export_service import export_to_powerbi

    payloads = (
        ("SemanticProject", semantic_project_json, SemanticProject),
        ("DashboardPlan", dashboard_plan_json, DashboardPlan),
        ("ReportLayout", report_layout_json, ReportLayout),
    )
    parsed: dict[str, BaseModel | None] = {}
    errors: list[str] = []
    for label, payload, model_type in payloads:
        if payload is None:
            parsed[label] = None
            errors.append(f"Falta {label}")
            continue
        try:
            parsed[label] = model_type.model_validate_json(payload)
        except (ValidationError, ValueError, TypeError) as exc:
            parsed[label] = None
            errors.append(f"{label} invalido: {exc}")

    if errors:
        return PowerBIExportResult(
            success=False,
            message="No se pudo exportar el proyecto Power BI.",
            errors=errors,
        )

    return export_to_powerbi(
        semantic_project=parsed["SemanticProject"],
        dashboard_plan=parsed["DashboardPlan"],
        report_layout=parsed["ReportLayout"],
        output_path=output_path,
        project_name=project_name,
        source_base_path=source_base_path,
    )

def get_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("profile_dataset", "Analiza la estructura y calidad de un dataset sin modificarlo.", {"file_path": "str"}, wrap_profile_dataset)
    reg.register("clean_dataset", "Limpia datos basándose en el perfilado.", {"input_path": "str", "output_path": "str", "actions": "list"}, wrap_clean_dataset)
    reg.register(
        "build_semantic_model",
        "Deduce roles de negocio y conserva la ruta real del dataset modelado.",
        {"diagnostic_json": "str", "source_path": "str"},
        wrap_build_semantic,
    )
    reg.register("create_dashboard_plan", "Planifica el reporte analítico.", {"semantic_project_json": "str"}, wrap_create_planner)
    reg.register("generate_layout", "Asigna coordenadas matemáticas.", {"dashboard_plan_json": "str", "columns": "int"}, wrap_generate_layout)
    reg.register("validate_layout", "Verifica colisiones visuales AABB.", {"layout_json": "str"}, wrap_validate_layout)
    reg.register(
        "export_to_powerbi",
        "Exporta SemanticProject, DashboardPlan y ReportLayout validados a PBIP/TMDL/PBIR.",
        {
            "semantic_project_json": "str",
            "dashboard_plan_json": "str",
            "report_layout_json": "str",
            "output_path": "str",
            "project_name": "str",
            "source_base_path": "str",
        },
        wrap_export_to_powerbi,
    )
    return reg
