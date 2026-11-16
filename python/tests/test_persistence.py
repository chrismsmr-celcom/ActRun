import sqlite3

from actrun.persistence import PersistentWorkspace


def test_roundtrip_state_events_and_leases(tmp_path):
    db = tmp_path / "ws.db"
    with PersistentWorkspace(db) as ws:
        b = ws.create_branch("A", "f1")
        b.set("task", "done")
        ws.commit("A", b)
        ws.acquire_lease("A", "X", 30)
        ws.acquire_lease("A", "Y", 30)
        ws.release_lease("A", "Y")
        before = [e.action for e in ws.get_events()]

    with PersistentWorkspace(db) as ws2:
        assert ws2.head.data == {"task": "done"}
        assert ws2.get_active_lease_count() == 1
        assert [e.action for e in ws2.get_events()] == before
        # les événements de lease sont bien en base (régression : seul le dernier événement workspace l'était)
    rows = [r[0] for r in sqlite3.connect(db).execute("select action from events")]
    assert rows.count("lease.acquire") == 2 and rows.count("lease.release") == 1


def test_acquire_lease_accepts_wait_kwargs(tmp_path):
    with PersistentWorkspace(tmp_path / "w.db") as ws:
        ws.acquire_lease("A", "X", 10, wait=True, timeout_seconds=1)


def test_jsonl_export_roundtrip(tmp_path):
    with PersistentWorkspace(tmp_path / "w.db") as ws:
        b = ws.create_branch("A", "f")
        b.set("k", 1)
        ws.commit("A", b)
        n = ws.export_events_jsonl(tmp_path / "out.jsonl")
    assert n == 2
    assert len((tmp_path / "out.jsonl").read_text().splitlines()) == 2


def test_reload_is_a_verified_replay_with_identical_ids(tmp_path):
    db = tmp_path / "ws.db"
    with PersistentWorkspace(db) as ws:
        ws.seed({"spec": "v1", "n": 1})
        a, b = ws.create_branch("A", "a"), ws.create_branch("B", "b")
        a.set("spec", "par A")
        b.set("n", 2)
        ws.commit("A", a)
        ws.commit("B", b)
        head, ids = ws.head.version_id, set(ws._workspace._snapshots)

    with PersistentWorkspace(db) as ws2:
        assert ws2.head.version_id == head
        assert set(ws2._workspace._snapshots) == ids
        assert ws2.head.data == {"spec": "par A", "n": 2}
        c = ws2.create_branch("C", "c")        # la chaîne continue après redémarrage
        c.set("n", 3)
        ws2.commit("C", c)
        assert ws2.head.parents == (head,)


def test_conflict_event_is_persisted_even_though_commit_raises(tmp_path):
    import pytest
    from actrun import ConflictError
    db = tmp_path / "ws.db"
    with PersistentWorkspace(db) as ws:
        ws.seed({"k": 1})
        a, b = ws.create_branch("A", "a"), ws.create_branch("B", "b")
        a.set("k", 2)
        b.set("k", 3)
        ws.commit("A", a)
        with pytest.raises(ConflictError):
            ws.commit("B", b)
    rows = [r[0] for r in sqlite3.connect(db).execute("select action from events")]
    assert rows.count("coordination.conflict") == 1


def test_tampered_database_is_refused_at_load(tmp_path):
    import pytest
    from actrun import ReplayError
    db = tmp_path / "ws.db"
    with PersistentWorkspace(db) as ws:
        ws.seed({"k": "valeur"})
    con = sqlite3.connect(db)
    con.execute("UPDATE objects SET content = '\"falsifié\"'")
    con.commit()
    con.close()
    with pytest.raises(ReplayError):
        PersistentWorkspace(db)


def test_log_written_before_replay_format_is_refused(tmp_path):
    import json
    import pytest
    from actrun import ReplayError
    db = tmp_path / "old.db"
    PersistentWorkspace(db).close()
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO events (event_id, timestamp, agent_id, action, payload_json) VALUES (?,?,?,?,?)",
        ("e1", "2026-01-01T00:00:00+00:00", "A", "workspace.commit",
         json.dumps({"version_id": "x", "parent_version": None, "merge_type": "fast-forward"})),
    )
    con.commit()
    con.close()
    with pytest.raises(ReplayError, match="format antérieur"):
        PersistentWorkspace(db)


def test_resolved_commit_survives_reload_and_replays_identically(tmp_path):
    from actrun import PreferBranch
    db = tmp_path / "res.db"
    with PersistentWorkspace(db) as ws:
        ws.seed({"spec": "v1"})
        a, b = ws.create_branch("A", "a"), ws.create_branch("B", "b")
        a.set("spec", "par A", intent="durcir")
        b.set("spec", "par B")
        ws.commit("A", a)
        ws.commit("B", b, resolver=PreferBranch())
        head = ws.head.version_id
    with PersistentWorkspace(db) as ws2:
        assert ws2.head.version_id == head and ws2.head.data == {"spec": "par B"}
        acts = [e.action for e in ws2.get_events()]
        assert "coordination.resolved" in acts and "coordination.conflict" in acts
