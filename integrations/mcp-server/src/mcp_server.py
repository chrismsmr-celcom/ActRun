"""
ActRun MCP Server
=================
Expose ActRun coordination tools to LLMs via Model Context Protocol.

Usage:
    python -m mcp_server
"""
import asyncio
import json
import sys
import os
from typing import Any

# Ajouter le chemin pour importer actrun (si pas installé globalement)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../python/src'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from actrun.workspace import Workspace
from actrun.merge import ConflictError
from actrun.lease import LeaseError

# === État global partagé ===
# Un seul workspace pour toute la session MCP
workspace = Workspace()

# Initialiser avec un état par défaut
workspace.head.data.update({
    "status": "initialized",
    "message": "ActRun workspace prêt. Utilisez les tools pour collaborer."
})


# === Création du serveur MCP ===
server = Server("actrun")


# === DÉFINITION DES TOOLS ===

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Liste tous les outils disponibles pour le LLM."""
    return [
        types.Tool(
            name="workspace_get_state",
            description="Lit l'état actuel du workspace partagé (HEAD). Retourne toutes les clés et valeurs.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="workspace_create_branch",
            description=(
                "Crée une nouvelle branche isolée à partir de l'état actuel. "
                "À utiliser AVANT de modifier l'état pour ne pas perturber les autres agents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Identifiant de l'agent"},
                    "branch_name": {"type": "string", "description": "Nom de la branche"},
                },
                "required": ["agent_id", "branch_name"],
            },
        ),
        types.Tool(
            name="workspace_set_in_branch",
            description=(
                "Modifie une clé dans une branche. "
                "Nécessite d'avoir un lease actif sur cette clé (voir lease_acquire)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "branch_name": {"type": "string"},
                    "key": {"type": "string"},
                    "value": {"description": "La nouvelle valeur (tout type JSON)"},
                },
                "required": ["agent_id", "branch_name", "key", "value"],
            },
        ),
        types.Tool(
            name="workspace_commit",
            description=(
                "Valide les modifications d'une branche dans le workspace principal. "
                "Détecte automatiquement les conflits avec les commits d'autres agents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "branch_name": {"type": "string"},
                },
                "required": ["agent_id", "branch_name"],
            },
        ),
        types.Tool(
            name="lease_acquire",
            description=(
                "Réserve une ressource (clé) pour une durée donnée. "
                "Empêche les autres agents de la modifier pendant ce temps. "
                "À utiliser AVANT de modifier une ressource partagée."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "resource_key": {"type": "string"},
                    "duration_seconds": {
                        "type": "number",
                        "description": "Durée du verrou en secondes (défaut: 30)",
                        "default": 30.0,
                    },
                },
                "required": ["agent_id", "resource_key"],
            },
        ),
        types.Tool(
            name="lease_release",
            description="Libère volontairement un verrou sur une ressource.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "resource_key": {"type": "string"},
                },
                "required": ["agent_id", "resource_key"],
            },
        ),
        types.Tool(
            name="get_events",
            description=(
                "Retourne le journal immuable de tous les événements. "
                "Utile pour auditer ce qui s'est passé ou déboguer."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Nombre max d'événements à retourner (défaut: 50)",
                        "default": 50,
                    }
                },
            },
        ),
    ]


# === STOCKAGE DES BRANCHES EN MÉMOIRE ===
# Les branches doivent être conservées entre les appels d'outils
_branches: dict[str, Any] = {}


def _get_branch(agent_id: str, branch_name: str):
    """Récupère une branche existante ou lève une erreur."""
    key = f"{agent_id}:{branch_name}"
    if key not in _branches:
        raise ValueError(f"Branche '{branch_name}' introuvable pour l'agent '{agent_id}'. Créez-la d'abord avec workspace_create_branch.")
    return _branches[key]


# === APPEL DES TOOLS ===

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Dispatche l'appel vers la bonne fonction."""
    try:
        if name == "workspace_get_state":
            return _handle_get_state()
        elif name == "workspace_create_branch":
            return _handle_create_branch(**arguments)
        elif name == "workspace_set_in_branch":
            return _handle_set_in_branch(**arguments)
        elif name == "workspace_commit":
            return _handle_commit(**arguments)
        elif name == "lease_acquire":
            return _handle_lease_acquire(**arguments)
        elif name == "lease_release":
            return _handle_lease_release(**arguments)
        elif name == "get_events":
            return _handle_get_events(**arguments)
        else:
            return [types.TextContent(type="text", text=f"❌ Outil inconnu : {name}")]
    except (ConflictError, LeaseError, ValueError) as e:
        return [types.TextContent(type="text", text=f"⚠️ Erreur : {e}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Erreur interne : {type(e).__name__}: {e}")]


# === HANDLERS ===

def _handle_get_state() -> list[types.TextContent]:
    state = workspace.head.data
    text = f"📍 État actuel du workspace (HEAD: {workspace.head.version_id[:8]})\n\n"
    if not state:
        text += "(vide)"
    else:
        for k, v in state.items():
            text += f"  • {k}: {json.dumps(v, ensure_ascii=False)}\n"
    return [types.TextContent(type="text", text=text)]


def _handle_create_branch(agent_id: str, branch_name: str) -> list[types.TextContent]:
    branch = workspace.create_branch(agent_id, branch_name)
    _branches[f"{agent_id}:{branch_name}"] = branch
    return [types.TextContent(
        type="text",
        text=f"✅ Branche '{branch_name}' créée par {agent_id} à partir de la version {branch.base_version[:8]}"
    )]


def _handle_set_in_branch(agent_id: str, branch_name: str, key: str, value: Any) -> list[types.TextContent]:
    branch = _get_branch(agent_id, branch_name)
    branch.set(key, value)
    return [types.TextContent(
        type="text",
        text=f"✅ Clé '{key}' mise à jour dans la branche '{branch_name}' de {agent_id}"
    )]


def _handle_commit(agent_id: str, branch_name: str) -> list[types.TextContent]:
    branch = _get_branch(agent_id, branch_name)
    snapshot = workspace.commit(agent_id, branch)
    # Supprimer la branche après commit (elle est "consommée")
    del _branches[f"{agent_id}:{branch_name}"]
    return [types.TextContent(
        type="text",
        text=f"✅ Commit réussi ! Nouvelle version HEAD : {snapshot.version_id[:8]}"
    )]


def _handle_lease_acquire(agent_id: str, resource_key: str, duration_seconds: float = 30.0) -> list[types.TextContent]:
    lease = workspace.acquire_lease(agent_id, resource_key, duration_seconds)
    return [types.TextContent(
        type="text",
        text=f"🔒 Lease acquis sur '{resource_key}' par {agent_id} pour {duration_seconds}s"
    )]


def _handle_lease_release(agent_id: str, resource_key: str) -> list[types.TextContent]:
    workspace.release_lease(agent_id, resource_key)
    return [types.TextContent(
        type="text",
        text=f"🔓 Lease libéré sur '{resource_key}' par {agent_id}"
    )]


def _handle_get_events(limit: int = 50) -> list[types.TextContent]:
    events = workspace.get_events()
    if not events:
        return [types.TextContent(type="text", text="📜 Aucun événement enregistré.")]
    
    recent = events[-limit:]
    lines = [f"📜 {len(events)} événements au total (derniers {len(recent)}) :\n"]
    for e in recent:
        lines.append(f"  • [{e.action}] {e.agent_id} → {json.dumps(e.payload, ensure_ascii=False)}")
    
    return [types.TextContent(type="text", text="\n".join(lines))]


# === POINT D'ENTRÉE ===

async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Point d'entrée CLI."""
    asyncio.run(_run())


if __name__ == "__main__":
    main()
