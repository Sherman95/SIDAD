from abc import ABC, abstractmethod
from src.models.semantic_model import SemanticProject
from src.models.dashboard import DashboardPlan

class BIProvider(ABC):
    """
    Interfaz abstracta para proveedores de Business Intelligence.
    Desacopla la lógica heurística del Agente de la tecnología final (Power BI, Tableau, etc.)
    Cumple con el requerimiento de Abstracción de BI (Sección 15).
    """
    @abstractmethod
    def deploy_semantic_model(self, semantic: SemanticProject, output_path: str) -> bool:
        """Exporta o despliega el modelo semántico al formato del proveedor."""
        pass

    @abstractmethod
    def deploy_dashboard(self, plan: DashboardPlan, output_path: str) -> bool:
        """Exporta o despliega la configuración visual al formato del proveedor."""
        pass
