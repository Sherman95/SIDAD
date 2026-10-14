from pathlib import Path
from typing import Optional, Any

from pydantic import BaseModel, Field
from src.models.profiling import DiagnosticResult
from src.models.transformations import TransformationLog
from src.models.semantic_model import SemanticProject
from src.models.dashboard import DashboardPlan
from src.models.report_layout import ReportLayout
from src.models.powerbi_export import PowerBIExportResult
from src.agent.validator import ValidationReport


DEFAULT_PROJECT_BASE_PATH = Path(__file__).resolve().parents[2]

class CriticVerdict(BaseModel):
    status: str = Field(description="PASS o FAIL")
    issue: str = Field(description="Descripción del problema")
    severity: str = Field(description="INFO, WARNING, ERROR")
    recommended_action: str = Field(description="Acción sugerida para corregir")
    reason: str = Field(description="Razón de la evaluación")

class ActionRecord(BaseModel):
    step: int
    tool_name: str
    arguments: dict
    operational_reason: str
    result_summary: str
    is_error: bool = False

class AgentState(BaseModel):
    # Contexto Inicial
    user_request: str
    input_dataset_path: str
    current_goal: str
    project_base_path: str = Field(
        default_factory=lambda: str(DEFAULT_PROJECT_BASE_PATH),
        description="Base estable para resolver rutas relativas del flujo",
    )
    powerbi_output_path: str = "data/output/powerbi_export"
    powerbi_project_name: str = "SIDAD"
    processed_dataset_path: Optional[str] = None
    
    # Artefactos
    dataset_profile: Optional[DiagnosticResult] = None
    transformation_logs: list[TransformationLog] = []
    semantic_project: Optional[SemanticProject] = None
    dashboard_plan: Optional[DashboardPlan] = None
    report_layout: Optional[ReportLayout] = None
    validation_report: Optional[ValidationReport] = None
    powerbi_export: Optional[PowerBIExportResult] = None
    
    # Orquestación y Meta-Datos
    pending_issues: list[str] = []
    critic_verdicts: list[CriticVerdict] = []
    execution_history: list[ActionRecord] = []
    iteration_count: int = 0
    max_iterations: int = 15
    status: str = "IN_PROGRESS" # IN_PROGRESS, SUCCESS, FAILED
    last_tool_result: Optional[str] = None

    def resolve_project_path(self, value: str) -> str:
        """Resuelve rutas del agente contra una base explicita, nunca contra el CWD."""

        base_path = Path(self.project_base_path).expanduser()
        if not base_path.is_absolute():
            raise ValueError("project_base_path debe ser una ruta absoluta")
        base_path = base_path.resolve(strict=True)
        if not base_path.is_dir():
            raise ValueError("project_base_path debe apuntar a un directorio")

        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return str(candidate.resolve(strict=False))

        resolved = (base_path / candidate).resolve(strict=False)
        try:
            resolved.relative_to(base_path)
        except ValueError as exc:
            raise ValueError(
                "Una ruta relativa del agente no puede escapar de project_base_path"
            ) from exc
        return str(resolved)
