from pydantic import BaseModel, Field

class TransformationLog(BaseModel):
    """
    Registra los metadatos de una transformación para garantizar la trazabilidad.
    Responde a las preguntas de la Sección 10 del documento de diseño.
    """
    action: str = Field(description="QUÉ CAMBIÓ (ej. 'Eliminar duplicados')")
    reason: str = Field(description="POR QUÉ CAMBIÓ (ej. 'Limpieza recomendada por el perfilado')")
    tool_used: str = Field(description="QUÉ HERRAMIENTA LO CAMBIÓ (ej. 'DataCleaner.remove_duplicates')")
    records_affected: int = Field(description="CUÁNTOS REGISTROS FUERON AFECTADOS")

class CleaningReport(BaseModel):
    """
    Agrupa todos los logs de un proceso de limpieza.
    """
    logs: list[TransformationLog] = Field(default_factory=list)
