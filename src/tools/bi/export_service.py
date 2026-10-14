from pathlib import Path

from src.agent.validator import LayoutValidator
from src.models.dashboard import DashboardPlan
from src.models.powerbi_export import PowerBIExportResult
from src.models.report_layout import ReportLayout
from src.models.semantic_model import SemanticProject
from src.tools.bi.powerbi_provider import PowerBIProvider


def export_to_powerbi(
    semantic_project: SemanticProject | None,
    dashboard_plan: DashboardPlan | None,
    report_layout: ReportLayout | None,
    output_path: str | Path,
    project_name: str = "SIDAD",
    source_base_path: str | Path | None = None,
) -> PowerBIExportResult:
    """Valida modelos de dominio y delega la exportacion completa al provider."""

    errors = _missing_model_errors(
        semantic_project,
        dashboard_plan,
        report_layout,
    )
    if errors:
        return _failure(errors)

    assert semantic_project is not None
    assert dashboard_plan is not None
    assert report_layout is not None

    try:
        provider = PowerBIProvider(
            project_name=project_name,
            source_base_path=source_base_path,
        )
        output_dir = _resolve_safe_output_path(
            output_path,
            provider.source_base_path,
        )

        source_paths = provider.validate_semantic_project(semantic_project)
        _validate_output_does_not_contain_sources(output_dir, source_paths)
        provider.validate_dashboard_project(
            dashboard_plan,
            semantic_project,
            report_layout,
        )

        validation = LayoutValidator().validate(report_layout)
        layout_errors = [
            issue.description
            for issue in validation.issues
            if issue.level == "Error"
        ]
        if layout_errors:
            return _failure(
                [f"ReportLayout invalido: {error}" for error in layout_errors],
                output_dir=output_dir,
            )

        provider.deploy_semantic_model(semantic_project, str(output_dir))
        provider.deploy_dashboard(
            dashboard_plan,
            str(output_dir),
            semantic_project,
            report_layout,
        )

        project_path = output_dir / f"{provider.project_name}.pbip"
        semantic_model_path = output_dir / f"{provider.project_name}.SemanticModel"
        report_path = output_dir / f"{provider.project_name}.Report"
        required_paths = [
            project_path,
            semantic_model_path / "definition.pbism",
            semantic_model_path / "definition" / "database.tmdl",
            semantic_model_path / "definition" / "model.tmdl",
            report_path / "definition.pbir",
            report_path / "definition" / "version.json",
            report_path / "definition" / "report.json",
            report_path / "definition" / "pages" / "pages.json",
        ]
        missing_artifacts = [
            str(path) for path in required_paths if not path.is_file()
        ]
        if missing_artifacts:
            return _failure(
                [
                    "La exportacion no genero los artefactos obligatorios: "
                    + ", ".join(missing_artifacts)
                ],
                output_dir=output_dir,
            )

        generated_files = sorted(
            str(path.resolve())
            for root in (semantic_model_path, report_path)
            for path in root.rglob("*")
            if path.is_file()
        )
        generated_files.insert(0, str(project_path.resolve()))
        return PowerBIExportResult(
            success=True,
            project_path=str(project_path.resolve()),
            semantic_model_path=str(semantic_model_path.resolve()),
            report_path=str(report_path.resolve()),
            generated_files=generated_files,
            message="Proyecto PBIP, modelo semantico TMDL y reporte PBIR exportados correctamente.",
        )
    except Exception as exc:
        return _failure([str(exc)], output_dir=locals().get("output_dir"))


def _missing_model_errors(
    semantic_project: SemanticProject | None,
    dashboard_plan: DashboardPlan | None,
    report_layout: ReportLayout | None,
) -> list[str]:
    errors: list[str] = []
    if semantic_project is None:
        errors.append("Falta SemanticProject")
    if dashboard_plan is None:
        errors.append("Falta DashboardPlan")
    if report_layout is None:
        errors.append("Falta ReportLayout")
    return errors


def _resolve_safe_output_path(
    output_path: str | Path,
    source_base_path: Path,
) -> Path:
    raw_output = str(output_path)
    if not raw_output.strip():
        raise ValueError("output_path no puede estar vacio")
    if "\n" in raw_output or "\r" in raw_output:
        raise ValueError("output_path contiene saltos de linea no permitidos")

    candidate = Path(output_path).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
    else:
        resolved = (source_base_path / candidate).resolve(strict=False)
        try:
            resolved.relative_to(source_base_path)
        except ValueError as exc:
            raise ValueError(
                "Una ruta de salida relativa no puede escapar de source_base_path"
            ) from exc

    if resolved == Path(resolved.anchor):
        raise ValueError("output_path no puede ser la raiz del sistema")
    if resolved == source_base_path:
        raise ValueError("output_path no puede ser la raiz estable del proyecto")
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("output_path debe apuntar a un directorio")

    raw_data_dir = (source_base_path / "data" / "raw").resolve(strict=False)
    if resolved == raw_data_dir or raw_data_dir in resolved.parents:
        raise ValueError("No se permite exportar dentro de data/raw")
    return resolved


def _validate_output_does_not_contain_sources(
    output_dir: Path,
    source_paths: list[Path],
) -> None:
    for source_path in source_paths:
        try:
            source_path.relative_to(output_dir)
        except ValueError:
            continue
        raise ValueError(
            "output_path no puede contener el dataset fuente que sera exportado"
        )


def _failure(
    errors: list[str],
    *,
    output_dir: Path | None = None,
) -> PowerBIExportResult:
    location = str(output_dir) if output_dir is not None else None
    return PowerBIExportResult(
        success=False,
        project_path=None,
        semantic_model_path=None,
        report_path=None,
        generated_files=[],
        message="No se pudo exportar el proyecto Power BI.",
        errors=errors if errors else ([f"Fallo de exportacion en {location}"] if location else []),
    )
