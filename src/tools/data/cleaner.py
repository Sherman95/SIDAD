import polars as pl
from typing import Tuple
from src.models.transformations import TransformationLog

class DataCleaner:
    """
    Herramienta determinista para limpiar y transformar datos.
    Todas las operaciones retornan el DataFrame modificado y un log estructurado (trazabilidad).
    """
    def __init__(self, df: pl.DataFrame):
        self.df = df
        
    def remove_duplicates(self, reason: str = "Eliminación de registros exactamente iguales para evitar doble conteo") -> Tuple[pl.DataFrame, TransformationLog]:
        initial_count = self.df.height
        new_df = self.df.unique()
        final_count = new_df.height
        affected = initial_count - final_count
        
        log = TransformationLog(
            action="Eliminar filas duplicadas",
            reason=reason,
            tool_used="DataCleaner.remove_duplicates",
            records_affected=affected
        )
        return new_df, log
        
    def fill_nulls(self, column: str, fill_value: any, reason: str) -> Tuple[pl.DataFrame, TransformationLog]:
        if column not in self.df.columns:
            raise ValueError(f"La columna '{column}' no existe en el dataset.")
            
        affected = self.df[column].null_count()
        new_df = self.df.with_columns(pl.col(column).fill_null(fill_value))
        
        log = TransformationLog(
            action=f"Imputar nulos en '{column}' con valor '{fill_value}'",
            reason=reason,
            tool_used="DataCleaner.fill_nulls",
            records_affected=affected
        )
        return new_df, log
        
    def drop_column(self, column: str, reason: str) -> Tuple[pl.DataFrame, TransformationLog]:
        if column not in self.df.columns:
            raise ValueError(f"La columna '{column}' no existe en el dataset.")
            
        new_df = self.df.drop(column)
        
        log = TransformationLog(
            action=f"Eliminar columna '{column}'",
            reason=reason,
            tool_used="DataCleaner.drop_column",
            records_affected=self.df.height
        )
        return new_df, log
