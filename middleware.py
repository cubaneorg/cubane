# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponse
from django.http.response import HttpResponseRedirectBase
from django.utils.encoding import force_unicode
from cubane.templatetags.resource_tags import get_resources_markup
from cubane.lib.url import url_without_port, make_absolute_url
from cubane.lib.serve import serve_static_with_context
import re


def is_html_response(request, response):
    """
    Return True, if the given response is a valid text/http 200 GET response
    """
    # only affects GET requests
    if not request.method == 'GET':
        return False

    # redirects?
    if isinstance(response, (HttpResponseRedirect, HttpResponsePermanentRedirect)):
        return False

    # only affect HTML responses
    try:
        if not response['Content-Type'].strip().lower().startswith('text/html'):
            return False
    except KeyError:
        return False

    # only affect 200 OK responses
    if response.status_code != 200:
        return False

    return True


class SSLResponseRedirectMiddleware(object):
    """
    When SSL is turned on, force any HttpResponseRedirect to encode the
    Location header as https:// rather than http://.
    """
    def process_response(self, request, response):
        if settings.SSL and isinstance(response, HttpResponseRedirectBase):
            response['Location'] = make_absolute_url(response['Location'], domain=request.META['HTTP_HOST'])
        return response


class RequireSSLMiddleware(object):
    """
    Redirects to https:// if the request is on http://.
    """
    def _is_secure(self, request):
        if request.is_secure():
            return True

        # Handle the Webfaction case until this gets resolved in the request.is_secure()
        if 'HTTP_X_FORWARDED_SSL' in request.META:
            return request.META['HTTP_X_FORWARDED_SSL'] == 'on'

        return False


    def process_request(self, request):
        if not settings.DEBUG:
            # redirect to https if this is not a secure connection
            if not self._is_secure(request):
                if 'HTTP_X_FORWARDED_HOST' in request.META:
                    url = request.META['HTTP_X_FORWARDED_HOST']
                else:
                    url = request.get_host()

                if url.startswith('www.'):
                    url = url.replace('www.', '')

                return HttpResponsePermanentRedirect('https://www.%s%s' % (url, request.get_full_path()))


class TransparentProxyMiddleware(object):
    """
    Appends the full domain name to a redirect response for transparent proxies,
    so that we do not end up on the proxy after redirecting.
    """
    def process_response(self, request, response):
        if not settings.DEBUG and isinstance(response, (HttpResponseRedirect, HttpResponsePermanentRedirect)):
            url = response.get('Location', '')
            if url.startswith('http://') or url.startswith('https://'):
                response['Location'] = url_without_port(url)
            else:
                response['Location'] = 'http://%s%s' % (
                    settings.DOMAIN_NAME,
                    url
                )

        return response


class SettingsMiddleware(object):
    """
    Provides CMS/Shop settings if the cms and/or shop are used.
    """
    def process_request(self, request):
        # ignore static assets
        path = request.path
        if '.js' in path or '.css' in path or 'woff' in path or path == '/admin/heartbeat/':
            return

        if 'cubane.cms' in settings.INSTALLED_APPS or 'cubane.ishop' in settings.INSTALLED_APPS:
            from cubane.cms.views import get_cms_settings_or_none
            request.settings = get_cms_settings_or_none()

        if 'cubane.ishop' in settings.INSTALLED_APPS:
            # TODO: Remove eventuallty to maintain backward compatibility with large parts
            # of the ishop code base
            from cubane.ishop.api.context import IShopClientContext
            request.client = request.settings
            request.context = IShopClientContext(request)


class FrontendEditingMiddleware(object):
    """
    Provides frontend editing capabilities.
    """
    def process_response(self, request, response):
        # not enabled?
        if not settings.CUBANE_FRONTEND_EDITING:
            return response

        # non-admin request
        if request.path.startswith('/admin/'):
           return response

        # HTTP 200 GET?
        if not is_html_response(request, response):
            return response

        # inject
        inject = get_resources_markup('frontend-editing-loader', 'js', inline=True)
        content = force_unicode(response.content)
        response.content = re.sub(r'</body>\s*?</html>\s*?$', inject + '</body></html>', content)
        return response