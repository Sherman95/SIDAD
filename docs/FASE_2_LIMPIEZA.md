# Fase 2: Limpieza y Transformación Automática

## 1. Introducción
La segunda fase del sistema materializa las acciones sugeridas durante el perfilado. En el contexto de un sistema de soporte de decisiones, la alteración de los datos subyacentes debe ser un proceso trazable y justificado.

## 2. Principio de Trazabilidad
Se introduce el concepto de "Trazabilidad Estricta" a través del modelo `CleaningReport` y `TransformationLog`. El sistema no asume transformaciones "caja negra"; cada alteración al dataset registra de manera determinista:
- **Acción:** Operación técnica ejecutada (e.g., eliminación de filas).
- **Motivo:** Justificación técnica o semántica que originó la transformación.
- **Herramienta:** El módulo específico que ejecutó la instrucción.
- **Registros Afectados:** El impacto cuantitativo en el dataset.

## 3. Lógica Implementada
La clase `DataCleaner` proporciona métodos puros y deterministas (eliminación de duplicados, imputación de nulos, eliminación de columnas) que procesan el DataFrame de Polars devolviendo el nuevo estado y el log correspondiente. Los datos transformados se aíslan en una capa independiente (`data/processed`) para salvaguardar la integridad de la fuente original (`data/raw`).
