from abc import ABC, abstractmethod
from pydantic import BaseModel
from src.agent.state import AgentState

class Decision(BaseModel):
    tool_name: str
    arguments: dict
    operational_reason: str

class LLMProvider(ABC):
    """
    Interfaz abstracta para el motor de razonamiento del Agente.
    Asegura que el orquestador no esté acoplado a un proveedor específico (OpenAI, Anthropic, etc.)
    """
    @abstractmethod
    def predict_next_action(self, state: AgentState, available_tools: list[dict]) -> Decision:
        pass
