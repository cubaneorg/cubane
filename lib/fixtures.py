# coding=UTF-8
from __future__ import unicode_literals
from django.core.management import call_command
from cubane.lib.app import get_models
import sys


def get_model_fixtures(model):
    """
    Return a list of paths to individual fixture files for the given model.
    """
    try:
        fixtures = model.Cubane.fixtures
        if not isinstance(fixtures, list):
            fixtures = [fixtures]
    except AttributeError:
        fixtures = []

    return fixtures


def load_model_fixtures(connection, stdout=sys.stdout, verbosity=1):
    """
    Load the initial data for all models as defined for each model.
    """
    for model in get_models():
        fixtures = get_model_fixtures(model)
        if len(fixtures) > 0:
            if verbosity >= 1:
                for fixture in fixtures:
                    stdout.write('Loading initial data fixture: %s.\n' % fixture)
            args = ['loaddata'] + fixtures
            call_command(
                *args,
                interactive=False,
                database=connection.alias,
                run_syncdb=True,
                verbosity=verbosity
            )