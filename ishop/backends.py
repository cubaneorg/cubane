# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.contrib.auth.models import User


class CustomerEmailModelBackend(object):
    def authenticate(self, email=None, client=None, password=None):
        try:
            user = User.objects.get(email=email)
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
