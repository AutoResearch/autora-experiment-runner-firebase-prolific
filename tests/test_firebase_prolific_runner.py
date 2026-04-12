from autora.experiment_runner import firebase_prolific as runner_mod


def test_firebase_prolific_runner_transitions_without_real_services(monkeypatch):
    calls = {
        "send_conditions": 0,
        "publish_study": 0,
        "start_study": 0,
        "pause_study": 0,
    }

    def fake_send_conditions(*_args, **_kwargs):
        calls["send_conditions"] += 1

    firebase_states = iter(["available", "available", "unavailable", "finished"])
    prolific_states = iter(
        [
            {"status": "UNPUBLISHED", "number_of_submissions_finished": 0, "total_available_places": 2},
            {"status": "PAUSED", "number_of_submissions_finished": 0, "total_available_places": 2},
            {"status": "STARTED", "number_of_submissions_finished": 0, "total_available_places": 2},
            {"status": "STARTED", "number_of_submissions_finished": 2, "total_available_places": 2},
        ]
    )

    monkeypatch.setattr(runner_mod, "send_conditions", fake_send_conditions)
    monkeypatch.setattr(
        runner_mod, "setup_study", lambda *args, **kwargs: {"id": "study-1", "maximum_allowed_time": 30}
    )
    monkeypatch.setattr(runner_mod, "check_firebase_status", lambda *_args, **_kwargs: next(firebase_states))
    monkeypatch.setattr(runner_mod, "check_prolific_status", lambda *_args, **_kwargs: next(prolific_states))
    monkeypatch.setattr(runner_mod, "get_observations", lambda *_args, **_kwargs: {"0": {"y": 1}})
    monkeypatch.setattr(runner_mod, "get_submissions_incompleted", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(runner_mod, "approve_all_no_code", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runner_mod, "request_return_all", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runner_mod, "publish_study", lambda *_args, **_kwargs: calls.__setitem__("publish_study", calls["publish_study"] + 1))
    monkeypatch.setattr(runner_mod, "start_study", lambda *_args, **_kwargs: calls.__setitem__("start_study", calls["start_study"] + 1))
    monkeypatch.setattr(runner_mod, "pause_study", lambda *_args, **_kwargs: calls.__setitem__("pause_study", calls["pause_study"] + 1))
    monkeypatch.setattr(runner_mod.time, "sleep", lambda *_args, **_kwargs: None)

    runner = runner_mod.firebase_prolific_runner(
        firebase_credentials={"project_id": "demo"},
        prolific_token="TOKEN",
        sleep_time=0,
        study_name="autora-test",
        study_description="desc",
        study_url="https://example.org",
        study_completion_time=3,
        completion_code="ABC123",
    )
    out = runner([{"condition": 0}, {"condition": 1}])

    assert out == [{"y": 1}]
    assert calls["send_conditions"] == 1
    assert calls["publish_study"] == 1
    assert calls["start_study"] == 1
    assert calls["pause_study"] == 1
