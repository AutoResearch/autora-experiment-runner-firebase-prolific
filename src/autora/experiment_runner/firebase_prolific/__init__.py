import time
from datetime import datetime

from autora.experiment_runner.experimentation_manager.firebase import (
    check_firebase_status,
    get_observations,
    get_observations_with_meta,
    send_conditions,
)
from autora.experiment_runner.recruitment_manager.prolific import (
    check_prolific_status,
    pause_study,
    setup_study,
    start_study,
    publish_study,
    get_submissions_incompleted,
    request_return_all,
    approve_all_no_code,
    approve_all,
)


def _log(message: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[firebase_prolific {ts}] {message}", flush=True)


def _validate_firebase_prolific_kwargs(kwargs):
    required = [
        "firebase_credentials",
        "sleep_time",
        "study_name",
        "study_description",
        "study_url",
        "study_completion_time",
        "prolific_token",
    ]
    missing = [k for k in required if k not in kwargs or kwargs[k] in (None, "")]
    if missing:
        raise ValueError(
            "firebase_prolific_runner missing required arguments: "
            + ", ".join(sorted(missing))
        )
    study_url = str(kwargs["study_url"])
    if not (study_url.startswith("http://") or study_url.startswith("https://")):
        raise ValueError("study_url must start with http:// or https://")


def _observations_as_sorted_list(collection_name: str, firebase_credentials: dict):
    """Return observations as a list ordered by slot key.

    Each element is an envelope dict::

        {
            "slot_key":     <autora condition slot key, str>,
            "prolific_pid": <Prolific participant id from autora_meta.<slot>.pId,
                             or None when the slot was claimed without a
                             Prolific URL (local dev)>,
            "obs":          <observation payload from setObservation>,
        }

    Downstream parsers in sweetbean (`parse_autora_observations`) accept
    this envelope shape, so per-subject reports can carry `prolific_pid`
    end-to-end (kept and dropped subjects alike — important for payment).

    Pre-patch this helper returned a list of bare observation strings; the
    envelope is a strict superset and the obs string is still available
    under the ``obs`` key, so any caller that previously did
    ``json.loads(item)`` should switch to ``json.loads(item["obs"])``.
    """
    joined = get_observations_with_meta(collection_name, firebase_credentials)
    return [
        {
            "slot_key": key,
            "prolific_pid": joined[key].get("pId"),
            "obs": joined[key].get("obs"),
        }
        for key in sorted(joined.keys())
    ]


def _firebase_run(conditions, **kwargs):
    """
    Running an experiment with firebase to host the experiment and store the data.
    Args:
        conditions: the conditions
        **kwargs:  configuration of the experiment (this typically doesn't vary from cycle to cycle)

    Returns:
        observations
    """
    firebase_credentials = kwargs["firebase_credentials"]
    time_out = None
    if "time_out" in kwargs:
        time_out = kwargs["time_out"]
    sleep_time = kwargs["sleep_time"]

    # set up study on firebase
    send_conditions("autora", conditions, firebase_credentials)

    # run the experiment as long as not all conditions are met
    while True:
        check_firebase = check_firebase_status("autora", firebase_credentials, time_out)
        if check_firebase == "finished":
            # get observations returns a dict
            return _observations_as_sorted_list("autora", firebase_credentials)
        time.sleep(sleep_time)


def _firebase_prolific_run(conditions, **kwargs):
    """
    Running an experiment with firebase to host the experiment and store the data
    and prolific to recruit participants
    Args:
        conditions: the conditions
        **kwargs: configuration of the experiment (this typically doesn't vary from cycle to cycle)

    Returns:
        observations
    """
    if not 'exclude_studies' in kwargs:
        exclude_studies = ["default"]
    else:
        exclude_studies = kwargs["exclude_studies"]

    if not 'approve_no_code' in kwargs:
        print(
            'Warning: Approving submissions with no code. Set approve_no_code to False if no code submissions should be requested to return')
        approve_no_code = True
    else:
        approve_no_code = kwargs['approve_no_code']

    # set up study on firebase
    _log(f"Uploading {len(conditions)} conditions to Firebase")
    send_conditions("autora", conditions, kwargs["firebase_credentials"])

    # set up study on prolific
    _log("Creating Prolific study draft")
    # `reward` is the per-participant payment in the smallest currency unit
    # (cents / pence). 0 (default) keeps the upstream auto-calc inside
    # setup_study (20 * estimated_completion_time, i.e. ~$12/hour). Pass an
    # explicit value to anchor at e.g. Prolific's policy minimum.
    prolific_dict = setup_study(
        kwargs["study_name"],
        kwargs["study_description"],
        kwargs["study_url"],
        kwargs["study_completion_time"],
        kwargs["prolific_token"],
        total_available_places=len(conditions),
        completion_code=kwargs.get("completion_code", ""),
        exclude_studies=exclude_studies,
        reward=int(kwargs.get("reward", 0) or 0),
        # Optional project pin. Required for tokens whose effective scope is
        # project-level (typical for shared lab accounts): without it the
        # study lands outside the token's reach and the subsequent PUBLISH
        # transition 400s with error_code 140007 ("A Researcher is not
        # allowed to publish a UNPUBLISHED study"). Default None keeps
        # existing single-workspace setups unaffected — Prolific then
        # routes the new study to the token's default location.
        project_id=kwargs.get("project_id"),
    )
    if not prolific_dict or "id" not in prolific_dict:
        raise RuntimeError(
            "Failed to set up Prolific study. "
            "Check for existing uncompleted studies with the same name or API errors."
        )

    # get the specification on prolific
    time_out = prolific_dict["maximum_allowed_time"] * 60
    study_id = prolific_dict["id"]
    _log(f"Prolific study ready (id={study_id}, firebase_timeout={time_out}s)")
    counter = 1

    while True:
        # check firebase
        check_firebase = check_firebase_status(
            "autora", kwargs["firebase_credentials"], time_out
        )
        _log(f"Loop {counter}: Firebase status={check_firebase}")
        if check_firebase == "finished":
            # Firebase completion is sufficient to terminate and return observations.
            # Avoid extra Prolific API calls that can stall shutdown.
            _log("Firebase finished; returning observations")
            return _observations_as_sorted_list("autora", kwargs["firebase_credentials"])
        # check prolific
        if prolific_dict:
            incomplete_submissions = get_submissions_incompleted(
                study_id, kwargs["prolific_token"]
            )
            if incomplete_submissions:
                _log(
                    f"Loop {counter}: freeing {len(incomplete_submissions)} returned/timed-out participants"
                )
            check_firebase = check_firebase_status(
                "autora", kwargs["firebase_credentials"], time_out, incomplete_submissions
            )
            if check_firebase == "finished":
                _log("Firebase finished after abort cleanup; returning observations")
                return _observations_as_sorted_list("autora", kwargs["firebase_credentials"])
            if not counter % 5:
                if approve_no_code:
                    _log("Auto-approving no-code submissions")
                    approve_all_no_code(study_id, kwargs["prolific_token"])
                else:
                    _log("Requesting return for no-code submissions")
                    request_return_all(study_id, kwargs["prolific_token"])

            check_prolific = check_prolific_status(study_id, kwargs["prolific_token"])
            _log(
                "Loop "
                f"{counter}: Prolific status={check_prolific['status']} "
                f"finished={check_prolific['number_of_submissions_finished']}/"
                f"{check_prolific['total_available_places']}"
            )
            if (
                    check_prolific["number_of_submissions_finished"]
                    >= check_prolific["total_available_places"]
            ):
                if check_firebase == "finished":
                    return _observations_as_sorted_list("autora", kwargs["firebase_credentials"])
                else:
                    print(
                        "Warning: Number of collected participants was lower than submission number")
                    return _observations_as_sorted_list("autora", kwargs["firebase_credentials"])

            # Prolific itself reports the study is finished. This happens when
            # places_taken < total_available_places but every settled
            # submission accounts for the original recruit budget (e.g. 49
            # APPROVED + 6 RETURNED = 55 submissions consumed all 50 places
            # plus retries; Prolific then auto-flips to COMPLETED). The
            # ``finished >= total_available_places`` check above does NOT fire
            # in that case (49 < 50), but no new participant will ever join,
            # so spinning on the "available Firebase slot" cleanup loop wastes
            # cycles forever. Treat a Prolific-side COMPLETED status as a hard
            # terminate and return whatever observations Firebase has — the
            # caller handles the under-recruit case (just like the warning
            # branch above).
            if check_prolific["status"] == "COMPLETED":
                _log(
                    f"Prolific study marked COMPLETED with "
                    f"finished={check_prolific['number_of_submissions_finished']}/"
                    f"{check_prolific['total_available_places']}; returning observations"
                )
                return _observations_as_sorted_list("autora", kwargs["firebase_credentials"])
        # firebase places available
        if check_firebase == "available":
            if check_prolific["status"] == "UNPUBLISHED":
                _log("Publishing Prolific study")
                publish_study(
                    study_id=study_id, prolific_token=kwargs["prolific_token"]
                )
            if check_prolific["status"] == "PAUSED":
                _log("Resuming paused Prolific study")
                start_study(
                    study_id=study_id, prolific_token=kwargs["prolific_token"]
                )
        if check_firebase == "unavailable":
            if check_prolific["status"] == "STARTED":
                _log("Pausing Prolific study (no free Firebase slots)")
                pause_study(
                    study_id=study_id, prolific_token=kwargs["prolific_token"]
                )
        time.sleep(kwargs["sleep_time"])
        counter += 1


def firebase_prolific_runner(**kwargs):
    """
    A runner that uses firebase to store the condition and the dependent variable and prolific to
    recruit participants.
    Args:
        **kwargs: the configuration of the experiment.
            firebase_credentials: a dict with firebase service account credentials
            sleep_time: the time between checks to the firebase database and updates of the prolific experiment
            study_name: a name for the study showing up in prolific
            study_description: a description for the study showing up in prolific
            study_url: the url to your experiment
            study_completion_time: the average completion time for a participant to complete the study
            prolific_token: api token from prolific
    Returns:
        the runner
    """
    _validate_firebase_prolific_kwargs(kwargs)

    def runner(x):
        return _firebase_prolific_run(x, **kwargs)

    return runner


def firebase_runner(**kwargs):
    """
    A runner that uses firebase to store the condition and the dependent variable.
    Args:
        **kwargs: the configuration of the experiment
            firebase_credentials: a dict with firebase service account credentials
            time_out: time out to reset a condition that was started but not finished
            sleep_time: the time between checks and updates of the firebase database

    Returns:
        the runner
    """

    def runner(x):
        return _firebase_run(x, **kwargs)

    return runner
