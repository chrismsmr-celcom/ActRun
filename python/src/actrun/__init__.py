"""
ActRun : Couche de coordination pour systèmes multi-agents
"""

from .events import ActRunEvent
from .workspace import Workspace, Snapshot, Branch
from .merge import detect_and_merge, MergeResult, ConflictError
from .lease import LeaseManager, Lease, LeaseError, DeadlockError

__version__ = "0.1.0"
__all__ = [
    "ActRunEvent",
    "Workspace",
    "Snapshot", 
    "Branch",
    "detect_and_merge",
    "MergeResult",
    "ConflictError",
    "LeaseManager",
    "Lease",
    "LeaseError",
    "DeadlockError",
]
