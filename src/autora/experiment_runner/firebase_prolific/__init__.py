import time

from autora.experiment_runner.experimentation_manager.firebase import (
    check_firebase_status,
    get_observations,
    send_conditions,
)
from autora.experiment_runner.recruitment_manager.prolific import (
    check_prolific_status,
    pause_study,
    setup_study,
    start_study,
    publish_study,
    get_submissions_incompleted,
    request_return_all
)


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
    time_out = kwargs["time_out"]
    sleep_time = kwargs["sleep_time"]

    # set up study on firebase
    send_conditions("autora", conditions, firebase_credentials)

    # run the experiment as long as not all conditions are met
    while True:
        check_firebase = check_firebase_status("autora", firebase_credentials, time_out)
        if check_firebase == "finished":
            # get observations returns a dict
            observation = get_observations("autora", firebase_credentials)
            observation_list = [observation[key] for key in sorted(observation.keys())]
            return observation_list
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

    # set up study on firebase
    send_conditions("autora", conditions, kwargs["firebase_credentials"])

    # set up study on prolific
    prolific_dict = setup_study(
        kwargs["study_name"],
        kwargs["study_description"],
        kwargs["study_url"],
        kwargs["study_completion_time"],
        kwargs["prolific_token"],
        total_available_places=len(conditions),
        completion_code=kwargs["completion_code"]
    )

    # get the specification on prolific
    time_out = prolific_dict["maximum_allowed_time"] * 60
    study_id = prolific_dict["id"]
    counter = 1

    while True:
        # check firebase
        check_firebase = check_firebase_status(
            "autora", kwargs["firebase_credentials"], time_out
        )
        # check prolific
        if prolific_dict:
            if not counter % 5:
                request_return_all(study_id, kwargs["prolific_token"])
                incomplete_submissions = get_submissions_incompleted(study_id,
                                                                     kwargs["prolific_token"])
                check_firebase = check_firebase_status(
                    "autora", kwargs["firebase_credentials"], time_out, incomplete_submissions
                )

            check_prolific = check_prolific_status(study_id, kwargs["prolific_token"])
            if (
                    check_prolific["number_of_submissions"]
                    >= check_prolific["total_available_places"] and check_firebase == "finished"
            ):
                observation = get_observations("autora", kwargs["firebase_credentials"])
                observation_list = [observation[key] for key in sorted(observation.keys())]
                return observation_list

        # firebase places available
        if check_firebase == "finished":
            pass
            # return get_observations("autora", kwargs["firebase_credentials"])
        if check_firebase == "available":
            if check_prolific["status"] == "UNPUBLISHED":
                publish_study(
                    study_id=study_id, prolific_token=kwargs["prolific_token"]
                )
            if check_prolific["status"] == "PAUSED":
                start_study(
                    study_id=study_id, prolific_token=kwargs["prolific_token"]
                )
        if check_firebase == "unavailable":
            if check_prolific["status"] == "STARTED":
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

    def run(x):
        return _firebase_prolific_run(x, **kwargs)

    return run


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
