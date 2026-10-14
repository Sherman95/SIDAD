from pydantic import BaseModel, Field

from src.models.dashboard import DashboardPage, VisualElement


class Position(BaseModel):
    x: int = Field(ge=0, description="Posición X en píxeles")
    y: int = Field(ge=0, description="Posición Y en píxeles")
    width: int = Field(gt=0, description="Ancho del visual en píxeles")
    height: int = Field(gt=0, description="Alto del visual en píxeles")


class PlacedVisual(BaseModel):
    """Un visual instanciado y posicionado en un lienzo físico."""

    visual_ref: str = Field(
        min_length=1,
        description="Referencia estable al visual de DashboardPlan",
    )
    visual: VisualElement
    position: Position
    z_index: int = Field(default=0, ge=0, description="Orden de profundidad")
    tab_order: int = Field(default=0, ge=0, description="Orden de navegación")


class RenderedPage(BaseModel):
    """Una página con todos sus visuales posicionados físicamente."""

    page_info: DashboardPage
    canvas_width: int = Field(
        default=1280,
        gt=0,
        description="Ancho de página (16:9 estándar)",
    )
    canvas_height: int = Field(default=720, gt=0, description="Alto de página")
    placed_visuals: list[PlacedVisual] = Field(default_factory=list)


class ReportLayout(BaseModel):
    """El reporte visual completo. Listo para renderizado gráfico o traducción a PBIP."""

    pages: list[RenderedPage] = Field(default_factory=list)
