from pathlib import Path

import polars as pl


SUPPORTED_DATASET_SUFFIXES = frozenset({".csv", ".xlsx"})


def load_tabular_dataset(file_path: str | Path) -> pl.DataFrame:
    """Carga un dataset tabular soportado y rechaza entradas sin registros."""

    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"El archivo no existe: {path}")

    suffix = path.suffix.casefold()
    if suffix not in SUPPORTED_DATASET_SUFFIXES:
        supported = ", ".join(
            sorted(item.removeprefix(".").upper() for item in SUPPORTED_DATASET_SUFFIXES)
        )
        raise ValueError(
            f"Formato no soportado: {suffix or '(sin extension)'}. "
            f"Formatos soportados: {supported}."
        )

    if path.stat().st_size == 0:
        raise ValueError(f"El dataset esta vacio: {path}")

    try:
        if suffix == ".csv":
            dataframe = pl.read_csv(
                path,
                infer_schema_length=10000,
                ignore_errors=True,
            )
        else:
            # openpyxl ya es una dependencia declarada y evita depender del
            # motor opcional fastexcel para el soporte XLSX anunciado.
            dataframe = pl.read_excel(path, engine="openpyxl")
    except pl.exceptions.NoDataError as exc:
        raise ValueError(f"El dataset esta vacio: {path}") from exc

    if dataframe.height == 0 or dataframe.width == 0:
        raise ValueError(f"El dataset esta vacio: {path}")

    return dataframe
