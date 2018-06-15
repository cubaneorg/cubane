# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail.backends.filebased import EmailBackend
import os
import datetime


class EmailAuthBackend(object):
    """
    Allow user authentication via email address
    """
    def authenticate(self, username=None, password=None):
        # auth. against local database via email/password
        try:
            user = User.objects.get(is_active=True, email__iexact=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None


    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


    supports_object_permissions = False
    supports_anonymous_user = False


class EmailEmlFileBackend(EmailBackend):
    """
    Generate log files for each email sent.
    """
    def _get_filename(self):
        """
        Override: Return a unique file name with the .eml extension, so that
        we can open email files easily.
        """
        if self._fname is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = "%s-%s.eml" % (timestamp, abs(id(self)))
            self._fname = os.path.join(self.file_path, fname)
        return self._fname