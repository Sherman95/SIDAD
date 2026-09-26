from src.models.semantic_model import SemanticProject, ColumnRole
from src.models.dashboard import DashboardPlan, DashboardPage, VisualElement, VisualType

class DashboardPlanner:
    """
    Herramienta heurística que toma un Modelo Semántico y
    construye un Plan de Dashboard estructurado.
    Separa completamente la intención analítica de la implementación en Power BI.
    """
    def __init__(self, semantic_project: SemanticProject):
        self.semantic = semantic_project

    def generate_plan(self) -> DashboardPlan:
        plan = DashboardPlan(theme="Corporate Dark")
        
        # Obtenemos las dimensiones y fechas
        all_columns = []
        for t in self.semantic.tables:
            all_columns.extend(t.columns)
            
        dates = [c for c in all_columns if c.role == ColumnRole.DATE]
        dimensions = [c for c in all_columns if c.role == ColumnRole.DIMENSION]
        
        # --- PÁGINA 1: Resumen Ejecutivo ---
        exec_page = DashboardPage(
            name="Resumen Ejecutivo",
            objective="Visión global de alto nivel para toma de decisiones rápidas",
        )
        
        # Agregamos Cards para cada KPI principal
        for kpi in self.semantic.kpis:
            exec_page.visuals.append(VisualElement(
                title=kpi.name,
                type=VisualType.CARD,
                kpi_ref=kpi.name,
                description=f"Muestra rápidamente el valor de {kpi.name}"
            ))
            
        # Si hay fecha, agregamos un gráfico de evolución
        if dates and self.semantic.kpis:
            exec_page.visuals.append(VisualElement(
                title="Evolución Temporal",
                type=VisualType.LINE_CHART,
                x_axis=dates[0].name,
                y_axis=self.semantic.kpis[-1].name, # Tomamos uno de los KPIs de métrica
                kpi_ref=self.semantic.kpis[-1].name,
                description="Analiza la tendencia a lo largo del tiempo"
            ))
            
        # Si hay dimensiones, usamos la primera para un gráfico de barras (Top N)
        if dimensions and self.semantic.kpis:
            exec_page.visuals.append(VisualElement(
                title=f"Distribución por {dimensions[0].name.title()}",
                type=VisualType.BAR_CHART,
                x_axis=dimensions[0].name,
                y_axis=self.semantic.kpis[-1].name,
                description=f"Identifica los {dimensions[0].name} de mayor rendimiento"
            ))
            
        # Agregamos Slicers
        if dates:
            exec_page.slicers.append(dates[0].name)
        if dimensions:
            exec_page.slicers.append(dimensions[0].name)
            
        plan.pages.append(exec_page)
        
        # --- PÁGINA 2: Detalles (Solo si hay múltiples dimensiones) ---
        if len(dimensions) > 1:
            detail_page = DashboardPage(
                name="Análisis Detallado",
                objective="Exploración en profundidad de dimensiones secundarias"
            )
            
            detail_page.visuals.append(VisualElement(
                title=f"Desglose por {dimensions[1].name.title()}",
                type=VisualType.PIE_CHART,
                x_axis=dimensions[1].name,
                y_axis=self.semantic.kpis[-1].name,
                description=f"Proporción de mercado por {dimensions[1].name}"
            ))
            
            detail_page.visuals.append(VisualElement(
                title="Tabla de Registros",
                type=VisualType.TABLE,
                description="Vista granular para exportación o auditoría detallada"
            ))
            
            detail_page.slicers.extend([d.name for d in dimensions[:2]])
            plan.pages.append(detail_page)
            
        return plan
