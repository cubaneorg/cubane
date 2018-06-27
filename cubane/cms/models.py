# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import slugify
from django.db.models.signals import post_save, post_delete
from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import ForeignKey
from django.db.models.query_utils import DeferredAttribute
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from cubane.cms import get_page_model, get_page_model_name
from cubane.cms.cache import Cache
from cubane.directory import DirectoryOrder
from cubane.models import DateTimeBase
from cubane.models.fields import IntegerRangeField, MultiSelectField
from cubane.models.mixin import SEOMixin, LegacyUrlMixin
from cubane.models.mixin import AddressMixin, GeoLocationWithZoomMixin
from cubane.media.models import Media
from cubane.lib.url import normalise_slug, url_join
from cubane.lib.url import get_absolute_url
from cubane.lib.default import default_choice
from cubane.lib.excerpt import excerpt_from_text, excerpt_from_html
from cubane.lib.app import get_models
from cubane.lib.utf8 import ENCODING_CHOICES, DEFAULT_ENCOPDING
from cubane.lib.model import get_listing_option
from datetime import datetime
import cPickle as pickle
import base64
import os
import re


# legacy
from cubane.media.models import MediaGallery


class ChildPageWithoutParentError(Exception):
    pass


class EditableHtmlField(models.TextField):
    """
    Represents editable HTML content and renders as a TinyMCE editor form field.
    """
    def formfield(self, **kwargs):
        from cubane.cms.forms import EditableHtmlField as EditableHtmlFormField
        from cubane.cms.forms import EditableHtmlWidget

        defaults = {
            'max_length': self.max_length,
            'form_class': EditableHtmlFormField,
            'widget': EditableHtmlWidget
        }
        defaults.update(kwargs)

        return super(EditableHtmlField, self).formfield(**defaults)


class DirectorySettingsMixin(models.Model):
    class Meta:
        abstract = True


    order_mode = models.IntegerField(
        verbose_name='Order',
        choices=DirectoryOrder.DEFAULT_ORDER_CHOICES,
        default=DirectoryOrder.ORDER_RANDOM,
    )


class EditableContentMixin(models.Model):
    """
    Base class for editable content.
    """
    class Meta:
        abstract = True


    _data = models.TextField(
        verbose_name='Content',
        db_column='data',
        null=True,
        blank=True,
        help_text='Edit the content of your webpage.'
    )


    def set_data(self, data):
        """
        Encode given python content object as a string.
        """
        self._data = base64.encodestring(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))


    def get_data(self):
        """
        Return the binary encoded content data as a python object (cached)
        """
        if self._data:
            return pickle.loads(base64.decodestring(self._data))
        else:
            return {}


    def set_slot_content(self, slotname, content):
        """
        Sets the content of the slot with the given name for this page.
        """
        if slotname not in settings.CMS_SLOTNAMES:
            return

        data = self.get_data()

        # enforce dict
        if not data or not isinstance(data, dict):
            data = dict()

        # enforce unicode string for inputs
        slotname = unicode(slotname)
        content = unicode(content)

        # set slot data
        data[slotname] = content

        # save back
        self.set_data(data)


    def get_slot_content(self, slotname):
        """
        Return the html content of the slot with the given name for this page.
        """
        if slotname not in settings.CMS_SLOTNAMES:
            return ''

        data = self.get_data()
        if not data or not isinstance(data, dict):
            return ''
        else:
            return data.get(slotname, '')


    def get_combined_slot_content(self, slotnames):
        """
        Return the html content of the given list of slots combined.
        """
        content = [self.get_slot_content(slotname) for slotname in slotnames]
        content = filter(lambda x: x, content)
        return ' '.join(content)


    def slotnames_with_content(self):
        """
        Return a list of slot names that have content.
        """
        data = self.get_data()

        if not data or not isinstance(data, dict):
            return []
        else:
            slotnames = data.keys()
            return [slotname for slotname in slotnames if data.get(slotname, '').strip() != '']


    def content_by_slot(self, images=None):
        """
        Return a dictionary with all slots and its content for all slots that
        do have content.
        """
        from cubane.media.templatetags.media_tags import render_image
        from cubane.cms.templatetags.cms_tags import rewrite_images

        data = self.get_data()
        if not data or not isinstance(data, dict):
            return {}
        else:
            slotnames = data.keys()
            result = {}
            for slotname in slotnames:
                content = data.get(slotname, '').strip()

                if images:
                    content = rewrite_images(content, images, render_image)

                result[slotname] = content

            return result


class ExcerptMixin(models.Model):
    """
    Provides the ability to store a short excerpt. If the excerpt is empty,
    an excerpt is generated based on the main (html) content.
    """
    class Meta:
        abstract = True


    _excerpt = models.TextField(
        verbose_name='Excerpt',
        db_column='excerpt',
        null=True,
        blank=True,
        help_text='Provide a brief summary for this entity which is usually ' +
                  'presented alongside an image for this entity.'
    )


    @property
    def excerpt(self):
        """
        Return the excerpt for this item (which might be generated).
        """
        return self.get_excerpt()


    @property
    def has_excerpt(self):
        """
        Return True, if there is a custom excerpt available; otherwise return
        False, even if an automatically generated excerpt is available.
        """
        return self._excerpt is not None and self._excerpt != ''


    def get_excerpt(self, length=settings.CMS_EXCERPT_LENGTH):
        if self._excerpt:
            return excerpt_from_text(self._excerpt, length)
        else:
            return self.generate_excerpt(length)


    def generate_excerpt(self, length):
        if hasattr(settings, 'CMS_NO_AUTO_EXCERPT'):
            if settings.CMS_NO_AUTO_EXCERPT:
                return ''

        if hasattr(self, 'get_slot_content'):
            return excerpt_from_html(self.get_slot_content('content'), length)
        elif hasattr(self, 'description'):
            return excerpt_from_html(self.description, length)
        else:
            return ''


class NavigationMixin(models.Model):
    """
    Provides helper methods and properties for managing cms content, such as
    pages to appear in navigation elements, like menues.
    """
    class Meta:
        abstract = True


    _nav = models.CharField(
        verbose_name='Navigation',
        db_column='nav',
        max_length=255,
        null=True,
        blank=True
    )


    def get_nav(self):
        """
        Return list of navigation sections this page should appear in.
        """
        if self._nav == None:
            return []
        else:
            return self._nav.split(',')


    def set_nav(self, nav):
        """
        Set the list of navigation sections this page should appear in.
        """
        if len(nav) == 0:
            self._nav = None
        else:
            self._nav = ','.join([n.strip() for n in nav])


    nav = property(get_nav, set_nav)


class PageBase(
    DateTimeBase,
    EditableContentMixin,
    SEOMixin,
    LegacyUrlMixin,
    ExcerptMixin
):
    """
    Base class for a default CMS page (with timestamps and with SEO data).
    Derive your own CMS entities from this base class.
    """
    class Meta:
        abstract            = True
        ordering            = ['seq', 'title']
        verbose_name        = 'Page'
        verbose_name_plural = 'Pages'

    class Listing:
        columns = ['title', '_meta_description', 'disabled']
        grid_view = True
        sortable = True
        filter_by = [
            'title',
            'slug',
            'template',
            'disabled'
        ]
        data_export = True
        data_ignore = ['_data']


    def save(self, *args, **kwargs):
        """
        Automatically generate slug based on title if no slug has been provided.
        """
        # slug changed?
        if not self.slug:
            self.slug = slugify(self.title)

        # actually save model
        super(PageBase, self).save(*args, **kwargs)


    title = models.CharField(
        verbose_name='Title',
        max_length=255,
        db_index=True,
        help_text='The title of the page that is displayed on the website.'
    )

    slug = models.SlugField(
        verbose_name='Slug',
        db_index=True,
        max_length=120,
        help_text='The name of the html file for the page as part of the ' +
                  'page''s address.'
    )

    template = models.CharField(
        verbose_name='Template',
        choices=settings.CMS_TEMPLATES,
        default=default_choice(settings.CMS_TEMPLATES),
        max_length=255,
        help_text='The name of the template that is used to render this page.'
    )

    image = models.ForeignKey(
        Media,
        verbose_name='Primary Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Select an image that is used to represent this entity ' +
                  'within a list of entities.'
    )

    gallery_images = GenericRelation(
        MediaGallery,
        content_type_field='content_type',
        object_id_field='target_id'
    )

    disabled = models.BooleanField(
        verbose_name='Disabled',
        db_index=True,
        default=False,
        help_text='A disabled web page is not visible to visitors nor to ' +
                  'search engines. A disabled web page will also not show ' +
                  'up in the navigation section(s) of your website.'
    )

    sitemap = models.BooleanField(
        verbose_name='Sitemap Listed',
        default=True,
        help_text='This page is listed within the sitemap.xml file for this website.'
    )

    seq = models.IntegerField(
        verbose_name='Sequence',
        db_index=True,
        default=0,
        editable=False,
        help_text='The sequence number determines the order in which pages ' +
                  'are presented, for example within the navigation ' +
                  'section(s) of your website.'
    )

    nav_updated_on = models.DateTimeField(
        verbose_name='Navigation-relevant data updated timestamp',
        db_index=True,
        null=True,
        blank=False,
        editable=False
    )


    @classmethod
    def get_backend_section_group(cls):
        """
        Return the group name for the section within the backend system or None.
        """
        return get_listing_option(cls, 'group')


    @classmethod
    def get_form(cls):
        from cubane.cms.forms import PageForm
        return PageForm


    @classmethod
    def filter_visibility(cls, objects, visibility_filter_args={}):
        """
        Filter given queryset by visibility. The system will use this method
        whenever content is loaded from the database to check if this content is
        suppose to be visible and will give derived class implementation an
        opportunity to implement custom logic here.
        """
        return objects.filter(disabled=False)


    def is_visible(self):
        """
        Return True, if this page is visible; otherwise return False.
        """
        return not self.disabled


    @property
    def html_title(self):
        """
        Return the page title, which is marked as a safe string, because it
        may contain markup, such as &nbsp;.
        """
        if self.title == None:
            return ''
        else:
            return mark_safe(self.title.replace('_', '&nbsp;'))


    @property
    def text_title(self):
        """
        Return the page title as plain text without any markup and underscore
        characters replaced with spaces.
        """
        if self.title == None:
            return ''
        else:
            return self.title.replace('_', ' ')


    @property
    def url(self):
        return self._get_absolute_url()


    @property
    def url_path(self):
        return self._get_absolute_url(path_only=True)


    @property
    def gallery(self):
        """
        Return a (cached) list of gallery images that are assigned to this
        page or child page.
        """
        if not hasattr(self, '_cached_gallery'):
            media = self.gallery_images.select_related('media').order_by('seq')
            self._cached_gallery = list([m.media for m in media])

        return self._cached_gallery


    @property
    def page_path(self):
        """
        Returns a list of all pages with in a hierarchy starting with root element.
        """
        items = []
        p = self
        while p is not None:
            items.insert(0, p)
            p = p.parent
        return items


    def get_filepath(self):
        """
        Return path to cache file for this page.
        """
        return os.path.join(self.slug, 'index.html')


    def get_slug(self):
        """
        Return the slug for this page, which might be empty for the homepage.
        """
        return self.slug


    def get_fullslug(self):
        """
        Return the full slug for this page.
        """
        if self.slug:
            return '/%s/' % self.slug
        else:
            return '/'


    def get_absolute_url(self):
        """
        Return absolute url.
        """
        return self._get_absolute_url()


    def _get_absolute_url(self, path_only=False):
        """
        Return absolute url or url path.
        """
        slug = normalise_slug(self.slug)
        if settings.APPEND_SLASH: slug = slug + '/'
        return get_absolute_url('cubane.cms.page', [slug], path_only=path_only)


    def to_dict(self, extras=None):
        d = {
            'id': self.pk,
            'title': self.title,
            'slug': self.slug,
            'url': self.url,
            'url_path': self.url_path
        }

        if extras != None:
            d.update(extras)

        return d


    def __unicode__(self):
        return u'%s' % self.title


class PageAbstract(PageBase, NavigationMixin):
    """
    Base class for default CMS pages with navigation data. Child pages would
    derive from PageBase directly.
    """
    class Meta:
        abstract            = True
        ordering            = ['seq', 'title']
        verbose_name        = 'Page'
        verbose_name_plural = 'Pages'

    class Listing:
        columns = [
            'title',
            '_meta_description',
            'get_entity_model_display_name|Listing Type',
            'get_template_display|Template',
            '/sitemap|Sitemap',
            '/disabled'
        ]
        edit_columns = [
            'title',
            '_meta_description',
            'entity_type|Listing Type',
            'template',
            'sitemap|Sitemap',
            'disabled',
        ]
        edit_view = True
        grid_view = True
        sortable = True
        filter_by = [
            ':Title and Slug',
            'title',
            'slug',

            ':Status',
            'disabled',
            'sitemap',

            ':Legacy URL',
            'legacy_url',

            ':Navigation',
            'navigation',
            'navigation_title',
            'identifier',

            ':Meta Information',
            '_meta_title',
            '_meta_description',
            '_meta_keywords',

            ':Template and Entity Type',
            'template',
            'entity_type',
        ]


    entity_type = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Child Pages (type)',
    )

    navigation_title = models.CharField(
        verbose_name='Navigation Title',
        max_length=255,
        null=True,
        blank=True,
        help_text='Override the regular title that is used within the navigation of the website.'
    )

    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        verbose_name='Parent Page',
        on_delete=models.SET_NULL,
        help_text='Select the parent page for this page for the purpose of presenting multi-level navigation.'
    )

    identifier = models.CharField(
        verbose_name='Unique Identifier',
        max_length=255,
        db_index=True,
        null=True,
        blank=True,
        help_text='The unique identifier allows us to refer to this page ' +
                  'independently of its title or slug.'
    )

    is_homepage = models.BooleanField(
        verbose_name='Is Homepage',
        default=False,
        editable=False
    )


    def __init__(self, *args, **kwargs):
        super(PageAbstract, self).__init__(*args, **kwargs)
        self._entity_model = None


    @property
    def nav_title(self):
        """
        Return the navigation title if a navigation title is defined; otherwise
        return the regular page title.
        """
        return self.navigation_title if self.navigation_title else self.title


    def get_entity_model(self):
        """
        Return the entity model that this page manages.
        """
        if self._entity_model == None:
            self._entity_model = False
            for model in get_models():
                if model.__name__ == self.entity_type:
                    self._entity_model = model
                    break

        if self._entity_model:
            return self._entity_model
        else:
            return None


    def get_entity_model_display_name(self):
        """
        Return the name of the entity model for display purposes (plural).
        """
        entity_model = self.get_entity_model()
        if entity_model:
            return entity_model._meta.verbose_name_plural
        else:
            return None


    def get_filepath(self):
        """
        Return path to cache file for this page.
        """
        if self.is_homepage:
            return 'index.html'
        else:
            return os.path.join(self.slug, 'index.html')


    def get_slug(self):
        """
        Return the slug for this page, which might be empty for the homepage.
        """
        if self.is_homepage:
            return ''
        else:
            return self.slug


    def get_fullslug(self):
        """
        Return the full slug for this page.
        """
        if self.is_homepage or not self.slug:
            return ''
        else:
            return '/%s/' % self.slug


    def _get_absolute_url(self, path_only=False):
        """
        Return absolute url or url path.
        """
        if self.is_homepage:
            return get_absolute_url('cubane.cms.page', [''], path_only=path_only)
        else:
            slug = normalise_slug(self.slug)
            if settings.APPEND_SLASH: slug = slug + '/'
            return get_absolute_url('cubane.cms.page', [slug], path_only=path_only)


    @property
    def has_entity_type(self):
        """
        Return True, if this page has an entity type assigned.
        """
        return self.entity_type is not None and self.entity_type != ''


class Page(PageAbstract):
    """
    Regular default CMS page.
    """
    pass


class ChildPageManager(models.Manager):
    def get_queryset(self):
        """
        Fetching child pages should always select the parent page with it,
        so that we can effectively generate absolute url from it.
        """
        return super(ChildPageManager, self).get_queryset().select_related('image', 'page')


class ChildPage(PageBase):
    """
    Base class for CMS child pages that are derived from Page, so they have
    most of the properties that a normal page has including the ability to
    edit rich html content.
    """
    class Meta:
        abstract = True


    class Listing:
        columns = ['title', '_meta_description', 'page|Listed On', 'disabled']
        edit_view = True
        grid_view = True
        sortable = True
        filter_by = [
            'title',
            'slug',
            'template',
            'disabled',
            'page',
        ]


    page = models.ForeignKey(
        get_page_model_name(),
        verbose_name='Belongs to Page',
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        help_text='Select the page that should be used to present this entity.'
    )


    @classmethod
    def get_form(self):
        from cubane.cms.forms import ChildPageForm
        return ChildPageForm


    def get_filepath(self):
        """
        Return path to cache file for this child page.
        """
        page = self.page
        if not page:
            raise ChildPageWithoutParentError()

        return os.path.join(self.page.get_slug(), self.slug, 'index.html')


    def get_slug(self):
        """
        Return the slug for this child page.
        """
        return self.slug


    def get_fullslug(self):
        """
        Return the full slug for this child page based on the slug of the parent
        page and the child page, e.g. /page/child-page. Raise ValueError, if
        the parent page happend to be undefined, which might happend whenever
        the parent page is deleted but child pages remain, causing the parent
        page relationship to be detroyed.
        """
        page = self.page
        if not page:
            raise ChildPageWithoutParentError()

        if self.slug:
            slug = '%s%s/' % (page.get_fullslug(), self.slug)
            if not slug.startswith('/'):
                slug = '/' + slug
            return slug
        else:
            return page.get_fullslug()


    @property
    def identifier(self):
        return None


    @property
    def nav_title(self):
        """
        Return the navigation title. For child pages, this is always the regular
        title since there is no way to change the navigation title.
        """
        return self.title


    @property
    def page_path(self):
        """
        Returns a list of all pages with in a hierarchy starting with root element.
        """
        if self.page is not None:
            return self.page.page_path + [self]
        else:
            return [self]


    objects = ChildPageManager()


    def _get_absolute_url(self, path_only=False):
        """
        Return absolute url or url path.
        """
        parent = self.page
        if parent:
            if parent.is_homepage:
                parent_slug = '/'
            else:
                parent_slug = parent.slug

            slug = normalise_slug(url_join(parent_slug, self.slug))
            if settings.APPEND_SLASH: slug = slug + '/'
            return get_absolute_url('cubane.cms.page', [slug], path_only=path_only)
        else:
            return None


class Post(ChildPage):
    """
    The name ChildPage is confusing in relation to page hierarchies, which is
    why we are introducing a separate name 'Post' for this concept all
    together. It also makes clear that a page may have many posts.
    """
    class Meta:
        abstract = True


class EntityManager(models.Manager):
    def get_queryset(self):
        """
        Fetching entities should always select related images.
        """
        qs = super(EntityManager, self).get_queryset()

        try:
            field = self.model._meta.get_field('image')
            if isinstance(field, ForeignKey):
                qs = qs.select_related('image')
        except FieldDoesNotExist:
            pass

        return qs


class Entity(DateTimeBase):
    """
    Base class for CMS entities that do not have any build-in properties.
    """
    class Meta:
        abstract = True

    seq = models.IntegerField(
        verbose_name='Sequence',
        editable=False,
        db_index=True,
        default=0,
        help_text='The sequence number determines the order in which entities ' +
                  'are presented, for example within the navigation ' +
                  'section(s) of your website.'
    )


    objects = EntityManager()


    @classmethod
    def get_backend_section_group(cls):
        """
        Return the group name for the section within the backend system or None.
        """
        return get_listing_option(cls, 'group')


class DefaultPagesSettingsMixin(models.Model):
    class Meta:
        abstract = True


    homepage = models.ForeignKey(
        get_page_model_name(),
        verbose_name='Homepage',
        related_name='+',
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        help_text='Select the page that should be presented as the ' +
                  'homepage for your website.'
    )

    default_404 = models.ForeignKey(
        get_page_model_name(),
        verbose_name='404 Page',
        related_name='+',
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        help_text='Select the page that should be present in the case that ' +
                  'no other page could be found. Usually the 404 page gives ' +
                  'some useful links for the visitor to progress to.'
    )

    contact_page = models.ForeignKey(
        get_page_model_name(),
        verbose_name='Contact Page',
        related_name='+',
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        help_text='Select the page that should present the contact us form ' +
                  'that allows visitors to send an enquiry message to you.'
    )

    enquiry_template = models.ForeignKey(
        get_page_model_name(),
        verbose_name='Enquiry Email Template',
        related_name='+',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Select the page that is used to send the enquiry email ' + \
                  'to customers who are using the enquiry form on the website.'
    )


    def get_default_pages_pks(self):
        """
        Return a list of ids of all default pages in settings.
        """
        return filter(lambda pk: pk, [
            self.homepage_id,
            self.contact_page_id,
            self.default_404_id,
            self.enquiry_template_id
        ])


class SocialMediaSettingsMixin(models.Model):
    class Meta:
        abstract = True


    skype = models.CharField(
        verbose_name='Skype',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the name of your Skype account.'
    )

    facebook = models.CharField(
        verbose_name='Facebook',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the url of your Facebook page.'
    )

    twitter = models.CharField(
        verbose_name='Twitter Link',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the url of your Twitter page.'
    )

    google_plus = models.CharField(
        verbose_name='Google Plus',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the url of your Google Plus page.'
    )

    youtube = models.CharField(
        verbose_name='Youtube',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the url of your Youtube page.'
    )

    instagram = models.CharField(
        verbose_name='Instagram',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the url of your Instagram page.'
    )

    linkedin = models.CharField(
        verbose_name='LinkedIn',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the url of your LinkedIn page.'
    )

    blogger = models.CharField(
        verbose_name='Blogger',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the url of your Blogger page.'
    )

    pinterest = models.CharField(
        verbose_name='Pinterest',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the url of your Pinterest page.'
    )


    @property
    def social_links(self):
        return [
            ('skype', self.skype),
            ('facebook', self.facebook),
            ('twitter', self.twitter),
            ('google_plus', self.google_plus),
            ('youtube', self.youtube),
            ('instagram', self.instagram),
            ('linkedin', self.linkedin),
            ('blogger', self.blogger),
            ('pinterest', self.pinterest)
        ]


    @property
    def social_media(self):
        """
        Return a list of all social media.
        """
        return [instance for _, instance in self.social_links]


    @property
    def has_social_media(self):
        """
        Return true, if at least one social media has been configured.
        """
        return any(self.social_media)


class ContactSocialMediaSettingsMixin(SocialMediaSettingsMixin):
    class Meta:
        abstract = True


    email = models.EmailField(
        verbose_name='Email',
        max_length=255,
        null=True,
        blank=True,
        help_text='Your email address'
    )

    phone = models.CharField(
        verbose_name='Phone',
        max_length=255,
        null=True,
        blank=True,
        help_text='Your primary phone number of your business.'
    )

    twitter_name = models.CharField(
        verbose_name='Twitter Name',
        max_length=255,
        null=True,
        blank=True,
        help_text='This is the name of your Twitter account ( for example @InnerShed ).'
    )

    twitter_widget_id = models.CharField(
        verbose_name='Twitter Widget Id',
        max_length=255,
        null=True,
        blank=True,
        help_text='Copy and paste the data-widget-id of your Twitter widget.' +
                  'This is generated when you create a widget with your Twitter account.'
    )

    mailchimp_api = models.CharField(
        verbose_name='MailChimp API',
        max_length=255,
        null=True,
        blank=True,
        help_text='Enter the API key for your MailChimp account.'
    )

    mailchimp_list_id = models.CharField(
        verbose_name='MailChimp List ID',
        max_length=255,
        null=True,
        blank=True,
        help_text='Enter the MailChimp subscription list identifier for your MailChimp account.'
    )

    enquiry_email = models.EmailField(
        verbose_name='Enquiry Email',
        max_length=255,
        null=True,
        blank=False,
        help_text='Enquiries via the contact us form are send to this email ' +
                  'address. '
    )

    enquiry_from = models.EmailField(
        verbose_name='From Email',
        max_length=255,
        null=True,
        blank=False,
        help_text='Whenever the website is sending email to you or directly ' +
                  'to your visitors (for example by using the contact us ' +
                  'form), this email address is used as the ' +
                  'from address.'
    )

    enquiry_reply = models.EmailField(
        verbose_name='Reply Email',
        max_length=255,
        null=True,
        blank=False,
        help_text='This email address is used as the reply address.'
    )


    @property
    def mailchimp_enabled(self):
        """
        Return True, if mailchimp is configured.
        """
        return self.mailchimp_api and self.mailchimp_list_id


    @property
    def phone_spaceless(self):
        """
        Return the phone number without spaces.
        """
        if self.phone:
            return re.sub(r'\s', '', self.phone)
        else:
            return ''


class PaginationSettingsMixin(models.Model):
    class Meta:
        abstract = True


    paging_enabled = models.BooleanField(
        verbose_name='Enable Pagination',
        default=True,
        help_text='Presents things on your site (for example News, Events, Projects etc) in pages.'
    )

    paging_child_pages = MultiSelectField(
        verbose_name='Pagination for',
        null=True,
        blank=True,
        help_text='Enable pagination on a per-section basis.'
    )

    page_size = IntegerRangeField(
        verbose_name='Page size',
        default=10,
        min_value=2,
        max_value=None,
        blank=True,
        help_text='Amount of elements presented per page.'
    )

    max_page_size = IntegerRangeField(
        verbose_name='Max. page size',
        default=100,
        min_value=2,
        max_value=None,
        blank=True,
        help_text="Maximum amount of elements presented per page for " +
                  "'View all'."
    )


    def paging_enabled_for(self, child_page_model):
        """
        Return True, if pagination is enabled specificaly for the given
        child page model type.
        """
        if not self.paging_enabled:
            return False

        if self.paging_child_pages:
            return child_page_model._meta.db_table in self.paging_child_pages
        else:
            return False


class IdentificationSettingsMixin(models.Model):
    class Meta:
        abstract = True


    analytics_key = models.CharField(
        verbose_name='Google Analytics Key',
        max_length=64,
        null=True,
        blank=True,
        help_text='Enter the google analytics key for your website.'
    )

    analytics_hash_location = models.BooleanField(
        verbose_name='Enable Hash Location',
        default=False,
        help_text='Enable hash location tracking for google analytics.'
    )

    webmaster_key = models.CharField(
        verbose_name='Google Webmaster Tools',
        max_length=64,
        null=True,
        blank=True,
        help_text='Enter the google webmaster tools site identification key.'
    )

    globalsign_key = models.CharField(
        verbose_name='GlobalSign Key',
        max_length=64,
        null=True,
        blank=True,
        help_text='Enter the GlobalSign domain identification key ' + \
                  '(SSL certificate).'
    )


class OpeningTimesSettingsMixin(models.Model):
    class Meta:
        abstract = True


    opening_times_enabled = models.BooleanField(
        verbose_name='Enable Opening Times',
        default=False
    )

    monday_start = models.TimeField(
        verbose_name='Monday Start Time',
        null=True,
        blank=True,
        help_text='Enter the opening time or leave empty to display nothing (Format: HH:MM).'
    )

    monday_close = models.TimeField(
        verbose_name='Monday Close Time',
        null=True,
        blank=True,
        help_text='Enter the closing time or leave empty to display nothing (Format: HH:MM).'
    )

    tuesday_start = models.TimeField(
        verbose_name='Tuesday Start Time',
        null=True,
        blank=True,
        help_text='Enter the opening time or leave empty to display nothing (Format: HH:MM).'
    )

    tuesday_close = models.TimeField(
        verbose_name='Tuesday Close Time',
        null=True,
        blank=True,
        help_text='Enter the closing time or leave empty to display nothing (Format: HH:MM).'
    )

    wednesday_start = models.TimeField(
        verbose_name='Wednesday Start Time',
        null=True,
        blank=True,
        help_text='Enter the opening time or leave empty to display nothing (Format: HH:MM).'
    )

    wednesday_close = models.TimeField(
        verbose_name='Wednesday Close Time',
        null=True,
        blank=True,
        help_text='Enter the closing time or leave empty to display nothing (Format: HH:MM).'
    )

    thursday_start = models.TimeField(
        verbose_name='Thursday Start Time',
        null=True,
        blank=True,
        help_text='Enter the opening time or leave empty to display nothing (Format: HH:MM).'
    )

    thursday_close = models.TimeField(
        verbose_name='Thursday Close Time',
        null=True,
        blank=True,
        help_text='Enter the closing time or leave empty to display nothing (Format: HH:MM).'
    )

    friday_start = models.TimeField(
        verbose_name='Friday Start Time',
        null=True,
        blank=True,
        help_text='Enter the opening time or leave empty to display nothing (Format: HH:MM).'
    )

    friday_close = models.TimeField(
        verbose_name='Friday Close Time',
        null=True,
        blank=True,
        help_text='Enter the closing time or leave empty to display nothing (Format: HH:MM).'
    )

    saturday_start = models.TimeField(
        verbose_name='Saturday Start Time',
        null=True,
        blank=True,
        help_text='Enter the opening time or leave empty to display nothing (Format: HH:MM).'
    )

    saturday_close = models.TimeField(
        verbose_name='Saturday Close Time',
        null=True,
        blank=True,
        help_text='Enter the closing time or leave empty to display nothing (Format: HH:MM).'
    )

    sunday_start = models.TimeField(
        verbose_name='Sunday Start Time',
        null=True,
        blank=True,
        help_text='Enter the opening time or leave empty to display nothing (Format: HH:MM).'
    )

    sunday_close = models.TimeField(
        verbose_name='Sunday close Time',
        null=True,
        blank=True,
        help_text='Enter the closing time or leave empty to display nothing (Format: HH:MM).'
    )


    def set_opening_times(self, weekdays, start, close):
        """
        Set the given opening and closing time for the given week days.
        """
        if start: self.set_opening_time(weekdays, 'start', start)
        if close: self.set_opening_time(weekdays, 'close', close)


    def set_opening_time(self, day, bound, value):
        """
        Set the opening time for the given day to the given value. Bound is
        start or close and defines the opening times boundary to be set.
        """
        if isinstance(day, list):
            for d in day:
                self.set_opening_time(d, bound, value)
        else:
            if day not in self.week_days and day not in self.weekend_days:
                return False

            if bound not in ['start', 'close']:
                return False

            if isinstance(value, basestring):
                value = datetime.strptime(value, '%H:%M')

            if not isinstance(value, datetime):
                return False;

            setattr(self, '%s_%s' % (day, bound), value)
            return True


    @property
    def week_days(self):
        """
        Return a list of names for all weekdays from Mon. to Sun.
        """
        return [
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'friday',

        ]

    @property
    def weekend_days(self):
        return [
            'saturday',
            'sunday'
        ]


    @property
    def full_week_days(self):
        return self.week_days + self.weekend_days


    @property
    def opening_times_weekdays(self):
        """
        Return weekday opening times (Mon.-Fri.).
        """
        return [
            ('monday', self.monday_start, self.monday_close),
            ('tuesday', self.tuesday_start, self.tuesday_close),
            ('wednesday', self.wednesday_start, self.wednesday_close),
            ('thursday', self.thursday_start, self.thursday_close),
            ('friday', self.friday_start, self.friday_close),
        ]


    @property
    def opening_times(self):
        """
        Return weekday and weekend opening times (Mon.-Sun.).
        """
        return self.opening_times_weekdays + [
            ('saturday', self.saturday_start, self.saturday_close),
            ('sunday', self.sunday_start, self.sunday_close),
        ]


    @property
    def same_opening_times_for_weekdays(self):
        """
        Return True, if all opening hours during the week are the same.
        """
        starts = set([start for _, start, close in self.opening_times_weekdays])
        close = set([close for _, start, close in self.opening_times_weekdays])
        return len(starts) == 1 and len(close) == 1


class SettingsBase(
    DateTimeBase,
    AddressMixin,
    GeoLocationWithZoomMixin,
    DefaultPagesSettingsMixin,
    ContactSocialMediaSettingsMixin,
    PaginationSettingsMixin,
    IdentificationSettingsMixin,
    OpeningTimesSettingsMixin,
    DirectorySettingsMixin
):
    """
    Application-wide settings base class.
    """
    class Meta:
        abstract            = True
        verbose_name        = 'Settings'
        verbose_name_plural = 'Settings'


    name = models.CharField(
        verbose_name='Company Name',
        max_length=60,
        null=True,
        blank=False,
        help_text='The name of the website. This is used to promote the name ' +
                  'of your company to google and other search engines and is ' +
                  'attached to the title of each page.'
    )

    meta_name = models.CharField(
        verbose_name='Meta Title Name',
        max_length=60,
        null=True,
        blank=True,
        help_text='The name of the website as it will typically appear ' +
                  'at the end of the meta title for each page.'
    )

    entity_deleted_on = models.DateTimeField(
        verbose_name='Entity Deleted on',
        null=True,
        blank=True,
        db_index=True,
        editable=False
    )

    default_encoding = models.CharField(
        verbose_name='Default Encoding',
        max_length=64,
        choices=ENCODING_CHOICES,
        default=DEFAULT_ENCOPDING,
        null=True,
        blank=False,
        help_text='Default Encoding when importing/exporting data.'
    )

    notification_text = models.TextField(
        verbose_name='Notification',
        null=True,
        blank=True,
        help_text='Enter text that is presented on every page as a notification text.'
    )

    notification_enabled = models.BooleanField(
        verbose_name='Notification Enabled',
        default=False,
        help_text='Tick to enable the notification as above to be presented on every page.'
    )


    @property
    def google_map_location_url(self):
        """
        Return url to be used for getting location link to google maps.
        """
        if self.lat and self.lng:
            return 'http://www.google.com/maps/?q=%s,%s' % (self.lat, self.lng)
        else:
            return 'http://www.google.com/maps/?q=%s' % ', '.join(self.short_address_fields)


    @classmethod
    def get_form(cls):
        from cubane.cms.forms import SettingsForm
        return SettingsForm


    def __unicode__(self):
        return self.name if self.name is not None else '<cubane.cms.models.SettingsBase>'


def get_child_page_models():
    """
    Return a list of all models that are derived from ChildPage.
    """
    _models = []
    for model in get_models():
        if issubclass(model, ChildPage):
            _models.append(model)
    return _models


def get_child_page_model_choices():
    """
    Return choices for all models that are derived from ChildPage.
    """
    _models = get_child_page_models()

    names = [m._meta.db_table for m in _models]
    labels = [m._meta.verbose_name_plural for m in _models]

    return zip(names, labels)


#
# Any CMS entity deleted should reflect this within the settings as a seperate
# timestamp in order to detect content changes due to content deletion.
#
@receiver(post_delete)
def update_entity_deleted_on(sender, **kwargs):
    if 'cubane.cms' in settings.INSTALLED_APPS:
        from cubane.cms.views import get_cms
        cms = get_cms()
        cms.notify_content_changed(sender, (PageBase, Entity, SettingsBase, DateTimeBase), delete=True)


#
# Invalidate cache when saving or deleting cms content
#
@receiver(post_save)
def invalidate_cache_on_content_changed(sender, **kwargs):
    if 'cubane.cms' in settings.INSTALLED_APPS:
        from cubane.cms.views import get_cms
        cms = get_cms()
        cms.notify_content_changed(sender, (PageBase, Entity, SettingsBase, DateTimeBase))