# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib import verbose
import sys


def ask(question, options, default_option_label = '[1]', interactive=True):
    """
    Ask the user the given question and presents the given list of options
    to choose from. The user reponse is a number between 1 and n.
    """
    choices = zip(xrange(1, 999), options)

    if not interactive:
        return choices[0]

    def verbose_choices():
        for option, label in choices:
            print "\t(%2d)\t%s" % (option, label)
        sys.stdout.write('%s [%s]: ' % (question, default_option_label))

    while True:
        verbose.conditional(verbose_choices)
        response = sys.stdin.readline().strip()

        # just hitting enter selects the default response, which is always the
        # first one in the list
        if response == '': response = '1'

        # try to match based on numeric response
        try:
            option = int(response)
            if option >= 1 and option <= len(options):
                return (option, options[option - 1])
        except ValueError:
            pass

        # try to match by label
        for option, label in choices:
            if response == label:
                return (option, options[option - 1])


def ask_confirm(question, interactive=True):
    """
    Ask the given yes|no question. The outcome is True for yes and False for no.
    The default answer (ENTER) is no.
    """
    if not interactive:
        return True

    while True:
        verbose.out('%s [no]: ' % question, newline=False)
        response = sys.stdin.readline().strip().lower()

        # just hitting ENTER is considered as no
        if response == 'yes':
            return True
        elif response == '' or response == 'no':
            return False


def ask_rename_table(model, tablenames, interactive=True):
    """
    Ask the user if the table was renamed, if so we ask for the previous name.
    """
    options = ['no, was added.'] + tablenames
    return ask(
        "Was the table '%s' renamed?" % model._meta.db_table,
        options,
        'no',
        interactive=interactive
    )


def ask_rename_field(model, field, columnnames, interactive=True):
    """
    Ask the user if the field was renamed, if so we ask for the previous name.
    """
    options = ['no, was added.'] + columnnames
    return ask(
        "Was the field '%s.%s' renamed?" % (model._meta.db_table, field.column),
        options,
        'no',
        interactive=interactive
    )
