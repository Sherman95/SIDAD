import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler
from src.tools.modeling.semantic_builder import SemanticBuilder
from src.tools.dashboard.planner import DashboardPlanner
from src.tools.dashboard.generator import ReportGenerator
from src.agent.validator import LayoutValidator

def run():
    print("=== Iniciando FASE 7: Validación Visual ===\n")
    
    file_path = os.path.join("data", "processed", "ventas_limpio.csv")
    
    profiler = DataProfiler(file_path)
    semantic_project = SemanticBuilder(profiler.profile().profile).build_project(
        source_path=file_path
    )
    dashboard_plan = DashboardPlanner(semantic_project).generate_plan()
    report_layout = ReportGenerator(dashboard_plan).generate_layout()
    
    validator = LayoutValidator()
    
    print("1. Ejecutando validación sobre el Layout Original (Debería ser perfecto)...")
    report = validator.validate(report_layout)
    print(f"Estado del Layout: {'VALIDO' if report.is_valid else 'INVALIDO'}")
    for i in report.issues:
        print(f"[{i.level}] {i.description}")
        
    print("\n2. Simulando corrupción de diseño (Forzando Superposición y desbordamiento)...")
    # Forzamos un solapamiento moviendo el gráfico 2 exactamente a las mismas coordenadas del gráfico 1
    if len(report_layout.pages[0].placed_visuals) > 1:
        v1 = report_layout.pages[0].placed_visuals[0]
        v2 = report_layout.pages[0].placed_visuals[1]
        
        # Hacemos que choquen y se desborden
        v2.position.x = v1.position.x + 10
        v2.position.y = v1.position.y + 10
        v2.position.width = 2000 # Desborda el canvas
        
        report_corrupt = validator.validate(report_layout)
        
        print(f"\nEstado del Layout Corrupto: {'VALIDO' if report_corrupt.is_valid else 'INVALIDO'}")
        print("Problemas detectados automáticamente:")
        for i in report_corrupt.issues:
            print(f"  -> [{i.level}] {i.description}")

if __name__ == "__main__":
    run()
