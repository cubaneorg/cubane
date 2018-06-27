# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db.models import Q
from cubane.lib.module import register_class_extensions
from cubane.cms import get_page_model
from cubane.cms.models import PageBase


class CMSNavigationBuilder(object):
    @classmethod
    def register_extension(cls, *args):
        """
        Register a new extension(s) for the CMS navigation builder class.
        """
        return register_class_extensions('ExtendedCMSNavigationBuilder', cls, args)


    def __init__(self, cms, page_context, active_page=None, current_page_or_child_page=None, cache_context=None):
        """
        Create a new navigation builder for the given page context.
        """
        self.cms = cms
        self.page_context = page_context
        self.active_page = active_page
        self.active_page_id = self.active_page.id if self.active_page else None
        self.current_page_or_child_page = current_page_or_child_page
        self.cache_context = cache_context
        self.child_page_cache = {}
        self.pages = self.cache_context.cached('PAGES', self.get_pages)


    def get_objects(self, objects):
        """
        Return a queryset that returns all pages on which bases navigation items
        are constructed.
        """
        return objects


    def get_pages(self):
        """
        Return a list of navigate-able content pages
        """
        page_model = get_page_model()
        related_fields = []
        if hasattr(settings, 'CMS_NAVIGATION_RELATED_FIELDS'):
            related_fields = related_fields + settings.CMS_NAVIGATION_RELATED_FIELDS
        related_fields = filter(
            lambda field: hasattr(page_model, field),
            related_fields
        )
        pages = list(
            page_model.filter_visibility(
                self.get_objects(
                    page_model.objects.select_related(*related_fields).filter(
                        Q(_nav__isnull=False) |       # appears in at least one
                                                      # navigation section
                        Q(identifier__isnull=False),  # OR has an identifier
                        disabled=False                # not disabled
                    ).order_by(
                        'seq', 'title'
                    )
                )
            )
        )

        return pages


    def get_title(self, page):
        """
        Return the navigation title for the given page.
        """
        return page.navigation_title if hasattr(page, 'navigation_title') and page.navigation_title else page.title


    def has_active_child(self, items):
        """
        Return True, if any child or sub-child of the given navigation items
        is active.
        """
        for item in items:
            if item.get('active'):
                return True
            if self.has_active_child(item.get('children')):
                return True
        return False


    def has_active_child_page(self, page, children):
        """
        Return True, if the current page is a child page of the navigation item
        page or any children thereof.
        """
        if not hasattr(self.current_page_or_child_page, 'page_id'):
            return False

        if self.current_is_child_page_of(page):
            return True

        if children:
            for child in children:
                if self.current_is_child_page_of(child):
                    return True

        return False


    def current_is_child_page_of(self, page):
        """
        Return True, if the current page is a child page of the given page.
        """
        pk = page.get('id') if isinstance(page, dict) else getattr(page, 'pk', None)
        return self.current_page_or_child_page.page_id == pk


    def child_page_model_excluded_from_nav(self, child_page_model):
        """
        Return True, if the given child page model is excluded from navigation.
        """
        if not hasattr(child_page_model, 'exclude_from_navigation'):
            return False
        else:
            return child_page_model.exclude_from_navigation


    def get_nav_child_pages(self, page, nav_name=None):
        """
        Return a list of navigation items for all child pages of the given page,
        if this feature is enabled via CMS_NAVIGATION_INCLUDE_CHILD_PAGES.
        """
        # empty list if feature is not enabled
        if not settings.CMS_NAVIGATION_INCLUDE_CHILD_PAGES:
            return []

        # empty list if the given page is not a page that has child pages
        if not isinstance(page, get_page_model()):
            return []

        # valid child page model that is not excluded for navigation
        child_page_model = page.get_entity_model()
        if not child_page_model or self.child_page_model_excluded_from_nav(child_page_model):
            return []

        # get cached list of child pages for the given page
        key = unicode(page.pk)
        if key not in self.child_page_cache:
            self.child_page_cache[key] = []

            # get child pages for this page
            child_pages = child_page_model.filter_visibility(
                child_page_model.objects.filter(page=page).exclude(disabled=True).order_by('seq')
            )

            self.child_page_cache[key] = list([self.get_nav_item(p, nav_name) for p in child_pages])

        # receive list of child pages
        return self.child_page_cache.get(key, [])


    def get_url_getter(self, page):
        """
        Return a getter method for receiving the URL for the given page.
        """
        def _get_url():
            return '/' if self.page_context.page_is_homepage(page) else page.get_absolute_url()
        return _get_url


    def get_nav_item(self, page, nav_name=None):
        """
        Return a navigation item for the given page.
        """
        # get children
        children = self.get_nav_children(page)
        nav_children = self.get_nav_children(page, nav_name)

        # related fields
        item_fields = {}
        if hasattr(settings, 'CMS_NAVIGATION_RELATED_FIELDS'):
            for field in settings.CMS_NAVIGATION_RELATED_FIELDS:
                if hasattr(page, field):
                    item_fields[field] = getattr(page, field)

        # child pages / posts
        child_pages = self.get_nav_child_pages(page, nav_name)

        item_fields.update({
            'id': page.id,
            'identifier': page.identifier if hasattr(page, 'identifier') else None,
            'title': self.get_title(page),
            'slug': page.slug,
            'page_title': page.title,
            'nav_title': page.navigation_title if hasattr(page, 'navigation_title') else page.title,
            'url': self.get_url_getter(page),
            'active': (type(page) == type(self.current_page_or_child_page) and page.id == self.active_page_id) or (self.current_page_or_child_page != None and page.id == self.current_page_or_child_page.id and page.__class__ == self.current_page_or_child_page.__class__),
            'active_child': self.has_active_child(children),
            'active_child_page': self.has_active_child_page(page, children),
            'excerpt': page.excerpt,
            'entity_type': page.entity_type if hasattr(page, 'entity_type') else None,
            'children': children,
            'nav_children': nav_children,
            'child_pages': child_pages,   # legacy
            'posts': child_pages,
            'nav_image': page.nav_image if hasattr(page, 'nav_image_id') else None,
            'updated_on': getattr(page, 'nav_updated_on', None)
        })

        return item_fields


    def get_nav_children(self, parent, nav_name=None):
        """
        Return the child pages of the given parent page based on the given
        list of all pages (cached).
        """
        # get children
        if isinstance(parent, PageBase) and settings.PAGE_HIERARCHY:
            children = filter(lambda p: isinstance(p, PageBase) and p.parent_id == parent.id, self.pages)

            if nav_name:
                children = filter(lambda p: nav_name in p.nav, children)
        else:
            children = []

        return [self.get_nav_item(p, nav_name) for p in children]


    def is_root_page(self, page):
        """
        Return True, if the given page is a root page (has no parent pages).
        """
        return page.parent_id == None


    def get_navigation(self):
        """
        Return the website-wide navigation objects which contains a list of
        all pages that are at least in one navigation bar and/or are navigable
        because a page defines a unique identifier.
        """
        # construict navigation structure
        _nav = {}
        _pages = {}
        _active_nav = None
        for p in self.pages:
            # add to list of navigatable pages if there is an identifier
            if hasattr(p, 'identifier') and p.identifier:
                _pages[p.identifier] = self.get_nav_item(p)

            # skip if enquiry template
            if self.page_context.page_is_enquiry_template(p):
                continue

            # skip if not root page
            if not self.is_root_page(p):
                continue

            # skip if no navigation is defined
            if not p._nav:
                continue

            # attach to navigation structure
            for name in p.nav:
                if name not in _nav: _nav[name] = []

                item = self.get_nav_item(p, name)
                _nav[name].append(item)

                # return active navigation item seperately
                if not _active_nav and (item.get('active') or item.get('active_child')):
                    _active_nav = item

        return (_nav, _active_nav, _pages)