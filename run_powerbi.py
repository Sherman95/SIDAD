import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler
from src.tools.modeling.semantic_builder import SemanticBuilder
from src.tools.dashboard.planner import DashboardPlanner
from src.tools.bi.powerbi_provider import PowerBIProvider

def run():
    print("=== Iniciando FASE 5: Integración con Power BI ===\n")
    
    file_path = os.path.join("data", "processed", "ventas_limpio.csv")
    output_dir = os.path.join("data", "output", "powerbi_export")
    
    # Pre-requisitos
    profiler = DataProfiler(file_path)
    diagnostic = profiler.profile()
    
    semantic_builder = SemanticBuilder(diagnostic.profile)
    semantic_project = semantic_builder.build_project()
    
    planner = DashboardPlanner(semantic_project)
    dashboard_plan = planner.generate_plan()
    
    # Integración PBI
    print("1. Instanciando Proveedor de BI: Power BI...")
    pbi = PowerBIProvider()
    
    print("2. Desplegando Modelo Semántico (Generando script TMDL)...")
    pbi.deploy_semantic_model(semantic_project, output_dir)
    print(f"   -> Creado: {os.path.join(output_dir, 'model.tmdl')}")
    
    print("3. Desplegando Estructura de Reporte (PBIP JSON fallback)...")
    pbi.deploy_dashboard(dashboard_plan, output_dir)
    print(f"   -> Creado: {os.path.join(output_dir, 'report_spec.json')}")
    
    print("\n¡Exportación finalizada! Estos archivos pueden ser inyectados en un Power BI Project (.pbip) o Tabular Editor.")

if __name__ == "__main__":
    run()
