from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ColumnRole(str, Enum):
    DIMENSION = "Dimension"  # Atributos descriptivos, categorias
    METRIC = "Metric"  # Hechos, valores numericos a agregar
    KEY = "Key"  # Identificadores
    DATE = "Date"  # Eje de tiempo temporal
    UNKNOWN = "Unknown"


class SemanticDataType(str, Enum):
    """Tipos portables del dominio, independientes del proveedor de BI."""

    STRING = "String"
    INTEGER = "Integer"
    DECIMAL = "Decimal"
    DATETIME = "DateTime"
    BOOLEAN = "Boolean"
    UNKNOWN = "Unknown"


class TableType(str, Enum):
    FACT = "Fact"
    DIMENSION = "Dimension"


class CrossFilterDirection(str, Enum):
    ONE_DIRECTION = "OneDirection"
    BOTH_DIRECTIONS = "BothDirections"


class SemanticColumn(BaseModel):
    """Representa el contexto de negocio y el tipo portable de una columna."""

    name: str = Field(min_length=1, description="Nombre de la columna en el origen")
    role: ColumnRole = Field(description="Rol semantico asignado")
    data_type: SemanticDataType = Field(
        default=SemanticDataType.UNKNOWN,
        description="Tipo fisico portable inferido desde el origen",
    )
    description: str = Field(default="", description="Descripcion autogenerada o deducida")


class SemanticTable(BaseModel):
    """Representa una entidad dentro del modelo estrella/copo de nieve."""

    name: str = Field(min_length=1, description="Nombre logico de la tabla")
    table_type: TableType = Field(description="Tipo de tabla: Hechos o Dimension")
    columns: list[SemanticColumn] = Field(min_length=1, description="Columnas categorizadas")
    primary_key: Optional[str] = Field(default=None, description="Llave primaria si existe")
    source_path: Optional[str] = Field(
        default=None,
        description="Ruta del dataset que materializa esta tabla; no contiene logica del proveedor",
    )

    @model_validator(mode="after")
    def validate_columns(self) -> "SemanticTable":
        column_names = [column.name for column in self.columns]
        if len(column_names) != len(set(column_names)):
            raise ValueError(f"La tabla '{self.name}' contiene nombres de columna duplicados")
        if self.primary_key and self.primary_key not in column_names:
            raise ValueError(
                f"La llave primaria '{self.primary_key}' no existe en la tabla '{self.name}'"
            )
        return self


class Relationship(BaseModel):
    """Relacion logica entre una columna de hechos y una columna de dimension."""

    name: Optional[str] = Field(default=None, description="Nombre estable opcional")
    from_table: str = Field(min_length=1, description="Tabla del lado muchos")
    from_column: str = Field(min_length=1, description="Columna del lado muchos")
    to_table: str = Field(min_length=1, description="Tabla del lado uno")
    to_column: str = Field(min_length=1, description="Columna del lado uno")
    is_active: bool = Field(default=True, description="Indica si la relacion esta activa")
    cross_filter_direction: CrossFilterDirection = Field(
        default=CrossFilterDirection.ONE_DIRECTION,
        description="Direccion de propagacion de filtros",
    )


class KPI(BaseModel):
    """Definicion agnostica de un Indicador Clave de Rendimiento."""

    name: str = Field(min_length=1, description="Nombre legible del KPI")
    description: str = Field(description="Proposito del KPI")
    aggregation_type: str = Field(description="Tipo de agregacion basica")
    base_column: str = Field(min_length=1, description="Columna sobre la que se calcula")
    base_table: Optional[str] = Field(
        default=None,
        description="Tabla propietaria; opcional para compatibilidad con modelos de una sola tabla",
    )
    dax_suggestion: Optional[str] = Field(
        default=None,
        description="Expresion DAX sugerida para Power BI",
    )


class SemanticProject(BaseModel):
    """Agrupa el modelo dimensional, sus relaciones y las metricas detectadas."""

    tables: list[SemanticTable] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    kpis: list[KPI] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "SemanticProject":
        tables_by_name = {table.name: table for table in self.tables}
        if len(tables_by_name) != len(self.tables):
            raise ValueError("El proyecto contiene nombres de tabla duplicados")

        for relationship in self.relationships:
            self._require_column(
                tables_by_name,
                relationship.from_table,
                relationship.from_column,
                "origen",
            )
            self._require_column(
                tables_by_name,
                relationship.to_table,
                relationship.to_column,
                "destino",
            )

            from_type = self._column_type(
                tables_by_name, relationship.from_table, relationship.from_column
            )
            to_type = self._column_type(
                tables_by_name, relationship.to_table, relationship.to_column
            )
            if (
                from_type != SemanticDataType.UNKNOWN
                and to_type != SemanticDataType.UNKNOWN
                and from_type != to_type
            ):
                raise ValueError(
                    f"La relacion '{relationship.name or 'sin nombre'}' conecta tipos incompatibles: "
                    f"{from_type.value} y {to_type.value}"
                )

        for kpi in self.kpis:
            if kpi.base_table:
                self._require_column(tables_by_name, kpi.base_table, kpi.base_column, "KPI")
                continue

            matching_tables = [
                table.name
                for table in self.tables
                if any(column.name == kpi.base_column for column in table.columns)
            ]
            if not matching_tables:
                raise ValueError(
                    f"La columna base '{kpi.base_column}' del KPI '{kpi.name}' no existe"
                )
            if len(matching_tables) > 1:
                raise ValueError(
                    f"El KPI '{kpi.name}' debe indicar base_table porque "
                    f"'{kpi.base_column}' existe en varias tablas"
                )

        return self

    @staticmethod
    def _require_column(
        tables_by_name: dict[str, SemanticTable],
        table_name: str,
        column_name: str,
        endpoint: str,
    ) -> None:
        table = tables_by_name.get(table_name)
        if table is None:
            raise ValueError(f"La tabla {endpoint} '{table_name}' no existe")
        if not any(column.name == column_name for column in table.columns):
            raise ValueError(
                f"La columna {endpoint} '{table_name}.{column_name}' no existe"
            )

    @staticmethod
    def _column_type(
        tables_by_name: dict[str, SemanticTable], table_name: str, column_name: str
    ) -> SemanticDataType:
        table = tables_by_name[table_name]
        return next(column.data_type for column in table.columns if column.name == column_name)
