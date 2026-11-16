# python/src/cerbere_cohort/events.py
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CerbereCohortEvent(BaseModel):
    """Immutable event in the Cerbere Cohort append-only log.

    The serialized representation follows schemas/event.v1.schema.json.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0.0"] = Field(
        default="1.0.0",
        description="Version of the serialized event contract",
    )
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique event ID",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp",
    )
    agent_id: str = Field(..., description="ID of the acting agent")
    action: str = Field(..., description="Type of action performed")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific data",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context",
    )

    def to_jsonl(self) -> str:
        """Serialize one event as a JSONL record."""
        return self.model_dump_json()

    @classmethod
    def from_jsonl(cls, line: str) -> "CerbereCohortEvent":
        """Deserialize one JSONL record.

        Legacy records without schema_version are accepted as v1.0.0.
        """
        return cls.model_validate_json(line)


# Backward-compatible event model alias for existing integrations.
ActRunEvent = CerbereCohortEvent
