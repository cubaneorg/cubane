# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404
from cubane.views import ApiView, view_url
from cubane.cms.views import get_cms


class CmsApiView(ApiView):
    """
    Backend api (XHR only).
    """
    namespace = 'cubane.cms.api'
    slug = 'api'
    patterns = [
        ('publish/', 'publish', {}, 'publish'),
    ]


    def publish(self, request):
        """
        Publish cms changes.
        """
        cms = get_cms()

        try:
            items, size, time_sec = cms.publish()
        except Http404, e:
            # http404 errors are not send via email notification in production
            # mode, therefore rethrow the exception here
            raise ValueError(unicode(e))

        return {
            'success': True,
            'items': items,
            'size': size,
            'time_sec': time_sec
        }