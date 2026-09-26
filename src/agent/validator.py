from pydantic import BaseModel, Field
from src.models.report_layout import ReportLayout, PlacedVisual

class ValidationIssue(BaseModel):
    level: str = Field(description="'Warning' o 'Error'")
    description: str = Field(description="Descripción del problema visual detectado")
    element_ref: str = Field(description="Referencia al elemento urológico afectado")

class ValidationReport(BaseModel):
    is_valid: bool = Field(description="Indica si el layout está libre de Errores críticos")
    issues: list[ValidationIssue] = Field(default_factory=list)

class LayoutValidator:
    """
    Simula la 'Validación Visual' descrita en la Sección 18.
    Evalúa determinísticamente las coordenadas físicas y las cajas delimitadoras (Bounding Boxes)
    para detectar superposiciones, ilegibilidad y problemas de jerarquía sin requerir renderizado humano.
    """
    def validate(self, layout: ReportLayout) -> ValidationReport:
        issues = []
        
        for page in layout.pages:
            total_area = page.canvas_width * page.canvas_height
            used_area = 0
            
            # 1. Analizar reglas individuales y superposiciones
            for i, v1 in enumerate(page.placed_visuals):
                used_area += (v1.position.width * v1.position.height)
                
                # Regla: Ilegibilidad por tamaño reducido
                if v1.position.width < 250 or v1.position.height < 100:
                    issues.append(ValidationIssue(
                        level="Error",
                        description=f"El visual '{v1.visual.title}' es demasiado pequeño y será ilegible ({v1.position.width}x{v1.position.height}px).",
                        element_ref=v1.visual.title
                    ))
                
                # Regla: Salida del lienzo (Overflow)
                if (v1.position.x + v1.position.width > page.canvas_width) or (v1.position.y + v1.position.height > page.canvas_height):
                    issues.append(ValidationIssue(
                        level="Error",
                        description=f"El visual '{v1.visual.title}' excede los límites del lienzo (Overflow).",
                        element_ref=v1.visual.title
                    ))

                # Check overlaps
                for j, v2 in enumerate(page.placed_visuals):
                    if i >= j: continue # Evitar comprobaciones redundantes
                    
                    if self._check_overlap(v1, v2):
                        issues.append(ValidationIssue(
                            level="Error",
                            description=f"Superposición detectada entre gráficos: '{v1.visual.title}' y '{v2.visual.title}'.",
                            element_ref=f"{v1.visual.title} | {v2.visual.title}"
                        ))
                        
            # 2. Heurística de espacios vacíos
            if total_area > 0:
                utilization = used_area / total_area
                if utilization < 0.20 and len(page.placed_visuals) > 0:
                    issues.append(ValidationIssue(
                        level="Warning",
                        description=f"La página '{page.page_info.name}' desperdicia demasiado espacio (Área usada: {utilization*100:.1f}%).",
                        element_ref=page.page_info.name
                    ))
                elif utilization > 0.85:
                    issues.append(ValidationIssue(
                        level="Warning",
                        description=f"La página '{page.page_info.name}' está muy saturada y dificulta la jerarquía visual (Área usada: {utilization*100:.1f}%).",
                        element_ref=page.page_info.name
                    ))
                
        # Es válido solo si no hay problemas de nivel "Error"
        is_valid = len([i for i in issues if i.level == "Error"]) == 0
        return ValidationReport(is_valid=is_valid, issues=issues)
        
    def _check_overlap(self, v1: PlacedVisual, v2: PlacedVisual) -> bool:
        """Verifica intersección usando lógica de cajas delimitadoras (AABB)."""
        p1 = v1.position
        p2 = v2.position
        
        # Un rectangulo está totalmente a la izquierda o derecha del otro
        if p1.x >= p2.x + p2.width or p2.x >= p1.x + p1.width:
            return False
            
        # Un rectangulo está totalmente arriba o abajo del otro
        if p1.y >= p2.y + p2.height or p2.y >= p1.y + p1.height:
            return False
            
        return True
