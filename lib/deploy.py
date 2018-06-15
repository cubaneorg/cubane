# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.file import file_get_contents, file_put_contents
from datetime import datetime
import os


TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S'


def get_deploy_timestamp_filename():
    """
    Return the filename that keeps the timestamp when the last deployment
    has happened in ISO format.
    """
    return os.path.join(settings.STATIC_ROOT, 'deployts')


def save_deploy_timestamp():
    """
    Write the current timestamp to the timestamp file that stores the timestamp
    when the last deployment happened in ISO format.
    """
    ts = datetime.now()
    file_put_contents(get_deploy_timestamp_filename(), ts.strftime(TIMESTAMP_FORMAT))
    return ts


def load_deploy_timestamp():
    """
    Load resource version identifier from the website's deployment target folder.
    """
    try:
        return datetime.strptime(
            file_get_contents(get_deploy_timestamp_filename()),
            TIMESTAMP_FORMAT
        )
    except (IOError, ValueError):
        return None


def delete_deploy_timestamp():
    """
    Remove the deployment timestamp file (if exists).
    """
    filename = get_deploy_timestamp_filename()
    if os.path.isfile(filename):
        os.unlink(filename)