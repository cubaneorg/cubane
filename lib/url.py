# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.core.urlresolvers import reverse
from urlparse import urlsplit, urlunsplit, urlparse, parse_qs
import os
import re
import time
import urllib


def normalise_slug(slug):
    """
    Return the given slug without leading or trailing / characters, unless the entire
    string only contains /.
    """
    stripped_slug = slug.strip('/')
    return slug if stripped_slug == '' and len(slug) >= 1 else stripped_slug


def url_append_slash(url):
    """
    Append missing slash to url if there is no /.
    """
    p = url.split('?', 2)
    if len(p) > 1:
        return url_append_slash(p[0]) + '?' + p[1]
    elif not p[0].endswith('/'):
        return p[0] + '/'
    else:
        return p[0]


def url_join(*args):
    """
    Similar to os.path.join, url_join joins all given url arguments into one
    resulting url.
    Each part may contain leading or tailing / or multiple / as part of the
    argument.
    The first url part may contain query string arguments which are retained
    within the resulting url.
    """
    # first part may contain query string arguments
    query_string = None
    if len(args) > 0:
        if '?' in args[0]:
            parts = args[0].split('?', 2)
            args = list(args)
            args[0] = parts[0]
            query_string = parts[1]

    # join parts
    url = '/'.join([part.strip('/') for part in args])

    # eleminate dublicate /
    url = re.sub(r'//{1,}', '', url)

    # assure url starts with /
    if not url.startswith('/'): url = '/' + url

    # append query string taken from first argument (if present)
    if query_string:
        url += '?' + query_string

    return url


def domain_without_port(domain):
    """
    Remove any port information from the given domain.
    """
    if domain:
        p = domain.split(':', 1)
        if len(p) == 2:
            domain = p[0]

    return domain


def url_without_port(url):
    """
    Remove any port information from the given url.
    Scheme must be provided; http://tools.ietf.org/html/rfc1808.html
    """
    p = urlsplit(url)
    return urlunsplit(
        (p.scheme, domain_without_port(p.netloc), p.path, p.query, p.fragment)
    )


def get_url_patterns(patterns):
    """
    Yield a list of all url patterns, so that we can perform a url reverse
    lookup in javascript templates.
    """
    def get_patterns(patterns, prefix = ''):
        for e in patterns:
            name = e.name if hasattr(e, 'name') else None
            url = e.regex.pattern.strip('^$').replace('\\', '').decode("string-escape")
            url = re.sub(r'\(\?P<[-\d\w_]+>.*?\)', '*', url)
            url = prefix + url

            yield (name, url)

            if hasattr(e, 'url_patterns'):
                for item in get_patterns(e.url_patterns, url):
                    yield item

    result = get_patterns(patterns)
    result = dict(filter(lambda item: item[0] != None, result))

    for name, url in result.items():
        if not url.startswith('/'):
            result[name] = '/' + url

    return result


def is_external_url(url, domain=None):
    """
    Determine if the given url is an external url.
    """
    if not url:
        return False

    # strip and lower case
    url = url.strip().lower()

    # does not start with http/https
    if not url.startswith('http://') and not url.startswith('https://'):
        return False

    # build domain name and variations thereof
    if not domain:
        domain = settings.DOMAIN_NAME
    domain = domain.lower()

    # build domain variations
    ssl_domain = 'https://%s' % domain
    ssl_domain_www = 'https://www.%s' % domain
    domain_www = 'http://www.%s' % domain
    domain_plain = 'http://%s' % domain

    # starts with domain name
    return (
        not url.startswith('/') and
        not url.startswith(domain_plain) and
        not url.startswith(domain_www) and
        not url.startswith(ssl_domain) and
        not url.startswith(ssl_domain_www)
    )


def make_absolute_url(path, domain=None, https=None, force_debug=False, path_only=False):
    """
    Return the full url including protocol and domain name based on the given
    path and optionally given domain name and https flag. Domain name and https
    flag are taken from settings if not provided. Making a url absolute that is
    already absolute has no affect.
    """
    # trim input
    path = path.strip()

    # ignore external urls
    if is_external_url(path, domain):
        return path

    # make sure that the path ends with /, unless the path ends with
    # a file extension
    if settings.APPEND_SLASH and not path.endswith('/') and not re.match(r'.*?\w+\.\w{3,4}$', path):
        # add slash before querystring
        el = path.split('?')
        if len(el) == 2:
            if el[0].endswith('/'):
                path = '%s?%s' % (el[0], el[1])
            else:
                path = '%s/?%s' % (el[0], el[1])
        else:
            path += '/'

    # skip if protocol is present (already absolute)
    p = path.lower()
    if p.startswith('http://') or p.startswith('https://'):
        return path

    # make sure the path starts with /
    if not path.startswith('/'):
        path = '/' + path

    # in debug mode, simply return the path, unless we configured a debug
    # domain name to be used...
    if (settings.DEBUG and not force_debug and settings.DEBUG_DOMAIN_NAME is None) or path_only:
        return path

    # append domain name
    if domain:
        url = domain + path
    else:
        if settings.DEBUG and settings.DEBUG_DOMAIN_NAME:
            url = settings.DEBUG_DOMAIN_NAME + path
        else:
            url = settings.DOMAIN_NAME + path

    # prepend www
    if not settings.DEBUG and settings.PREPEND_WWW:
        if not url.lower().startswith('www'):
            url = 'www.%s' % url

    # append protocol
    return get_protocol(https) + '://' + url


def get_protocol(https=None):
    if https == None:
        https = settings.SSL and not settings.DEBUG

    return 'https' if https else 'http'


def get_absolute_url(reverse_name, args=[], domain=None, https=None, path_only=False):
    """
    Return the full url including protocol and domain name based on the
    given reverse url pattern name and given url arguments.
    """
    return make_absolute_url(reverse(reverse_name, args=args), domain=domain, https=https, path_only=path_only)


def get_compatible_url(url, https=None):
    """
    Return the given url and ensure the url is https if the given https
    argument is true. If https is None (default), then the site-wide SSL
    settings is taken into consideration.
    """
    if url is None:
        return None

    if https is None:
        https = settings.SSL

    url = url.strip()
    if https:
        if url.lower().startswith('http://'):
            url = 'https://%s' % url[7:]

    return url


def url_with_arg(url, name, v):
    """
    Return a new url based on the given url by appending the given argument name
    and value. If the query string already contains arguments, the new argument
    is combined with the existing ones.
    """
    return url_with_args(url, {
        name: v
    })


def url_with_args(url, args):
    """
    Return a new url based on the given url by appending the given arguments.
    If the query string already contains arguments, the new argument
    is combined with the existing ones.
    """
    if args:
        c = urlparse(url)
        d = parse_query_string(c.query)
        d.update(args)
        return url_from_components(c, d)
    else:
        return url


def url_with_arg_substitution(url, obj, default_name=None, default_value=None):
    """
    Substitute given url arguments using property values from given object.
    """
    if obj:
        c = urlparse(url)
        d = parse_query_string(c.query)

        for k, v in d.items():
            if v.startswith('$'):
                v = v[1:]
                try:
                    d[k] = getattr(obj, v)
                except:
                    del d[k]

        if default_name is not None and default_value is not None:
            d[default_name] = default_value

        return url_from_components(c, d)
    else:
        return url


def url_from_components(components, query_args):
    """
    Re-assemble full url based on given components of the url and given set
    of query string arguments.
    """
    return (
        ((components.scheme + '://') if components.scheme else '') +
        components.netloc +
        components.path +
        ((';' + components.params) if components.params else '') +
        (('?' + urllib.urlencode(query_args)) if query_args else '') +
        (('#' + components.fragment) if components.fragment else '')
    )


def parse_query_string(query_string):
    """
    Parse given query string and return its key/value pairs as a dictionary.
    Single values are returned as single values and not arrays.
    """
    return dict(
        (k, v if len(v) > 1 else v[0])
        for k, v in parse_qs(query_string, keep_blank_values=True).iteritems()
    )


def no_cache_url(url):
    """
    Return a new url based on the given url that is not cached by the cache
    sub-system. A none-cachable url is constructed by appending the _ argument
    with a the current timestamp as its argument value.
    """
    return url_with_arg(url, '_', '%s' % int(time.time() * 10000))


def url_with_http(url):
    """
    Enfore http:// if no protocol is defined.
    """
    u = url.lower()
    if not u.startswith('http://') and not u.startswith('https://'):
        url = 'http://' + url
    return url


def to_legacy_url(url):
    """
    Takes a full or partial url and converts it to a legacy path without
    protocol, port or fragment. The result is an absolute path of a document
    which may contain query string arguments.
    """
    # valid argument?
    if url is None or not isinstance(url, basestring):
        return None

    # empty?
    url = url.strip()
    if url == '':
        return None

    # ignore data urls
    if url.lower().startswith('data:'):
        return None

    # add missing scheme if we do not have one, so that urlparse will
    # behave correcly
    if url.startswith('//'):
        url = 'http:' + url

    # missing protocol for something that looks like a domain name
    if not re.match(r'^\w+://.*?$', url) and re.match(r'^.+\..+.*?$', url):
        url = 'http://' + url

    # missing slash for path?
    if not url.startswith('/') and not re.match(r'^\w+://.*?$', url):
        url = '/' + url

    # parse url via urlparse (urllib) and extract path component
    c = urlparse(url)
    path = c.path

    # append query string to path
    if c.query != '':
        path += '?' + c.query

    # legacy path should always be absolute, starting with /
    if not path.startswith('/'):
        path = '/' + path

    return path


def get_filepath_from_url(reverse_name, args=[]):
    """
    Return a relative file path based on the given reverse name and url
    arguments.
    """
    url = reverse(reverse_name, args=args)
    url = url.strip()

    if url.endswith('/'):
        url += 'index.html'

    # remove surrounding /, otherwise we end up with empty path components
    url = url.strip('/')

    # convert url path to file path
    return os.path.join(*url.split('/'))


def get_content_object_or_404(queryset, slug, pk, url_name):
    """
    Return a content object of given model based on given slug and pk or raises
    Http404 error. If the slug is incorrect, HttpResponsePermanentRedirect is
    returned to redirect to the correct url (301).
    """
    try:
        obj = queryset.get(pk=pk)
        if obj.slug != slug:
            return HttpResponsePermanentRedirect(
                get_absolute_url(url_name, args=[obj.slug, obj.pk])
            )
        else:
            return obj
    except ObjectDoesNotExist:
        raise Http404
