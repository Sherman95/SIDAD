from math import ceil

from src.models.dashboard import DashboardPlan, VisualType
from src.models.report_layout import PlacedVisual, Position, RenderedPage, ReportLayout
from src.tools.dashboard.visual_identity import PageVisualInstance, page_visual_instances


class ReportGenerator:
    """Motor determinista de layout para un canvas base de 1280 x 720."""

    CANVAS_WIDTH = 1280
    CANVAS_HEIGHT = 720
    MARGIN = 20
    CARD_HEIGHT = 100
    SLICER_HEIGHT = 100
    BODY_MIN_HEIGHT = 200
    BODY_MAX_HEIGHT = 440
    MIN_WIDTH_BY_TYPE = {
        VisualType.CARD: 250,
        VisualType.SLICER: 250,
        VisualType.LINE_CHART: 400,
        VisualType.BAR_CHART: 400,
        VisualType.PIE_CHART: 400,
        VisualType.TABLE: 500,
    }
    MIN_HEIGHT_BY_TYPE = {
        VisualType.CARD: CARD_HEIGHT,
        VisualType.SLICER: SLICER_HEIGHT,
        VisualType.LINE_CHART: BODY_MIN_HEIGHT,
        VisualType.BAR_CHART: BODY_MIN_HEIGHT,
        VisualType.PIE_CHART: BODY_MIN_HEIGHT,
        VisualType.TABLE: BODY_MIN_HEIGHT,
    }

    def __init__(self, plan: DashboardPlan):
        self.plan = plan

    def generate_layout(self) -> ReportLayout:
        layout = ReportLayout()

        for dashboard_page in self.plan.pages:
            rendered_page = RenderedPage(
                page_info=dashboard_page,
                canvas_width=self.CANVAS_WIDTH,
                canvas_height=self.CANVAS_HEIGHT,
            )
            instances = page_visual_instances(dashboard_page)
            cards = [item for item in instances if item.visual.type == VisualType.CARD]
            slicers = [
                item for item in instances if item.visual.type == VisualType.SLICER
            ]
            body = [
                item
                for item in instances
                if item.visual.type not in {VisualType.CARD, VisualType.SLICER}
            ]

            current_y = self.MARGIN
            current_y = self._place_fixed_rows(
                rendered_page,
                cards,
                current_y,
                max_columns=4,
                row_height=self.CARD_HEIGHT,
            )
            current_y = self._place_fixed_rows(
                rendered_page,
                slicers,
                current_y,
                max_columns=4,
                row_height=self.SLICER_HEIGHT,
            )
            self._place_body(rendered_page, body, current_y)
            for order, placed_visual in enumerate(rendered_page.placed_visuals):
                placed_visual.z_index = order
                placed_visual.tab_order = order
            layout.pages.append(rendered_page)

        return layout

    def _place_fixed_rows(
        self,
        page: RenderedPage,
        instances: list[PageVisualInstance],
        start_y: int,
        *,
        max_columns: int,
        row_height: int,
    ) -> int:
        if not instances:
            return start_y

        current_y = start_y
        for row_start in range(0, len(instances), max_columns):
            row = instances[row_start : row_start + max_columns]
            width = self._row_item_width(len(row))
            self._require_minimum_width(width, row)
            for column, instance in enumerate(row):
                x = self.MARGIN + column * (width + self.MARGIN)
                page.placed_visuals.append(
                    self._placed_visual(instance, x, current_y, width, row_height)
                )
            current_y += row_height + self.MARGIN
        return current_y

    def _place_body(
        self,
        page: RenderedPage,
        instances: list[PageVisualInstance],
        start_y: int,
    ) -> None:
        if not instances:
            return

        columns = 2
        rows = ceil(len(instances) / columns)
        available_height = page.canvas_height - self.MARGIN - start_y
        row_height = min(
            self.BODY_MAX_HEIGHT,
            (available_height - self.MARGIN * (rows - 1)) // rows,
        )
        required_height = max(
            self.MIN_HEIGHT_BY_TYPE[item.visual.type] for item in instances
        )
        if row_height < required_height:
            raise ValueError(
                f"La página '{page.page_info.name}' no tiene altura suficiente para "
                f"{len(instances)} visuales de contenido en un canvas "
                f"{page.canvas_width}x{page.canvas_height}"
            )

        pair_width = self._row_item_width(columns)
        self._require_minimum_width(pair_width, instances)
        for row_index in range(rows):
            row = instances[row_index * columns : (row_index + 1) * columns]
            width = self._row_item_width(len(row))
            self._require_minimum_width(width, row)
            y = start_y + row_index * (row_height + self.MARGIN)
            for column, instance in enumerate(row):
                x = self.MARGIN + column * (width + self.MARGIN)
                page.placed_visuals.append(
                    self._placed_visual(instance, x, y, width, row_height)
                )

    def _row_item_width(self, item_count: int) -> int:
        inner_width = self.CANVAS_WIDTH - (2 * self.MARGIN)
        return (inner_width - self.MARGIN * (item_count - 1)) // item_count

    def _require_minimum_width(
        self,
        width: int,
        instances: list[PageVisualInstance],
    ) -> None:
        required_width = max(
            self.MIN_WIDTH_BY_TYPE[item.visual.type] for item in instances
        )
        if width < required_width:
            titles = ", ".join(item.visual.title for item in instances)
            raise ValueError(
                f"El canvas no permite un ancho legible para los visuales: {titles}"
            )

    @staticmethod
    def _placed_visual(
        instance: PageVisualInstance,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> PlacedVisual:
        return PlacedVisual(
            visual_ref=instance.visual_ref,
            visual=instance.visual,
            position=Position(x=x, y=y, width=width, height=height),
        )
