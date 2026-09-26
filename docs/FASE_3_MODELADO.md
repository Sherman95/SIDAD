# Fase 3: Modelado Semántico y Generación de KPIs

## 1. Introducción
Una vez que el dataset ha sido perfilado y limpiado de manera estructurada, el sistema debe "entender" la semántica de la información. El modelado no se limita a pasar tablas a Power BI, sino a abstraer el negocio en un modelo dimensional estructurado e identificar los Indicadores Clave de Rendimiento (KPIs) pertinentes.

## 2. Decisiones Arquitectónicas
- **Agnosticismo de BI:** Para cumplir la visión del sistema de no acoplarse estrictamente a Power BI desde el principio, creamos un `SemanticProject` con Pydantic. Este objeto intermedio contiene `SemanticTable`, `SemanticColumn` y `KPI`, los cuales más adelante podrán ser traducidos a XMLA para Power BI o a especificaciones para Tableau.
- **Deducción Heurística:** A través de la clase `SemanticBuilder`, se introducen reglas deterministas básicas (ej. todo lo que diga "id" es llave primaria, fechas son ejes temporales, números de alta cardinalidad son hechos/métricas) para construir una propuesta inicial rápida y libre de alucinaciones. Posteriormente, un Agente LLM tomará esta propuesta para refinarla basándose en el contexto del negocio.

## 3. Lógica Implementada
1. Clasificación estricta de variables en roles de negocio (Dimensión, Métrica, Fecha, Llave).
2. Agrupación en Entidades de negocio (Tablas de Hechos o Dimensiones).
3. Inferencia de fórmulas agregadas básicas (Ej. Conteo de transacciones, Sumas, Promedios) estructurando automáticamente propuestas de código DAX.
