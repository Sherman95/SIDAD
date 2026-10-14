# Fase 12.3: integración de ReportLayout con PBIR

## Objetivo y estado

La Fase 12.3 conecta el layout físico ya calculado por SIDAD con los visuales
PBIR creados en 12.2:

```text
DashboardPlan + SemanticProject + ReportLayout
                    |
                    v
             PowerBIProvider
                    |
                    v
       PBIR con posiciones y tamaños reales
```

**FASE 12.3 IMPLEMENTADA, VALIDADA ESTRUCTURALMENTE Y VERIFICADA EN POWER BI DESKTOP PARA POSICIONAMIENTO, DIMENSIONES Y DISTRIBUCIÓN DE VISUALES PBIR.**

La verificación manual confirmó que el layout físico generado se interpreta
correctamente en Power BI Desktop y conserva el contenido y los bindings de
12.2.

El provider no calcula el diseño. `ReportGenerator` decide el layout y
`PowerBIProvider` solo asocia, valida y traduce sus valores al contrato PBIR.

## Asociación estable

`visual_identity.py` expande de forma compartida los visuales declarados y los
slicers de página. Para cada instancia genera:

- un fingerprint canónico del `VisualElement`;
- un número de ocurrencia para visuales idénticos;
- un `visual_ref` UUID v5 determinista e independiente de Power BI.

`PlacedVisual.visual_ref` conserva esa referencia dentro de `ReportLayout`.
Antes de escribir archivos, el provider exige una correspondencia uno a uno
entre las páginas y visuales del plan y los elementos posicionados. Falla si:

- falta una página o un visual;
- existe una página adicional;
- un `visual_ref` aparece más de una vez;
- existe un elemento de layout que no pertenece al plan;
- el contenido asociado al `visual_ref` no corresponde al visual original.

Los IDs PBIR de páginas y visuales siguen usando el algoritmo de 12.2. El
layout, sus coordenadas y el orden de `placed_visuals` no participan en esos
IDs.

## Layout determinista

`ReportGenerator` utiliza un canvas base de `1280 x 720` y márgenes de 20 px.
El orden de zonas es:

1. cards;
2. slicers explícitos y slicers declarados en `DashboardPage.slicers`;
3. gráficos y tablas en una cuadrícula de dos columnas.

Restricciones por tipo:

| Tipo | Ancho mínimo | Altura |
| --- | ---: | ---: |
| `Card` | 250 | 100 |
| `Slicer` | 250 | 100 |
| `LineChart` | 400 | 200–440 |
| `BarChart` | 400 | 200–440 |
| `PieChart` | 400 | 200–440 |
| `Table` | 500 | 200–440 |

Si el número de elementos no cabe respetando esas restricciones, el generador
falla en lugar de emitir coordenadas fuera del canvas.

Cada `PlacedVisual` recibe además `z_index` y `tab_order` deterministas siguiendo
el orden espacial generado: cards, slicers y contenido, de izquierda a derecha
y de arriba hacia abajo.

## Traducción a PBIR

`PowerBIProvider` copia a `visual.json.position`:

```json
{
  "x": 20,
  "y": 20,
  "height": 100,
  "width": 295,
  "z": 0,
  "tabOrder": 0
}
```

`page.json.width` y `page.json.height` proceden de `RenderedPage`. Ya no se
utiliza la posición placeholder común de 12.2.

Los campos corresponden a `VisualContainerPosition` del schema oficial
`visualContainer/2.9.0`: `x` e `y` ubican el borde superior izquierdo,
`width`/`height` definen el tamaño, `z` controla profundidad y `tabOrder` la
navegación por teclado.

## Validación AABB

Antes de generar PBIR, el provider reutiliza `LayoutValidator`:

- comprueba tamaños mínimos legibles;
- detecta overflow respecto del canvas;
- detecta intersecciones mediante AABB;
- convierte cualquier issue de nivel `Error` en un fallo explícito de
  exportación.

La ejecución real de cierre produjo un layout `VALIDO`, sin errores ni
advertencias. Una corrupción controlada fue rechazada por solapamiento y
overflow, demostrando que el guardrail está activo.

## Pruebas

`tests/test_powerbi_phase_12_3.py` cubre:

- determinismo del layout y de `visual_ref`;
- canvas `1280 x 720`;
- tamaños mínimos por cada familia visual;
- posiciones distintas, dentro del canvas y sin solapamientos;
- traducción exacta de `x`, `y`, `width`, `height`, `z` y `tabOrder`;
- estabilidad de IDs PBIR aunque cambien posiciones u orden físico;
- asociación independiente del orden de `placed_visuals`;
- error por layout ausente;
- error por visual faltante o asociación duplicada;
- rechazo de overflow y solapamiento por el validador AABB.

Las regresiones de 12.1A y 12.2 permanecen activas. El PBIR generado también se
validó contra los schemas oficiales en línea.

## Evidencia de validación manual en Power BI Desktop

La validación manual de cierre al abrir
`data/output/powerbi_export/SIDAD.pbip` confirmó satisfactoriamente:

- canvas de `1280 × 720`;
- cuatro KPI alineados en la página `Resumen Ejecutivo`;
- slicers distribuidos correctamente;
- gráficos inferiores sin solapamientos;
- página `Análisis Detallado` con slicers, pie chart y tabla correctamente
  distribuidos;
- ausencia de superposiciones entre visuales;
- conservación de páginas, visuales, bindings e IDs deterministas de 12.2;
- datos reales visibles y medidas funcionando correctamente.

## Fuera de alcance

- styling avanzado y materialización de temas;
- bookmarks e interacciones personalizadas;
- responsive layout o canvases alternativos;
- integración del exportador en el agente o `ToolRegistry`;
- cambios en el modelo semántico o en los bindings PBIR de 12.2.

## Fuentes oficiales

- [Power BI Desktop project report folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)
- [Schema visualContainer 2.9.0](https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json)
- [Repositorio oficial de schemas Fabric/PBIR](https://github.com/microsoft/json-schemas/tree/main/fabric/item/report)
