# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.fonts.fontcache import FontCache


class Command(BaseCommand):
    """
    Clear font cache.
    """
    args = ''
    help = 'Clear font cache.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        fontcache = FontCache()
        fontcache.clear(verbose=True)