# AutoRA Firebase Prolific Runner

AutoRA Firebase Prolific Runner provides runners to run experiments with Firebase and Prolific

**WARNING:** The firebase prolific runner creates an experiment on prolific and runs recruits participants automatically. This is an
early alpha version and should be used with extreme caution.


Website: https://autoresearch.github.io/autora/

## User Guide

Install this in an environment using your chosen package manager. In this example we are using virtualenv

Install:
- python (3.8 or greater): https://www.python.org/downloads/
- virtualenv: https://virtualenv.pypa.io/en/latest/installation.html

Install the Prolific Recruitment Manager as part of the autora package:

pip install -U "autora[runner-firebase-prolific]"

**WARNING:** The runner only works with a specific set up of the firebase database. For starters, follow this guide to set up an experiment using firebase here: https://github.com/AutoResearch/cra-template-autora-firebase

## Developer Guide

### Get started
Clone the repository (e.g. using GitHub desktop, or the gh command line tool) and install it in "editable" mode in an isolated python environment, (e.g. with virtualenv) as follows:


Create a new virtual environment:
```shell
virtualenv venv
```

Activate it:
```shell
source venv/bin/activate
```

Use `pip install` to install the current project (`"."`) in editable mode (`-e`) with dev-dependencies (`[dev]`):
```shell
pip install -e ".[dev]"
```

## Add new dependencies 

In pyproject.toml add the new dependencies under `dependencies`

Install the added dependencies
```shell
pip install -e ".[dev]"
```

## Publishing the package

Update the metadata under `project` in the pyproject.toml file to include name, description, author-name, author-email and version

- Follow the guide here: https://packaging.python.org/en/latest/tutorials/packaging-projects/

Build the package using:
```shell
python -m build
```

Publish the package to PyPI using `twine`:
```shell
twine upload dist/*
```