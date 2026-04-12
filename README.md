# AutoRA Firebase Prolific Experiment Runner

Firebase Prolific Runner provides runners to run experiments with Firebase and Prolific

**WARNING:** The firebase prolific runner creates an experiment on prolific and runs recruits participants automatically. This is an
early alpha version and should be used with extreme caution.

## Quick Start

Install this in an environment using your chosen package manager. In this example we are using virtualenv

Install:
- python (3.8 or greater): https://www.python.org/downloads/
- virtualenv: https://virtualenv.pypa.io/en/latest/installation.html

Install the runner directly:

pip install -U "autora-experiment-runner-firebase-prolific @ git+https://github.com/AutoResearch/autora-experiment-runner-firebase-prolific.git@main"

**WARNING:** Both runners work with a specific set up of the firebase database. For starters, follow this guide to set up an experiment using firebase here: https://github.com/AutoResearch/cra-template-autora-firebase

Study creation on Prolific uses the current Prolific REST schema via `autora-experiment-runner-recruitment-manager-prolific` (`setup_study`: `filters`, `completion_codes`). Use a recent release of that package together with this runner.

## Standalone usage (no researcher_hub dependency)

```python
from autora.experiment_runner.firebase_prolific import firebase_prolific_runner

runner = firebase_prolific_runner(
    firebase_credentials={...},          # service account JSON as dict
    prolific_token="PROLIFIC_API_TOKEN", # from Prolific settings
    sleep_time=5,
    study_name="autora-demo",
    study_description="Category-learning task",
    study_url="https://your-hosted-task.example",
    study_completion_time=10,            # minutes
    completion_code="ABC123",            # optional; random if empty in recruitment manager
)

observations = runner(
    [
        {"condition": {"serialized": "{\"x\":1}"}, "experiment_code": "..."},
        {"condition": {"serialized": "{\"x\":2}"}, "experiment_code": "..."},
    ]
)
```

Required runtime parameters:
- `firebase_credentials`
- `prolific_token`
- `study_name`
- `study_description`
- `study_url`
- `study_completion_time`
- `sleep_time`

## Test without real Prolific/Firebase

Unit tests in this repository fully mock:
- Prolific setup/status transitions (`UNPUBLISHED` -> `PAUSED` -> `STARTED`)
- Firebase availability transitions (`available` -> `unavailable` -> `finished`)
- side effects (`publish_study`, `start_study`, `pause_study`)

Run:

```bash
pytest tests/test_firebase_prolific_runner.py -q
```
