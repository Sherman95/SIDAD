# Fase 12.1A: cierre del modelo semantico y TMDL

## Alcance

Esta fase cierra la representacion de tablas, columnas, KPIs, fuentes CSV y
relaciones antes de implementar paginas o visuales PBIR. La exportacion sigue
siendo determinista; el LLM no escribe TMDL.

**Estado de cierre:** **FASE 12.1A IMPLEMENTADA, VALIDADA ESTRUCTURALMENTE Y
VERIFICADA EN POWER BI DESKTOP PARA CARGA Y ACTUALIZACIÓN DEL MODELO
SEMÁNTICO.**

Esta clasificacion se limita al modelo semantico PBIP/TMDL. No implica que exista
un dashboard completo ni que las fases PBIR posteriores esten implementadas.

## Decisiones de dominio

- `SemanticColumn.data_type` conserva un tipo portable (`String`, `Integer`,
  `Decimal`, `DateTime`, `Boolean`) separado del rol analitico. Un identificador
  entero ya no se convierte a texto o numero por su rol.
- `SemanticTable.source_path` conserva la procedencia real por tabla. La ruta se
  resuelve y valida al exportar respecto a una base explicita o a la raiz estable
  del proyecto; no depende del working directory accidental y no existe un
  dataset de respaldo ficticio.
- `KPI.base_table` elimina la ambiguedad cuando distintas tablas contienen una
  columna con el mismo nombre. Se mantiene `dax_suggestion` como extension
  opcional del modelo actual por compatibilidad; una separacion completa de DAX
  puede abordarse en una evolucion posterior.
- `Relationship` representa explicitamente los extremos, estado activo y
  direccion de filtro. `from_*` es el lado muchos/hechos y `to_*` el lado
  uno/dimension.
- `SemanticProject` valida tablas, columnas, llaves, extremos de relacion, tipos
  compatibles y referencias de KPIs antes de llegar al provider.

El `SemanticBuilder` actual recibe el perfil de una sola tabla plana. Por tanto,
genera `relationships=[]`: no se inventan dimensiones ni relaciones sin evidencia
en los datos o en una entrada de modelado posterior.

## Traduccion Power BI implementada

`PowerBIProvider` genera:

```text
SIDAD.pbip
SIDAD.SemanticModel/
  definition.pbism
  definition/
    database.tmdl
    model.tmdl
    relationships.tmdl       # solo si existen relaciones
    tables/
      <nombre exacto>.tmdl
SIDAD.Report/
  definition.pbir            # solo metadato raiz en esta fase
```

Las particiones CSV:

- usan la ruta real resuelta de cada `SemanticTable`;
- emplean `Encoding = 65001` y `QuoteStyle.Csv`;
- detectan el numero de columnas desde el archivo, sin `Columns=1`;
- promueven los encabezados;
- aplican conversiones M coherentes con los tipos semanticos;
- escapan comillas y la secuencia especial `#(` de Power Query M sin duplicar
  las barras invertidas de rutas Windows;
- fallan de forma explicita si la fuente no existe, no es CSV o conserva un tipo
  desconocido.

La exportacion elimina archivos de tablas o relaciones obsoletos dentro del
directorio generado para que una ejecucion posterior no reincorpore objetos que
ya no pertenecen al modelo. Tambien elimina los antiguos `model.tmdl` y
`report_spec.json` de la raiz de salida; este ultimo no es PBIR.

## Metadatos estructurales

- `definition.pbism` usa version `4.2`, necesaria para la carpeta TMDL
  `definition/`, e incluye su `$schema` oficial.
- `database.tmdl` contiene nivel y modo de compatibilidad.
- `model.tmdl` contiene cultura, `defaultPowerBIDataSourceVersion` y referencias
  de tablas.
- `.pbip` y `definition.pbir` incluyen sus esquemas oficiales.
- `definition.pbir` usa solamente una referencia relativa `byPath`; no emite un
  `byConnection: null`.

El nivel de compatibilidad predeterminado es `1600` y se puede configurar al
crear el provider. TMDL soporta modelos tabulares desde nivel 1200; cambiar el
nivel requiere una prueba de apertura/refresco con la version objetivo de Power
BI Desktop.

## Validación automatizada

La validacion automatizada final se repitio el 2026-09-29 con estos resultados:

```text
python -m pytest tests/test_powerbi_phase_12_1a.py -q -p no:cacheprovider
15 passed

python -m pytest tests -q -p no:cacheprovider -k "not metrics_generation_and_report"
18 passed, 1 deselected

python -m compileall -q src tests run_powerbi.py run_semantic.py run_generator.py run_planner.py run_validator.py
exit 0

git diff --check
exit 0
```

El test `test_metrics_generation_and_report` se excluyo de la suite relevante
porque reescribe `docs/comparison_report.json` con tiempos de ejecucion y no
aporta evidencia funcional a 12.1A.

Las pruebas automatizadas cubren:

- propagacion de fuente y tipos desde `SemanticBuilder`;
- deteccion de claves mediante nombres explicitos y tokens delimitados, sin usar
  una busqueda ingenua por la subcadena `id`;
- clasificacion de `cantidad` como metrica y generacion de `Total Cantidad`;
- traduccion Boolean completa a `type logical` en M y `boolean` en TMDL;
- rechazo de relaciones con extremos inexistentes;
- estructura PBIP/PBISM/PBIR y archivos TMDL requeridos;
- ruta real, UTF-8, encabezados y conversiones de la particion M;
- escape de comillas y de `#(` en literales M, conservando las barras invertidas
  de Windows;
- resolucion de una ruta relativa contra un contexto explicito aun cuando el
  proceso se ejecuta desde un working directory distinto;
- generacion de `relationships.tmdl` con extremos correctos;
- ausencia del antiguo `File.Contents("data.csv")`;
- rechazo de fuentes inexistentes;
- eliminacion de relaciones y tablas generadas obsoletas.

Estas pruebas validan el comportamiento de SIDAD y la estructura contrastada con
la documentacion oficial. No ejecutan automaticamente el parser TOM/TMDL de
Microsoft ni automatizan Power BI Desktop.

## Validación manual en Power BI Desktop

La validacion manual fue realizada sobre la salida real de SIDAD y comprobo:

- apertura correcta de `SIDAD.pbip`;
- reconocimiento del proyecto y de `SIDAD.SemanticModel`;
- carga de la tabla `FACT_DATA`;
- reconocimiento de sus columnas y tipos esperados;
- reconocimiento de `id_venta` como clave/no agregable;
- reconocimiento de `cantidad` y `precio` como columnas numericas agregables;
- reconocimiento de las medidas DAX `Total Registros`, `Total Cantidad`,
  `Total Precio` y `Promedio de Precio`;
- lectura y aceptacion de la particion Power Query M;
- carga desde el CSV procesado real;
- actualizacion del modelo sin errores;
- aceptacion por Power BI Desktop del TMDL generado por SIDAD.

Esta evidencia manual verifica la carga y actualizacion del modelo semantico. No
verifica paginas, visuales, bindings ni layout de un dashboard, porque esos
elementos aun no estan implementados.

## Limitaciones pendientes y fuera de alcance

- Validacion automatizada mediante parser o deserializacion TOM/TMDL oficial.
- Fase 12.2: estructura PBIR completa, incluyendo `report.json`, `version.json`,
  `pages/`, visuales y bindings visuales.
- Traduccion `ReportLayout -> PBIR` (Fase 12.3).
- `export_to_powerbi` en `ToolRegistry` (Fase 12.4).
- Validacion final del dashboard completo en Power BI Desktop (Fase 12.5).

## Fuentes primarias

- [Power BI Desktop projects](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
- [Power BI semantic model project folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset)
- [Power BI report project folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)
- [Tabular Model Definition Language](https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-overview)
- [Csv.Document](https://learn.microsoft.com/en-us/powerquery-m/csv-document)
