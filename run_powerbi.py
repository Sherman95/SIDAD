import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler
from src.tools.modeling.semantic_builder import SemanticBuilder
from src.tools.dashboard.planner import DashboardPlanner
from src.tools.dashboard.generator import ReportGenerator
from src.tools.bi.export_service import export_to_powerbi

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
    report_layout = ReportGenerator(dashboard_plan).generate_layout()
    
    print("1. Ejecutando export_to_powerbi con modelos tipados...")
    result = export_to_powerbi(
        semantic_project=semantic_project,
        dashboard_plan=dashboard_plan,
        report_layout=report_layout,
        output_path=output_dir,
        project_name="SIDAD",
        source_base_path=project_root,
    )
    if not result.success:
        raise RuntimeError(" | ".join(result.errors))
    print(result.model_dump_json(indent=2))
    
    print("\nExportación PBIP/TMDL/PBIR mediante la herramienta 12.4 finalizada.")

if __name__ == "__main__":
    run()
