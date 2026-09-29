from pydantic import BaseModel, Field
from typing import Optional, Any
from src.models.profiling import DiagnosticResult
from src.models.transformations import TransformationLog
from src.models.semantic_model import SemanticProject
from src.models.dashboard import DashboardPlan
from src.models.report_layout import ReportLayout
from src.agent.validator import ValidationReport

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
    processed_dataset_path: Optional[str] = None
    
    # Artefactos
    dataset_profile: Optional[DiagnosticResult] = None
    transformation_logs: list[TransformationLog] = []
    semantic_project: Optional[SemanticProject] = None
    dashboard_plan: Optional[DashboardPlan] = None
    report_layout: Optional[ReportLayout] = None
    validation_report: Optional[ValidationReport] = None
    
    # Orquestación y Meta-Datos
    pending_issues: list[str] = []
    critic_verdicts: list[CriticVerdict] = []
    execution_history: list[ActionRecord] = []
    iteration_count: int = 0
    max_iterations: int = 15
    status: str = "IN_PROGRESS" # IN_PROGRESS, SUCCESS, FAILED
    last_tool_result: Optional[str] = None
