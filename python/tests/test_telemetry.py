from cerbere_cohort import telemetry


def test_telemetry_is_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("COHORT_TELEMETRY", raising=False)
    monkeypatch.setenv("COHORT_TELEMETRY_ID_PATH", str(tmp_path / "id"))
    assert telemetry.send_installation_ping() is False
    assert not (tmp_path / "id").exists()


def test_telemetry_sends_only_minimal_installation_fields(monkeypatch, tmp_path):
    captured = {}
    class Response:
        status = 202
        def __enter__(self): return self
        def __exit__(self, *args): return False
    def fake_urlopen(request, timeout):
        import json
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("COHORT_TELEMETRY", "true")
    monkeypatch.setenv("COHORT_TELEMETRY_URL", "https://collector.example.test/api/telemetry/install")
    monkeypatch.setenv("COHORT_TELEMETRY_ID_PATH", str(tmp_path / "id"))
    monkeypatch.setattr(telemetry.urllib.request, "urlopen", fake_urlopen)

    assert telemetry.send_installation_ping() is True
    assert set(captured["payload"]) == {"installation_id", "version", "deployment_type"}
    assert captured["payload"]["deployment_type"] == "self-hosted"
    assert captured["timeout"] == 2
    assert (tmp_path / "id").exists()


def test_telemetry_reuses_installation_identifier(monkeypatch, tmp_path):
    monkeypatch.setenv("COHORT_TELEMETRY_ID_PATH", str(tmp_path / "id"))
    first = telemetry._installation_id()
    second = telemetry._installation_id()
    assert first == second
