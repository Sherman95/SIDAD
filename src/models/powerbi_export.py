from pydantic import BaseModel, Field


class PowerBIExportResult(BaseModel):
    """Resultado portable y auditable de una exportacion PBIP completa."""

    success: bool
    project_path: str | None = None
    semantic_model_path: str | None = None
    report_path: str | None = None
    generated_files: list[str] = Field(default_factory=list)
    message: str
    errors: list[str] = Field(default_factory=list)
