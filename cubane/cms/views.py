# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpRequest, HttpResponse, Http404
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect, FileResponse
from django.test import RequestFactory
from django.core import urlresolvers
from django.template import engines
from django.core.urlresolvers import reverse_lazy, reverse, resolve
from django.core.exceptions import FieldDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.contrib import sitemaps
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.cache import SessionStore
from django.db.models import Q
from django.db.models.fields.related import ForeignKey
from django.utils.module_loading import import_module
from django.template.defaultfilters import slugify
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from cubane.cms import get_page_model
from cubane.cms.models import ChildPageWithoutParentError
from cubane.cms.models import SettingsBase
from cubane.cms.models import PageAbstract, PageBase, Page, ChildPage, Entity, MediaGallery
from cubane.cms.cache import Cache, CacheContext
from cubane.cms.cachegen import CacheGenerator
from cubane.cms.nav import CMSNavigationBuilder
from cubane.cms.sitemap import SitemapSection
from cubane.decorators import template
from cubane.views import View, ModelView, view, view_url
from cubane.media.models import Media
from cubane.media.views import load_media_gallery, save_media_gallery
from cubane.media.views import get_img_tags
from cubane.backend.views import BackendSection
from cubane.backend.api import LinkBuilder
from cubane.lib.url import normalise_slug, get_protocol, make_absolute_url
from cubane.lib.module import get_class_from_string
from cubane.lib.module import register_class_extensions
from cubane.lib.paginator import create_paginator
from cubane.lib.model import dict_to_model, get_fields, get_listing_option
from cubane.lib.app import get_models
from cubane.lib.deploy import load_deploy_timestamp
from cubane.lib.mail import cubane_send_cms_enquiry_mail
from cubane.lib.mail import cubane_send_mail_template
from cubane.lib.mail import get_ordered_list_of_fields
from cubane.lib.mail import send_exception_email
from cubane.lib.text import char_range
from cubane.lib.template import get_compatible_template
from datetime import datetime
import re
import os
import copy


_SETTINGS_CACHE = None


PAGE_PATTERN = '^(?P<slug>.*)$'


CMS_CLASS = None
PAGE_CONTEXT_CLASS = None
NAV_BUILDER_CLASS = None


class HomepageNotDefinedError(Http404):
    pass


def get_cms(ignore_cache=False):
    """
    Return the custom CMS implementation that is used to render CMS content.
    A site may implement its own CMS by deriving from the CMS base class.
    The custom class needs to be setup via settings.CMS, for example
    CMS = 'myproject.views.MyCMS'.
    """
    global CMS_CLASS

    if not CMS_CLASS or ignore_cache:
        try:
            if hasattr(settings, 'CMS'):
                # load base class
                CMS_CLASS = get_class_from_string(settings.CMS)

                # give each module the chance to extend the base class
                for app_name in settings.INSTALLED_APPS:
                    app = import_module(app_name)
                    if hasattr(app, 'install_cms'):
                        CMS_CLASS = app.install_cms(CMS_CLASS)
            else:
                raise ImportError()
        except ImportError as e:
            raise ValueError(
                unicode(e) + "\n" +
                "cubane.cms requires the settings variable 'CMS' " +
                "to be set to the full path of the cms class that represents " +
                "the cms system (derived from cubane.cms.views.CMS), " +
                "for example myproject.views.MyProjectCMS "
            )

    # creates a new instance every time...
    return CMS_CLASS()


def get_settings_model():
    """
    Return the settings model as configured by settings.CMS_SETTINGS_MODEL.
    """
    if 'cubane.cms' in settings.INSTALLED_APPS:
        if hasattr(settings, 'CMS_SETTINGS_MODEL'):
            return get_class_from_string(settings.CMS_SETTINGS_MODEL)
        else:
            raise ValueError(
                "cubane.cms requires the settings variable 'CMS_SETTINGS_MODEL' " +
                "to be set to the full path of the model class that represents " +
                "the settings for the CMS, for example myproject.models.Settings"
            )


def get_cms_settings_or_none():
    """
    Return the cms settings if exists or none.
    """
    global _SETTINGS_CACHE

    if _SETTINGS_CACHE == None:
        Settings = get_settings_model()

        # determine related fields required
        related = ['country']
        if 'cubane.ishop' in settings.INSTALLED_APPS:
            from cubane.ishop.models import ShopSettings
            if issubclass(Settings, ShopSettings):
                related.append('image_placeholder')

        # find all foreign relationships and load them as well
        for field in get_fields(Settings):
            if isinstance(field, ForeignKey):
                # skip DateTimeBase fields
                if field.name in ['created_by', 'updated_by', 'deleted_by']:
                    continue

                if field.name not in related:
                    related.append(field.name)

        # get settings
        try:
            s = Settings.objects.select_related(*related)[0]
        except (Settings.DoesNotExist, IndexError) as e:
            s = None

        _SETTINGS_CACHE = s

    return _SETTINGS_CACHE


def get_cms_settings():
    """
    Return the cms settings if exists or the default settings.
    """
    global _SETTINGS_CACHE

    s = get_cms_settings_or_none()
    if s is None:
        _SETTINGS_CACHE = get_settings_model()()
        return _SETTINGS_CACHE
    else:
        return s


def clear_settings_cache():
    """
    Clear settings cache.
    """
    global _SETTINGS_CACHE

    _SETTINGS_CACHE = None


class RedirectException(Exception):
    """
    Identifies a request where we need to redirect to the given url.
    """
    def __init__(self, url):
        super(RedirectException, self).__init__()
        self.url = url


class AppendSlashException(RedirectException):
    """
    Raised to identify the request as a redirect to the same url with
    a slash appended to it. The given url represents the new url which
    we should redirect to.
    """
    pass


def fake_request(path='/', cms=None):
    """
    Create a fake request object that is primarily used when calling into the
    CMS from command line.
    """
    factory = RequestFactory()
    request = factory.get(path)
    request.user = AnonymousUser()
    request.cms = cms
    request.settings = cms.settings if cms else None
    request.session = SessionStore()
    return request


def get_page_links_from_page(page, preview):
    """
    Extract all page links within any slot for the given page and return a
    data structure that can translate primary key page references into URLs.
    """
    if preview: return {}
    if not page: return {}
    if not isinstance(page, PageBase): return {}

    refs = _get_page_link_refs_from_page(page)
    return _load_page_link_refs(refs)


def get_page_links_from_content(content, preview):
    """
    Extract all page links within any slot for the given page and return a
    data structure that can translate primary key page references into URLs.
    """
    if preview: return {}
    if not content: return {}

    refs = {}
    _get_page_link_refs_from_content(content, refs)
    return _load_page_link_refs(refs)


def _load_page_link_refs(refs):
    links = {}
    for _type, _ids in refs.items():
        for model in get_models():
            try:
                model._meta.get_field('disabled')
                supports_disabled_state = True
            except FieldDoesNotExist:
                supports_disabled_state = False

            if model.__name__ == _type:
                links[_type] = {}

                _model = model.objects.filter(pk__in=_ids)
                if supports_disabled_state:
                    _model = _model.filter(disabled=False)

                for obj in _model:
                    links[_type][unicode(obj.pk)] = obj
    return links


def _get_page_link_refs_from_page(page):
    """
    Return a list of all media ids that are references in any slot for the
    given page.
    """
    _refs = {}
    if page:
        for slotname, content in page.get_data().items():
            _get_page_link_refs_from_content(content, _refs)
    return _refs


def _get_page_link_refs_from_content(content, refs):
    matches = re.findall(r'#link\[(\w+):(\d+)\]', content)
    for match in matches:
        _type = match[0]
        _id = match[1]
        if _type not in refs:
            refs[_type] = []
        if _id not in refs[_type]:
            refs[_type].append(_id)


class RenderResponse(object):
    """
    Encapsulates the result of rendering a page, which captures not only the
    resulting http response object but also meta data on which basis this result
    has been rendered, such as the render context and the template context used.
    """
    def __init__(self, response, context=None, template_context={}, filepath=None, mtime=None, changed=None):
        self.response = response
        self.context = context
        self.template_context = template_context
        self.filepath = filepath
        self.mtime = mtime
        self.changed = changed


    @classmethod
    def not_found(self):
        """
        Return a new render response, which represents an empty response
        (Not Found, status code 404).
        """
        return RenderResponse(HttpResponse('', status=404))


    @property
    def status_code(self):
        """
        Return the status code of the response, for example 200 OK (200).
        """
        return self.response.status_code


    @property
    def content(self):
        """
        Return the content of the response (HTML), if the status code of the
        request is 200 OK, otherwise return the empty string.
        """
        if self.response and self.response.status_code == 200:
            return self.response.content
        else:
            return ''


class PageContext(object):
    """
    Represents a context for rendering CMS pages and stores information
    about certain aspects of the page, such as settings and navigation data.
    """
    @classmethod
    def register_extension(cls, *args):
        """
        Register a new extension(s) for the CMS page context class.
        """
        return register_class_extensions('ExtendedPageContext', cls, args)


    def __init__(self, request, slug=None, page=None, view=None, cache_context=None, additional_context=None):
        """
        Create a new instance of a PageContext either by loading a page
        by the given slug or by directly loading the given page.
        """
        original_slug = slug

        if slug:
            slug = normalise_slug(slug)

        self._settings = False
        self.child_page_model = None
        self._slug_parts = None
        self.child_page = None
        self.child_pages = None
        self.paged_child_pages = None
        self.paginator = None
        self.gallery = None
        self.updated_on = None
        self.child_page_objects = None
        self.cache_context = cache_context
        self._is_legacy_url = False
        self._is_redirect = False
        self._redirect_url = None
        self._view = view
        self._default_pages = None
        self._additional_context = additional_context

        # create default cache context if no context was given
        if self.cache_context is None:
            self.cache_context = CacheContext()

        # obmit if this is not a page
        if page and not isinstance(page, PageBase):
            self.page = page
            return

        # create dummy request object
        if request == None:
            if page:
                request_url = page.get_fullslug()
            else:
                request_url = original_slug
            request = fake_request(request_url, view)
        self.request = request

        if slug == None and page == None:
            raise Http404('CMS: This request cannot be resolved with empty slug and empty page references.')

        # if the homepage is requested and we have query arguments,
        # then this might be a case for legacy urls
        # (e.g. wordpress default URL schema)...
        if request.path == '/' and page is None:
            self.process_legacy_urls(request)
            if self.is_redirect():
                return

        # load page content...
        try:
            self.load_page_or_404(request, slug, page)
        except Http404, ex:
            # CMS pages are required to end with a /, if it does not, then
            # we try again with /
            if not page and not slug.endswith('/'):
                try:
                    self.load_page_or_404(request, '%s/' % slug)
                    return
                except Http404:
                    pass

            # if such CMS page does definitly not exist, try to check
            # for legacy url...
            self.process_legacy_urls(request, ex)
        except RedirectException, ex:
            self._is_redirect = True
            self._redirect_url = ex.url


    def redirect_append_slash(self, request):
        """
        Raises AppendSlashException if there is a url pattern that matches the
        given url with a / appended and such url pattern is NOT the catch-all
        pattern for serving CMS pages.
        """
        if not settings.APPEND_SLASH:
            return

        url = request.path_info
        if url.endswith('/'):
            return

        urlconf = getattr(request, 'urlconf', None)
        url = '%s/' % url

        try:
            match = urlresolvers.resolve(url, urlconf)
            if match.url_name != 'cubane.cms.page':
                raise AppendSlashException(url)
        except urlresolvers.Resolver404:
            pass


    def is_standard_cms_page(self, page):
        """
        Return True, if the given page is a standard CMS page or child page.
        """
        # proceed with standard pipeline if no page is given to begin with
        if page == None:
            return True

        # standard CMS page model
        if isinstance(page, get_page_model()):
            return True

        # standard CMS child page model?
        if issubclass(type(page), ChildPage):
            return True

        # not standard cms content
        return False


    def get_child_pages_queryset(self, child_page_model):
        """
        Virtual: Allow user-code to construct base query, in particular to
        specify select related.
        """
        return child_page_model.objects.select_related(
            'page',
            'image'
        )


    def filter_child_pages(self, child_pages):
        """
        Virtual: Allow user-code to filter child pages.
        """
        return child_pages


    def load_page_or_404(self, request, slug=None, page=None):
        """
        Load the page based on given request, slug and/or page or raises
        404 exception if no such page exists.
        """
        self._request = request
        self._slug = slug
        self.page = page

        # setup standard content page if a page is given that is
        # not a default CMS page...
        if not self.is_standard_cms_page(page):
            return

        # construct slug from given page if no slug was given. For a child
        # page, this may fail because the child page no longer has a page.
        if self._slug == None:
            try:
                if self.page.slug:
                    self._slug = normalise_slug(self.page.get_fullslug())
                else:
                    self._slug = ''
            except ChildPageWithoutParentError:
                raise Http404('Child page without parent page.')

        # a regular (non-legacy) cms url MUST end with /. If it does NOT
        # end with /, see if there is a valid url pattern with the /
        # (APPEND_SLASH)
        self.redirect_append_slash(request)

        # split slug into parts to match page / child-page...
        self._slug_parts = self._slug.split('/', 2)

        # we cannot have sub-sub children
        if len(self._slug_parts) >= 3:
            raise Http404('Child pages cannot have sub-child pages.')

        # get page by first component of the slug
        if not self.page and self._slug != None:
            if self._slug == '':
                self.page = self.get_homepage_or_404()
            else:
                self.page = self.get_page_by_slug_or_404(self._slug_parts[0])

            # if the page is the 404 page and we reached the page via slug,
            # produce a real 404 and do not simply render the page as a regular
            # page
            if self.page_is_404_page(self.page):
                raise Http404('404 page cannot be presented as a regular page.')

        # if the page is a child_page, figure out the page
        if not isinstance(self.page, get_page_model()):
            self.child_page = self.page
            self.page = self.child_page.page

            # child page might not have a parent page, because parent page
            # might have been deleted...
            if self.page:
                self._slug_parts = [self.page.get_slug(), self.child_page.get_slug()]
            else:
                raise Http404('Child page without parent page.')

        # verify that the page is visible, unless this is the default 404 page
        if self.page and not self.page.is_visible() and not self.page_is_404_page(self.page):
            raise Http404('Page is not visible.')

        # verify that the child page is visible as well
        if self.child_page and not self.child_page.is_visible():
            raise Http404('Child page is not visible.')

        # determine the model for child_pages for this page
        self.request.paginator_within_url = False
        if self._slug_parts != None:
            # if the second url path component is of the format page-..., assume
            # it is refering to a page and patch the page argument of the GET
            # request accordingly.
            if len(self._slug_parts) > 1:
                m = re.match(r'((?P<all>all)-)?page-(?P<page>\d+)', self._slug_parts[1])
                if m:
                    # cannot fail because of the reg. expression
                    page_number = int(m.group('page'))

                    # patch paginator
                    self.request.paginator_within_url = True
                    self.request.paginator_page = page_number
                    self.request.paginator_all = '1' if m.group('all') == 'all' else '0'
                    del self._slug_parts[1]

                    # if we are refering to page-1, then simply redirect to the
                    # base url instead...
                    if page_number == 1 and self.request.paginator_all != '1':
                        raise RedirectException(self.page.url)

            # determine type of child page
            self.child_page_model = self.page.get_entity_model()
            if self.child_page_model != None:
                if not self.child_page:
                    # base query for child pages
                    self.child_page_objects = self.get_child_pages_queryset(self.child_page_model)

                    if len(self._slug_parts) == 1:
                        # list of child_pages
                        self.child_pages = self.child_page_objects.filter(
                            page=self.page,
                            disabled=False
                        )

                        # filter by custom user-code
                        self.child_pages = self.filter_child_pages(self.child_pages)

                        # run it through visibility filter
                        self.child_pages = self.child_page_model.filter_visibility(self.child_pages)

                        # sort child pages by seq if sortable in backend
                        try:
                            if get_listing_option(self.child_page_model, 'sortable'):
                                self.child_pages = self.child_pages.order_by('seq')
                        except AttributeError:
                            pass

                        # allow for overwriting child pages fetch operation
                        if self._view:
                            self.child_pages = self._view.get_child_pages(
                                request,
                                self.child_page_model,
                                self.child_pages
                            )
                    else:
                        # individual child page
                        try:
                            self.child_page = self.child_page_objects.get(
                                page=self.page,
                                slug=self._slug_parts[1],
                                disabled=False
                            )
                        except self.child_page_model.DoesNotExist:
                            raise Http404(
                                "Child page '%s' does not exist for page '%s'." % (
                                    self._slug_parts[1],
                                    self.page.title
                                )
                            )
            elif len(self._slug_parts) > 1:
                raise Http404(
                    ("Page '%s' does not support child pages, yet a child " +
                     "page is requested according to the given url.") % (
                        self.page.title
                    )
                )

        # at this point we found a page to server, but if the slug does NOT
        # end with /, redirect...
        if self._slug != '' and not request.path_info.endswith('/'):
            raise AppendSlashException('%s/' % request.path_info)

        # if we found a url that has pagination information embedded,
        # we need to have child pages and pagination enabled for it
        if self.request.paginator_within_url:
            if self.child_page_model:
                if not self.settings.paging_enabled_for(self.child_page_model):
                    raise Http404(
                        "Pagination is not enabled for child pages of type '%s'." % \
                        self.child_page_model._meta.verbose_name_plural
                    )
            else:
                raise Http404(
                    ("Page '%s' does not support pagination. " +
                     "Only child pages support pagination.") % (
                        self.page.title
                    )
                )

        # pagination
        if self._slug and self.child_page_model and self.settings.paging_enabled_for(self.child_page_model):
            self.paged_child_pages = create_paginator(
                self._request,
                self.child_pages,
                page_size = self.settings.page_size,
                min_page_size = self.settings.page_size,
                max_page_size = self.settings.max_page_size
            )
            self.paginator = self.paged_child_pages.paginator


    def get_legacy_url_models(self):
        """
        Return a list of models to test against for legacy url support.
        """
        models = [get_page_model()]
        for model in get_models():
            if issubclass(model, PageBase) or issubclass(model, ChildPage):
                models.append(model)
        return models


    def process_legacy_urls(self, request, ex_404=None):
        """
        Process given request against all known legacy urls in the hope that
        we find a page for it.
        """
        url = request.get_full_path()

        def get_query(model):
            # determine if the model supports disabled state
            try:
                model._meta.get_field('disabled')
                supports_disabled_state = True
            except FieldDoesNotExist:
                supports_disabled_state = False

            q = model.objects.filter(legacy_url=url)
            if supports_disabled_state:
                q = q.filter(disabled=False)

            return q

        def get_by_legacy_url_for(model):
            try:
                if hasattr(model, 'filter_visibility'):
                    return model.filter_visibility(get_query(model))[0]
                elif hasattr(model, 'filter_legacy_url'):
                    return model.filter_legacy_url(url)
                else:
                    return get_query(model)[0]
            except IndexError:
                return None

        # construct list of models to test against
        models = self.get_legacy_url_models()

        # test against all models (pages and child pages)...
        for model in models:
            page = get_by_legacy_url_for(model)
            if page and not self.page_is_enquiry_template(page):
                self._is_legacy_url = True
                self._redirect_url = page.get_absolute_url()
                return

        # if we could not find anything that matches, re-raise the given
        # original 404 exception if provided...
        if ex_404 is not None:
            raise ex_404


    @property
    def settings(self):
        """
        Return the website-wide settings objects or None.
        """
        if self._view:
            return self._view.settings
        else:
            return get_cms_settings()


    @property
    def current_page(self):
        """
        Return the current page that is rendered
        """
        return self.child_page if self.child_page else self.page


    def get_filepath(self):
        """
        Return the full file path of the current page or None.
        """
        page = self.current_page

        if page:
            filepath = page.get_filepath()

            # paginated result?
            if self.paginator:
                page = self.paged_child_pages.number
                if page > 1:
                    head, tail = os.path.split(filepath)
                    filepath = '%s/page-%d/%s' % (
                        head,
                        page,
                        tail
                    )
        else:
            filepath = None

        return filepath


    def has_identifier(self, identifier):
        """
        Return True, if the current page has the given identifier.
        """
        page = self.current_page
        return page and getattr(page, 'identifier', None) == identifier


    def get_redirect_url(self):
        """
        Return the redirect url for this page context. A redirect url might be
        set because of APPEND_SLASH or a legacy url.
        """
        return self._redirect_url


    def get_navigation_builder(self, active_page=None, current_page_or_child_page=None):
        """
        Return a new instance of the navigation builder for constructing the
        navigation for the website.
        """
        global NAV_BUILDER_CLASS

        if not NAV_BUILDER_CLASS:
            NAV_BUILDER_CLASS = CMSNavigationBuilder

            # give each module the chance to extend the base class
            for app_name in settings.INSTALLED_APPS:
                app = import_module(app_name)
                if hasattr(app, 'install_nav'):
                    NAV_BUILDER_CLASS = app.install_nav(NAV_BUILDER_CLASS)

        # creates a new navigation builder
        return NAV_BUILDER_CLASS(self._view, self, active_page, current_page_or_child_page, self.cache_context)


    def get_navigation(self, active_page=None, current_page_or_child_page=None):
        """
        Return the website-wide navigation objects which contains a list of
        all pages that are at least in one navigation bar and/or are navigable
        because a page defines a unique identifier.
        """
        builder = self.get_navigation_builder(active_page, current_page_or_child_page)
        (_nav, _active_nav, _pages) = builder.get_navigation()

        # allow custom code to manipulate the navigation before processing
        # it further...
        if self._view:
            (_nav, _active_nav, _pages) = self._view.on_navigation(_nav, _active_nav, _pages)

        # inject next/prev getters for navigation items
        def _inject_prev_next(items):
            prev_item = None
            for item, next_item in zip(items, items[1:]):
                item['prev'] = prev_item
                item['next'] = next_item
                prev_item = item
                if item.get('children'):
                    _inject_prev_next(item.get('children'))
        for items in _nav.values():
            _inject_prev_next(items)

        return (_nav, _active_nav, _pages)


    def get_child_page_navigation(self, child_pages, current_child_page):
        """
        Return a list of navigation objects for the current page which is
        a list of all child pages for the current page or child page.
        """
        current_id = current_child_page.id if current_child_page else None

        # filter out the disabled child pages
        child_pages = child_pages.filter(disabled=False)

        for p in child_pages:
            yield {
                'id': p.id,
                'title': p.title,
                'url': p.get_absolute_url(),
                'active': p.id == current_id
            }


    def get_default_page(self, name, allow_disabled_page=False):
        """
        Return a default CMS page from the CMS settings. However, even
        if a page is setup, we might still return None if the page is
        disabled for example. For performance reasons, we fetch all default
        pages in one query and separate the result from a cached list of pages
        when required.
        """
        # load default pages
        if not self._default_pages:
            pks = self.settings.get_default_pages_pks()
            pages = get_page_model().objects.filter(pk__in=pks)

            # allow disabled pages?
            if not allow_disabled_page:
                pages = pages.filter(disabled=False)

            # materialize
            self._default_pages = list(pages)

        try:
            pk = getattr(self.settings, '%s_id' % name)
            for p in self._default_pages:
                if p.pk == pk:
                    return p
        except AttributeError:
            pass

        return None


    def get_homepage(self):
        """
        Return the CMS page that represents the homepage or None.
        """
        return self.get_default_page('homepage')


    def get_contact_page(self):
        """
        Return the CMS page that represents the contact page or None.
        """
        return self.get_default_page('contact_page')


    def get_404_page(self):
        """
        Return the CMS page that represents the contact page or None.
        """
        return self.get_default_page('default_404', allow_disabled_page=True)


    def get_enquiry_template(self):
        """
        Return the CMS page that represents the enquiry email template.
        """
        return self.get_default_page('enquiry_template')


    def compare_pages(self, a, b):
        """
        Return True, if both given pages are the same page.
        """
        if not a or not b:
            return False

        return a.__class__ == b.__class__ and a.pk == b.pk


    def page_is_homepage(self, page):
        """
        Return True, if the given page is the homepage according to the
        settings.
        """
        return self.compare_pages(page, self.get_homepage())


    def page_is_contact_page(self, page):
        """
        Return True, if the given page is the contact page according to the
        settings.
        """
        return self.compare_pages(page, self.get_contact_page())


    def page_is_404_page(self, page):
        """
        Return True, if the given page is the default 404 page according to the
        settings.
        """
        return self.compare_pages(page, self.get_404_page())


    def page_is_enquiry_template(self, page):
        """
        Return True, if the given page is the default enquiry template page
        according to the settings.
        """
        return self.compare_pages(page, self.get_enquiry_template())


    def is_homepage(self):
        """
        Return True, if the current page is the front page of the website.
        The homepage is configured in cms settings (backend).
        """
        return self.page_is_homepage(self.page)


    def is_contact_page(self):
        """
        Return True, if the current page is the contact page of the website.
        The contact page is configured in cms settings (backend).
        """
        return self.page_is_contact_page(self.page)


    def is_404_page(self):
        """
        Return True, if the current page is the 404 page of the website.
        The default 404 page is configured in cms settings (backend).
        """
        return self.page_is_404_page(self.page)


    def is_enquiry_template(self):
        """
        Return True, if the current page is the enquiry email template page.
        """
        return self.page_is_enquiry_template(self.page)


    def is_redirect(self):
        """
        Return True, if this request is suppose to handle a redirect, for example
        because of a missing /. The url (with the slash) is otherwise known to the
        system and redirecting there would definitely resolve the situation.
        In any case, this cannot be a regular CMS page, since such pages must
        always end with /.
        """
        return self._is_redirect


    def is_legacy_url(self):
        """
        Return True, if this request targets a legacy url scheme.
        """
        return self._is_legacy_url


    def get_homepage_or_404(self):
        """
        Return the homepage for this website or raise Http404 if there is
        no homepage defined.
        """
        page = self.get_homepage()

        if page == None:
            raise HomepageNotDefinedError(
                'No homepage defined. Please select a page within the ' +
                'settings that should be presented here as the homepage.'
            )

        return page


    def get_page_by_slug(self, slug):
        """
        Return the CMS page that belongs to the given slug or None if there
        is no such CMS page.
        """
        try:
            page_model = get_page_model()
            pages = self._view.get_page_objects(page_model)
            return page_model.filter_visibility(pages.filter(slug=slug, disabled=False))[0]
        except IndexError:
            return None


    def get_page_by_slug_or_404(self, slug):
        """
        Return a page by slug. This could be a child page of the homepage as well.
        """
        # load standard cmd page
        page = self.get_page_by_slug(slug)

        # try to load a child page of the homepage instead
        if page == None:
            homepage = self.get_homepage()
            if homepage != None:
                child_page_model = homepage.get_entity_model()
                if child_page_model:
                    try:
                        page = child_page_model.objects.get(slug=slug, page=homepage)
                    except child_page_model.DoesNotExist:
                        page = None

        # 404?
        if page == None:
            raise Http404(
                "There is no CMS page with the given slug '%s' or the page is not visible." % slug
            )

        # enquiry template cannot be loaded as a cms page
        if self.page_is_enquiry_template(page):
            raise Http404(
                'Enquiry template page cannot be presented as a regular CMS page.'
            )

        return page


    def get_page_image_ids(self, page):
        """
        Return a list of all media ids that are references in any slot for the
        given page.
        """
        _ids = []
        if page:
            for slotname, content in page.get_data().items():
                for candidate in get_img_tags(content):
                    try:
                        _id = int(candidate)
                        _ids.append(_id)
                    except ValueError:
                        pass
        return sorted(_ids)


    def get_page_images(self, page, preview):
        """
        Extract all media that is references in any slot for the given page.
        """
        if preview: return {}
        if 'cubane.media' not in settings.INSTALLED_APPS: return {}
        if not page: return {}
        if not isinstance(page, PageBase): return {}

        from cubane.media.models import Media

        _ids = self.get_page_image_ids(page)

        if len(_ids) > 0:
            images = Media.objects.filter(is_image=True).in_bulk(_ids)
        else:
            images = {}

        return images


    def get_template_context(self, preview=False):
        """
        Return the template context for rendering the page.
        """
        # get navigation
        current_page = self.child_page if self.child_page else self.page
        nav, active_nav, pages = self.get_navigation(self.page, current_page)

        # basic template context
        context = {
            'current_page': current_page,
            'page': self.page,
            'images': self.get_page_images(current_page, preview),
            'page_links': get_page_links_from_page(current_page, preview),
            'settings': self.settings,
            'cms_preview': preview,   # deprecated
            'nav': nav,
            'active_nav': active_nav,
            'pages': pages,
            'homepage': self.get_homepage(),
            'is_homepage': self.page_is_homepage(current_page),
            'is_contact_page': self.is_contact_page(),
            'is_404_page': self.is_404_page(),
            'is_enquiry_template': self.is_enquiry_template(),
            'preview': preview,
        }

        # hierarchical pages
        if settings.PAGE_HIERARCHY and current_page.pk:
            hierarchical_pages = get_page_model().objects.filter(parent_id=current_page.pk).exclude(disabled=True).order_by('seq')
            context.update({
                'hierarchical_pages': list(
                    self._view.get_hierarchical_pages(self.request, current_page, hierarchical_pages)
                )
            })

        # child pages / posts
        if self.child_page_model:
            child_page_slug = slugify(self.child_page_model.__name__)

            context.update({
                'verbose_name': self.child_page_model._meta.verbose_name,
                'verbose_name_plural': self.child_page_model._meta.verbose_name_plural,

                # deprecated
                'child_page': self.child_page,
                'child_page_model': self.child_page_model.__name__,
                'child_page_slug': child_page_slug,
                'child_pages': self.child_pages,
                'paged_child_pages': self.paged_child_pages,

                # posts and paginator
                'post_slug': child_page_slug,
                'posts': self.child_pages,
                'paged_posts': self.paged_child_pages,
                'paginator': self.paginator
            })

            # deprecated, only available under the old name
            posts = self.get_child_page_navigation(self.child_page_objects, self.child_page)
            context.get('nav').update({
                'child_pages': posts,   # deprecated
                'posts': posts
            })

        # slots with content
        if current_page and isinstance(current_page, PageBase):
            context.update({
                'slots': current_page.slotnames_with_content()
            })

        # additional context
        if self._additional_context:
            context.update(self._additional_context)

        # determine base updated_on date from current page
        if current_page and hasattr(current_page, 'updated_on'):
            self.updated_on = current_page.updated_on

        return context


    def get_template(self):
        """
        Return the correct template to use for rendering this page, which
        is either the page template for a page or (if we have a child_page),
        the tmeplate that is associated with the child_page.
        """
        if self.child_page:
            return self.child_page.template
        else:
            return self.page.template


    def render(self, template_context, template=None):
        """
        Render given CMS page with this render context.
        """
        if template == None:
            template = self.get_template()

        return render(self._request, template, template_context, content_type='text/html; charset=utf-8')


class AbsoluteUrlSitemap(sitemaps.Sitemap):
    def get_item_attr(self, name, obj, default=None):
        try:
            attr = getattr(self, name)
        except AttributeError:
            return default
        if callable(attr):
            return attr(obj)
        return attr


    def get_urls(self, page=1, site=None, protocol=None):
        # ignore protocol and domain!

        urls = []
        for item in self.paginator.page(page).object_list:
            # we assume that all locations as provided are already absolute
            loc = self.get_item_attr('location', item)
            priority = self.get_item_attr('priority', item, None)
            url_info = {
                'item':       item,
                'location':   loc,
                'lastmod':    self.get_item_attr('lastmod', item, None),
                'changefreq': self.get_item_attr('changefreq', item, None),
                'priority':   unicode(priority is not None and priority or ''),
            }
            urls.append(url_info)
        return urls


class GenericAbsoluteUrlSitemap(AbsoluteUrlSitemap):
    priority = None
    changefreq = None


    def __init__(self, info_dict, priority=None, changefreq=None):
        self.queryset = info_dict['queryset']
        self.date_field = info_dict.get('date_field', None)
        self.priority = priority
        self.changefreq = changefreq


    def items(self):
        # Make sure to return a clone; we don't want premature evaluation.
        return self.queryset.filter()


    def lastmod(self, item):
        if self.date_field is not None:
            return getattr(item, self.date_field)
        return None


class HomepageSitemap(AbsoluteUrlSitemap):
    priority = 0.6
    protocol = get_protocol()


    def __init__(self, cms):
        self._cms = cms


    @property
    def homepage(self):
        if not hasattr(self, '_homepage'):
            settings = get_cms_settings()
            self._homepage = settings.homepage
        return self._homepage


    def items(self):
        homepage = self._cms.settings.homepage

        # no homepage to begin with
        if not homepage:
            return []

        # homepage is disabled or otherwise not visible
        if homepage.disabled or not homepage.is_visible():
            return []

        # homepage excluded from sitemap
        if not homepage.sitemap:
            return []

        # return homepage item (/)
        return [homepage]


    def location(self, item):
        return item.url


    def lastmod(self, item):
        return self._cms.settings.homepage.updated_on


class CustomSitemapItem(object):
    protocol = get_protocol()


    def __init__(self, local_url, lastmod):
        self.local_url = local_url
        self.url = make_absolute_url(local_url)
        self.lastmod = lastmod


class CustomSitemap(AbsoluteUrlSitemap):
    """
    Custom Sitemap will contain custom pages added by the on_custom_sitemap function
    """
    priority = 0.5
    protocol = get_protocol()


    def __init__(self, cms):
        self._cms = cms
        self._items = []
        self._cached_pages = []


    def add_url(self, url, lastmod, cached=False):
        if lastmod == None:
            lastmod = datetime.now()

        item = CustomSitemapItem(url, lastmod)
        self._items.append(item)

        if cached:
            self._cached_pages.append(item)


    def add(self, name, args=[], lastmod=None, cached=False):
        self.add_url(reverse_lazy(name, args=args), lastmod, cached)


    def items(self):
        self._items = []
        self._cached_pages = []
        self._cms.on_custom_sitemap(self)
        return self._items


    def cached_pages(self):
        self._items = []
        self._cached_pages = []
        self._cms.on_custom_sitemap(self)
        return self._cached_pages


    def location(self, item):
        return item.url


    def lastmod(self, item):
        return item.lastmod


class CMSGenericSitemap(GenericAbsoluteUrlSitemap):
    priority = 0.5
    protocol = get_protocol()


    def __init__(self, cms, model=None):
        self._cms = cms
        self._model = model
        self.date_field = 'updated_on'
        self.priority = 0.5
        self.changefreq = None


class CMSPagesSitemap(CMSGenericSitemap):
    html_name = 'Pages'


    def items(self):
        settings = self._cms.settings
        page_model = get_page_model()

        pages = page_model.filter_visibility(
            page_model.objects.filter(disabled=False, sitemap=True)
        )

        if settings.homepage:
            pages = pages.exclude(pk__in=filter(None, [
                settings.homepage_id,
                settings.default_404_id,
                settings.enquiry_template_id
            ]))
        return pages


class CMSChildPagesSitemap(CMSGenericSitemap):
    html_name = 'Second-Level Pages'


    def items(self):
        child_pages = self._model.filter_visibility(
            self._model.objects.filter(
                page__isnull=False,
                page__disabled=False,
                disabled=False,
                sitemap=True
            )
        )
        return self._cms.filter_out_childpages_on_sitemap(child_pages)


class CMS(View):
    """
    CMS base class. This may be overridden in order to hook custom things
    into the pipeline.
    """
    patterns = [
        view_url('mailchimp-subscription-ajax', view='submit_mailchimp_subscription', name='cubane.cms.submit_mailchimp_subscription'),
        view_url('^%s(?P<filename>.*?)$' % settings.MEDIA_DOWNLOAD_URL, view='download_media', name='cubane.cms.download_media'),
        view_url(PAGE_PATTERN, view='page_by_slug', name='cubane.cms.page')
    ]


    _HOOKS = [
        ('on_template_context', None),
        ('on_homepage',         lambda c: c.is_homepage()),
        ('on_contact_page',     lambda c: c.is_contact_page()),
        ('on_404_page',         lambda c: c.is_404_page()),
    ]


    def __init__(self, *args, **kwargs):
        """
        Create a new instance of the CMS class.
        """
        super(CMS, self).__init__(*args, **kwargs)
        self._content_map = {}


    @classmethod
    def register_extension(cls, *args):
        """
        Register a new extension(s) for the CMS class.
        """
        return register_class_extensions('ExtendedCMS', cls, args)


    def get_page_context(self, *args, **kwargs):
        """
        Return a new instance of the page context.
        """
        global PAGE_CONTEXT_CLASS

        if not PAGE_CONTEXT_CLASS:
            PAGE_CONTEXT_CLASS = PageContext

            # give each module the chance to extend the base class
            for app_name in settings.INSTALLED_APPS:
                app = import_module(app_name)
                if hasattr(app, 'install_page_context'):
                    PAGE_CONTEXT_CLASS = app.install_page_context(PAGE_CONTEXT_CLASS)

        # feed in view (self), if no such kwarg is present
        if 'view' not in kwargs:
            kwargs['view'] = self

        # creates a new page context with given arguments...
        return PAGE_CONTEXT_CLASS(*args, **kwargs)


    def get_page_model(self):
        return get_page_model()


    def fake_request(self, path='/'):
        return fake_request(path, cms=self)


    def get_page_objects(self, page_model):
        """
        Return the base queryset for accessing pages.
        """
        return page_model.objects.all()


    def map_content(self, pattern, replacement):
        """
        Register a certain pattern of text or which any occurrence within CMS
        content will be replaced with the given replacement string. The pattern
        will match any text or content in the format {pattern}.
        """
        key = '{%s}' % pattern
        if callable(replacement):
            is_callable = True
            contains_template_code = False
        else:
            is_callable = False
            contains_template_code = '{{' in replacement or '{%' in replacement

        self._content_map[key] = (replacement, contains_template_code, is_callable)


    def get_pages(self):
        """
        Return a list of all visible CMS pages.
        """
        settings = self.settings
        page_model = get_page_model()
        pages = self.get_page_objects(page_model)
        pages = page_model.filter_visibility(
            pages.filter(disabled=False)
        )
        pages = pages.exclude(pk__in=filter(None, [
            settings.default_404_id,
            settings.enquiry_template_id
        ]))
        return pages


    def get_page_by_slug(self, slug):
        """
        Return the CMS page that belongs to the given slug or None if there
        is no such CMS page.
        """
        page_model = get_page_model()
        try:
            pages = self.get_page_objects(page_model)
            return pages.get(slug=slug, disabled=False)
        except page_model.DoesNotExist:
            return None


    def get_child_page_models(self):
        """
        Return a list of all child page models.
        """
        models = []
        for model in get_models():
            if issubclass(model, ChildPage):
                models.append(model)
        return models


    def get_entity_models(self):
        """
        Return a list of all entity models.
        """
        entity_models = []
        for model in get_models():
            if issubclass(model, Entity):
                entity_models.append(model)
        return entity_models


    def get_child_pages_for_model(self, model):
        """
        Return a list of all child pages for the given model.
        """
        return model.objects.filter(disabled=False)


    def get_child_pages_for_page(self, page):
        """
        Return a list of child pages that belong to the given page.
        """
        ch_model = page.get_entity_model()
        if ch_model:
            return ch_model.objects.filter(page=page)
        else:
            return ''


    def get_homepage(self):
        """
        Return the homepage.
        """
        if self.settings:
            return self.settings.homepage
        else:
            return None


    def get_slotnames(self):
        """
        Return list of available slot names.
        """
        return settings.CMS_SLOTNAMES


    def get_default_slotname(self):
        """
        Return the default slotname, which is the first slotname defined.
        """
        try:
            return settings.CMS_SLOTNAMES[0]
        except IndexError:
            return None


    def create_default_enquiry_form(self, request, context, template_context):
        """
        By default, present the default enquiry form (same as backend).
        This can be changed by overriding this method.
        """
        if 'cubane.enquiry' in settings.INSTALLED_APPS:
            from cubane.enquiry.views import default_enquiry_form
            from cubane.enquiry.views import get_enquiry_model

            return default_enquiry_form(
                request,
                context,
                template_context,
                get_enquiry_model()
            )


    def create_nav(self, title, url, active=False, nav_title=None, page_title=None, excerpt=None, nav_image=None, identifier=None):
        """
        Create a new navigation item.
        """
        if page_title == None: page_title = title
        if nav_title == None: nav_title = title

        return {
            'identifier': identifier,
            'title': title,
            'slug': slugify(title),
            'page_title': page_title,
            'nav_title': nav_title,
            'url': url,
            'active': active,
            'active_child': False,
            'excerpt': excerpt,
            'entity_type': None,
            'children': [],
            'child_pages': [],
            'aggregated_pages': [],
            'nav_image': nav_image
        }


    def create_blank_enquiry_form(formclass=None):
        """
        Create and return a new blank instance of the default enquiry form.
        """
        if 'cubane.enquiry' in settings.INSTALLED_APPS:
            from cubane.enquiry.views import create_blank_enquiry_form
            from cubane.enquiry.views import get_enquiry_model
            return create_blank_enquiry_form(get_enquiry_model())


    @property
    def custom_sitemap(self):
        if not self._custom_sitemap:
            return CustomSitemap(self)
        return self._custom_sitemap
    _custom_sitemap = None


    @property
    def sitemaps(self):
        """
        Generate sitemap generators for all pages and entities.
        """
        return self.get_sitemaps()


    def get_sitemaps(self):
        """
        Generate sitemap generators for all pages and entities. This method
        may be overridden by other modules to add items to the sitemap.
        """
        _sitemaps = {}

        # homepage
        _sitemaps['homepage'] = HomepageSitemap(self)

        # pages
        _sitemaps['pages'] = CMSPagesSitemap(self)

        # child pages
        for model in get_models():
            if issubclass(model, ChildPage):
                _sitemaps[slugify(model._meta.verbose_name)] = CMSChildPagesSitemap(self, model)

        # custom urls
        _sitemaps['custom'] = self.custom_sitemap

        return _sitemaps


    def get_sitemap_links(self):
        """
        Return a list of all sitemap objects that would form the sitemap
        of the website sorted alphabetical.
        """
        sitemaps = self.get_sitemaps()
        sitemap = []
        for sitemap_generator in sitemaps.values():
            for item in sitemap_generator.items():
                sitemap.append(item)
        return sorted(sitemap, key=lambda item: item.title)


    def get_sitemap_links_az(self):
        """
        Return a list of all sitemap objects that would form the sitemap
        of the website sorted alphabetical and split by A-Z.
        """
        result = []
        items = []
        current_ch = None
        allowed_characters = list(char_range('A', 'Z')) + list(char_range('0', '9'))
        for item in self.get_sitemap_links():
            ch = item.title[0].upper()
            if ch not in allowed_characters:
                ch = '_'

            if ch != current_ch:
                if items:
                    result.append({
                        'ch': current_ch,
                        'items': items
                    })
                    items = []
                current_ch = ch

            items.append(item)

        if items:
            result.append({
                'ch': current_ch,
                'items': items
            })

        return result


    def filter_out_childpages_on_sitemap(self, child_pages):
        return child_pages


    @property
    def settings(self):
        """
        Return the website-wide settings objects or None.
        """
        return get_cms_settings()


    @property
    def deploy_timestamp(self):
        """
        Return the deployment timestamp (cached) or none.
        """
        if not hasattr(self, '_deploy_timestamp'):
            self._deploy_timestamp = load_deploy_timestamp()
        return self._deploy_timestamp


    def on_request(self, request, context):
        pass


    def on_legacy_url(self, request, context):
        pass


    def on_template_context(self, request, context, template_context):
        return template_context


    def on_navigation(self, nav, active_nav, pages):
        return (nav, active_nav, pages)


    def on_homepage(self, request, context, template_context):
        pass


    def on_contact_page(self, request, context, template_context):
        return self.create_default_enquiry_form(request, context, template_context)


    def on_404_page(self, request, context, template_context):
        pass


    def on_response(self, request, response):
        pass


    def on_render_content_pipeline(self, request, content, context):
        """
        Called whenever the given content will be rendered with the given
        template context. It executes registered content mapping rules and
        finally allows user code to run before the result is returned and
        ultimately rendered.
        """
        # execute content mapping
        for pattern, repl in self._content_map.items():
            if re.search(pattern, content):
                (replacement, contains_template_code, is_callable) = repl
                c = copy.copy(context)

                if contains_template_code:
                    django_engine = engines['django']
                    template = django_engine.from_string(replacement)
                else:
                    template = None

                def patcher(m):
                    if is_callable:
                        c.update(m.groupdict())
                        return replacement(request, c)
                    elif template:
                        c.update(m.groupdict())
                        return get_compatible_template(template).render(c)
                    else:
                        return replacement

                content = re.sub(pattern, patcher, content)

        # allow user code to run
        return self.on_render_content(request, content)


    def on_render_content(self, request, content):
        """
        Virtual: Called whenever a snippet of the given content will be rendered
        and allows user code to override in order to perform content inspection
        and/or alteration of content before it is being rendered.
        """
        return content


    def on_custom_sitemap(self, sitemap):
        """
        Called whenever the CMS requests the website's sitemap.xml file to be
        generated. Additional sitemap records can be added via:

            sitemap.add(url_name, args, lastmod, cache=False)

        If cache is True, then the corresponding page will be cached by the
        caching system if caching is enabled.
        """
        pass


    def on_object_links(self, links):
        """
        Called whenever the CMS requests a list of link types alongside all
        possible link targets to be generated for custom object types that
        a customer may want to link to.
        """
        pass


    def enquiry_configure_form(self, request, form, instance, edit):
        """
        Configure enquiry form.
        """
        return form.configure(request, instance, edit)


    def enquiry_send_mail_to_customer(self, request, instance, data):
        """
        Send an email to the customer how filled out the enquiry form.
        """
        return cubane_send_cms_enquiry_mail(
            request,
            instance.email,
            '%s | Your enquiry on our website.' % self.settings.name,
            data
        )


    def enquiry_send_mail_to_client(self, request, instance, data):
        """
        Send an email to the client to inform about the new
        enquiry that was made.
        """
        return cubane_send_mail_template(
            request,
            self.settings.enquiry_email,
            '%s | Enquiry from your website' % self.settings.name,
            settings.ENQUIRY_CLIENT_TEMPLATE, {
                'data': data,
                'fields': get_ordered_list_of_fields(data, data.items()),
                'settings': self.settings
            }
        )


    def on_enquiry_send(self, request, instance, data):
        """
        Called after an enquiry has been made successfully.
        """
        pass


    def mailchimp_subscribe(self, request, email):
        """
        Subscribe given email address with mailchimp if configured in settings.
        """
        from mailsnake import MailSnake
        from cubane.lib.mail import send_exception_email

        if self.settings and self.settings.mailchimp_api and self.settings.mailchimp_list_id:
            ms = MailSnake(self.settings.mailchimp_api)
            try:
                ms.listSubscribe(id=self.settings.mailchimp_list_id, email_address=email, merge_vars={})
                return True
            except:
                send_exception_email(request)

        return False


    def is_page_homepage(self, page):
        """
        Check if the page provided is the homepage.
        """
        if self.settings.homepage and page == self.settings.homepage:
            return True
        else:
            return False


    def get_child_pages(self, request, model, child_pages):
        """
        Deprecated: Use get_posts() instead!
        """
        return self.get_posts(request, model, child_pages)


    def get_posts(self, request, model, posts):
        """
        Override the way the system is determining posts of the given
        model. You may want to change the order by part of the given
        queryset in order to change the default ordering of child pages.
        """
        return posts


    def get_hierarchical_pages(self, request, current_page, pages):
        """
        Virtual: Return a queryset that represents all direct child pages of the
        given current page based on the given queryset.
        """
        return pages


    def get_contact_page_url(self, context):
        page = context.get_contact_page()
        if page:
            return page.url
        else:
            return ''


    def process_hook(self, hookname, request, context, template_context):
        """
        Process given name of hook with given request arguments.
        If the hook method returns something, it replaces the template context.
        """
        if hasattr(self, hookname):
            f = getattr(self, hookname)
            t = f(request, context, template_context)
            if t: return t
        return template_context


    def process_hooks(self, request, context, template_context):
        """
        Process all user hooks in a specific order. If a hook returns
        a direct response, any further hooks are skipped. The normal behaviour
        for a hook is to return a template context, in which case the next
        hook is executed.
        """
        for hook, predicate in self._HOOKS:
            if predicate:
                applies = predicate(context)
            else:
                applies = True

            if not applies:
                continue

            response = self.process_hook(
                hook,
                request,
                context,
                template_context
            )

            if isinstance(response, HttpResponse):
                return response
            else:
                template_context = response
        return template_context


    def dispatch_template_context(self, request, context, preview=False, initial_template_context=None):
        """
        Aquire and dispatch tempate process.
        """
        # get template context
        template_context = context.get_template_context(preview=preview)

        # merge into initial template context before processing hooks
        if initial_template_context:
            c = {}
            c.update(initial_template_context)
            c.update(template_context)
            template_context = c

        # process hooks
        return self.process_hooks(request, context, template_context)


    def dispatch_identifier_context(self, request, context, template_context):
        """
        Dispatch identifier-based handlers.
        """
        current_page = template_context.get('current_page')
        if current_page and isinstance(current_page, PageAbstract) and current_page.identifier:
            handler_name = 'on_page_identifier_%s' % current_page.identifier
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                if callable(handler):
                    template_context = handler(request, context, template_context)

        return template_context


    def dispatch(self, request, context, preview=False, custom_template_context=None, cache_generator=None):
        """
        Dispatches a content request through the processing pipeline and
        processes various hooks. A RenderResponse is returned, which
        encapsulates the result of this process including meta and input data
        that was used to generate the result. The result content might be empty
        if we are generating content for the cache and the last modification
        timestamp is older than the cached content we already have.
        """
        # on-request hook
        response = self.on_request(request, context)
        if response: return response

        # redirect (append /)?
        if context.is_redirect():
            return HttpResponsePermanentRedirect(context.get_redirect_url())

        # redirect to legacy page
        if context.is_legacy_url():
            response = self.on_legacy_url(request, context)
            if response: return response
            return HttpResponsePermanentRedirect(context.get_redirect_url())

        # accuire template context
        template_context = self.dispatch_template_context(request, context, preview)
        if isinstance(template_context, HttpResponse):
            return template_context

        # identifier-based context
        template_context = self.dispatch_identifier_context(request, context, template_context)
        if isinstance(template_context, HttpResponse):
            return template_context

        # merge with given template context
        if isinstance(custom_template_context, dict):
            custom_template_context.update(template_context)
            template_context = custom_template_context

        # render for cache?
        filepath = context.get_filepath()
        new_mtime = context.updated_on
        if cache_generator is not None:
            render_required, new_mtime = cache_generator.content_changed(
                template_context,
                filepath,
                new_mtime
            )
        else:
            render_required = True

        # render page
        if render_required:
            response = context.render(template_context)
        else:
            response = HttpResponse('')

        # post-response hooks
        user_response = self.on_response(request, response)
        if user_response: response = user_response

        # if we are rendering a 404 page, change response status to 404
        if context.is_404_page():
            response.status_code = 404

        # finally return the response to the client...
        return RenderResponse(
            response,
            context,
            template_context,
            filepath,
            new_mtime,
            render_required
        )


    def _welcome_page(self, request):
        """
        Present cubane welcome page.
        """
        return render(request, 'cubane/backend/welcome.html', {}, content_type='text/html; charset=utf-8')


    def page(self, request, page, preview=False, custom_template_context=None):
        """
        Render given page.
        """
        context = self.get_page_context(request, page=page, view=self)
        result = self.dispatch(request, context, preview, custom_template_context)
        return result.response if isinstance(result, RenderResponse) else result


    def get_template_context(self, request, preview=False, page=None, page_context={}, page_context_class=None, cache_generator=None, additional_context=None):
        """
        Return the default cms context without actually rendering a page.
        """
        # contruct page to render
        if page == None:
            page = get_page_model()()

        # apply context to page
        dict_to_model(page_context, page, exclude_many_to_many=True)

        # render page through pipeline
        if page_context_class:
            context = page_context_class(
                request,
                page=page,
                cache_context=cache_generator.cache_context if cache_generator is not None else None,
                view=self,
                additional_context=additional_context
            )
        else:
            context = self.get_page_context(
                request,
                page=page,
                cache_context=cache_generator.cache_context if cache_generator is not None else None,
                view=self,
                additional_context=additional_context
            )

        template_context = self.dispatch_template_context(request, context, preview)
        return template_context if isinstance(template_context, dict) else {}


    def default_404(self, request):
        """
        Render 404 Page.
        """
        page = self.settings.default_404

        if not page:
            return None
        else:
            return self.page(request, page)


    def render_page(self, page, request=None, additional_context=None, cache_generator=None):
        """
        Render given page and return a render response encapsulating the
        response object and its meta data. If the status code is not 200 (OK),
        an empty string is returned.
        """
        if not page:
            return RenderResponse.not_found()

        # get render context (based on given page)
        context = self.get_page_context(
            request,
            page=page,
            view=self,
            cache_context=cache_generator.cache_context if cache_generator is not None else None,
            additional_context=additional_context,
        )

        # get fake request from page context if we do not have a request
        if not request:
            request = context.request

        # dispatch request to content processing pipeline
        return self.dispatch(
            request,
            context,
            cache_generator=cache_generator
        )


    def render_page_by_slug(self, slug, request=None, preview=False, cache_generator=None):
        """
        Try to match the given full slug with a CMS page and serve the result.
        """
        # get render context (based on slug)
        context = self.get_page_context(
            request,
            slug,
            view=self,
            cache_context=cache_generator.cache_context if cache_generator is not None else None
        )

        # get fake request from page context if we do not have a request
        if not request:
            request = context.request

        # dispatch request to content processing pipeline
        return self.dispatch(
            request,
            context,
            preview,
            cache_generator=cache_generator
        )


    def render_page_by_url(self, filepath, url, args=[], request=None, cache_generator=None):
        """
        Render arbitrary page content by executing the given url endpoint.
        """
        # get view handler
        path = reverse(url, args=args)
        handler, args, kwargs = resolve(path)

        # get request
        if not request:
            request = fake_request(path, self)

        # execute view handler
        request.cache_generator = cache_generator
        request.cache_filepath = filepath
        request.cms = self
        kwargs['request'] = request
        response = handler(*args, **kwargs)

        if hasattr(response, 'cache_template_context') and hasattr(response, 'cache_mtime'):
            # pack response up onto a render response which the
            # cache system requires
            return RenderResponse(
                response,
                None,
                response.cache_template_context,
                filepath,
                response.cache_mtime,
                response.changed if hasattr(response, 'changed') else None
            )
        else:
            return response


    def page_by_slug(self, request, slug=None, preview=False):
        """
        URL handler for rendering an arbitrary url (given slug).
        """
        try:
            render_response = self.render_page_by_slug(slug, request, preview)
            if isinstance(render_response, RenderResponse):
                return render_response.response
            else:
                return render_response
        except HomepageNotDefinedError, e:
            # render welcome page in DEBUG mode if there is no homepage
            if settings.DEBUG and not preview:
                return self._welcome_page(request)
            else:
                raise e


    def render_page_without_dispatch(self, page, request=None, template=None, preview=False):
        """
        Render given page without dispatching the rendering through the entire
        pipeline; no hooks are executed.
        """
        if not page:
            return ''

        # render given page
        context = self.get_page_context(request, page=page, view=self)

        # get fake request from page context if we do not have a request
        if not request:
            request = context.request

        # get template context from context
        template_context = context.get_template_context(preview=preview)

        # render page
        response = context.render(template_context, template)
        if response and response.status_code == 200:
            return response.content
        else:
            return ''


    def render_page_without_disptach(self, page, request=None, template=None, preview=False):
        """
        Deprecated. Use render_page_without_disptach instead.
        (Spelling error disptach should be dispatch)
        """
        return self.render_page_without_dispatch(page, request, template, preview)


    def render_enquiry_template(self, request):
        """
        Render the enquiry page and return its content.
        """
        page = self.settings.enquiry_template
        return self.render_page(page, request).content


    def on_generate_cache(self, cache, verbose=False):
        """
        Virtual: May be overridden by other modules to append to the cache.
        """
        pass


    def get_cache_generator(self):
        """
        Return a new instance of the cache generator.
        """
        cache = Cache()
        return CacheGenerator(self, cache)


    def publish(self, verbose=False):
        """
        Publish cms content.
        """
        generator = self.get_cache_generator()
        return generator.publish(verbose)


    def invalidate(self, verbose=False):
        """
        Invalidates all CMS content from the cache which was generated by
        calling publish().
        """
        generator = self.get_cache_generator()
        return generator.invalidate(verbose)


    def clear_cache(self, verbose=False):
        """
        Clears the CMS cache entirely.
        """
        generator = self.get_cache_generator()
        return generator.clear_cache(verbose)


    def notify_content_changed(self, sender, bases, delete=False):
        """
        Should be called by the backend system whenever any content as part
        of the website's content model has been changed or deleted. The given
        deleted flag should be set to True, if an entity has been deleted.
        """
        # is target entity of any relevance?
        if not issubclass(sender, bases):
            return

        if settings.CACHE_ENABLED:
            # any CMS entity deleted should reflect this within the settings as a
            # seperate timestamp in order to detect content changes due to content
            # deletion...
            if delete:
                settings_model = get_settings_model()
                settings_model.objects.update(entity_deleted_on=datetime.now())

            # invalidate cache
            self.invalidate(verbose=False)

        # invalidate settings cache
        clear_settings_cache()


    @view(csrf_exempt)
    def submit_mailchimp_subscription(self, request):
        """
        Submit mailchimp newsletter subscription.
        """
        from cubane.cms.forms import MailChimpSubscriptionForm
        from cubane.lib.libjson import to_json_response
        from cubane.lib.template import get_template
        from mailsnake import MailSnake

        if not self.settings.mailchimp_api or not self.settings.mailchimp_list_id:
            raise Http404('Missing Mailchimp Api or List ID in settings.')

        if request.method == 'POST':
            form = MailChimpSubscriptionForm(request.POST)
        else:
            form = MailChimpSubscriptionForm()

        msg = None
        msg_type = None

        form.fields['mailchimp_subscription__name'].required = False
        del form.fields['mailchimp_subscription__name']

        if request.method == 'POST' and form.is_valid():
            d = form.cleaned_data

            merge_vars = {}

            ms = MailSnake(self.settings.mailchimp_api)

            try:
                ms.listSubscribe(id=self.settings.mailchimp_list_id, email_address=d['mailchimp_subscription__email'], merge_vars=merge_vars)
                msg = 'Almost finished...We need to confirm your email address. To complete the subscription process, please click the link in the email we just sent you.'
                msg_type = 'success'
            except:
                msg = 'Unfortunately we were unable to process your request. Please try again later...'
                msg_type = 'error'
                send_exception_email(request)

        template = get_template('cubane/cms/newsletter_form.html')
        context = {
            'form': form,
            'msg': msg,
            'msg_type': msg_type
        }
        html = template.render(context, request)

        if request.is_ajax():
            return to_json_response({
                'html': html,
            })
        raise Http404('This url is used for Ajax requests only.')


    def download_media(self, request, filename):
        """
        Download media asset via its public sharing filename (if sharing is enabled).
        """
        # get media
        media = get_object_or_404(Media, share_enabled=True, share_filename=filename)

        # serve file
        f = open(media.original_path, 'rb')
        response = FileResponse(f)
        response['Content-Type'] = 'application/force-download'
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


    def append_to_nav(self, nav, items, before=None, after=None):
        """
        Append a list of navigation items to the given navigation structure of
        the website.
        """
        def scan(nav, before):
            for i, item in enumerate(nav):
                if item.get('slug') == before:
                    return i
            return -1

        if nav is None:
            return

        if not isinstance(items, list):
            items = [items]

        if before is not None:
            index = scan(nav, before)
        elif after is not None:
            index = scan(nav, after) + 1
        else:
            index = len(nav)

        if index > 0:
            for title, url in reversed(items):
                nav.insert(index, {
                    'title': title,
                    'url': url
                })


    def get_sitemap_root_pages(self):
        """
        Return all root pages that are presented on the sitemap (backend).
        """
        page_model = get_page_model()
        return list(page_model.objects.all())


    def has_sitemap_children(self, node):
        """
        Return True, if the given sitemap node has children.
        """
        # child pages may have children
        if isinstance(node, ChildPage):
            model = node.get_entity_model()
            if model:
                return model.objects.filter(page=node).count() > 0

        # pages do not have children
        return False


    def get_sitemap_children(self, node):
        """
        Return a list of child nodes for the given parent node that appear
        logically underneath the parent node, for example child pages for a
        page.
        """
        if isinstance(node, ChildPage):
            model = node.get_entity_model()
            if model:
                return model.objects.filter(page=node)
        return []


    def get_sitemap_item(self, request, node):
        """
        Return sitemap information about the given node.
        """
        url = node.url if hasattr(node, 'url') else None
        edit_url = '%s?pk=%s' % (
            request.backend.get_url_for_model_instance(node, 'edit'),
            node.pk
        )

        return {
            'pk': node.pk,
            'type': node.__class__.__name__,
            'name': node._meta.verbose_name,
            'title': node.title,
            'url': url,
            'edit_url': edit_url,
            'has_children': self.has_sitemap_children(node)
        }


class PageContentView(ModelView):
    """
    Edit CMS page entity.
    """
    template_path = 'cubane/cms/pages/'
    patterns = [
        ('preview/(?P<pk>[^/]+)/', 'preview', {}, 'preview'),
        ('preview/',               'preview', {}, 'preview'),
    ]


    def __init__(self, model, slug=None, *args, **kwargs):
        self.model = model
        self.namespace = 'cubane.cms.%s' % (
            slug if slug is not None else slugify(model._meta.verbose_name_plural)
        )

        # enable hierarchycal pages
        if settings.PAGE_HIERARCHY and model == get_page_model():
            self.folder_model = get_page_model()

        super(PageContentView, self).__init__(*args, **kwargs)


    def _get_objects(self, request):
        return self.model.objects.all()


    def form_initial(self, request, initial, instance, edit):
        """
        Setup gallery images (initial form data)
        """
        initial['_gallery_images'] = load_media_gallery(instance.gallery_images)


    def before_save(self, request, d, instance, edit):
        """
        Set page slot content.
        """
        for slotname in settings.CMS_SLOTNAMES:
            instance.set_slot_content(
                slotname,
                request.POST.get('slot_%s' % slotname, '')
            )


    def after_save(self, request, d, instance, edit):
        """
        Save gallery items (in seq.)
        """
        save_media_gallery(request, instance, d.get('_gallery_images'))


    def after(self, request, handler, response):
        if isinstance(response, dict):
            response['preview_url'] = self.namespace + '.preview'
        return super(PageContentView, self).after(request, handler, response)


    def preview(self, request, pk=None):
        """
        Render CMS entity with given primary key pk in preview mode.
        """
        if pk:
            page = self.get_object_or_404(request, pk)
            if isinstance(page, ChildPage) and (page.page is None or not page.page.has_entity_type):
                # this is a child page without a parent, so render a message
                # that the preview is currently unavailable because of this
                return render(request, 'cubane/cms/child_page_without_parent.html', {
                    'has_parent': page.page is not None,
                    'has_entity_type': page.page.has_entity_type if page.page is not None else False,
                    'page': page,
                    'parent_page': page.page,
                    'entity_model_plural': page.__class__._meta.verbose_name_plural
                })
        else:
            page = self.model()
            if isinstance(page, ChildPage):
                page.page = get_page_model()()
                page.page._entity_model = page.__class__
            page.template = settings.CMS_TEMPLATES[0][0]

        # poke template (if argument was given)
        t = request.GET.get('template', '')
        if t in [x[0] for x in settings.CMS_TEMPLATES]:
            page.template = t

        # render cms content
        return get_cms().page(request, page, preview=True)


    def _get_folders(self, request, parent):
        if not hasattr(self, 'folder_model'):
            raise Http404('Folders have not been activated for this view.')

        folders = self.folder_model.objects.all()

        if parent:
            parent_name = self._get_folder_assignment_name()
            folders = folders.filter(**{parent_name: parent})

        return folders


class ContentView(ModelView):
    """
    Edit CMS entity.
    """
    template_path = 'cubane/cms/pages/'


    def __init__(self, model, *args, **kwargs):
        self.model = model
        self.namespace = 'cubane.cms.%s' % \
            slugify(model._meta.verbose_name_plural)

        super(ContentView, self).__init__(*args, **kwargs)


    def _get_objects(self, request):
        return self.model.objects.all()


class ContentChildPageSection(BackendSection):
    def __init__(self, model, group, slug=None, *args, **kwargs):
        super(ContentChildPageSection, self).__init__(*args, **kwargs)
        self.view = PageContentView(model, slug)
        self.title = model._meta.verbose_name_plural
        self.slug = slug if slug is not None else slugify(self.title)
        self.group = group


class ContentEntitySection(BackendSection):
    def __init__(self, model, group, *args, **kwargs):
        super(ContentEntitySection, self).__init__(*args, **kwargs)
        self.view = ContentView(model)
        self.title = model._meta.verbose_name_plural
        self.slug = slugify(self.title)
        self.group = group


class ContentBackendSection(BackendSection):
    """
    Backend section for editing CMS content, like pages, projects etc...
    """
    title = 'Content'
    priority = 5
    slug = 'content'


    def __init__(self, *args, **kwargs):
        super(ContentBackendSection, self).__init__(*args, **kwargs)

        # append all known cms entities
        cms = get_cms()
        page_models = cms.get_child_page_models()
        entity_models = cms.get_entity_models()

        # sort by name
        page_models = sorted(page_models, key=lambda m: m.__name__)
        entity_models = sorted(entity_models, key=lambda m: m.__name__)

        # create sections
        self.sections = [ContentChildPageSection(model, model.get_backend_section_group()) for model in page_models]
        self.sections.extend([ContentEntitySection(model, model.get_backend_section_group()) for model in entity_models])

        # create section for pages at the beginning of the list
        page_model = get_page_model()
        self.sections.insert(0, ContentChildPageSection(page_model, page_model.get_backend_section_group(), 'pages'))

        # append content from installed apps
        for app_name in settings.INSTALLED_APPS:
            app = import_module(app_name)
            if hasattr(app, 'install_backend_content'):
                app.install_backend_content(self)

        # insert sitemap at the very end
        if settings.CMS_BACKEND_SITEMAP:
            self.sections.append(SitemapSection())


class SettingsView(ModelView):
    """
    Edit website-wide general settings, such as the name of the website and
    what page the honmepage is.
    """
    namespace = 'cubane.cms.settings'
    template_path = 'cubane/cms/settings/'
    single_instance = True


    def _get_object(self, request):
        try:
            return self.model.objects.all()[0]
        except (self.model.DoesNotExist, IndexError) as e:
            return None


    def __init__(self, *args, **kwargs):
        self.model = get_settings_model()
        super(SettingsView, self).__init__(*args, **kwargs)


    def before_save(self, request, d, instance, edit):
        # update is_homepage for the page that is the homepage,
        # setting the property to false for all other pages...
        if instance != None and instance.homepage != None:
            hp = instance.homepage
            get_page_model().objects.exclude(pk=hp.pk).update(is_homepage=False)
            hp.is_homepage = True
            hp.save()


class SettingsBackendSection(BackendSection):
    """
    Backend section for editing website-wide settings.
    """
    title = 'Settings'
    slug = 'settings'
    view = SettingsView()
