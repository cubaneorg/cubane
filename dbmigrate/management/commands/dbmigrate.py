#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from cubane.dbmigrate import auto_migrate


class Command(BaseCommand):
    USAGE = 'Usage: dbmigrate'
    help = 'Migrates database schema accroding to django\'s model.'


    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_false', dest='interactive', default=True,
            help='Do NOT prompt the user for input of any kind.',
        )
        parser.add_argument(
            '--nooutput', '--no-output',
            action='store_false', dest='verbose', default=True,
            help='Do NOT print out verbose information of any kind.',
        )
        parser.add_argument(
            '--skip-fixtures', '--skip-fixtures',
            action='store_true', dest='skip_fixtures', default=False,
            help='Skip loading model fixtures.',
        )


    def handle(self, *args, **options):
        """
        Run command.
        """
        interactive = options.get('interactive', True)
        load_fixtures = not options.get('skip_fixtures', False)
        verbose = options.get('verbose', True)
        auto_migrate(interactive, load_fixtures, verbose)