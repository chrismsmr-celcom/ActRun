from cerbere_cohort import CerbereCohortEvent


def test_event_jsonl_roundtrip():
    e = CerbereCohortEvent(agent_id="A", action="workspace.branch", payload={"branch_name": "x"})
    assert CerbereCohortEvent.from_jsonl(e.to_jsonl()) == e
