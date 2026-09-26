import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler
from src.tools.modeling.semantic_builder import SemanticBuilder
from src.tools.dashboard.planner import DashboardPlanner
from src.tools.dashboard.generator import ReportGenerator

def run():
    print("=== Iniciando FASE 6: Generación Automática de Páginas y Visuales ===\n")
    
    file_path = os.path.join("data", "processed", "ventas_limpio.csv")
    
    # Construimos todo el pipeline conceptual anterior
    profiler = DataProfiler(file_path)
    diagnostic = profiler.profile()
    
    semantic_builder = SemanticBuilder(diagnostic.profile)
    semantic_project = semantic_builder.build_project()
    
    planner = DashboardPlanner(semantic_project)
    dashboard_plan = planner.generate_plan()
    
    # Fase 6: Generación y maquetación (UX/UI Analytics)
    print("1. Ejecutando motor de maquetación (Layout Engine)...")
    generator = ReportGenerator(dashboard_plan)
    report_layout = generator.generate_layout()
    
    print("\n=== MAQUETACIÓN FÍSICA GENERADA (Resolución 1280x720) ===")
    for i, page in enumerate(report_layout.pages, 1):
        print(f"\n- PÁGINA {i}: {page.page_info.name}")
        
        for p_vis in page.placed_visuals:
            v = p_vis.visual
            pos = p_vis.position
            print(f"  * [X:{pos.x:<4} Y:{pos.y:<4} | W:{pos.width:<4} H:{pos.height:<4}] -> {v.type.value}: {v.title}")

if __name__ == "__main__":
    run()
