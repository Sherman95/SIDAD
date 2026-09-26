import json
import sys
import os

# Agregamos la raíz del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler

def run():
    print("=== Iniciando Validación de la Fase 1 ===")
    
    file_path = os.path.join("data", "raw", "ventas_test.csv")
    print(f"1. Ingiriendo y perfilando archivo: {file_path}")
    
    try:
        profiler = DataProfiler(file_path)
        diagnostic = profiler.profile()
        
        print("\n=== PERFIL DEL DATASET ===")
        print(f"Filas: {diagnostic.profile.row_count}")
        print(f"Columnas: {diagnostic.profile.column_count}")
        print(f"Duplicados encontrados: {diagnostic.profile.duplicate_rows}")
        
        print("\n=== PROBLEMAS DETECTADOS ===")
        for prob in diagnostic.problems_detected:
            print(f"- [PROBLEMA]: {prob}")
            
        print("\n=== ACCIONES SUGERIDAS ===")
        for action in diagnostic.suggested_actions:
            print(f"- [ACCION]: {action}")
            
        print("\n=== SALIDA ESTRUCTURADA (JSON / Pydantic) ===")
        # Imprimir el modelo serializado, útil para el futuro Agente LLM
        print(diagnostic.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"Error durante el perfilado: {e}")

if __name__ == "__main__":
    run()
