import re
import unicodedata
from pathlib import Path

from src.models.profiling import DatasetProfile
from src.models.semantic_model import (
    ColumnRole,
    KPI,
    SemanticColumn,
    SemanticDataType,
    SemanticProject,
    SemanticTable,
    TableType,
)


class SemanticBuilder:
    """Construye deterministicamente un modelo semantico desde un perfil."""

    _KEY_MARKERS = {"id", "identifier", "identificador", "key", "clave"}
    _EXPLICIT_METRIC_NAMES = {"cantidad", "quantity", "qty"}

    def __init__(self, profile: DatasetProfile):
        self.profile = profile

    def build_project(
        self,
        table_name: str = "FACT_DATA",
        source_path: str | Path | None = None,
    ) -> SemanticProject:
        columns: list[SemanticColumn] = []
        kpis: list[KPI] = []

        for column_profile in self.profile.columns:
            name_lower = column_profile.name.lower()
            dtype_lower = column_profile.dtype.lower()

            if self._is_key_name(column_profile.name):
                role = ColumnRole.KEY
                description = f"Identificador principal ({column_profile.name})"
            elif (
                "fecha" in name_lower
                or "date" in name_lower
                or "datetime" in dtype_lower
            ):
                role = ColumnRole.DATE
                description = f"Eje temporal ({column_profile.name})"
            elif self._is_numeric(dtype_lower) and (
                column_profile.unique_count > 2
                or self._normalized_name(column_profile.name)
                in self._EXPLICIT_METRIC_NAMES
            ):
                role = ColumnRole.METRIC
                description = f"Metrica cuantitativa ({column_profile.name})"
                kpis.append(
                    KPI(
                        name=f"Total {column_profile.name.title()}",
                        description=f"Suma acumulada de {column_profile.name}",
                        aggregation_type="Sum",
                        base_column=column_profile.name,
                        base_table=table_name,
                        dax_suggestion=f"SUM('{table_name}'[{column_profile.name}])",
                    )
                )

                if self._is_decimal(dtype_lower) or "precio" in name_lower:
                    kpis.append(
                        KPI(
                            name=f"Promedio de {column_profile.name.title()}",
                            description=f"Valor promedio por transaccion de {column_profile.name}",
                            aggregation_type="Average",
                            base_column=column_profile.name,
                            base_table=table_name,
                            dax_suggestion=f"AVERAGE('{table_name}'[{column_profile.name}])",
                        )
                    )
            else:
                role = ColumnRole.DIMENSION
                description = f"Atributo descriptivo o categoria ({column_profile.name})"

            columns.append(
                SemanticColumn(
                    name=column_profile.name,
                    role=role,
                    data_type=self._infer_data_type(dtype_lower, role),
                    description=description,
                )
            )

        if not columns:
            raise ValueError("No se puede construir un modelo semantico sin columnas")

        primary_key = next(
            (column.name for column in columns if column.role == ColumnRole.KEY),
            None,
        )
        main_table = SemanticTable(
            name=table_name,
            table_type=TableType.FACT,
            columns=columns,
            primary_key=primary_key,
            source_path=str(source_path) if source_path is not None else None,
        )

        kpis.insert(
            0,
            KPI(
                name="Total Registros",
                description="Cantidad total de transacciones/registros analizados",
                aggregation_type="Count",
                base_column=columns[0].name,
                base_table=table_name,
                dax_suggestion=f"COUNTROWS('{table_name}')",
            ),
        )

        # El perfil actual describe una unica tabla plana. No se inventan relaciones.
        return SemanticProject(tables=[main_table], relationships=[], kpis=kpis)

    @staticmethod
    def _is_numeric(dtype: str) -> bool:
        return any(token in dtype for token in ("int", "uint", "float", "decimal", "numeric"))

    @staticmethod
    def _is_decimal(dtype: str) -> bool:
        return any(token in dtype for token in ("float", "decimal", "numeric"))

    @classmethod
    def _is_key_name(cls, name: str) -> bool:
        """Detecta identificadores por tokens, no por subcadenas accidentales."""

        normalized = cls._normalized_name(name)
        tokens = normalized.split("_") if normalized else []
        return bool(
            tokens
            and (tokens[0] in cls._KEY_MARKERS or tokens[-1] in cls._KEY_MARKERS)
        )

    @staticmethod
    def _normalized_name(name: str) -> str:
        snake_case = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        snake_case = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake_case)
        ascii_name = "".join(
            character
            for character in unicodedata.normalize("NFKD", snake_case)
            if not unicodedata.combining(character)
        )
        return re.sub(r"[^a-z0-9]+", "_", ascii_name.casefold()).strip("_")

    @classmethod
    def _infer_data_type(cls, dtype: str, role: ColumnRole) -> SemanticDataType:
        if role == ColumnRole.DATE or "date" in dtype or "time" in dtype:
            return SemanticDataType.DATETIME
        if "bool" in dtype:
            return SemanticDataType.BOOLEAN
        if "int" in dtype or "uint" in dtype:
            return SemanticDataType.INTEGER
        if cls._is_decimal(dtype):
            return SemanticDataType.DECIMAL
        if any(token in dtype for token in ("str", "string", "utf8", "categorical")):
            return SemanticDataType.STRING
        return SemanticDataType.UNKNOWN
