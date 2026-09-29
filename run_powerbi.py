import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler
from src.tools.modeling.semantic_builder import SemanticBuilder
from src.tools.dashboard.planner import DashboardPlanner
from src.tools.bi.powerbi_provider import PowerBIProvider

def run():
    print("=== Iniciando FASE 5: Integración con Power BI ===\n")
    
    project_root = Path(__file__).resolve().parent
    file_path = project_root / "data" / "processed" / "ventas_limpio.csv"
    output_dir = project_root / "data" / "output" / "powerbi_export"
    
    # Pre-requisitos
    profiler = DataProfiler(file_path)
    diagnostic = profiler.profile()
    
    semantic_builder = SemanticBuilder(diagnostic.profile)
    semantic_project = semantic_builder.build_project(source_path=file_path)
    
    planner = DashboardPlanner(semantic_project)
    dashboard_plan = planner.generate_plan()
    
    # Integración PBI
    print("1. Instanciando Proveedor de BI: Power BI...")
    pbi = PowerBIProvider(source_base_path=project_root)
    
    print("2. Desplegando Modelo Semántico (Generando script TMDL y esqueleto PBIP)...")
    pbi.deploy_semantic_model(semantic_project, output_dir)
    print(f"   -> Creado: Estructura PBIP en {output_dir}")
    
    print("3. Desplegando metadatos raíz del reporte PBIR...")
    pbi.deploy_dashboard(dashboard_plan, output_dir)
    print(f"   -> Creado: Estructura Report en {output_dir}")
    
    print("\nExportación estructural finalizada. Falta validarla experimentalmente en Power BI Desktop.")

if __name__ == "__main__":
    run()
