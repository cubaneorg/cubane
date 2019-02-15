# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import os


class Command(BaseCommand):
    """
    Create default admin user.
    """
    args = ''
    help = 'Create default admin user.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        self.create_admin_user()


    def create_admin_user(self):
        """
        Create default admin user.
        """
        users = User.objects.count()

        if users == 0:
            # create admin user account
            user = User()
            user.username = os.environ.get('DEFAULT_ADMIN_USER', settings.DEFAULT_ADMIN_USER)
            user.is_staff = True
            user.is_superuser = True
            user.set_password(os.environ.get('DEFAULT_ADMIN_PASSWORD', settings.DEFAULT_ADMIN_PASSWORD))
            user.save()

            # create backend profile (force user to reset password after login)
            profile = UserProfile()
            profile.user = user
            profile.reset = True
            profile.save()
