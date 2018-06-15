# coding=UTF-8
from __future__ import unicode_literals
from django import template
from cubane.lib.templatetags import value_or_none
from cubane.lib.url import url_with_arg as _url_with_arg
from cubane.lib.url import url_with_arg_substitution
from cubane.lib.url import make_absolute_url


register = template.Library()


@register.simple_tag()
def url_with_arg(url, name, value):
    """
    Return the given url with the given query string key/value pair
    attached.
    """
    return _url_with_arg(url, name, value)


@register.simple_tag()
def absolute_url(url):
    return make_absolute_url(url)


@register.simple_tag()
def shortcut_action_url(url, obj, default_name, default_value):
    """
    Return the given url as a shortcut action url for the given object.
    """
    return url_with_arg_substitution(url, obj, default_name, default_value)


@register.simple_tag(takes_context=True)
def current_url_with_args(context, **kwargs):
    """
    Return the current URL with all existing query arguments with the given
    query arguments added to the current URL.
    """
    request = value_or_none('request', context)
    if request:
        args = request.GET.copy()
        for k, v in kwargs.iteritems():
            if v is None:
                if k in args:
                    del args[k]
            else:
                args[k] = v

        if args:
            return make_absolute_url('%s?%s' % (request.path, args.urlencode()))
        else:
            return make_absolute_url(request.path)
    else:
        return ''
