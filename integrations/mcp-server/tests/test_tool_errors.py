# integrations/mcp-server/tests/test_tool_errors.py
"""Contrat d'erreurs structuré au niveau MCP : chaque échec d'outil transporte
une enveloppe JSON {"code", "message", "details"} ; les messages français
d'origine sont préservés ; aucune repr Python brute ne circule sans structure."""
import asyncio
import json
import time

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from mcp_server import CohortService, create_server


def _call_tool(server, name: str, **arguments) -> dict:
    """Exécute un outil via le tool manager FastMCP et retourne l'enveloppe d'erreur JSON.

    Reproduit le chemin exact de production : Tool.run enveloppe toute exception
    en ToolError("Error executing tool <name>: <message>").
    """
    with pytest.raises(ToolError) as info:
        asyncio.run(server._tool_manager.call_tool(name, arguments))
    message = info.value.args[0]
    start = message.index("{")
    return json.loads(message[start:])


@pytest.fixture()
def service(tmp_path):
    svc = CohortService(tmp_path / "cohort.db")
    yield svc
    svc.close()


@pytest.fixture()
def server(service):
    return create_server(service)


def test_conflict_envelope_has_stable_code_and_details(server):
    server._tool_manager.call_tool  # attribut présent
    asyncio.run(server._tool_manager.call_tool(
        "workspace_create_branch", {"agent_id": "cursor", "branch_name": "cursor-work"}
    ))
    asyncio.run(server._tool_manager.call_tool(
        "workspace_create_branch", {"agent_id": "codex", "branch_name": "codex-work"}
    ))
    asyncio.run(server._tool_manager.call_tool(
        "workspace_set_in_branch",
        {"agent_id": "cursor", "branch_name": "cursor-work", "key": "shared", "value": "cursor"},
    ))
    asyncio.run(server._tool_manager.call_tool(
        "workspace_set_in_branch",
        {"agent_id": "codex", "branch_name": "codex-work", "key": "shared", "value": "codex"},
    ))
    asyncio.run(server._tool_manager.call_tool(
        "workspace_commit", {"agent_id": "cursor", "branch_name": "cursor-work"}
    ))
    envelope = _call_tool(server, "workspace_commit", agent_id="codex", branch_name="codex-work")
    assert envelope["code"] == "conflict_detected"
    assert envelope["details"]["conflicting_keys"] == ["shared"]
    assert envelope["details"]["head_version"]
    assert "Conflit détecté" in envelope["message"]


def test_lease_not_owner_envelope_names_holder(server):
    asyncio.run(server._tool_manager.call_tool(
        "lease_acquire", {"agent_id": "holder-1", "resource_key": "res/r1", "duration_seconds": 30}
    ))
    envelope = _call_tool(server, "lease_release", agent_id="intruder", resource_key="res/r1")
    assert envelope["code"] == "lease_not_owner"
    assert envelope["details"] == {
        "agent_id": "intruder",
        "resource_key": "res/r1",
        "holder": "holder-1",
    }


def test_lease_held_envelope_carries_expiry(server):
    asyncio.run(server._tool_manager.call_tool(
        "lease_acquire", {"agent_id": "holder-2", "resource_key": "res/r2", "duration_seconds": 30}
    ))
    envelope = _call_tool(
        server, "lease_acquire", agent_id="other", resource_key="res/r2", duration_seconds=30
    )
    assert envelope["code"] == "lease_held"
    assert envelope["details"]["holder"] == "holder-2"
    assert envelope["details"]["expires_at"] > time.time()


def test_expired_lease_is_acquirable_by_other_agent(server):
    asyncio.run(server._tool_manager.call_tool(
        "lease_acquire", {"agent_id": "short-holder", "resource_key": "res/r3", "duration_seconds": 0.1}
    ))
    time.sleep(0.3)
    result = asyncio.run(server._tool_manager.call_tool(
        "lease_acquire", {"agent_id": "next-owner", "resource_key": "res/r3", "duration_seconds": 30}
    ))
    # call_tool renvoie le résultat converti : extraire la petite structure acquisite.
    payload = json.dumps(result, default=str)
    assert "next-owner" in payload
    assert "res/r3" in payload


def test_release_of_never_held_key_stays_backward_compatible(server):
    result = asyncio.run(server._tool_manager.call_tool(
        "lease_release", {"agent_id": "anyone", "resource_key": "res/unknown"}
    ))
    payload = json.dumps(result, default=str)
    # comportement historique conservé : succès silencieux (anomalie documentée)
    assert "released" in payload


def test_invalid_operations_map_to_invalid_argument(server):
    envelope = _call_tool(server, "workspace_commit", agent_id="ghost", branch_name="nope")
    assert envelope["code"] == "invalid_argument"
    assert "not found" in envelope["message"]

    envelope = _call_tool(server, "get_events", limit=0)
    assert envelope["code"] == "invalid_argument"

    envelope = _call_tool(server, "workspace_create_branch", agent_id="  ", branch_name="b")
    assert envelope["code"] == "invalid_argument"

    envelope = _call_tool(
        server, "workspace_create_branch", agent_id="a" * 300, branch_name="too-long"
    )
    assert envelope["code"] == "invalid_argument"


def test_successful_calls_are_untouched(server):
    result = asyncio.run(server._tool_manager.call_tool(
        "workspace_create_branch", {"agent_id": "cursor", "branch_name": "ok"}
    ))
    text = json.dumps(result, default=str)
    assert "ok" in text and "cursor" in text
