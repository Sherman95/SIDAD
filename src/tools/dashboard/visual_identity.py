import json
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from src.models.dashboard import DashboardPage, VisualElement, VisualType


@dataclass(frozen=True)
class PageVisualInstance:
    """Instancia estable de un visual dentro de una pagina del plan."""

    occurrence: int
    fingerprint: str
    visual_ref: str
    visual: VisualElement


def visual_fingerprint(visual: VisualElement) -> str:
    """Representacion canonica compartida por layout y adaptadores de BI."""

    return json.dumps(
        visual.model_dump(mode="json", exclude_none=True),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def page_visuals(page: DashboardPage) -> list[VisualElement]:
    """Expande los slicers declarativos sin introducir conceptos de PBIR."""

    visuals = list(page.visuals)
    visuals.extend(
        VisualElement(
            title=f"Filtro: {field_name}",
            type=VisualType.SLICER,
            x_axis=field_name,
            description="Filtro de pagina definido por DashboardPage.slicers",
        )
        for field_name in page.slicers
    )
    return visuals


def page_visual_instances(page: DashboardPage) -> list[PageVisualInstance]:
    """Asigna una referencia estable incluso cuando hay visuales repetidos."""

    occurrence_by_fingerprint: dict[str, int] = {}
    instances: list[PageVisualInstance] = []
    for visual in page_visuals(page):
        fingerprint = visual_fingerprint(visual)
        occurrence = occurrence_by_fingerprint.get(fingerprint, 0)
        occurrence_by_fingerprint[fingerprint] = occurrence + 1
        visual_ref = uuid5(
            NAMESPACE_URL,
            f"sidad:layout:{page.name}:{fingerprint}:{occurrence}",
        ).hex[:20]
        instances.append(
            PageVisualInstance(
                occurrence=occurrence,
                fingerprint=fingerprint,
                visual_ref=visual_ref,
                visual=visual,
            )
        )
    return instances
