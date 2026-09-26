import sys
import os
import polars as pl

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.data.profiler import DataProfiler
from src.tools.data.cleaner import DataCleaner
from src.models.transformations import CleaningReport

def run():
    print("=== Iniciando FASE 2: Limpieza con Trazabilidad ===\n")
    
    file_path = os.path.join("data", "raw", "ventas_test.csv")
    
    # 1. Cargamos el dataset
    print(f"Cargando dataset bruto...")
    df = pl.read_csv(file_path, ignore_errors=True)
    print(f"Dataset original: {df.height} filas.\n")
    
    report = CleaningReport()
    cleaner = DataCleaner(df)
    
    # 2. Aplicamos limpieza paso a paso basándonos en lo que detectamos en Fase 1
    
    # A. Eliminar duplicados
    df, log_dup = cleaner.remove_duplicates()
    report.logs.append(log_dup)
    cleaner.df = df # Actualizamos el estado interno
    
    # B. Imputar nulos en 'categoria' con 'Sin Categoria'
    df, log_cat = cleaner.fill_nulls(
        column="categoria", 
        fill_value="Desconocido", 
        reason="Evitar perder ventas completas imputando la categoría faltante."
    )
    report.logs.append(log_cat)
    cleaner.df = df
    
    # C. Imputar cantidad con 1 (asumimos compra mínima)
    df, log_cant = cleaner.fill_nulls(
        column="cantidad", 
        fill_value=1, 
        reason="Se asume 1 unidad como valor por defecto si no se especificó."
    )
    report.logs.append(log_cant)
    cleaner.df = df
    
    print("=== REPORTE DE TRAZABILIDAD DE LIMPIEZA ===")
    for log in report.logs:
        print(f"\n- Accion: {log.action}")
        print(f"  Motivo: {log.reason}")
        print(f"  Afectados: {log.records_affected} registros")
        print(f"  Herramienta: {log.tool_used}")

    print("\n=== DATASET LIMPIO (PROCESSED) ===")
    print("El dataset ha sido limpiado.")
    
    # Guardamos en processed
    out_path = os.path.join("data", "processed", "ventas_limpio.csv")
    df.write_csv(out_path)
    print(f"\nDatos guardados exitosamente en: {out_path}")

if __name__ == "__main__":
    run()
