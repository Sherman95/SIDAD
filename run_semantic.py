import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler
from src.tools.modeling.semantic_builder import SemanticBuilder

def run():
    print("=== Iniciando FASE 3: Modelado Semántico y KPIs ===\n")
    
    file_path = os.path.join("data", "processed", "ventas_limpio.csv")
    
    # Usamos el profiler de la Fase 1 para obtener la estructura (tipos, nombres) del dataset limpio
    print(f"1. Leyendo estructura del dataset limpio: {file_path}")
    profiler = DataProfiler(file_path)
    diagnostic = profiler.profile()
    
    # 2. Construimos el modelo semántico
    print(f"2. Construyendo propuesta semántica...")
    builder = SemanticBuilder(diagnostic.profile)
    semantic_project = builder.build_project(
        table_name="FACT_VENTAS",
        source_path=file_path,
    )
    
    print("\n=== MODELO DE TABLAS DETECTADO ===")
    for table in semantic_project.tables:
        print(f"\n- TABLA: {table.name} (Tipo: {table.table_type.value})")
        if table.primary_key:
            print(f"  Llave Primaria detectada: {table.primary_key}")
            
        print("Columnas y Roles:")
        for col in table.columns:
            print(f"  * {col.name.ljust(15)} -> {col.role.value.ljust(10)} | {col.description}")
            
    print("\n=== KPIs PROPUESTOS AUTOMÁTICAMENTE ===")
    for kpi in semantic_project.kpis:
        print(f"\n- KPI: {kpi.name}")
        print(f"   Desc: {kpi.description}")
        print(f"   Agregación: {kpi.aggregation_type} sobre '{kpi.base_column}'")
        print(f"   DAX Sugerido: {kpi.dax_suggestion}")

if __name__ == "__main__":
    run()
