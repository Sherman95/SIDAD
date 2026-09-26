from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

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
