from src.models.profiling import DatasetProfile
from src.models.semantic_model import (
    ColumnRole, TableType, SemanticColumn, 
    SemanticTable, KPI, SemanticProject
)

class SemanticBuilder:
    """
    Herramienta heurística determinista para proponer un modelo semántico base
    a partir del perfil de los datos limpios.
    Más adelante, el Agente LLM tomará esta propuesta para validarla o ajustarla.
    """
    def __init__(self, profile: DatasetProfile):
        self.profile = profile

    def build_project(self, table_name: str = "FACT_DATA") -> SemanticProject:
        columns = []
        kpis = []
        
        for col in self.profile.columns:
            name_lower = col.name.lower()
            dtype_lower = col.dtype.lower()
            
            # --- Reglas Heurísticas Simples ---
            role = ColumnRole.UNKNOWN
            
            if "id" in name_lower or "clave" in name_lower:
                role = ColumnRole.KEY
                desc = f"Identificador principal ({col.name})"
            elif "fecha" in name_lower or "date" in name_lower or "datetime" in dtype_lower:
                role = ColumnRole.DATE
                desc = f"Eje temporal ({col.name})"
            elif dtype_lower in ["int64", "float64", "int32", "float32"] and col.unique_count > 2:
                # Los números con alta cardinalidad suelen ser métricas/hechos
                role = ColumnRole.METRIC
                desc = f"Métrica cuantitativa ({col.name})"
                
                # Sugerimos KPIs automáticamente
                kpis.append(KPI(
                    name=f"Total {col.name.title()}",
                    description=f"Suma acumulada de {col.name}",
                    aggregation_type="Sum",
                    base_column=col.name,
                    dax_suggestion=f"SUM('{table_name}'[{col.name}])"
                ))
                
                if dtype_lower in ["float64", "float32"] or "precio" in name_lower:
                    kpis.append(KPI(
                        name=f"Promedio de {col.name.title()}",
                        description=f"Valor promedio por transacción de {col.name}",
                        aggregation_type="Average",
                        base_column=col.name,
                        dax_suggestion=f"AVERAGE('{table_name}'[{col.name}])"
                    ))
            else:
                role = ColumnRole.DIMENSION
                desc = f"Atributo descriptivo o categoría ({col.name})"
                
            columns.append(SemanticColumn(name=col.name, role=role, description=desc))
            
        # Para el MVP, asumimos un modelo plano (Flat Table) que luego puede ser 
        # transformado en Estrella por el Agente.
        primary_key = next((c.name for c in columns if c.role == ColumnRole.KEY), None)
        
        main_table = SemanticTable(
            name=table_name,
            table_type=TableType.FACT, # Por ahora todo está desnormalizado
            columns=columns,
            primary_key=primary_key
        )
        
        # KPI base implícito (Conteo de filas)
        kpis.insert(0, KPI(
            name="Total Registros",
            description="Cantidad total de transacciones/registros analizados",
            aggregation_type="Count",
            base_column=columns[0].name,
            dax_suggestion=f"COUNTROWS('{table_name}')"
        ))
        
        return SemanticProject(tables=[main_table], kpis=kpis)
