import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler
from src.tools.modeling.semantic_builder import SemanticBuilder
from src.tools.dashboard.planner import DashboardPlanner

def run():
    print("=== Iniciando FASE 4: Planificación de Dashboard ===\n")
    
    file_path = os.path.join("data", "processed", "ventas_limpio.csv")
    
    # Pre-requisitos: Perfilado -> Modelo Semántico
    profiler = DataProfiler(file_path)
    diagnostic = profiler.profile()
    
    semantic_builder = SemanticBuilder(diagnostic.profile)
    semantic_project = semantic_builder.build_project()
    
    # 1. Ejecutar Planner
    print("1. Diseñando estructura analítica del Dashboard basado en el Modelo Semántico...")
    planner = DashboardPlanner(semantic_project)
    dashboard_plan = planner.generate_plan()
    
    # 2. Imprimir salida
    print("\n=== PLAN DE DASHBOARD GENERADO ===")
    print(f"Tema Visual Sugerido: {dashboard_plan.theme}")
    
    for i, page in enumerate(dashboard_plan.pages, 1):
        print(f"\n- PÁGINA {i}: {page.name}")
        print(f"   Objetivo: {page.objective}")
        print(f"   Slicers (Filtros): {', '.join(page.slicers) if page.slicers else 'Ninguno'}")
        
        print("\n   Visualizaciones:")
        for v in page.visuals:
            print(f"   - [{v.type.value}] {v.title}")
            if v.x_axis or v.y_axis:
                print(f"     Ejes -> X: {v.x_axis} | Y: {v.y_axis}")
            print(f"     Justificación: {v.description}")

    print("\n=== SALIDA ESTRUCTURADA (Lista para Power BI / LLM) ===")
    print("El Agente utilizará esta estructura Pydantic determinista para invocar la API de BI en el futuro.")

if __name__ == "__main__":
    run()
