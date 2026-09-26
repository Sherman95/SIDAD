# CONTEXTO MAESTRO DEL PROYECTO

Quiero desarrollar desde cero un sistema de software basado en un agente inteligente cuyo objetivo es automatizar, de extremo a extremo, el proceso de transformación de datos sin estructurar o heterogéneos en dashboards orientados al soporte de decisiones.

## 1. TÍTULO DEL PROYECTO

"Desarrollo de un agente inteligente para el diseño e implementación automatizada de dashboards orientados al soporte de decisiones."

El proyecto tiene un enfoque académico y de ingeniería de software. No quiero construir únicamente un chatbot que consulte datos. Quiero desarrollar un sistema capaz de analizar datos, identificar problemas, proponer y ejecutar transformaciones, construir un modelo de datos, identificar indicadores relevantes, diseñar un dashboard y posteriormente implementarlo en una plataforma de Business Intelligence.

---

# 2. OBJETIVO GENERAL

Desarrollar un agente inteligente capaz de automatizar el flujo de procesamiento, análisis, modelado y visualización de datos para generar dashboards orientados al soporte de decisiones, reduciendo la intervención manual requerida para pasar desde datos fuente hasta un dashboard funcional.

---

# 3. VISIÓN DEL SISTEMA

El flujo conceptual que quiero conseguir es:

FUENTES DE DATOS
↓
INGESTA
↓
PERFILADO DE DATOS
↓
DETECCIÓN DE PROBLEMAS
↓
LIMPIEZA
↓
TRANSFORMACIÓN
↓
VALIDACIÓN
↓
MODELADO SEMÁNTICO
↓
IDENTIFICACIÓN DE KPIs
↓
GENERACIÓN DE MÉTRICAS / DAX
↓
PLANIFICACIÓN DEL DASHBOARD
↓
DISEÑO DE PÁGINAS Y VISUALES
↓
IMPLEMENTACIÓN EN POWER BI
↓
VALIDACIÓN VISUAL Y FUNCIONAL
↓
CRÍTICA AUTOMÁTICA
↓
CORRECCIONES
↓
DASHBOARD FINAL

El objetivo final es que un usuario pueda proporcionar datos y una instrucción de alto nivel como:

"Analiza estas ventas y genera un dashboard ejecutivo para apoyar decisiones comerciales."

y el sistema sea capaz de realizar la mayor cantidad posible del proceso automáticamente.

---

# 4. EJEMPLO DE USO

Entrada:

ventas.xlsx

El agente debería poder detectar automáticamente cosas como:

* número de filas y columnas
* nombres y tipos de columnas
* valores faltantes
* duplicados
* errores de formato
* fechas inválidas
* categorías inconsistentes
* posibles valores atípicos
* relaciones entre columnas
* posibles dimensiones
* posibles métricas
* posibles identificadores
* granularidad de los datos

Después debería generar un diagnóstico similar a:

DATOS ANALIZADOS

Filas: 15.342
Columnas: 8

Problemas detectados:

* 42 fechas inválidas
* 17 valores nulos
* 12 registros duplicados
* 8 categorías inconsistentes

Acciones propuestas:

* normalizar categorías
* convertir fechas
* tratar valores faltantes
* eliminar duplicados confirmados

Después de la limpieza:

* generar dataset procesado
* validar que las transformaciones no hayan alterado incorrectamente los datos
* identificar dimensiones y hechos
* proponer métricas
* identificar KPIs

Por ejemplo:

KPIs:

* ventas totales
* unidades vendidas
* ticket promedio
* crecimiento mensual
* ventas por categoría
* ventas por ciudad
* ventas por vendedor

Posteriormente debe diseñar el dashboard.

---

# 5. DASHBOARD

El sistema no debe limitarse a generar datos preparados para Power BI.

Uno de los objetivos principales es automatizar también la capa visual.

El agente debe poder decidir, justificadamente, aspectos como:

* cuántas páginas necesita el dashboard
* qué KPIs mostrar
* qué visualización corresponde a cada análisis
* qué dimensiones utilizar
* qué métricas utilizar
* qué filtros y slicers son útiles
* qué jerarquías deben existir
* cómo distribuir visuales en una página
* qué información debe tener mayor prioridad visual
* qué tema visual utilizar
* cómo organizar el dashboard para un usuario ejecutivo

Ejemplo:

PÁGINA 1 — RESUMEN EJECUTIVO

* Ventas totales
* Unidades vendidas
* Ticket promedio
* Crecimiento
* Tendencia mensual
* Ventas por categoría
* Ventas por región

PÁGINA 2 — ANÁLISIS COMERCIAL

* ventas por producto
* ventas por vendedor
* evolución temporal
* filtros por ciudad
* filtros por categoría

PÁGINA 3 — ANÁLISIS DE PRODUCTOS

* productos más vendidos
* productos menos vendidos
* participación por categoría
* tendencia de productos

La estructura debe ser generada dinámicamente según los datos disponibles, no estar completamente codificada de antemano.

---

# 6. PRINCIPIO FUNDAMENTAL DE ARQUITECTURA

NO quiero que un LLM realice directamente todas las operaciones de datos.

El sistema debe utilizar una arquitectura híbrida:

# LLM / AGENTE

PLANIFICACIÓN + RAZONAMIENTO + DECISIONES + INTERPRETACIÓN

# HERRAMIENTAS DETERMINISTAS

EJECUCIÓN + TRANSFORMACIÓN + VALIDACIÓN + CÁLCULO

Por ejemplo:

El agente decide:

"Esta columna representa una fecha y contiene valores inválidos."

Una herramienta determinista ejecuta:

normalize_dates()

El agente decide:

"Existe una métrica de ventas."

Una herramienta calcula:

calculate_total_sales()

El agente decide:

"Para comparar ventas por categoría es apropiado un gráfico de barras."

Una herramienta genera la configuración correspondiente para el dashboard.

Esto debe priorizar reproducibilidad, trazabilidad y confiabilidad.

---

# 7. ARQUITECTURA DEL AGENTE

Quiero una arquitectura modular.

Como mínimo conceptual:

AGENT
├── Planner
├── Analyst
├── Data Agent
├── Modeling Agent
├── KPI Agent
├── Dashboard Designer
├── BI Agent
└── Critic / Validator

No necesariamente deben ser agentes LLM independientes desde la primera versión.

La arquitectura debe permitir comenzar con un único agente orquestador y evolucionar posteriormente hacia múltiples agentes especializados si realmente aporta valor.

No crear complejidad innecesaria.

---

# 8. COMPONENTES PRINCIPALES

## A. INGESTA

Inicialmente soportar:

* CSV
* XLSX
* JSON
* PostgreSQL

Posteriormente:

* APIs REST
* otras bases de datos
* archivos adicionales
* fuentes web cuando sea apropiado

Debe existir una abstracción para las fuentes de datos.

---

# 9. PERFILADO

Crear herramientas deterministas para:

* cantidad de filas
* cantidad de columnas
* tipos de datos
* valores nulos
* duplicados
* cardinalidad
* distribución básica
* valores mínimos y máximos
* posibles outliers
* columnas categóricas
* columnas temporales
* posibles claves
* posibles relaciones

El resultado del perfilado debe ser estructurado, preferiblemente mediante modelos Pydantic.

---

# 10. LIMPIEZA

Crear herramientas para operaciones como:

* normalización de nombres
* conversión de tipos
* tratamiento de valores nulos
* eliminación o marcación de duplicados
* normalización de categorías
* tratamiento de fechas
* detección de valores inválidos
* validación de rangos
* eliminación de columnas innecesarias

IMPORTANTE:

Las transformaciones deben quedar registradas.

El sistema debe poder explicar:

QUÉ CAMBIÓ
POR QUÉ CAMBIÓ
QUÉ HERRAMIENTA LO CAMBIÓ
CUÁNTOS REGISTROS FUERON AFECTADOS

---

# 11. VALIDACIÓN

Después de cada transformación importante debe existir validación.

Ejemplos:

* cantidad de filas antes/después
* columnas eliminadas
* columnas agregadas
* tipos de datos
* nulos restantes
* duplicados restantes
* valores fuera de rango
* consistencia de métricas

Si una transformación genera resultados inesperados, el agente debe poder detectarlo y reconsiderar el paso.

---

# 12. MODELADO

Después de limpiar los datos, el sistema debe identificar:

* tablas de hechos
* dimensiones
* relaciones
* claves
* granularidad
* métricas
* jerarquías

Debe producir una representación estructurada del modelo.

Ejemplo:

FACT_VENTAS
├── fecha_id
├── producto_id
├── vendedor_id
├── ciudad_id
├── cantidad
└── importe

DIM_PRODUCTO
├── producto_id
├── producto
└── categoria

DIM_FECHA
├── fecha_id
├── fecha
├── mes
├── trimestre
└── año

---

# 13. KPI Y MÉTRICAS

El agente debe identificar indicadores relevantes basándose en:

* estructura de los datos
* objetivo del usuario
* contexto del negocio
* relaciones entre variables
* necesidades de decisión

Debe diferenciar entre:

* métricas básicas
* KPIs
* dimensiones
* atributos descriptivos

Cuando sea necesario para Power BI, debe generar expresiones DAX y validarlas antes de utilizarlas.

---

# 14. POWER BI

Power BI será inicialmente la plataforma principal de Business Intelligence.

El sistema debe contemplar integración con capacidades actuales de Power BI para automatizar:

* modelos semánticos
* tablas
* columnas
* medidas
* relaciones
* jerarquías
* DAX
* páginas
* visuales
* filtros
* slicers
* formato
* temas
* validación

No asumir que todas las operaciones estarán disponibles de la misma forma en todas las APIs, MCP o versiones de Power BI.

Antes de implementar una integración concreta, investigar la documentación oficial y comprobar las capacidades reales disponibles.

---

# 15. ABSTRACCIÓN DE BI

No quiero que toda la arquitectura dependa directamente de Power BI.

Diseñar una interfaz conceptual:

BIProvider

con una implementación inicial:

PowerBIProvider

y dejar preparada la arquitectura para una futura:

TableauProvider

La intención es que el sistema tenga una capa de abstracción de Business Intelligence.

---

# 16. MCP

El sistema puede utilizar MCP cuando aporte capacidades externas o acceso estructurado a herramientas.

Actualmente el entorno de desarrollo puede contar con herramientas como:

* Docling MCP
* Context7 MCP
* Sequential Thinking
* Supabase MCP
* Power BI MCP / capacidades oficiales disponibles

No asumir que MCP significa automáticamente que una tarea es posible.

Cada herramienta debe utilizarse según sus capacidades reales.

Investigar siempre la documentación oficial cuando una integración dependa de una característica externa que pueda cambiar.

---

# 17. PRINCIPIO SOBRE MCP

No quiero construir "otro MCP de Power BI" simplemente por hacerlo.

Si Microsoft ya ofrece herramientas oficiales para una capacidad, el proyecto debe aprovecharlas.

El valor principal de nuestro sistema debe estar en la capa inteligente que conecta:

DATOS
→
RAZONAMIENTO
→
LIMPIEZA
→
MODELADO
→
KPIs
→
DISEÑO
→
BI
→
VALIDACIÓN
→
CORRECCIÓN

Nuestro sistema será principalmente un ORQUESTADOR INTELIGENTE DE EXTREMO A EXTREMO.

---

# 18. VALIDACIÓN VISUAL

Esta parte es muy importante.

El agente no debería asumir que un dashboard es correcto únicamente porque el código o configuración sea válida.

Cuando sea posible debe existir un ciclo:

GENERAR
↓
RENDERIZAR
↓
CAPTURAR
↓
ANALIZAR VISUALMENTE
↓
DETECTAR PROBLEMAS
↓
CORREGIR
↓
VOLVER A VALIDAR

Debe poder detectar problemas como:

* visuales superpuestos
* espacios desperdiciados
* texto ilegible
* demasiados gráficos
* mala jerarquía visual
* filtros mal ubicados
* títulos poco claros
* KPIs poco visibles
* inconsistencias de formato

---

# 19. CRITIC / SELF-CORRECTION

El sistema debe incorporar una etapa crítica.

Después de generar un dashboard:

Dashboard Designer
↓
Dashboard Validator
↓
Critic

El Critic debe responder preguntas como:

* ¿Los KPIs responden al objetivo solicitado?
* ¿Los gráficos representan correctamente los datos?
* ¿Existen visualizaciones redundantes?
* ¿Existe información importante que no se está mostrando?
* ¿La distribución visual es coherente?
* ¿Existen errores de datos?
* ¿Existen medidas DAX inválidas?
* ¿El dashboard realmente ayuda a la decisión planteada?

Si encuentra problemas, debe generar correcciones.

---

# 20. TRAZABILIDAD

Una característica importante del proyecto será poder explicar las decisiones del agente.

Cada ejecución debería generar un registro parecido a:

INPUT
↓
PROFILE
↓
PROBLEMS DETECTED
↓
TRANSFORMATIONS
↓
VALIDATIONS
↓
MODEL
↓
KPIs
↓
DASHBOARD PLAN
↓
BI IMPLEMENTATION
↓
VALIDATION
↓
CORRECTIONS

El sistema debe evitar decisiones completamente opacas cuando sea posible.

---

# 21. TECNOLOGÍAS INICIALES

Quiero comenzar con:

Python
Polars
Pandas cuando sea necesario
PyArrow
Pydantic
OpenPyXL
PostgreSQL
Power BI
MCP
Git

Para una futura interfaz:

Next.js
TypeScript
Tailwind

Para una futura API:

FastAPI

No instalar ni utilizar una cantidad enorme de dependencias sin justificarlo.

---

# 22. ESTRUCTURA INICIAL PROPUESTA

La estructura inicial puede ser:

dashboard-agent/

├── src/
│   ├── agent/
│   │   ├── orchestrator.py
│   │   ├── planner.py
│   │   ├── analyst.py
│   │   └── critic.py
│   │
│   ├── tools/
│   │   ├── ingestion/
│   │   ├── data/
│   │   ├── modeling/
│   │   ├── kpi/
│   │   ├── dashboard/
│   │   └── powerbi/
│   │
│   ├── models/
│   │   ├── dataset.py
│   │   ├── profiling.py
│   │   ├── transformations.py
│   │   ├── semantic_model.py
│   │   └── dashboard.py
│   │
│   └── config/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── output/
│
├── tests/
│
├── .env
├── .gitignore
├── pyproject.toml
└── README.md

Esta estructura es una propuesta inicial. No crear automáticamente todos estos archivos sin analizar primero qué necesitamos realmente para el MVP.

---

# 23. ESTRATEGIA DE DESARROLLO

NO quiero intentar desarrollar todo de una vez.

Debemos trabajar por fases.

FASE 1
MVP de análisis de datos.

Entrada:
CSV/XLSX

Salida:
perfil + diagnóstico.

FASE 2
Limpieza y transformación automática.

FASE 3
Modelado y generación de KPIs.

FASE 4
Generación automática de un plan de dashboard.

FASE 5
Integración con Power BI.

FASE 6
Generación automática de páginas y visuales.

FASE 7
Validación visual.

FASE 8
Self-correction.

FASE 9
Interfaz web.

FASE 10
Evaluación experimental.

---

# 24. EVALUACIÓN DEL PROYECTO

El proyecto debe poder evaluarse académicamente.

Algunas métricas que posteriormente podremos estudiar:

* porcentaje de automatización
* tiempo de generación
* cantidad de intervención manual
* precisión de transformaciones
* calidad de datos
* validez de KPIs
* validez de visualizaciones
* errores detectados
* errores corregidos
* satisfacción/usabilidad
* tiempo humano ahorrado

No inventar resultados.

Primero construir el sistema y después diseñar los experimentos.

---

# 25. PRINCIPIOS DE DESARROLLO

Quiero que trabajes bajo estas reglas:

1. No sobreingenierizar.
2. No crear agentes separados si una función normal es suficiente.
3. No usar un LLM para operaciones que puedan ejecutarse determinísticamente.
4. Validar siempre los datos después de transformarlos.
5. Mantener separación entre razonamiento y ejecución.
6. Mantener trazabilidad.
7. Usar tipado fuerte mediante Pydantic cuando corresponda.
8. Crear tests desde las primeras herramientas importantes.
9. Mantener las funciones pequeñas y reutilizables.
10. No ocultar errores.
11. No inventar capacidades de APIs o MCP.
12. Consultar documentación oficial cuando una integración dependa de una característica externa.
13. No instalar dependencias innecesarias.
14. Mantener el sistema modular.
15. Priorizar primero un MVP funcional.
16. No construir una interfaz gráfica antes de tener funcionando el núcleo.
17. Todas las decisiones importantes del agente deben poder inspeccionarse.
18. Las operaciones destructivas sobre datos deben evitarse o requerir confirmación.
19. Nunca sobrescribir los datos originales.
20. Mantener siempre los datos RAW separados de los PROCESSED.

---

# 26. REGLA MUY IMPORTANTE PARA EL DESARROLLO

No quiero que simplemente generes cientos de líneas de código.

Antes de implementar una fase:

1. explica brevemente qué vamos a construir;
2. identifica dependencias;
3. propone la estructura necesaria;
4. implementa una pieza pequeña;
5. prueba esa pieza;
6. verifica el resultado;
7. solamente después continúa.

Si detectas que una decisión arquitectónica puede afectar fases posteriores, detente y explícala antes de implementarla.

---

# 27. PRIMER OBJETIVO

Por ahora NO implementes Power BI.

NO implementes la interfaz web.

NO implementes múltiples agentes.

NO implementes Tableau.

NO implementes APIs externas innecesarias.

Nuestro primer objetivo es construir un núcleo capaz de recibir un CSV/XLSX y producir un análisis estructurado y confiable del dataset.

El primer flujo debe ser:

ARCHIVO
↓
INGESTA
↓
PERFILADO
↓
DIAGNÓSTICO
↓
RESULTADO ESTRUCTURADO

Una vez que esto funcione correctamente, continuaremos con la siguiente fase.

---

# 28. TU PAPEL COMO AGENTE DE DESARROLLO

Actúa como arquitecto de software y desarrollador senior especializado en:

* sistemas de agentes
* ingeniería de datos
* Business Intelligence
* Python
* Power BI
* MCP
* automatización
* arquitectura de software

Pero no tomes decisiones arbitrarias.

Cuando exista más de una alternativa técnica razonable:

* presenta las opciones;
* explica ventajas y desventajas;
* recomienda una opción basada en el objetivo del proyecto;
* espera confirmación cuando la decisión tenga impacto arquitectónico importante.

Quiero construir el sistema conmigo, paso a paso, entendiendo qué estamos haciendo.

NO quiero que generes todo el proyecto de una sola vez.

Comienza analizando este contexto y proponiendo exactamente cómo debemos iniciar la FASE 1.
