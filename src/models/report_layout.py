from pydantic import BaseModel, Field
from src.models.dashboard import VisualElement, DashboardPage

class Position(BaseModel):
    x: int = Field(description="Posición X en píxeles")
    y: int = Field(description="Posición Y en píxeles")
    width: int = Field(description="Ancho del visual en píxeles")
    height: int = Field(description="Alto del visual en píxeles")

class PlacedVisual(BaseModel):
    """Un visual instanciado y posicionado en un lienzo físico."""
    visual: VisualElement
    position: Position
    z_index: int = Field(default=1, description="Orden de profundidad (z-index)")

class RenderedPage(BaseModel):
    """Una página con todos sus visuales posicionados físicamente."""
    page_info: DashboardPage
    canvas_width: int = Field(default=1280, description="Ancho de página (16:9 estándar)")
    canvas_height: int = Field(default=720, description="Alto de página")
    placed_visuals: list[PlacedVisual] = Field(default_factory=list)

class ReportLayout(BaseModel):
    """El reporte visual completo. Listo para renderizado gráfico o traducción a PBIP."""
    pages: list[RenderedPage] = Field(default_factory=list)
