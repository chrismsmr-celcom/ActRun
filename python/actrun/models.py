from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional

@dataclass
class ActRunEvent:
    agent_id: str
    action: str
    payload: Dict[str, Any]
    schema_version: str = "1.0.0"
    event_id: str = ""
    timestamp: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
