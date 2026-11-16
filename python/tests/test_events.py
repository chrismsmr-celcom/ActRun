from actrun import ActRunEvent


def test_event_jsonl_roundtrip():
    e = ActRunEvent(agent_id="A", action="workspace.branch", payload={"branch_name": "x"})
    assert ActRunEvent.from_jsonl(e.to_jsonl()) == e
