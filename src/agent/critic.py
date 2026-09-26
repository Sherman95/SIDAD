from src.agent.state import AgentState, CriticVerdict

class Critic:
    """
    Componente general de evaluación.
    Intercepta los resultados de validación y de las herramientas, y emite
    veredictos (CriticVerdict) estructurados para que el LLM (o Mock) pueda
    entender la causa raíz de un fallo y tomar acción correctiva.
    """
    def evaluate(self, state: AgentState) -> list[CriticVerdict]:
        verdicts = []
        
        # 1. Evaluar Layout Visual (Generado en Fase 6, validado en Fase 7)
        if state.validation_report and not state.validation_report.is_valid:
            for issue in state.validation_report.issues:
                if issue.level == "Error":
                    recommended_action = "review_design"
                    # Si el validador AABB detectó un error (ej. colisión o overflow)
                    if "superposición" in issue.description.lower() or "overflow" in issue.description.lower():
                        recommended_action = "regenerate_layout"
                        
                    verdicts.append(CriticVerdict(
                        status="FAIL",
                        issue=issue.description,
                        severity=issue.level.upper(),
                        recommended_action=recommended_action,
                        reason="Detectado por LayoutValidator algorítmico."
                    ))
                    
        # (Futuro: Aquí se pueden agregar validaciones sobre Datos o Modelo Semántico)
        # ej. if state.dataset_profile.null_count > 0 and no hay logs de limpieza...
        
        return verdicts
