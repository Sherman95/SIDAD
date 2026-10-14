# Fase 12.2: contenido y bindings PBIR

## Objetivo y estado

La Fase 12.2 traduce `DashboardPlan` y `SemanticProject` a la estructura modular
PBIR de un reporte Power BI. Esta fase responde que paginas y visuales contiene
el reporte y con que columnas o medidas se relaciona cada visual.

**FASE 12.2 IMPLEMENTADA, VALIDADA ESTRUCTURALMENTE Y VERIFICADA EN POWER BI DESKTOP PARA GENERACIÓN DE PÁGINAS, VISUALES Y BINDINGS PBIR.**

La verificación manual confirmó que el contenido PBIR generado por SIDAD carga
y funciona correctamente con datos reales. El placeholder espacial propio del
alcance de 12.2 fue sustituido posteriormente por la integración de
`ReportLayout` realizada en Fase 12.3.

Esta clasificacion no incluye layout final, validacion visual ni integracion del
exportador en el agente.

## Frontera arquitectonica

```text
DashboardPlan + SemanticProject
              |
              v
  PowerBIProvider (contenido y bindings PBIR)
              |
              v
     PBIR con posicion placeholder
              |
              v
   Fase 12.3: ReportLayout -> PBIR
```

- `DashboardPlan` conserva la intencion analitica y no contiene `queryState` ni
  nombres de roles de Power BI.
- `SemanticProject` es la fuente de verdad para tablas, columnas y medidas.
- `PowerBIProvider` contiene la traduccion a tipos, roles y expresiones PBIR.
- `ReportLayout` no se importa ni se consume en 12.2.
- `export_to_powerbi` no se registro en `ToolRegistry`; la orquestacion del
  agente no fue modificada.

## Modelos de dominio

Se agregaron modelos opcionales y agnosticos en `dashboard.py`:

- `SemanticFieldRef`: tabla, campo, clase `Column | Measure` y agregacion
  portable opcional;
- `SemanticAggregation`: `Sum`, `Average`, `DistinctCount`, `Min`, `Max` y
  `Count`;
- `VisualBindings`: categoria, valores multiples y serie.

`VisualElement.bindings` es opcional. Los campos historicos `kpi_ref`, `x_axis`
y `y_axis` siguen funcionando y se resuelven contra `SemanticProject`. Esta
compatibilidad permite que planes existentes sigan siendo validos, mientras que
los planes nuevos pueden eliminar ambiguedades indicando tabla y clase de campo.

El `DashboardPlanner` ahora completa la tabla de detalle con referencias a las
columnas reales de su entidad. No inventa columnas y permite que `tableEx`
reciba multiples campos.

## Estructura generada

```text
SIDAD.Report/
|-- definition.pbir
`-- definition/
    |-- version.json
    |-- report.json
    `-- pages/
        |-- pages.json
        `-- <page-id>/
            |-- page.json
            `-- visuals/
                `-- <visual-id>/
                    `-- visual.json
```

La generacion elimina `report_spec.json`, el `report.json` legacy que pudiera
existir en la raiz de `SIDAD.Report`, paginas que ya no pertenecen al plan y
visuales stale dentro de paginas conservadas.

## Schemas y versiones

Los archivos declaran estas versiones oficiales publicadas:

| Archivo | Schema |
| --- | --- |
| `definition.pbir` | `definitionProperties/2.0.0` |
| `definition/version.json` | `versionMetadata/1.0.0` |
| `definition/report.json` | `report/3.3.0` |
| `definition/pages/pages.json` | `pagesMetadata/1.1.0` |
| `page.json` | `page/2.1.0` |
| `visual.json` | `visualContainer/2.9.0` |

`version.json` declara la version de definicion PBIR `2.0.0` y
`definition.pbir` conserva la version de artefacto `4.0`. El schema de visual
usado referencia `visualConfiguration/2.3.0` y `semanticQuery/1.4.0`.

Se usa `visualContainer/2.9.0` porque es la version actual publicada y accesible
en el catalogo oficial validado durante esta fase. No se apunta a una version de
schema que Microsoft Desktop pueda emitir pero cuyo endpoint publico no este
disponible.

## Traduccion DashboardPlan -> PBIR

### Paginas

- Cada `DashboardPage.name` produce un ID hexadecimal determinista de 20
  caracteres mediante UUID v5.
- Nombres de pagina duplicados se rechazan.
- `pages.json.pageOrder` conserva el orden de `DashboardPlan.pages`.
- `activePageName` es la primera pagina, cuando existe al menos una.
- `page.json.displayName` conserva el nombre legible y una anotacion conserva el
  objetivo de negocio.

### Visuales

| SIDAD | PBIR | Roles principales |
| --- | --- | --- |
| `Card` | `cardVisual` | `Data` |
| `BarChart` | `clusteredBarChart` | `Category`, `Y`, `Series` opcional |
| `LineChart` | `lineChart` | `Category`, `Y`, `Series` opcional |
| `Table` | `tableEx` | `Values` |
| `PieChart` | `pieChart` | `Category`, `Y`, `Series` opcional |
| `Slicer` | `slicer` | `Values` |

Los elementos de `DashboardPage.slicers` tambien producen visuales `slicer`.
Los titulos se escriben como metadatos de contenedor PBIR, con escape de
literales, y la descripcion se conserva como anotacion.

Cada visual recibe un ID UUID v5 hexadecimal de 20 caracteres calculado desde
la pagina y el contenido canonico del visual. El mismo plan genera los mismos
IDs en directorios distintos. Cambiar el contenido o titulo de un visual cambia
su ID; visuales identicos se distinguen mediante su numero de ocurrencia.

## Resolucion y bindings semanticos

- `kpi_ref` solo puede resolver una medida existente con DAX materializado en el
  TMDL. Una columna con el mismo nombre no se acepta como sustituto.
- Una referencia explicita `SemanticFieldRef` debe coincidir con tabla, campo y
  clase en `SemanticProject`.
- Una referencia historica por nombre se acepta solamente cuando es inequivoca.
  Si la misma columna existe en varias tablas, la exportacion falla y exige una
  referencia explicita o calificada.
- Se admiten formas calificadas `Tabla.columna` y `Tabla[columna]` para columnas
  historicas.
- Las categorias, series y slicers requieren columnas sin agregacion.
- Los valores de graficos aceptan medidas o columnas metricas numericas. Una
  columna metrica historica se traduce a `Aggregation` con `Sum`; las
  agregaciones explicitas usan el codigo oficial de `semanticQuery`.
- `tableEx` admite multiples columnas y medidas mediante
  `VisualBindings.values`.

Las expresiones se escriben como arboles `Column`, `Measure` o `Aggregation`, y
cada proyeccion incluye un `queryRef` estable. No se selecciona una tabla
arbitraria ante ambiguedad.

## Posicion placeholder y frontera con 12.3

`visualContainer` exige `x`, `y`, `width` y `height`. Por ese requisito tecnico,
12.2 escribe la misma posicion placeholder interna para todos los visuales:

```json
{"x": 0, "y": 0, "height": 180, "width": 320}
```

La pagina usa un canvas tecnico `1280 x 720`. Estos valores:

- no se derivan de `DashboardPlan`;
- no consumen `ReportLayout`;
- no intentan distribuir visuales;
- no incluyen `z` ni `tabOrder`;
- se identifican mediante anotaciones como placeholders de 12.2.

La posicion, el tamano, la profundidad, el orden de teclado y la integracion
real `ReportLayout -> PBIR` pertenecen exclusivamente a 12.3.

## Validacion automatizada

`tests/test_powerbi_phase_12_2.py` cubre:

- estructura completa de carpetas y archivos PBIR;
- JSON valido y URLs de schema esperadas;
- IDs deterministas;
- `pageOrder`, `activePageName` y `displayName`;
- los seis `VisualType` soportados;
- roles `queryState` correctos;
- resolucion de columnas, medidas y agregaciones;
- multiples campos en `tableEx`;
- fallo ante referencias inexistentes o ambiguas;
- limpieza de paginas, visuales y archivos legacy stale;
- ausencia de `z` y `tabOrder` en el placeholder de 12.2;
- obligacion de proporcionar `SemanticProject` para planes con paginas;
- bindings reales creados por `DashboardPlanner` para la tabla de detalle.

La prueba en linea
`test_generated_pbir_validates_against_live_official_schemas` descarga los
schemas declarados y valida cada JSON, incluidas sus referencias anidadas. Es
opt-in para no introducir una dependencia de red en la suite normal:

```powershell
$env:SIDAD_VALIDATE_ONLINE_PBIR_SCHEMAS = "1"
python -m pytest tests/test_powerbi_phase_12_2.py::test_generated_pbir_validates_against_live_official_schemas -q -p no:cacheprovider
```

Durante el cierre de esta fase la validacion en linea termino con `1 passed`.

## Evidencia de validacion manual en Power BI Desktop

La validación manual de cierre al abrir
`data/output/powerbi_export/SIDAD.pbip` verificó satisfactoriamente:

- 2 páginas: `Resumen Ejecutivo` y `Análisis Detallado`;
- 12 visuales generados;
- cards, slicers, line chart, clustered bar chart, pie chart y `tableEx`;
- bindings con columnas y medidas reales del modelo semántico;
- carga de los datos reales y funcionamiento de los visuales;
- ausencia de errores por referencias semánticas o formato PBIR.

Como era esperado para el alcance de 12.2, todos los visuales ocuparon la misma
posicion placeholder y aparecieron superpuestos. La comprobacion se centro en
carga, contenido, tipos y bindings; el layout real corresponde a 12.3.

## Limitaciones y riesgos pendientes

- La validacion de schemas comprueba forma JSON, no la existencia de campos en
  TMDL; esa coherencia se valida por separado contra `SemanticProject`.
- Los IDs son estables para contenido estable, pero un cambio de nombre o
  contenido produce un ID nuevo y elimina el anterior como stale.
- Un `VisualElement` externo de tipo `Table` sin campos sigue generando un
  contenedor vacio; el planner propio ya emite bindings multiples reales.
- El alcance propio de 12.2 no incluía layout final, `z`, `tabOrder`, bookmarks,
  interacciones personalizadas, tema materializado ni filtros con selección
  persistida.
- Fase 12.3 consumió `ReportLayout` y sustituyó los placeholders espaciales sin
  reconstruir los bindings validados en esta fase.

## Fuentes primarias

- [Power BI Desktop project report folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)
- [Repositorio oficial de schemas Fabric/PBIR](https://github.com/microsoft/json-schemas/tree/main/fabric/item/report)
- [Schema `report.json` 3.3.0](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json)
- [Schema `page.json` 2.1.0](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json)
- [Schema `visual.json` 2.9.0](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json)
- [Schema de consulta semantica 1.4.0](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/semanticQuery/1.4.0/schema.json)
