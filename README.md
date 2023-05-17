# AutoRA Firebase Prolific Experiment Runner

Firebase Prolific Runner provides runners to run experiments with Firebase and Prolific

**WARNING:** The firebase prolific runner creates an experiment on prolific and runs recruits participants automatically. This is an
early alpha version and should be used with extreme caution.

## Quick Start

Install this in an environment using your chosen package manager. In this example we are using virtualenv

Install:
- python (3.8 or greater): https://www.python.org/downloads/
- virtualenv: https://virtualenv.pypa.io/en/latest/installation.html

Install the Prolific Recruitment Manager as part of the autora package:

pip install -U "autora[experiment-runner-firebase-prolific]"

**WARNING:** Both runners work with a specific set up of the firebase database. For starters, follow this guide to set up an experiment using firebase here: https://github.com/AutoResearch/cra-template-autora-firebase
