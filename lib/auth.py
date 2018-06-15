# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.contrib.auth import login as auth_login
import string
import random
import uuid


#
# We try to avoid characters that could be confused with other valid
# characters all togehter, for example 1 and I, O and 0.
#
DEFAULT_PASSWORD_CHARACTERS = \
    list('abcdefghjkpqrstuvwxyz') + \
    list('ABCEFGHJKPRSTUVWXYZ') + \
    list('23456789')


#
# Length of UUID (base64 encoded).
#
UUID_STR_LENGTH = 22


def generate_random_pw(length=8, chars=DEFAULT_PASSWORD_CHARACTERS):
    """
    Return a randomly generated password based on the given length and
    the set of allowed characters.
    """
    if len(chars) == 0: chars = DEFAULT_PASSWORD_CHARACTERS
    return ''.join(random.choice(chars) for _ in range(length))


def new_uuid2id():
    """
    Generate a new uuid and return its id representation that can fit into
    django's username field (max. 30 characters).
    """
    return uuid2id(unicode(uuid.uuid4()))


def uuid2id(uuidstring):
    """
    Generate unique id with base64 encoding that can fit into 30 characters
    (django username).
    """
    return uuid.UUID(uuidstring).bytes.encode('base64').rstrip('=\n').replace('/', '_')


def id2uuid(slug):
    """
    Convert a base64 encoded uuid back to its uuid format as a string.
    """
    return unicode(uuid.UUID(bytes=(slug + '==').replace('_', '/').decode('base64')))


def login_user_without_password(request, user):
    """
    Perform a user login without knowing the password by pretending that the
    first user authentication backend that is configured in settings
    authenticated the user successfully. This is useful if the actual
    authentication happens as part of the user registration process or through
    other (3rd party) authentication mechanisms.
    """
    auth_login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])