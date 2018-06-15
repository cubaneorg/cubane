# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db.models import Q
from django.template.defaultfilters import slugify
from cubane.backend.views import BackendSection
from cubane.lib.module import get_class_from_string
from cubane.views import ModelView
from cubane.ishop.models import FeaturedItemBase
from cubane.lib.app import get_models


def get_featured_item_model():
    """
    Return the page model as configured by settings.CMS_PAGE_MODEL.
    """
    if hasattr(settings, 'SHOP_FEATURED_ITEM_MODEL'):
        return get_class_from_string(settings.SHOP_FEATURED_ITEM_MODEL)
    else:
        raise ValueError(
            "cubane.ishop requires the settings variable 'SHOP_FEATURED_ITEM_MODEL' " +
            "to be set to the full path of the model class that represents " +
            "the featured items for the shop, for example myproject.models.FeaturedItem"
        )


def get_featured_items(related=[]):
    if not isinstance(related, list):
        related = [related]

    sections = {}
    _related = ['product', 'product__image', 'category', 'category__image', 'image', 'page'] + related
    featured_items = list(get_featured_item_model().objects.select_related(*_related).filter(
        Q(enabled=True),
        Q(product__isnull=False) | Q(category__isnull=False) | Q(page__isnull=False)
    ).order_by('seq'))

    for section_name, title in settings.FEATURED_SET_CHOICES:
        sections[section_name] = filter(lambda item: item.featured_set_section == section_name, featured_items)

    return sections


class FeaturedView(ModelView):
    """
    Edit featured item.
    """
    template_path = 'cubane/ishop/merchant/featured/'


    def __init__(self, section_name, *args, **kwargs):
        self.model = get_featured_item_model()
        self.section_name = section_name
        self.namespace = 'cubane.ishop.%s' % \
            slugify(section_name)

        super(FeaturedView, self).__init__(*args, **kwargs)


    def _get_objects(self, request):
        return self.model.objects.filter(featured_set_section=self.section_name)


    def before_save(self, request, cleaned_data, instance, edit):
        """
        Called before the given model instance is saved.
        """
        instance.featured_set_section = self.section_name


class FeaturedItemBackendSection(BackendSection):
    title = 'Featured'
    slug = 'featured'

    def __init__(self, *args, **kwargs):
        super(FeaturedItemBackendSection, self).__init__(*args, **kwargs)
        self.sections = []

        for section_name, title in settings.FEATURED_SET_CHOICES:
            slug = slugify(section_name)
            self.sections.append(FeaturedItemSubSection(title, slug, section_name))

        # sort sections by title
        self.sections.sort(key=lambda s: s.title)


class FeaturedItemSubSection(BackendSection):
    """
    Backend sub-section for featured items.
    """
    def __init__(self, title, slug, section_name, *args, **kwargs):
        super(FeaturedItemSubSection, self).__init__(*args, **kwargs)

        self.view = FeaturedView(section_name)
        self.title = title
        self.slug = slug
