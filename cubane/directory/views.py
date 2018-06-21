# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404
from django.template.defaultfilters import slugify
from django.http import HttpResponsePermanentRedirect
from cubane.backend.views import BackendSection
from cubane.directory import DirectoryOrder
from cubane.directory.models import DirectoryContentMixin
from cubane.directory.models import DirectoryContentAggregator
from cubane.directory.models import DirectoryContentAndAggregator
from cubane.directory.models import DirectoryPageAggregator
from cubane.directory.models import DirectoryContentBase
from cubane.directory.models import DirectoryContentEntity
from cubane.directory.models import DirectoryEntity
from cubane.directory.models import DirectoryCategory
from cubane.directory.models import DirectoryTag
from cubane.cms.views import PageContentView, ContentView, get_cms
from cubane.cms.views import CMSGenericSitemap
from cubane.cms.models import PageBase
from cubane.views import ModelView
from cubane.lib.app import get_models
from cubane.lib.args import *
from cubane.lib.model import get_listing_option
from datetime import datetime
import datetime as dt
import itertools
import random


def get_directory_content_backend_sections(backend_section):
    """
    Return a list of all backend sections that are related to directory content.
    """
    # append all known directory content entities and categories
    sections = []
    content_models = []
    for model in get_models():
        if issubclass(model, DirectoryContentBase) or issubclass(model, DirectoryContentEntity):
            content_models.append(model)

    # create sections
    sections = []
    for title, attr, value, model in backend_section.get_model_sections(content_models):
        slug = slugify(title)
        _title = get_listing_option(model, 'title')
        if _title is not None:
            title = _title

        if attr and value and hasattr(model, 'get_backend_section_title'):
            title = model.get_backend_section_title(value)

        sections.append(DirectoryContentSubSection(title, slug, attr, value, model, model.get_backend_section_group()))

    return sections


class DirectoryBackendSection(BackendSection):
    """
    Backend section for editing directory content, like links, stories etc.
    """
    title = 'Directory'
    slug = 'directory'


    def __init__(self, *args, **kwargs):
        super(DirectoryBackendSection, self).__init__(*args, **kwargs)

        # tags
        self.sections = [DirectoryTagsSection()]

        # categories
        category_models = []
        for model in get_models():
            if issubclass(model, DirectoryCategory):
                category_models.append(model)
        category_models.sort(key=lambda m: m.__name__)
        self.sections.extend([DirectoryCategorySection(m) for m in category_models])

        # directory entities
        content_models = []
        for model in get_models():
            if issubclass(model, DirectoryEntity):
                content_models.append(model)
        for title, attr, value, model in self.get_model_sections(content_models):
            slug = slugify(title)
            _title = get_listing_option(model, 'title')
            if _title is not None:
                title = _title
            self.sections.append(DirectoryContentSubSection(title, slug, attr, value, model, model.get_backend_section_group()))

        # sort sections by title
        self.sections.sort(key=lambda s: s.title)


class DirectoryTagsSection(BackendSection):
    """
    Backend sub-section for tags.
    """
    def __init__(self, *args, **kwargs):
        super(DirectoryTagsSection, self).__init__(*args, **kwargs)
        self.view = DirectoryTagsView()
        self.title = 'Tags'
        self.slug = 'tags'


class DirectoryTagsView(ModelView):
    template_path = 'cubane/directory/directorytags/'
    model = DirectoryTag

    def _get_objects(self, request):
        return self.model.objects.all()


class DirectoryCategorySection(BackendSection):
    """
    Backend sub-section for tags.
    """
    def __init__(self, model, *args, **kwargs):
        super(DirectoryCategorySection, self).__init__(*args, **kwargs)
        self.title = model._meta.verbose_name_plural
        self.slug = slugify(self.title)
        self.view = DirectoryCategoryView(self.slug, model)


class DirectoryCategoryView(ModelView):
    template_path = 'cubane/directory/categories/'


    def __init__(self, slug, model, *args, **kwargs):
        self.model = model
        self.namespace = 'cubane.directory.%s' % slug
        super(DirectoryCategoryView, self).__init__(*args, **kwargs)


    def _get_objects(self, request):
        return self.model.objects.all()



class DirectoryContentSubSection(BackendSection):
    """
    Backend sub-section for directory content entities.
    """
    def __init__(self, title, slug, attr, value, model, group, *args, **kwargs):
        super(DirectoryContentSubSection, self).__init__(*args, **kwargs)

        if issubclass(model, DirectoryContentBase):
            self.view = DirectoryContentView(title, attr, value, model)
        else:
            self.view = ContentView(model)

        self.title = title
        self.slug = slug
        self.group = group


class DirectoryContentView(PageContentView):
    def __init__(self, title, attr, value, model, *args, **kwargs):
        super(DirectoryContentView, self).__init__(model, *args, **kwargs)
        self.namespace = 'cubane.directory.%s' % slugify(title)
        self.model_attr = attr
        self.model_attr_value = value


    def _get_objects(self, request):
        if self.model_attr and self.model_attr_value:
            return self.model.objects.filter(**{self.model_attr: self.model_attr_value})
        else:
            return self.model.objects.all()


    def preview(self, request, pk=None):
        """
        Render directory content page with given primary key pk in preview mode.
        """
        if pk:
            page = self.get_object_or_404(request, pk)
        else:
            page = self.model()
            page.template = settings.CMS_TEMPLATES[0][0]

        self._configure_model_backend_section(page)

        # poke template (if argument was given)
        t = request.GET.get('template', '')
        if t in [x[0] for x in settings.CMS_TEMPLATES]:
            page.template = t

        return get_cms().page(request, page, preview=True)


class CMSDirectoryContentSitemap(CMSGenericSitemap):
    """
    Sitemap generator for directory content.
    """
    def items(self):
        objects = self._model.objects.exclude(disabled=True)

        if issubclass(self._model, PageBase):
            objects = self._model.filter_visibility(objects)

        return objects


class CMSExtensions(object):
    """
    Extension methods for the CMS class in order to work with directory content.
    """
    def get_directory_tags(self):
        """
        Return a list of directory tags (cached).
        """
        if not hasattr(self, '_directory_tags_cached'):
            self._directory_tags_cached = list(DirectoryTag.objects.all())
        return self._directory_tags_cached


    def get_directory_tag_choices(self):
        """
        Return directory tags as choices (cached).
        """
        return [(tag.title, tag.title) for tag in self.get_directory_tags()]


    def get_directory_category_models(self):
        """
        Return a list of models representing directory categories.
        """
        models = []
        for model in get_models():
            if issubclass(model, DirectoryCategory):
                models.append(model)
        return models


    def get_directory_models(self):
        """
        Return a list of aggregate-able directory content asset models.
        """
        models = []
        for model in get_models():
            if issubclass(model, DirectoryContentBase):
                models.append(model)
        return models


    def get_entity_models(self):
        """
        Override: Only return CMS-related child pages and not directory-related
        content entities (which happen to derive from Entity).
        """
        entity_models = super(CMSExtensions, self).get_entity_models()
        return filter(
            lambda m: not issubclass(m, DirectoryContentEntity),
            entity_models
        )


    def get_sitemaps(self):
        """
        Override: Add directory-specific content to sitemap.
        """
        _sitemaps = super(CMSExtensions, self).get_sitemaps()

        # directory content
        for model in get_models():
            if issubclass(model, DirectoryContentBase):
                _sitemaps[slugify(model._meta.verbose_name)] = CMSDirectoryContentSitemap(self, model)

        return _sitemaps


    def on_generate_cache(self, generator, verbose=False):
        """
        Override: Add directory content to cache system.
        """
        super(CMSExtensions, self).on_generate_cache(generator, verbose)

        for model in self.get_directory_models():
            if generator.quit: break

            pages = model.objects.filter(disabled=False)

            if issubclass(model, PageBase):
                pages = model.filter_visibility(pages)

            for page in pages:
                if generator.quit: break
                generator.process_page(page=page, verbose=verbose)


    def on_object_links(self, links):
        """
        Override: Support for link-able directory content.
        """
        for model in self.get_directory_models():
            pages = model.objects.filter(disabled=False)

            if issubclass(model, PageBase):
                pages = model.filter_visibility(pages)

            if hasattr(model, 'get_backend_sections'):
                attr_name, backend_sections = model.get_backend_sections()
                for backend_section_id, section_title in backend_sections:
                    links.add(model, pages.filter(**{attr_name: backend_section_id}), section_title)
            else:
                links.add(model, pages)


    def get_aggregated_pages(self, include_tags, exclude_tags=[], order=DirectoryOrder.ORDER_DEFAULT, max_items=None, navigation=False, visibility_filter_args={}):
        """
        Return a list of all aggregated pages for the given include tags and exclude tags
        ordered by the given order. If no order is given, the system-wide order applies
        (settings). The number of result records may be limited to the number given.
        If the navigation argument is True, then directory content entities are NOT
        included in the result set.
        """
        # enfore list of list of tags for include tags
        include_tags = list_of_list(include_tags)
        exclude_tags = list_of(exclude_tags)

        # create cache
        if not hasattr(self, '_agg_cache'):
            self._agg_cache = {}

        # collect all aggregated content
        pages = []
        el_tags = set()
        for model in get_models():
            if issubclass(model, DirectoryContentBase) or (not navigation and issubclass(model, DirectoryContentEntity)):
                # create cache key
                cache_id = '%s-%s-%d-%s' % (
                    '-'.join(itertools.chain(*include_tags)),
                    '-'.join(exclude_tags),
                    order,
                    model
                )

                # deliver partial result from cache?
                if cache_id in self._agg_cache:
                    agg_pages = self._agg_cache[cache_id]
                else:
                    agg_pages = self._agg_cache[cache_id] = model.objects.filter_by_tags(include_tags, exclude_tags, visibility_filter_args)

                # if the page is an aggregator as well as directory content,
                # then collect cascading tags to eliminate content
                if issubclass(model, DirectoryContentAndAggregator):
                    for p in agg_pages:
                        el_tags |= p.get_cascading_tags()

                pages.extend(agg_pages)

        # eliminate all pages that match one of the cascading tags found...
        if len(el_tags) > 0:
            pages = filter(lambda p: not p.matches_tags(el_tags), pages)

        # default order from settings?
        if order == DirectoryOrder.ORDER_DEFAULT:
            order = self.settings.order_mode

        # order pages
        if order == DirectoryOrder.ORDER_RANDOM:
            # seed random number generator based on the week and year, so that
            # we get a different random order every week but the order stays the
            # same during the week...
            now = datetime.now()
            random.seed('%s/%s' % (now.year, now.isocalendar()[1]))

            # generate and inject a random seq...
            for p in pages:
                p._random_seq = random.randint(0, 65535)

            # sort by random seq
            pages.sort(key=lambda x: x._random_seq)
        elif order == DirectoryOrder.ORDER_SEQ:
            pages.sort(key=lambda x: x.seq)
        elif order == DirectoryOrder.ORDER_TITLE:
            pages.sort(key=lambda x: x.title if hasattr(x, 'title') else False)
        elif order == DirectoryOrder.ORDER_DATE:
            pages.sort(key=lambda x: x.created_on, reverse=True)
        elif order == DirectoryOrder.ORDER_CUSTOM_DATE:
            pages.sort(key=lambda x: (x.custom_date or dt.datetime(1970, 1, 1)), reverse=False)

        # sort by priority
        pages.sort(key=lambda x: not x.priority)

        # move items with top priority to the top of the listing
        pages.sort(key=lambda x: not x.top_priority)

        # restrict the maximum number of aggregated items
        if max_items != None:
            pages = pages[:max_items]

        return pages


    def get_aggregated_pages_for_page(self, page, visibility_filter_args={}):
        """
        Return a list of all aggregated pages for the given page.
        """
        items = self.get_aggregated_pages(
            page.get_include_tags(),
            page.exclude_tags,
            page.order_mode,
            page.max_items,
            visibility_filter_args=visibility_filter_args
        )

        # remove page from list as it doesn't make sense to display itself
        [items.remove(item) for item in items if item.id == page.id and type(item) == type(page)]

        return items


    def has_sitemap_children(self, node):
        """
        Override: Return True, if the given sitemap node has children.
        """
        if isinstance(node, (DirectoryPageAggregator, DirectoryContentAndAggregator, DirectoryCategory)):
            return len(self.get_aggregated_pages_for_page(node)) > 0
        else:
            return super(CMSExtensions, self).has_sitemap_children(node)


    def get_sitemap_children(self, node):
        """
        Override: Return a list of child nodes for the given parent node that appear
        logically underneath the parent node, for example child pages for a
        page.
        """
        if isinstance(node, (DirectoryPageAggregator, DirectoryContentAndAggregator, DirectoryCategory)):
            return self.get_aggregated_pages_for_page(node)
        else:
            return super(CMSExtensions, self).get_sitemap_children(node)


    def get_sitemap_item(self, request, node):
        """
        Extended: Return sitemap information about the given node.
        """
        item = super(CMSExtensions, self).get_sitemap_item(request, node)

        if isinstance(node, DirectoryContentMixin):
            item.update({
                'tags': node.get_tags_display()
            })

        if isinstance(node, DirectoryContentAggregator):
            item.update({
                'include_tags': node.get_include_tags_1_display()
            })

        return item


def content(request, pk, slug, model=None, attr_name=None, backend_section=None):
    """
    Request handler for directory content assets.
    """
    # get page by id only, ignoring slug
    q = {
        'pk': pk,
        'disabled': False
    }

    # backend section?
    if attr_name and backend_section:
        q[attr_name] = backend_section

    # get that page
    try:
        page = model.filter_visibility(model.objects.filter(**q))[0]
    except IndexError:
        page = None

    # raise 404 if we cannot find a page
    if page == None:
        raise Http404('Unknown primary key or page is disabled.')

    # if we have a page, check if the slug is matching, if not redirect
    # to the correct url (temporary redirect)
    if page.slug != slug:
        return HttpResponsePermanentRedirect(page.get_fullslug())

    # render page or 404
    return get_cms().page(request, page)
