# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils.module_loading import import_module
from cubane.backend.models import UserToken


class Command(BaseCommand):
    """
    Cleanup various operation data.
    """
    args = ''
    help = 'Cleanup.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        print 'Cleanup...Please Wait...'
        print

        # execute default cleanup commands
        if 'django.contrib.sessions' in settings.INSTALLED_APPS:
            call_command('clearsessions', interactive=False)

        # allow each app to cleanup
        for app_name in settings.INSTALLED_APPS:
            app = import_module(app_name)
            if hasattr(app, 'cleanup'):
                app.cleanup()

        print 'done.'