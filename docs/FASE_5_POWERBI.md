# Fase 5: Abstraccion de BI

## Estado

Esta fase introdujo el patron Adapter mediante `BIProvider` y su implementacion
`PowerBIProvider`. La abstraccion sigue vigente: el modelo semantico, el plan y el
layout son modelos de dominio de SIDAD; Power BI es un destino de exportacion.

La implementacion original generaba un `model.tmdl` monolitico y un
`report_spec.json`. Esos artefactos demostraban la traduccion inicial, pero no
constituian un proyecto Power BI validado.

## Evolucion

La generacion estructural del modelo Power BI se completa incrementalmente en
[Fase 12.1A](FASE_12_1A_TMDL.md). Las fases posteriores conservan esta cadena:

`DashboardPlan -> ReportLayout -> PBIR -> Power BI`

El antiguo `report_spec.json` era un artefacto intermedio, no PBIR. El provider ya
no lo genera ni lo usa como sustituto de paginas y visuales oficiales.

## Limite de evidencia

- **Implementado:** adaptador determinista, estructura PBIP y modelo TMDL.
- **Validado automaticamente:** modelos Pydantic, estructura y contenido generado
  mediante pruebas unitarias.
- **Verificado manualmente en Power BI Desktop:** apertura de `SIDAD.pbip`,
  reconocimiento del modelo semantico y de `FACT_DATA`, tipos, medidas DAX,
  lectura de la particion M desde el CSV procesado real y actualizacion sin
  errores.
- **No implementado todavia:** estructura PBIR completa, paginas, visuales,
  bindings, traduccion `ReportLayout -> PBIR` e integracion del exportador en el
  agente.

La evidencia de Desktop cierra la carga y actualizacion del modelo semantico de
12.1A. No demuestra un dashboard terminado, una implementacion completa de Power
BI ni un pipeline Power BI end-to-end validado.
