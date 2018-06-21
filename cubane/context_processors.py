# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from cubane.lib.libjson import to_json


def config(request):
    """
    Provides a default set of configuration options for templates.
    """
    return {
        'DOMAIN_NAME': settings.DOMAIN_NAME,
        'DEBUG': settings.DEBUG,
        'STATIC_URL': settings.STATIC_URL,
        'CLIENT_LOGO': settings.CLIENT_LOGO
    }


def backend(request):
    """
    Provides backend-specific data for templates if backend is used.
    """
    if 'cubane.backend' in settings.INSTALLED_APPS:
        # dialog
        is_browse_dialog = request.GET.get('browse', 'false') == 'true'
        is_create_dialog = request.GET.get('create', 'false') == 'true'
        is_edit_dialog = request.GET.get('edit', 'false') == 'true'
        is_dialog = request.GET.get('dialog', 'false') == 'true'
        is_index_dialog = request.GET.get('index-dialog', 'false') == 'true'
        is_external_dialog = request.GET.get('external-dialog', 'false') == 'true'
        is_frontend_editing = request.GET.get('frontend-editing', 'false') == 'true'

        # error messages
        _messages = list(messages.get_messages(request))
        _error_messages = []
        for m in _messages:
            if m.tags == 'error':
                _error_messages.append(m)

        # link to website (frontend)
        if 'cubane.cms' in settings.INSTALLED_APPS:
            frontend_link = '/' if reverse('cubane.backend.index') != '/' else False
        else:
            frontend_link = None

        # context
        context = {
            'BACKEND': request.backend if hasattr(request, 'backend') else None,
            'THEME': settings.BACKEND_THEME,
            'DASHBOARD': settings.CUBANE_DASHBOARD,
            'BACKEND_DEFAULT_SAVE_BUTTON_LABEL': mark_safe(settings.CUBANE_BACKEND_DEFAULT_SAVE_BUTTON_LABEL),
            'BACKEND_DEFAULT_SAVE_AND_CONTINUE_BUTTON_LABEL': mark_safe(settings.CUBANE_BACKEND_DEFAULT_SAVE_AND_CONTINUE_BUTTON_LABEL),
            'BACKEND_DEFAULT_BACK_BUTTON_LABEL': mark_safe(settings.CUBANE_BACKEND_DEFAULT_BACK_BUTTON_LABEL),
            'messages': _messages,
            'error_messages': _error_messages,
            'SETTINGS': to_json({
                'CUBANE_BACKEND_EDITOR_PLUGINS': settings.CUBANE_BACKEND_EDITOR_PLUGINS,
                'CUBANE_BACKEND_EDITOR_YOUTUBE': settings.CUBANE_BACKEND_EDITOR_YOUTUBE,
                'CMS_ADV_EDITOR_PLUGINS': settings.CMS_ADV_EDITOR_PLUGINS,
                'CMS_DEFAULT_SLOTNAME': settings.CMS_DEFAULT_SLOTNAME
            }),
            'frontend_link': frontend_link,
            'is_browse_dialog': is_browse_dialog,
            'is_create_dialog': is_create_dialog,
            'is_edit_dialog': is_edit_dialog,
            'is_index_dialog': is_index_dialog,
            'is_external_dialog': is_external_dialog,
            'is_frontend_editing': is_frontend_editing,
            'is_dialog': is_dialog or is_browse_dialog or is_create_dialog or is_edit_dialog or is_index_dialog or is_external_dialog or is_frontend_editing
        }

        # postcode lookup
        if 'cubane.postcode' in settings.INSTALLED_APPS:
            context.update({
                'is_postcode_lookup': True
            })


        # cms publish
        if 'cubane.cms' in settings.INSTALLED_APPS:
            # cms settings
            from cubane.cms.views import get_cms_settings_or_none
            context.update({
                'settings': get_cms_settings_or_none()
            })

            # cache
            context.update({
                'cms_cache_enabled': settings.CACHE_ENABLED
            })
            if settings.CACHE_ENABLED:
                from cubane.cms.cache import Cache
                cache = Cache()
                context.update({
                    'cms_publish': cache.publish_required()
                })
    else:
        context = {}

    return context
