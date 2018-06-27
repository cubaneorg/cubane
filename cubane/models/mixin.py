# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db import models
from django.utils.text import Truncator
from django.utils.html import mark_safe
from django.template.defaultfilters import striptags
from cubane.lib.text import text_from_html, get_keywords
from cubane.models import Country
import re


class SEOMixin(models.Model):
    """
    Provides basic SEO meta data for a model.
    """
    class Meta:
        abstract = True


    _meta_title = models.CharField(
        verbose_name='Meta Title',
        db_column='meta_title',
        max_length=255,
        null=True,
        blank=True,
        help_text='The title of the page that is displayed in google ' +
                  'or other search engines.'
    )

    _meta_description = models.CharField(
        verbose_name='Meta Description',
        db_column='meta_description',
        max_length=255,
        null=True,
        blank=True,
        help_text='A short description that is displayed underneath the meta ' +
                  'title in google or other search engines.'
    )

    _meta_keywords = models.CharField(
        verbose_name='Meta Keywords',
        db_column='meta_keywords',
        max_length=255,
        null=True,
        blank=True,
        help_text='A list of keywords that are significant for the content ' +
                  'of this page.'
    )


    @property
    def meta_title(self):
        """
        Return the meta title or if that is not defined the normal page title.
        """
        if self._meta_title:
            return self._meta_title
        else:
            return self.title


    @property
    def meta_description(self):
        if self._meta_description != None:
            return self._meta_description
        elif hasattr(self, 'get_slot_content'):
            return Truncator(text_from_html(self.get_combined_slot_content(settings.CMS_SLOTNAMES))).words(30, truncate='')
        else:
            return ''


    @property
    def meta_keywords(self):
        if self._meta_keywords != None:
            return self._meta_keywords
        elif hasattr(self, 'get_slot_content'):
            return self.get_generated_keywords(text_from_html(self.get_combined_slot_content(settings.CMS_SLOTNAMES)))
        else:
            return ''


    def get_generated_keywords(self, s=None):
        if not hasattr(self, 'cached_keywords'):
            # join by comma
            self.cached_keywords = ', '.join(get_keywords(s))

        return self.cached_keywords


class LegacyUrlMixin(models.Model):
    """
    Provides support for a legacy urls for a model. If a request hits the site,
    legacy urls are checked against the query string to determine the
    resulting url to redirect to.
    """
    class Meta:
        abstract = True


    legacy_url = models.CharField(
        verbose_name='Legacy Url',
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='Legacy document path or full URL. Provide the legacy ' + \
                  'URL to this page; how it was used to be named on ' + \
                  'the old site.'
    )


class HierarchyMixin(models.Model):
    """
    Provides support for a basic hierarchical structure for a model.
    The model requires a foreign key called 'parent' to self and an integer
    field 'seq' that encodes the sequence in which elements are ordered
    (starting with index 1).
    """
    class Meta:
        abstract = True


    def append_before(self, ref):
        """
        Append this instance before the given reference
        """
        if ref != None and self.pk != ref.pk and self.seq != ref.seq - 1:
            self.parent = ref.parent
            self.seq = self._put_in(ref, True)
            self.save()
        return self


    def append_after(self, ref):
        """
        Append this instance after the given reference.
        """
        if ref != None and self.pk != ref.pk and self.seq != ref.seq + 1:
            self.parent = ref.parent
            self.seq = self._put_in(ref, False)
            self.save()
        return self


    def append_to(self, ref, pos='last'):
        """
        Append this instance into the given reference container, depending on
        given position argument (first, last).
        """
        if ref == None: return self

        try:
            if pos == 'last':
                self.append_after(ref.get_children_reversed()[0])
            elif pos == 'first':
                self.append_before(ref.get_children()[0])
        except IndexError:
            # empty container
            self.parent = ref
            self.seq = 1
            self.save()

        return self


    def append_top_level(self):
        """
        Append this node as the last top level node.
        """
        try:
            last = self.__class__.objects.filter(parent__isnull=True).order_by('-seq')[0]
            self.append_after(last)
        except IndexError:
            # first top level node
            self.parent = None
            self.seq = 1
            self.save()


    def has_parent(self):
        """
        Return True, if this node has a parent node.
        """
        return self.get_parent() != None


    def get_parent(self):
        """
        Return the parent of this node of None.
        """
        if not hasattr(self, '_parent'):
            self._parent = self.parent
        return self._parent


    def get_children(self):
        """
        Return a cached queryset of all child nodes of this node in seq. order.
        """
        return list(self.get_children_queryset())


    def get_children_queryset(self):
        """
        Return a queryset of all child nodes of this node in seq. order.
        """
        return self.__class__.objects.filter(parent=self).order_by('seq')


    def get_children_reversed(self):
        """
        Return a queryset of all child nodes of this node in reversed seq. order.
        """
        return list(self.__class__.objects.filter(parent=self).order_by('-seq'))


    def get_path(self):
        """
        Return a list of all nodes within the hierarchy starting with the
        root node up until this node.
        """
        l = []
        p = self
        while p != None:
            l.append(p)
            p = p.get_parent()
        return list(reversed(l))


    def get_root(self):
        """
        Return the root category for this category (which might be the category itself).
        """
        c = self
        parent = c.parent
        while parent:
            c = parent
            parent = c.parent
        return c


    def _put_in(self, ref, include_ref):
        """
        Update seq for all nodes within the same hierarchy level as the given
        reference node so that a new node can be inserted before or after the
        reference node. Returns the index seq number for the new node.
        """
        nodes = self.__class__.objects.filter(parent=ref.parent).exclude(pk=self.pk).only('seq')
        i = 1
        for n in nodes:
            if include_ref and n.pk == ref.pk:
                seq = i
                i += 1

            n.seq = i
            n.save()
            i += 1

            if not include_ref and n.pk == ref.pk:
                seq = i
                i += 1

        return seq


class NationalAddressMixin(models.Model):
    """
    Provide generic address fields for a postal address.
    """
    class Meta:
        abstract = True


    address1 = models.CharField(
        verbose_name='Address line 1',
        max_length=255,
        help_text='First line of your company''s postal address.'
    )

    address2 = models.CharField(
        verbose_name='Address line 2',
        max_length=255,
        null=True,
        blank=True,
        help_text='Second (optional) line of your company''s postal address.'
    )

    postcode = models.CharField(
        verbose_name='Postcode',
        max_length=255,
        null=True,
        blank=True,
        help_text='The postcode or ZIP code of your postal address.'
    )

    city = models.CharField(
        verbose_name='City or Town',
        max_length=255,
        help_text='The city or town of your postal address.'
    )

    county = models.CharField(
        verbose_name='County / State',
        max_length=255,
        help_text='The county or state (US only) of your postal address.'
    )


    @property
    def has_address(self):
        """
        Return True, if required address information has been configured and is available.
        """
        return all([self.address1, self.postcode, self.city])


    @property
    def address_fields(self):
        """
        Return a list of address fields that are not empty.
        """
        return filter(lambda a: a, [
            self.address1,
            self.address2,
            self.city,
            self.county,
            self.postcode,
        ])


    @property
    def address_lines(self):
        """
        Return address components seperated by <br/> as a safe string.
        """
        return mark_safe('<br/>'.join(self.address_fields))


class AddressMixin(NationalAddressMixin):
    """
    Provide generic address fields for a postal address.
    """
    class Meta:
        abstract = True

    country = models.ForeignKey(
        Country,
        default='GB',
        verbose_name='Country',
        help_text='Select the country for your postal address.'
    )


    @property
    def local_address_fields(self):
        """
        Return a list of address fields that are not empty representation a
        local address (excluding country and county).
        """
        return filter(lambda a: a, [
            self.address1,
            self.address2,
            self.city,
            self.postcode
        ])


    @property
    def short_address_fields(self):
        """
        Return a list of address fields that are not empty (excluding country).
        """
        return filter(lambda a: a, [
            self.address1,
            self.address2,
            self.city,
            self.county,
            self.postcode
        ])


    @property
    def address_fields(self):
        """
        Return a list of address fields that are not empty.
        """
        return filter(lambda a: a, [
            self.address1,
            self.address2,
            self.city,
            self.county,
            self.postcode,
            unicode(self.country)
        ])


class ContactMixin(models.Model):
    """
    Contact information.
    """
    class Meta:
        abstract = True


    email = models.EmailField(
        verbose_name='Email',
        max_length=255,
        null=True,
        blank=True,
        help_text='Email address'
    )

    phone = models.CharField(
        verbose_name='Phone',
        max_length=255,
        null=True,
        blank=True,
        help_text='Primary phone number.'
    )


class GeoLocationMixin(models.Model):
    """
    Provides a geo-location in the form of latitude and longitude
    coordinates for a specific geo location along with brief directions.
    """
    class Meta:
        abstract = True


    lat = models.FloatField(
        verbose_name='Latitude',
        null=True,
        blank=True
    )

    lng = models.FloatField(
        verbose_name='Longitude',
        null=True,
        blank=True,
    )


    @property
    def has_location(self):
        """
        Return True if this mixin represents a valid location, which is not
        None and not 0.0 degrees for both, latitude and longitude.
        """
        if self.lat is None or self.lng is None:
            return False

        if self.lat == 0.0 and self.lng == 0.0:
            return False

        return True


class GeoLocationWithZoomMixin(GeoLocationMixin):
    """
    Provides a geo location with zoom level.
    """
    class Meta:
        abstract = True


    zoom = models.IntegerField(
        verbose_name='Zoom',
        null=True,
        blank=True,
    )