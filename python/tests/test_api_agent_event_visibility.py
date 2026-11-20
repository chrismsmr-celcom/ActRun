from cerbere_cohort import api
from cerbere_cohort.events import CerbereCohortEvent


class _EventWorkspace:
    def get_events(self):
        return [
            CerbereCohortEvent(agent_id="worker-a", action="workspace.commit", payload={"changes": {"a": 1}}),
            CerbereCohortEvent(agent_id="worker-b", action="workspace.commit", payload={"changes": {"secret": "value"}}),
            CerbereCohortEvent(agent_id="worker-a", action="lease.acquire"),
        ]


def test_agent_event_feed_only_returns_own_events(monkeypatch):
    monkeypatch.setattr(api, "workspace", _EventWorkspace())

    result = api.get_events(
        limit=100,
        context={"principal_type": "agent", "agent_id": "worker-a"},
    )

    assert [item["agent_id"] for item in result["items"]] == ["worker-a", "worker-a"]
    assert all("secret" not in str(item) for item in result["items"])


def test_member_event_feed_keeps_organization_wide_visibility(monkeypatch):
    monkeypatch.setattr(api, "workspace", _EventWorkspace())

    result = api.get_events(limit=100, context={"principal_type": "user", "user_id": "user-1"})

    assert {item["agent_id"] for item in result["items"]} == {"worker-a", "worker-b"}
