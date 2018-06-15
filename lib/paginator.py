# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404
from django.core.paginator import Paginator as DjangoPaginator
from django.core.paginator import Page as DjangoPage
from django.core.paginator import EmptyPage, InvalidPage
from cubane.lib.url import url_append_slash, url_join
import re
import urllib
import urlparse


VIEW_ALL_LABEL = 'View all'


class CachedPaginator(DjangoPaginator):
    def page(self, number):
        """
        Returns a Page object for the given 1-based page number.
        """
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if top + self.orphans >= self.count:
            top = self.count
        return CachedPage(self.object_list[bottom:top], number, self)


class CachedPage(DjangoPage):
    def __init__(self, object_list, number, paginator):
        self.queryset = object_list
        self._object_list = None
        self.number = number
        self.paginator = paginator


    def _get_object_list(self):
        if self._object_list is None:
            self._object_list = list(self.queryset)
        return self._object_list
    object_list = property(_get_object_list)


    def count(self):
        return len(self.object_list)


def create_paginator(
    request,
    object_list,
    page=None,
    page_size=settings.DEFAULT_PAGE_SIZE,
    min_page_size=settings.DEFAULT_MIN_PAGE_SIZE,
    max_page_size=settings.DEFAULT_MAX_PAGE_SIZE
):
    """
    Wrap given object list into a django paginator.
    """
    objects = object_list if object_list is not None else []

    # get all argument
    if getattr(request, 'paginator_all', request.GET.get('all', '0')) == '1':
        page_size = max_page_size

    # all argument expressed in request path?
    m = re.match(r'^.*?\/(all-)?page-(\d+)\/$', request.path)
    if m:
        if m.group(1) == 'all-':
            page_size = max_page_size

        if page == None:
            page = int(m.group(2))

    # create paginator of given page size
    paginator = CachedPaginator(objects, page_size)

    # get page argument
    try:
        if page == None:
            page = int(getattr(request, 'paginator_page', request.GET.get('page', '1')))
    except ValueError:
        raise Http404('Invalid page argument.')

    # generate list of pages around the current page
    i = page - 1
    i0 = max(0, i - 2)
    
    i1 = min(paginator.num_pages, i + 3)

    # fit to have 5 entries in the list at any time (if we can)
    if i1 - i0 < 5 and i0 > 0: i0 = max(0, i0 - (5 - (i1 - i0)))
    if i1 - i0 < 5 and i1 < paginator.num_pages: i1 = min(paginator.num_pages, i1 + (5 - (i1 - i0)))

    paginator.range = list(paginator.page_range)[i0:i1]

    # inject option for view all or view n if we hit the page limit
    n = paginator.count
    if page_size == max_page_size:
        view_all_label = 'View %d' % min_page_size
        view_all = True
    else:
        view_all = False
        if n > max_page_size:
            view_all_label = 'View %d' % max_page_size
        else:
            view_all_label = VIEW_ALL_LABEL
    paginator.view_all_label = view_all_label
    paginator.max_page_size  = max_page_size
    paginator.min_page_size  = min_page_size
    paginator.view_all       = view_all

    try:
        objects = paginator.page(page)
    except (EmptyPage, InvalidPage):
        objects = paginator.page(paginator.num_pages)

    if (page > 1 and page > paginator.num_pages) or page < 1:
        raise Http404('No page #%d' % page)

    # generate urls for next/prev
    base_url = request.get_full_path()
    parts = base_url.split('?', 2)
    base_url = parts[0]
    if len(parts) == 2:
        args = dict(
            (k, v if len(v)>1 else v[0])
            for k, v in urlparse.parse_qs(parts[1]).iteritems()
        )
    else:
        args = {}

    # remove page-xxx and all-page-xxx from base_url, since we are going
    # to re-encode those...
    base_url = re.sub(r'\/((all-)?page-\d+\/)$', '', base_url)
    if not base_url.endswith('/'):
        base_url = '%s/' % base_url

    # remove all and page query arguments, since we will encode those in
    # the correct way...
    if 'all' in args:
        del args['all']
    if 'page' in args:
        del args['page']

    # re-build url
    if len(args.keys()) > 0:
        base_url += '?' + urllib.urlencode(args, doseq=True)

    def get_paginator_url(page_func, has_page=True):
        if has_page:
            page = page_func() if hasattr(page_func, '__call__') else page_func
            if page == 1 and not paginator.view_all:
                return base_url
            else:
                return url_append_slash(url_join(base_url, '%spage-%s' % (
                    'all-' if paginator.view_all else '',
                    page
                )))
        else:
            return None

    objects.prev_url = get_paginator_url(objects.previous_page_number, objects.has_previous())
    objects.next_url = get_paginator_url(objects.next_page_number, objects.has_next())

    # construct view all url
    if paginator.view_all:
        objects.view_all_url = url_append_slash(base_url)
    else:
        objects.view_all_url = url_append_slash(url_join(base_url, 'all-page-1'))

    objects.pages = [{
        'page': p,
        'url': get_paginator_url(p)
    } for p in paginator.range]

    return objects
