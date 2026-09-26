from typing import Any

from pydantic import BaseModel, Field

class ColumnProfile(BaseModel):
    """
    Representa el perfil estadístico y de estructura de una sola columna.
    """
    name: str = Field(description="Nombre de la columna")
    dtype: str = Field(description="Tipo de dato inferido (e.g., Int64, Float64, String, Date)")
    null_count: int = Field(default=0, description="Cantidad de valores nulos")
    null_percentage: float = Field(default=0.0, description="Porcentaje de valores nulos")
    unique_count: int = Field(default=0, description="Cantidad de valores únicos (cardinalidad)")
    min_value: Any | None = Field(default=None, description="Valor mínimo (si aplica)")
    max_value: Any | None = Field(default=None, description="Valor máximo (si aplica)")
    
class DatasetProfile(BaseModel):
    """
    Representa el perfil global de un conjunto de datos.
    """
    row_count: int = Field(description="Cantidad total de filas")
    column_count: int = Field(description="Cantidad total de columnas")
    duplicate_rows: int = Field(default=0, description="Cantidad de filas completamente duplicadas")
    columns: list[ColumnProfile] = Field(default_factory=list, description="Lista de perfiles de cada columna")

class DiagnosticResult(BaseModel):
    """
    Agrupa el perfil del dataset junto con los problemas detectados y las acciones sugeridas.
    Esta es la salida estructurada de la Fase 1.
    """
    profile: DatasetProfile
    problems_detected: list[str] = Field(
        default_factory=list, 
        description="Lista de problemas detectados (e.g., 'Columna X tiene 50% de nulos')"
    )
    suggested_actions: list[str] = Field(
        default_factory=list, 
        description="Acciones deterministas sugeridas para solucionar los problemas"
    )
