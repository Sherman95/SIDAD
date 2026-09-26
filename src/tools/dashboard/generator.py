from src.models.dashboard import DashboardPlan, VisualType
from src.models.report_layout import ReportLayout, RenderedPage, PlacedVisual, Position

class ReportGenerator:
    """
    Herramienta determinista que toma un plan de dashboard abstracto (Fase 4)
    y le asigna coordenadas físicas y tamaño (Layout) basándose en reglas 
    heurísticas de diseño de interfaces analíticas (UX/UI para BI).
    """
    def __init__(self, plan: DashboardPlan):
        self.plan = plan

    def generate_layout(self) -> ReportLayout:
        layout = ReportLayout()
        
        # Grid settings (Resolución estándar 1280x720)
        CANVAS_W = 1280
        CANVAS_H = 720
        MARGIN = 20
        HEADER_H = 80 # Espacio reservado para título y filtros globales
        
        for page in self.plan.pages:
            rendered_page = RenderedPage(page_info=page, canvas_width=CANVAS_W, canvas_height=CANVAS_H)
            current_y = HEADER_H
            
            # 1. Posicionar Tarjetas (Cards / KPIs) en la franja superior
            # Prioridad de diseño visual: Los números principales siempre van arriba.
            cards = [v for v in page.visuals if v.type == VisualType.CARD]
            if cards:
                card_w = (CANVAS_W - (MARGIN * (len(cards) + 1))) // len(cards)
                card_h = 100
                current_x = MARGIN
                
                for card in cards:
                    rendered_page.placed_visuals.append(PlacedVisual(
                        visual=card,
                        position=Position(x=current_x, y=current_y, width=card_w, height=card_h)
                    ))
                    current_x += card_w + MARGIN
                current_y += card_h + MARGIN # Salto de línea
                
            # 2. Posicionar el resto de gráficos (Estructura de cuadrícula)
            other_visuals = [v for v in page.visuals if v.type != VisualType.CARD]
            if other_visuals:
                # Calculamos altura restante dinámicamente
                remaining_h = CANVAS_H - current_y - MARGIN
                # Asumimos 2 columnas por defecto para reportes de BI
                cols = 2
                vis_w = (CANVAS_W - (MARGIN * (cols + 1))) // cols
                
                rows_needed = (len(other_visuals) + 1) // 2
                vis_h = max(200, remaining_h // rows_needed) # Mínimo 200px de alto
                
                current_x = MARGIN
                for i, vis in enumerate(other_visuals):
                    # Si es el último visual y sobra espacio en la fila, lo hacemos ocupar el ancho completo
                    is_last_odd = (i == len(other_visuals) - 1) and (len(other_visuals) % 2 != 0)
                    actual_w = (vis_w * 2) + MARGIN if is_last_odd else vis_w
                    
                    rendered_page.placed_visuals.append(PlacedVisual(
                        visual=vis,
                        position=Position(x=current_x, y=current_y, width=actual_w, height=vis_h)
                    ))
                    
                    if is_last_odd or (i + 1) % cols == 0:
                        current_x = MARGIN
                        current_y += vis_h + MARGIN
                    else:
                        current_x += vis_w + MARGIN
                        
            layout.pages.append(rendered_page)
            
        return layout
