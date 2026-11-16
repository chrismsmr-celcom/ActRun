"""ActRun : Couche de coordination pour systèmes multi-agents"""

from .events import ActRunEvent
from .hashing import ContentError, canonical_json, content_hash, snapshot_id
from .workspace import Workspace, Snapshot, Branch, ContentStore, ReplayError
from .resolve import (Conflict, Side, Resolution, Resolver, ResolutionError, PreferBranch,
                      PreferHead, PreferAgent, CallbackResolver, ResolverChain)
from .merge import detect_and_merge, MergeResult, ConflictError
from .lease import LeaseManager, Lease, LeaseError
from .deadlock import WaitForGraph, DeadlockCycle, DeadlockError

__version__ = "0.1.0"
__all__ = [
    "ActRunEvent", "Workspace", "Snapshot", "Branch", "ContentStore", "ReplayError",
    "Conflict", "Side", "Resolution", "Resolver", "ResolutionError", "PreferBranch",
    "PreferHead", "PreferAgent", "CallbackResolver", "ResolverChain",
    "ContentError", "canonical_json", "content_hash", "snapshot_id",
    "detect_and_merge", "MergeResult", "ConflictError",
    "LeaseManager", "Lease", "LeaseError",
    "WaitForGraph", "DeadlockCycle", "DeadlockError",
]
