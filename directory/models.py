# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from cubane.models import DateTimeBase
from cubane.models.fields import TagsField
from cubane.cms.models import PageBase, Entity
from cubane.cms.cache import Cache
from cubane.directory import DirectoryOrder
from cubane.lib.url import normalise_slug, make_absolute_url
from cubane.lib.app import get_models
from cubane.lib.model import get_listing_option
import os


class DirectoryTag(models.Model):
    """
    Tag.
    """
    class Meta:
        ordering            = ['title']
        verbose_name        = 'Tag'
        verbose_name_plural = 'Tags'

    class Listing:
        columns = ['title']
        edit_view = True


    title = models.CharField(
        verbose_name='Tag Name',
        max_length=32,
        db_index=True,
        unique=True,
        help_text='The unique name of the tag (lowercase, A-Z or 0-9, no spaces or punctation characters).'
    )


    @classmethod
    def get_form(cls):
        from cubane.directory.forms import DirectoryTagForm
        return DirectoryTagForm


    def delete(self):
        super(DirectoryTag, self).delete()
        for model in get_models():
            self.remove_tags_from_model(model, self.title)


    def save(self, *args, **kwargs):
        try:
            old_title = DirectoryTag.objects.get(pk=self.pk).title
        except:
            old_title = None

        for model in get_models():
            self.update_tags_for_model(model, old_title, self.title)

        super(DirectoryTag, self).save(*args, **kwargs)


    def update_tags_for_model(self, model, old_tagname, new_tagname):
        tag_fields = self.get_tag_fields_for_model(model)
        instances = self.get_model_instances_with_tagname(model, tag_fields, old_tagname)
        if instances:
            for instance in instances:
                self.update_tag_for_instance_fields(instance, tag_fields, old_tagname, new_tagname)


    def remove_tags_from_model(self, model, tagname):
        tag_fields = self.get_tag_fields_for_model(model)
        instances = self.get_model_instances_with_tagname(model, tag_fields, tagname)
        if instances:
            for instance in instances:
                self.remove_tag_from_instance_fields(instance, tag_fields, tagname)


    def get_tag_fields_for_model(self, model):
        tag_fields = []
        for field in model._meta.fields:
            if type(field) == TagsField:
                # is TagsField
                tag_fields.append(unicode(field.name))
        return tag_fields


    def get_model_instances_with_tagname(self, model, tag_fields, tagname):
        queryset = None
        if len(tag_fields) > 0:
            q = Q()
            for field in tag_fields:
                query = field + '__icontains'
                q |= Q(**{query: '#%s#' % tagname})

            queryset = model.objects.filter(q)

        return queryset


    def remove_tag_from_instance_fields(self, instance, tag_fields, tagname):
        for field in tag_fields:
            value = getattr(instance, field)
            if tagname in value:
                value.remove(tagname)
                instance.save()


    def update_tag_for_instance_fields(self, instance, tag_fields, old_tagname, new_tagname):
        for field in tag_fields:
            value = getattr(instance, field)
            if old_tagname in value:
                value.remove(old_tagname)
                value.append(new_tagname)
                setattr(instance, field, value)
                instance.save()


    def __unicode__(self):
        return self.title


class DirectoryContentAggregator(models.Model):
    """
    Mixin for providing aggregation tags to pages and child pages.
    """
    class Meta:
        abstract = True


    include_tags_1 = TagsField(
        verbose_name='Inclusion Tags 1',
        max_length=1024,
        null=True,
        blank=True
    )

    include_tags_2 = TagsField(
        verbose_name='Inclusion Tags 2',
        max_length=1024,
        null=True,
        blank=True
    )

    include_tags_3 = TagsField(
        verbose_name='Inclusion Tags 3',
        max_length=1024,
        null=True,
        blank=True
    )

    include_tags_4 = TagsField(
        verbose_name='Inclusion Tags 4',
        max_length=1024,
        null=True,
        blank=True
    )

    include_tags_5 = TagsField(
        verbose_name='Inclusion Tags 5',
        max_length=1024,
        null=True,
        blank=True
    )

    include_tags_6 = TagsField(
        verbose_name='Inclusion Tags 6',
        max_length=1024,
        null=True,
        blank=True
    )

    exclude_tags = TagsField(
        verbose_name='Exclusion Tags',
        max_length=1024,
        null=True,
        blank=True
    )

    order_mode = models.IntegerField(
        verbose_name='Order',
        choices=DirectoryOrder.ORDER_CHOICES,
        default=DirectoryOrder.ORDER_DEFAULT,
    )

    max_items = models.IntegerField(
        verbose_name='Max. Items',
        null=True,
        blank=True,
        help_text='Optional: Restrict the maximum number of items that are aggregated. Leave empty for no restriction.'
    )


    def get_include_tags(self):
        """
        Return a list of all inclusion tags.
        """
        return filter(lambda x: x, [
            self.include_tags_1,
            self.include_tags_2,
            self.include_tags_3,
            self.include_tags_4,
            self.include_tags_5,
            self.include_tags_6
        ])


    def get_include_tag_list(self):
        """
        Return a simplified list of inclusion tags.
        """
        result = []
        for tag_set in self.get_include_tags():
            for tag in tag_set:
                if tag not in result:
                    result.append(tag)
        return result


class DirectoryPageAggregator(DirectoryContentAggregator):
    """
    Mixin for providing aggregation tags to pages and child pages as well as
    aggregatable navigation.
    """
    class Meta:
        abstract = True


    nav_include_tags = TagsField(
        verbose_name='Navigation Tags',
        max_length=1024,
        null=True,
        blank=True
    )

    nav_exclude_tags = TagsField(
        verbose_name='Exclusion Tags',
        max_length=1024,
        null=True,
        blank=True
    )

    nav_order_mode = models.IntegerField(
        verbose_name='Navigation Order',
        choices=DirectoryOrder.ORDER_CHOICES,
        default=DirectoryOrder.ORDER_DEFAULT,
    )


class DirectoryCategory(DateTimeBase, DirectoryContentAggregator):
    """
    Base class for directory categories that aggregate content based on
    tags but itself does not have a presentable page.
    """
    class Meta:
        abstract            = True
        ordering            = ['seq']
        verbose_name        = 'Directory Category'
        verbose_name_plural = 'Directory Categories'

    class Listing:
        columns = ['title', 'get_include_tags_1_display|Tags', 'get_exclude_tags_display|Exclude Tags', 'disabled']
        grid_view = False
        sortable = True
        filter_by = [
            'title',
            'include_tags_1',
            'include_tags_2',
            'include_tags_3',
            'include_tags_4',
            'include_tags_5',
            'include_tags_6',
            'exclude_tags',
            'disabled'
        ]


    title = models.CharField(
        verbose_name='Title',
        max_length=255,
        db_index=True
    )

    disabled = models.BooleanField(
        verbose_name='Disabled',
        db_index=True,
        default=False,
        help_text='A disabled category is not visible to visitors.'
    )

    seq = models.IntegerField(
        verbose_name='Sequence',
        db_index=True,
        default=0,
        editable=False,
        help_text='The sequence number determines the order in which categories ' +
                  'are presented, for example on a map page.'
    )


    def __unicode__(self):
        return self.title


class DirectoryContentBaseManager(models.Manager):
    """
    Directory content manager for receiving content aggregated by inclusion and
    exclusion tags.
    """
    def filter_by_tags(self, include_tags, exclude_tags=[], visibility_filter_args={}):
        """
        Filter directory content for this model based on the given include and exclude tags.
        """
        # constuct inclusion filters
        include_q = Q()
        tags = {}
        for include_tag_set in include_tags:
            sub_q = Q()
            for tag in include_tag_set:
                sub_q &= Q(tags__icontains='#%s#' % tag) | Q(ptags__icontains='#%s#' % tag)
                tags[tag] = True
            if len(sub_q) > 0:
                include_q |= sub_q

        # constuct exclusion filter
        exclude_q = Q()
        for tag in exclude_tags:
            exclude_q |= Q(tags__icontains='#%s#' % tag) | Q(ptags__icontains='#%s#' % tag)
            tags.pop(tag, None)

        # receive list of aggregated content
        if len(include_q) > 0:
            qs = self.get_queryset()
            if hasattr(qs.model, 'image'):
                qs = qs.select_related('image')
            q = qs.exclude(disabled=True).filter(include_q)
            if len(exclude_q) > 0:
                q = q.exclude(exclude_q)

            # filter visibility
            if issubclass(self.model, PageBase):
                q = self.model.filter_visibility(q, visibility_filter_args)

            # materialise
            items = list(q)
        else:
            items = []

        # determine priority. an item is priority if any priority tag matches
        # any tag we are looking for
        for item in items:
            item.priority = False
            for ptag in item.ptags:
                if ptag in tags:
                    item.priority = True
                    break

        return items


    def filter_by_tags_from_page(self, page):
        """
        Filter directory content for this model based on include and exclude
        tags provided by the given page.
        """
        return self.filter_by_tags(page.get_include_tags(), page.exclude_tags)


class DirectoryContentMixin(models.Model):
    """
    Mixin for directory content.
    """
    class Meta:
        abstract = True

    # navigation title
    _nav_title = models.CharField(
        verbose_name='Short Title',
        db_column='nav_title',
        max_length=20,
        db_index=True,
        null=True,
        blank=True,
        help_text='Title used to present this page when listed (max. 20 characters).'
    )

    # standard tags
    tags = TagsField(
        verbose_name='Tags',
        db_index=True,
        max_length=1024,
        null=True,
        blank=True,
        help_text='Standard Tags (no priority)'
    )

    # priority tags
    ptags = TagsField(
        verbose_name='Priority Tags',
        db_index=True,
        max_length=1024,
        null=True,
        blank=True,
        help_text='Priority Tags. Only assign priority tags if this content is important to be presented at the top.'
    )

    # absolute priority
    top_priority = models.BooleanField(
        verbose_name='Top Priority',
        default=False,
        help_text='If ticked, this item will most likely appear at the top of the listing.'
    )


    @classmethod
    def get_directory_content_type_slugs(cls):
        """
        Return a list of all directory content types.
        """
        if hasattr(cls, 'get_backend_sections'):
            attr_name, sections = cls.get_backend_sections()
            return [(attr_name, backend_section, slugify(name)) for backend_section, name in sections]
        else:
            return [(None, None, slugify(cls._meta.verbose_name_plural))]


    def get_directory_content_type_slug(self):
        """
        Return the slug prefix for this type of directory content.
        """
        if hasattr(self, 'get_backend_sections'):
            attr_name, _ = self.get_backend_sections()
            getter = getattr(self, 'get_%s_display' % attr_name)
            return slugify(getter())
        else:
            return slugify(self._meta.verbose_name_plural)


    @property
    def unique_pk(self):
        """
        Return a unique primary key that is unique among multiple models.
        """
        if not hasattr(self, '_unique_pk'):
            self._unique_pk = '%d-%s' % (self.pk, self.get_directory_content_type_slug())
        return self._unique_pk


    @property
    def tags_set(self):
        """
        Return all tags of this page as a set of tags (including default and priority tags).
        """
        _tags = self.tags
        if _tags is None: _tags = []

        _ptags = self.ptags
        if _ptags is None: _ptags = []

        return set(_tags) | set(_ptags)


    @property
    def nav_title(self):
        """
        Return the navigation title for this directory content page or - if
        no navigation title is defined - the regular page title.
        """
        if self._nav_title:
            return mark_safe(self._nav_title.replace('_', '&nbsp;'))
        else:
            return self.html_title


    @property
    def breakable_nav_title(self):
        """
        Return the navigation title for this directory content page or - if
        no navigation title is defined - the regular page title.
        """
        if self._nav_title:
            return mark_safe(self._nav_title.replace('_', ' '))
        else:
            return self.text_title


    @property
    def has_nav_title(self):
        """
        Return True if there is a nav title else False.
        """
        return True if self._nav_title else False


    def matches_tags(self, tags):
        """
        Return True, if this page matches a subset of the given set of tags.
        """
        if len(tags) > 0:
            return len(tags.intersection(self.tags_set)) > 0
        else:
            return False


    def matches_inclusion_tags(self, include_tags, exclude_tags=None):
        """
        Return True, if this page matches one of the given set of include tags
        while not matching any of the given exclusion tags.
        """
        # make sure that we do not match any exclusion tags
        if exclude_tags:
            for tag in exclude_tags:
                if tag in self.tags or tag in self.ptags:
                    return False

        # match inclusion tags
        matched = False
        for include_tag_set in include_tags:
            for tag in include_tag_set:
                if tag in self.tags or tag in self.ptags:
                    return True

        # we did not match
        return False


class DirectoryContentBase(PageBase, DirectoryContentMixin):
    """
    Directory Content Page (Base). Provides content for the directory alongside
    with a list of tags the content is classified as.
    """
    class Meta:
        abstract            = True
        ordering            = ['seq']
        verbose_name        = 'Directory Content'
        verbose_name_plural = 'Directory Content'

    class Listing:
        columns = ['_title', '_meta_description', 'get_tags_display|Tags', 'get_ptags_display|Priority Tags']
        grid_view = True
        filter_by = [
            '_title',
            'slug',
            'tags',
            'ptags',
            'disabled'
        ]


    custom_date = models.DateTimeField(
        verbose_name='Custom Date',
        db_index=True,
        null=True,
        blank=True
    )


    objects = DirectoryContentBaseManager()


    @property
    def slug_with_id(self):
        """
        Return the primary key together with the slug.
        """
        if self.pk:
            return '%s-%d' % (self.slug, self.pk)
        else:
            return self.slug


    def get_filepath(self):
        """
        Return path to cache file for this directory content item.
        """
        return os.path.join(self.get_directory_content_type_slug(), self.slug_with_id, 'index.html')


    def get_fullslug(self):
        """
        Return the full slug for this page.
        """
        return '/%s/%s/' % (self.get_directory_content_type_slug(), self.slug_with_id)


    @property
    def url(self):
        """
        Return absolute url.
        """
        return self.get_absolute_url()


    def get_absolute_url(self):
        """
        Return absolute url.
        """
        return make_absolute_url(self.get_fullslug())



class DirectoryContentAndAggregator(DirectoryContentBase, DirectoryContentAggregator):
    """
    Directory Content and Aggregator.
    """
    class Meta:
        abstract            = True
        ordering            = ['seq']
        verbose_name        = 'Directory Content and Aggregator'
        verbose_name_plural = 'Directory Content and Aggregator'

    class Listing:
        columns = ['_title', '_meta_title', '_meta_description']
        grid_view = True
        filter_by = [
            '_title',
            'slug',
            'tags',
            'disabled'
        ]


    cascade_tags = models.BooleanField(
        verbose_name='Cascade Tags',
        default=False,
        help_text='Content listed on this page will not be listed on any page this item is listen on.'
    )


    def get_cascading_tags(self):
        """
        Return a list of cascading tags, which are tags that define
        content that is listed on this page but would also be listed on the page
        that aggregates this page.
        """
        # cascade?
        if not self.cascade_tags:
            return set()

        # classification tags for this page
        cl_tags = self.tags_set

        # subtract
        result = set()
        for tags in self.get_include_tags():
            tag_set = set(tags)
            result |= tag_set - cl_tags

        return result


class DirectoryContentEntityManager(DirectoryContentBaseManager):
    def get_queryset(self):
        """
        Fetching entities should always select related images.
        """
        qs = super(DirectoryContentEntityManager, self).get_queryset()
        if hasattr(self.model, 'image'):
            qs = qs.select_related('image')
        return qs


class DirectoryContentEntity(Entity, DirectoryContentMixin):
    """
    Directory content entity (not a cms page).
    """
    class Meta:
        abstract = True
        ordering = ['seq']

    class Listing:
        columns = ['title', 'get_tags_display|Tags', 'get_ptags_display|Priority Tags', 'disabled']
        filter_by = [
            'title',
            'tags',
            'ptags',
            'disabled'
        ]


    disabled = models.BooleanField(
        verbose_name='Disabled',
        db_index=True,
        default=False,
        help_text='A disabled entity is not visible to visitors nor to ' +
                  'search engines.'
    )


    objects = DirectoryContentEntityManager()


    @property
    def is_entity(self):
        return True


class DirectoryEntityManager(models.Manager):
    def get_queryset(self):
        """
        Fetching entities should always select related images.
        """
        qs = super(DirectoryEntityManager, self).get_queryset()
        if hasattr(qs.model, 'image'):
            qs = qs.select_related('image')
        return qs


class DirectoryEntity(DateTimeBase):
    """
    Base class for directory entities that do not have any build-in properties.
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


    objects = DirectoryEntityManager()


    @classmethod
    def get_backend_section_group(cls):
        """
        Return the group name for the section within the backend system or None.
        """
        return get_listing_option(cls, 'group')


#
# Any CMS entity deleted should reflect this within the settings as a seperate
# timestamp in order to detect content changes due to content deletion.
#
@receiver(post_delete)
def update_entity_deleted_on(sender, **kwargs):
    from cubane.cms.views import get_cms
    cms = get_cms()
    cms.notify_content_changed(sender, (DirectoryEntity, DirectoryCategory), delete=True)


#
# Invalidate cache when saving or deleting directory content
#
@receiver(post_save)
def invalidate_cache_on_content_changed(sender, **kwargs):
    from cubane.cms.views import get_cms
    cms = get_cms()
    cms.notify_content_changed(sender, (DirectoryEntity, DirectoryCategory))
