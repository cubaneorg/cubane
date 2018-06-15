# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.url import url_with_args
import urllib
import urllib2
import json


class HttpResponse(object):
    def __init__(self, data='', code=200):
        self.data = data
        self.code = code


    def __unicode__(self):
        return self.data


def get_response_encoding(response):
    """
    Return the encoding of the response based on the response header.
    """
    content_type = response.headers['content-type']
    if 'charset=' in content_type:
        return content_type.split('charset=')[-1]
    else:
        return 'utf-8' # assume if no charset is given


def get_response_unicode(response):
    """
    Decode the responde and return unicode data based on the response encoding header.
    """
    encoding = get_response_encoding(response)
    content = response.read()
    return unicode(content, encoding)


def wget(url, data=None, timeout=None):
    """
    Download given resource and return the response for it.
    """
    try:
        if data:
            url = url_with_args(url, data)

        opener = urllib2.build_opener()
        response = opener.open(url, timeout=timeout)

        return HttpResponse(get_response_unicode(response))
    except urllib2.HTTPError as e:
        return HttpResponse(code=e.code)


def wget_json(url, data=None, timeout=None):
    """
    Download given resource and return json.
    """
    try:
        if data:
            url = url_with_args(url, data)

        opener = urllib2.build_opener()
        response = opener.open(url, timeout=timeout)

        return json.loads(get_response_unicode(response))
    except urllib2.HTTPError as e:
        return {}


def wpost(url, data=None, timeout=None):
    """
    Post given data to given url.
    """
    try:
        if data:
            data = urllib.urlencode(data)

        opener = urllib2.build_opener()
        response = opener.open(url, data, timeout=timeout)

        return HttpResponse(response.read())
    except urllib2.HTTPError as e:
        return HttpResponse(code=e.code)
