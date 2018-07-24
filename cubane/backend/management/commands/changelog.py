# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from cubane.backend.models import ChangeLog


class Command(BaseCommand):
    """
    Deletes all change-log entries that are older than 1 month.
    """
    args = ''
    help = 'Deletes expired change-log entries.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        print 'Deleting expired change-log entries...Please Wait...'

        ChangeLog.cleanup()

        print 'done.'