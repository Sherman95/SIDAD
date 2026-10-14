from pydantic import BaseModel, Field, model_validator
from enum import Enum
from typing import Optional


class SemanticFieldKind(str, Enum):
    """Clase portable de campo expuesto por un modelo semantico."""

    COLUMN = "Column"
    MEASURE = "Measure"


class SemanticAggregation(str, Enum):
    """Agregaciones portables que un adaptador de BI puede traducir."""

    SUM = "Sum"
    AVERAGE = "Average"
    DISTINCT_COUNT = "DistinctCount"
    MIN = "Min"
    MAX = "Max"
    COUNT = "Count"


class SemanticFieldRef(BaseModel):
    """Referencia inequivoca a una columna o medida, sin detalles de PBIR."""

    table: str = Field(min_length=1)
    field: str = Field(min_length=1)
    kind: SemanticFieldKind
    aggregation: Optional[SemanticAggregation] = None

    @model_validator(mode="after")
    def validate_aggregation(self) -> "SemanticFieldRef":
        if self.kind == SemanticFieldKind.MEASURE and self.aggregation is not None:
            raise ValueError("Una medida no admite una segunda agregacion")
        return self


class VisualBindings(BaseModel):
    """Roles analiticos portables de un visual, independientes del proveedor."""

    category: Optional[SemanticFieldRef] = None
    values: list[SemanticFieldRef] = Field(default_factory=list)
    series: Optional[SemanticFieldRef] = None

class VisualType(str, Enum):
    CARD = "Card"                 # Para mostrar un KPI único
    BAR_CHART = "BarChart"        # Comparación categórica
    LINE_CHART = "LineChart"      # Evolución temporal
    TABLE = "Table"               # Detalles a nivel de registro
    PIE_CHART = "PieChart"        # Distribución porcentual
    SLICER = "Slicer"             # Filtro interactivo

class VisualElement(BaseModel):
    """Representa una visualización individual en el dashboard."""
    title: str = Field(description="Título visible del gráfico")
    type: VisualType = Field(description="Tipo de gráfico recomendado")
    kpi_ref: Optional[str] = Field(default=None, description="Nombre del KPI asociado, si aplica")
    bindings: Optional[VisualBindings] = Field(
        default=None,
        description="Referencias semanticas inequivocas; conserva compatibilidad con los ejes existentes",
    )
    x_axis: Optional[str] = Field(default=None, description="Dimensión en el eje X")
    y_axis: Optional[str] = Field(default=None, description="Métrica en el eje Y")
    description: str = Field(default="", description="Justificación técnica/de negocio para usar este visual")

class DashboardPage(BaseModel):
    """Representa una pestaña/página dentro del dashboard."""
    name: str = Field(description="Nombre de la página (Ej. Resumen Ejecutivo)")
    objective: str = Field(description="Qué preguntas de negocio responde esta página")
    visuals: list[VisualElement] = Field(default_factory=list, description="Gráficos y tarjetas incluidos")
    slicers: list[str] = Field(default_factory=list, description="Columnas usadas como filtros globales de página")

class DashboardPlan(BaseModel):
    """Abstracción total de la estructura de un Dashboard antes de implementarse en BI."""
    theme: str = Field(default="Corporate Light", description="Estilo visual sugerido")
    pages: list[DashboardPage] = Field(default_factory=list)
