# Fase 1: Ingesta y Perfilado de Datos

## 1. Introducción
El primer componente de la arquitectura híbrida consiste en la ingesta y el perfilado determinista de datos estructurados (CSV/XLSX). El objetivo principal de esta fase es extraer metadatos estadísticos y estructurales del conjunto de datos fuente, permitiendo al sistema identificar anomalías y proponer acciones correctivas antes de cualquier transformación destructiva.

## 2. Decisiones Arquitectónicas
- **Tipado Fuerte (Pydantic):** Para garantizar la consistencia en el intercambio de información entre herramientas deterministas y el agente LLM, se implementaron modelos de datos formales (`ColumnProfile`, `DatasetProfile`, `DiagnosticResult`). Esto elimina la ambigüedad inherente al procesamiento de lenguaje natural.
- **Eficiencia Computacional (Polars):** La ingesta y perfilado se realizan a través de la biblioteca Polars, cuyo motor basado en Rust permite el manejo de grandes volúmenes de datos superando las limitaciones tradicionales de consumo de memoria y rendimiento en Python.

## 3. Lógica Implementada
El script `DataProfiler` procesa el dataset y extrae:
1. Dimensiones del conjunto de datos (filas, columnas).
2. Cardinalidad y valores nulos por columna.
3. Duplicidad exacta de registros.

El resultado estructurado servirá de entrada (contexto semántico) para las posteriores decisiones de limpieza ejecutadas en la Fase 2.
