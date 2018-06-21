# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.utils.http import cookie_date
from cubane.lib.app import require_app
import time


FRONTEND_EDITING_COOKIE_NAME = 'frontend-editing'
FRONTEND_EDITING_ENABLED     = '1'


RESOURCES = [
    # css
    'css/base.css',
    'css/btn.css',
    'css/editing.css',
    'css/dialog.css',

    # javascript
    'js/editing.js',
]


RESOURCE_TARGETS = {
    'frontend-editing': [
        'cubane.custom_event',
        'cubane.frontend'
    ]
}


def enable_frontend_editing(request, response):
    """
    Enable frontend-editing for the current user session.
    """
    if settings.CUBANE_FRONTEND_EDITING:
        max_age = request.session.get_expiry_age()
        expires_time = time.time() + max_age
        expires = cookie_date(expires_time)

        response.set_cookie(
            FRONTEND_EDITING_COOKIE_NAME,
            FRONTEND_EDITING_ENABLED,
            max_age=max_age,
            expires=expires,
            domain=settings.SESSION_COOKIE_DOMAIN,
            path=settings.SESSION_COOKIE_PATH,
            secure=settings.SESSION_COOKIE_SECURE or None,
            httponly=None,   # js needs access to this cookie
        )


def disable_frontend_editing(response):
    """
    Disable frontend editing for the current user session.
    """
    response.delete_cookie(FRONTEND_EDITING_COOKIE_NAME)