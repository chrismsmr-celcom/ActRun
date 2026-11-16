import threading
import time

import pytest

from actrun import DeadlockError, LeaseError, LeaseManager, Workspace


def test_lease_required_only_when_enabled():
    ws = Workspace(require_leases=True)
    b = ws.create_branch("A", "a")
    with pytest.raises(LeaseError):
        b.set("k", 1)
    ws.acquire_lease("A", "k", 5)
    b.set("k", 1)


def test_second_agent_is_refused_then_gets_lease_after_expiry():
    lm = LeaseManager()
    lm.acquire("A", "X", duration_seconds=0.2)
    with pytest.raises(LeaseError):
        lm.acquire("B", "X")
    time.sleep(0.3)
    assert lm.acquire("B", "X").agent_id == "B"


def test_only_holder_can_release():
    lm = LeaseManager()
    lm.acquire("A", "X")
    with pytest.raises(LeaseError):
        lm.release("B", "X")


def test_waiter_gets_resource_when_holder_releases():
    lm = LeaseManager()
    lm.acquire("A", "X", duration_seconds=30)
    got = {}

    def waiter():
        t = time.monotonic()
        got["lease"] = lm.acquire("B", "X", wait=True, timeout_seconds=3)
        got["elapsed"] = time.monotonic() - t

    th = threading.Thread(target=waiter)
    th.start()
    time.sleep(0.2)
    lm.release("A", "X")  # ne doit pas être bloqué par l'attente de B
    th.join(timeout=5)
    assert got["lease"].agent_id == "B"
    assert got["elapsed"] < 1.5


def test_wait_times_out():
    lm = LeaseManager()
    lm.acquire("A", "X", duration_seconds=30)
    with pytest.raises(LeaseError):
        lm.acquire("B", "X", wait=True, timeout_seconds=0.2)


def test_two_agent_deadlock_is_detected_quickly():
    lm = LeaseManager()
    lm.acquire("A", "X", 60)
    lm.acquire("B", "Y", 60)
    outcome = {}

    def a_waits_for_y():
        try:
            lm.acquire("A", "Y", wait=True, timeout_seconds=3)
        except Exception as e:  # noqa: BLE001
            outcome["A"] = e

    th = threading.Thread(target=a_waits_for_y)
    th.start()
    time.sleep(0.2)
    t = time.monotonic()
    with pytest.raises(DeadlockError):
        lm.acquire("B", "X", wait=True, timeout_seconds=3)
    assert time.monotonic() - t < 1.0  # détecté tout de suite, pas après le timeout
    lm.release("B", "Y")  # B abandonne : A peut alors obtenir Y
    th.join(timeout=5)
    assert "A" not in outcome


def test_three_agent_cycle_is_detected():
    lm = LeaseManager()
    for agent, res in (("A", "X"), ("B", "Y"), ("C", "Z")):
        lm.acquire(agent, res, 60)
    threads = []
    for agent, res in (("A", "Y"), ("B", "Z")):
        th = threading.Thread(
            target=lambda a=agent, r=res: _swallow(lambda: lm.acquire(a, r, wait=True, timeout_seconds=2))
        )
        th.start()
        threads.append(th)
        time.sleep(0.15)
    with pytest.raises(DeadlockError):
        lm.acquire("C", "X", wait=True, timeout_seconds=2)
    for th in threads:
        th.join(timeout=5)


def _swallow(fn):
    try:
        fn()
    except Exception:  # noqa: BLE001
        pass
