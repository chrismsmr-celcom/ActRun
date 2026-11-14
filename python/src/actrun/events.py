# python/src/actrun/events.py
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict

class ActRunEvent(BaseModel):
    """
    Représente un événement immuable dans le journal ActRun.
    Ce modèle est strictement aligné avec schemas/event.v1.schema.json
    """
    model_config = ConfigDict(frozen=True)  # Rend l'objet immuable après création

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 timestamp")
    agent_id: str = Field(..., description="ID of the acting agent")
    action: str = Field(..., description="Type of action performed")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action-specific data")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")

    def to_jsonl(self) -> str:
        """Sérialise l'événement au format JSONL (une ligne par événement)"""
        return self.model_dump_json()

    @classmethod
    def from_jsonl(cls, line: str) -> "ActRunEvent":
        """Désérialise une ligne JSONL en objet ActRunEvent"""
        return cls.model_validate_json(line)
