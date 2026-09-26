from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class ColumnRole(str, Enum):
    DIMENSION = "Dimension" # Atributos descriptivos, categorías
    METRIC = "Metric"       # Hechos, valores numéricos a agregar
    KEY = "Key"             # Identificadores
    DATE = "Date"           # Eje de tiempo temporal
    UNKNOWN = "Unknown"

class TableType(str, Enum):
    FACT = "Fact"
    DIMENSION = "Dimension"

class SemanticColumn(BaseModel):
    """Representa el contexto de negocio de una columna."""
    name: str = Field(description="Nombre de la columna en el origen")
    role: ColumnRole = Field(description="Rol semántico asignado (Ej. Dimensión o Métrica)")
    description: str = Field(default="", description="Descripción autogenerada o deducida")

class SemanticTable(BaseModel):
    """Representa una entidad dentro del modelo estrella/copo de nieve."""
    name: str = Field(description="Nombre lógico de la tabla")
    table_type: TableType = Field(description="Tipo de tabla: Hechos o Dimensión")
    columns: list[SemanticColumn] = Field(description="Lista de columnas categorizadas")
    primary_key: Optional[str] = Field(default=None, description="Llave primaria si existe")

class KPI(BaseModel):
    """Definición agnóstica de un Indicador Clave de Rendimiento."""
    name: str = Field(description="Nombre legible del KPI (Ej. Ventas Totales)")
    description: str = Field(description="Propósito del KPI")
    aggregation_type: str = Field(description="Tipo de agregación básica (Sum, Average, Count, DistinctCount)")
    base_column: str = Field(description="Columna sobre la que se calcula")
    dax_suggestion: Optional[str] = Field(default=None, description="Expresión DAX sugerida para PowerBI")

class SemanticProject(BaseModel):
    """Agrupa todo el modelo dimensional y las métricas detectadas."""
    tables: list[SemanticTable] = Field(default_factory=list)
    kpis: list[KPI] = Field(default_factory=list)
