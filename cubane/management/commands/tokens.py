# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from cubane.backend.models import UserToken


class Command(BaseCommand):
    """
    Destroys all invalid and/or expired user tokens (for example password forgotten).
    """
    args = ''
    help = 'Destroys invalid/expired user tokens.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        print 'Destroying invalid/expired user tokens...Please Wait...'
        print

        UserToken.cleanup()

        print 'done.'