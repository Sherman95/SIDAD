import os
import polars as pl
from src.models.profiling import ColumnProfile, DatasetProfile, DiagnosticResult

class DataProfiler:
    """
    Herramienta determinista para perfilar conjuntos de datos.
    Se encarga de ingerir el archivo y calcular métricas estructurales
    utilizando Polars para máxima eficiencia.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo no existe: {file_path}")

    def _load_data(self) -> pl.DataFrame:
        """Carga el archivo usando Polars. Soporta CSV y Excel (XLSX)."""
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == '.csv':
            # ignore_errors permite continuar leyendo si hay problemas de parseo aislados,
            # pero para mayor robustez inferimos el esquema desde más líneas.
            return pl.read_csv(self.file_path, infer_schema_length=10000, ignore_errors=True)
        elif ext in ['.xlsx', '.xls']:
            return pl.read_excel(self.file_path)
        else:
            raise ValueError(f"Formato no soportado: {ext}. Utilice CSV o XLSX.")

    def profile(self) -> DiagnosticResult:
        """Genera el perfil completo y diagnóstico del dataset."""
        df = self._load_data()
        
        row_count = df.height
        col_count = df.width
        
        # Conteo de duplicados exactos (todas las columnas iguales)
        duplicate_count = df.height - df.unique().height

        columns_profile = []
        problems = []
        actions = []

        for col_name in df.columns:
            series = df[col_name]
            dtype_str = str(series.dtype)
            
            null_count = series.null_count()
            null_perc = (null_count / row_count) * 100 if row_count > 0 else 0.0
            unique_count = series.n_unique()
            
            # Calculamos min y max si la serie no es completamente nula
            min_val = None
            max_val = None
            try:
                if not series.is_null().all():
                    min_val = series.min()
                    max_val = series.max()
            except Exception:
                # Polars puede lanzar excepción si no soporta min/max en algún tipo de objeto raro
                pass

            col_prof = ColumnProfile(
                name=col_name,
                dtype=dtype_str,
                null_count=null_count,
                null_percentage=null_perc,
                unique_count=unique_count,
                min_value=min_val,
                max_value=max_val
            )
            columns_profile.append(col_prof)

            # --- Diagnósticos Deterministas (Reglas Base) ---
            if null_perc > 0:
                problems.append(f"La columna '{col_name}' tiene {null_perc:.2f}% de valores nulos ({null_count} nulos).")
                if null_perc > 80:
                    actions.append(f"Considerar eliminar la columna '{col_name}' debido a exceso de nulos (>80%).")
                else:
                    actions.append(f"Imputar o tratar valores nulos en la columna '{col_name}'.")

            if unique_count == 1 and row_count > 1:
                if null_count == row_count:
                    problems.append(f"La columna '{col_name}' está completamente vacía.")
                    actions.append(f"Eliminar la columna '{col_name}'.")
                else:
                    problems.append(f"La columna '{col_name}' tiene un solo valor constante.")
                    actions.append(f"Considerar eliminar la columna '{col_name}' (sin varianza).")

        # Diagnóstico a nivel de Dataset
        if duplicate_count > 0:
            problems.append(f"Se encontraron {duplicate_count} filas completamente duplicadas.")
            actions.append("Eliminar o marcar filas duplicadas confirmadas.")

        dataset_profile = DatasetProfile(
            row_count=row_count,
            column_count=col_count,
            duplicate_rows=duplicate_count,
            columns=columns_profile
        )

        return DiagnosticResult(
            profile=dataset_profile,
            problems_detected=problems,
            suggested_actions=actions
        )
