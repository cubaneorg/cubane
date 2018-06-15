# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.fonts.fontcache import FontCache


class Command(BaseCommand):
    """
    Update the font cache.
    """
    args = ''
    help = 'Update the font cache.'


    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh', action='store_true', dest='refresh',
            help='Removes all currently cached fonts and downloads them again.',
        )


    def handle(self, *args, **options):
        """
        Run command.
        """
        fontcache = FontCache()

        # clear first if we are refreshing the cache
        if options.get('refresh'):
            fontcache.clear(verbose=True)

        # update font cache
        fontcache.update(verbose=True)