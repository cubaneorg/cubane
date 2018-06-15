# coding=UTF-8
from __future__ import unicode_literals
from django.contrib.sessions.models import Session
import datetime


def get_unexpired_sessions_for_user_by_id(user_id):
    """
    Return a list of all un-expired sessions for the user with the given pk,
    assuming that sessions are stored within the database.
    Based on: https://stackoverflow.com/questions/6656708/most-optimized-way-to-delete-all-sessions-for-a-specific-user-in-django
    """
    pks = []
    all_sessions = Session.objects.filter(expire_date__gte=datetime.datetime.now())
    user_pk = unicode(user_id)
    for session in all_sessions:
        session_data = session.get_decoded()
        if user_pk == unicode(session_data.get('_auth_user_id')):
            pks.append(session.pk)
    return Session.objects.filter(pk__in=pks)


def get_unexpired_sessions_for_user(user):
    """
    Return a list of all un-expired sessions for the given user assuming that
    sessions are stored within the database.
    """
    return get_unexpired_sessions_for_user_by_id(user.pk)


def delete_sessions_for_user_by_id(user_id):
    """
    Delete all (un-expired) session data for the user with the given pk.
    """
    session_list = get_unexpired_sessions_for_user_by_id(user_id)
    session_list.delete()


def delete_sessions_for_user(user):
    """
    Delete all (un-expired) session data for the given user.
    """
    delete_sessions_for_user_by_id(user.pk)