# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, Prefetch
from django.contrib import messages
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify, striptags, escape
from django.core.urlresolvers import reverse, get_urlconf
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from cubane.models import DateTimeBase, Country, PostCodeField
from cubane.models.mixin import SEOMixin, HierarchyMixin
from cubane.models.fields import MultiSelectField
from cubane.cms import get_page_model_name
from cubane.cms.models import SettingsBase, ExcerptMixin, NavigationMixin, EditableHtmlField
from cubane.cms.models import EntityManager
from cubane.media.models import Media, MediaGallery
from cubane.lib.conversion import inch_to_cm
from cubane.lib.libjson import to_json, decode_json
from cubane.lib.crypt import encrypt, decrypt
from cubane.lib.url import get_absolute_url, get_filepath_from_url
from cubane.lib.choices import get_choices_display
from cubane.lib.barcodes import get_barcode_choices
from cubane.lib.model import get_listing_option
from cubane.ishop import get_category_model_name, get_category_model
from cubane.ishop import get_product_model_name, get_product_model
from cubane.ishop import get_order_model
from cubane.ishop import get_customer_model
from cubane.ishop.mail import *
from cubane.ishop.apps.merchant.categories.google_categories import get_google_categories
from decimal import Decimal
import copy
import hashlib
import datetime
import os
import re
import collections


class ShopEntityManager(EntityManager):
    """
    Manager for shop entities. We will always fetch images alongside entities.
    """
    pass


class ShopEntity(DateTimeBase):
    """
    Base class for Shop entities that do not have any built-in properties.
    """
    class Meta:
        abstract = True

    seq = models.IntegerField(
        verbose_name='Sequence',
        editable=False,
        db_index=True,
        default=0,
        help_text='The sequence number determines the order in which ' + \
                  'entities are presented, for example within the ' + \
                  'navigation section(s) of your website.'
    )

    objects = ShopEntityManager()


    @classmethod
    def get_backend_section_group(cls):
        """
        Return the group name for the section within the backend
        system or None.
        """
        return get_listing_option(cls, 'group')


class DeliveryOption(DateTimeBase):
    """
    Shop-wide delivery options.
    """
    class Meta:
        db_table            = 'ishop_delivery'
        ordering            = ['seq']
        verbose_name        = 'Delivery Option'
        verbose_name_plural = 'Delivery Options'


    class Listing:
        columns = [
            'title',
            'enabled',
            '/deliver_uk|UK',
            '/-uk_def|UK|currency',
            '/deliver_eu|EU',
            '/-eu_def|EU|currency',
            '/deliver_world|Non-EU',
            '/-world_def|Non-EU|currency'
        ]
        edit_view = True
        sortable = True
        filter_by = [
            'title',
            'deliver_uk',
            'deliver_eu',
            'deliver_world'
        ]


    title = models.CharField(
        verbose_name='Title',
        max_length=120,
        db_index=True
    )

    description = models.TextField(
        verbose_name='Description',
        null=True,
        blank=True,
        help_text='Additional description is presented alongside a choosen ' + \
                  'delivery method when selected.'
    )

    enabled = models.BooleanField(
        verbose_name='Enabled',
        db_index=True,
        default=True,
        help_text='Enable this delivery option globally to make it ' + \
                  'available to all products. Disabled delivery option ' + \
                  'cannot be selected by customers.'
    )

    free_delivery = models.BooleanField(
        verbose_name='Free Delivery',
        default=False,
        help_text='Enable Free Delivery (based on threshold).'
    )

    free_delivery_threshold = models.DecimalField(
        verbose_name='Free Delivery Threshold',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='If the total amount of any given order exceeds this ' + \
                  'threshold then no delivery cost is charged.'
    )

    deliver_uk = models.BooleanField(
        verbose_name='UK Delivery',
        default=False,
        db_index=True,
        help_text='Accept deliveries to the UK by standard charge.'
    )

    quote_uk = models.BooleanField(
        verbose_name='UK Delivery Quote',
        default=False,
        db_index=True,
        help_text='Provide individual quote for UK deliveries.'
    )

    uk_def = models.DecimalField(
        verbose_name='UK Charge',
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True
    )

    deliver_eu = models.BooleanField(
        verbose_name='EU Delivery',
        default=False,
        db_index=True,
        help_text='Accept deliveries to the EU by standard charge'
    )

    quote_eu = models.BooleanField(
        verbose_name='EU Delivery Quote',
        default=False,
        db_index=True,
        help_text='Provide individual quote for EU deliveries.'
    )

    eu_def = models.DecimalField(
        verbose_name='EU Charge',
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True
    )

    deliver_world = models.BooleanField(
        verbose_name='Worldwide Delivery',
        default=False,
        db_index=True,
        help_text='Accept worldwide deliveries by standard charge'
    )

    quote_world = models.BooleanField(
        verbose_name='Worldwide Delivery Quote',
        default=False,
        db_index=True,
        help_text='Provide individual quote for Worldwide deliveries.'
    )

    world_def = models.DecimalField(
        verbose_name='Worldwide Charge',
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True
    )

    seq = models.IntegerField(db_index=True, default=1)


    @classmethod
    def get_form(cls):
        """
        Return the default form for editing delivery options in the backend.
        """
        from cubane.ishop.apps.merchant.delivery.forms import DeliveryOptionForm
        return DeliveryOptionForm


    def get_defaults(self):
        """
        Return the default delivery charges for UK, Europe and World.
        """
        return (self.uk_def, self.eu_def, self.world_def)


    def __unicode__(self):
        return self.title


class Variety(DateTimeBase):
    """
    Product Variety.
    """
    class Meta:
        db_table            = 'ishop_variety'
        ordering            = ['title']
        verbose_name        = 'Variety'
        verbose_name_plural = 'Varieties'


    class Listing:
        columns = [
            'title',
            'get_options_display|Options|action:options',
            'get_style_display|Type',
            'get_product_count_display|Products|action:products',
            'sku',
            'enabled',
        ]
        edit_columns = [
            'title',
            'display_title',
            'style|Type',
            'sku',
            'enabled'
        ]
        edit_view = True
        grid_view = True
        filter_by = [
            'title',
            'style',
            'unit',
            'sku',
            'enabled'
        ]
        sortable = True
        data_export = True
        data_columns = [
            'title',
            'display_title:as(customer_title)',
            'get_style_display:as(type)',
            'get_product_count_display:as(product_count)',
            'sku',
            'enabled',
            'get_options_display:as(options)',
        ]


    UNIT_NONE     = 'none'
    UNIT_LENGTH   = 'length'
    UNIT_CHOICES  = (
        (UNIT_NONE, 'No unit (text only)'),
        (UNIT_LENGTH, 'Length (inch)')
    )


    STYLE_SELECT                      = 1
    STYLE_LIST                        = 2
    STYLE_LIST_WITH_IMAGE             = 3
    STYLE_ATTRIBUTE                   = 999
    STYLE_CHOICES = (
        (STYLE_SELECT,          'Select Box (or List)'),
        (STYLE_LIST,            'List'),
        (STYLE_LIST_WITH_IMAGE, 'List with image'),
        (STYLE_ATTRIBUTE,       'Attribute'),
    )


    title = models.CharField(
        verbose_name='Title',
        max_length=255,
        db_index=True,
        help_text='Used within the backend only. Not presented to customers.'
    )

    display_title = models.CharField(
        verbose_name='Display Title',
        max_length=255,
        db_index=True,
        help_text='Visible to customers.'
    )

    slug = models.SlugField(
        verbose_name='Slug',
        max_length=255,
        db_index=True
    )

    parent = models.ForeignKey(
        'self',
        verbose_name='Parent',
        null=True,
        blank=True,
        help_text='Parent Variety'
    )

    unit = models.CharField(
        verbose_name='Unit',
        max_length=10,
        default=UNIT_NONE,
        choices=UNIT_CHOICES
    )

    sku = models.BooleanField(
        verbose_name='SKU',
        db_index=True,
        default=False,
        help_text='Allow this variety to take part in SKU numbers (Stock Keeping Units).'
    )

    enabled = models.BooleanField(
        verbose_name='Enabled',
        db_index=True,
        default=True,
        help_text='Enabled varieties are available for customers to ' + \
                  'choose from.'
    )

    preview_listing = models.BooleanField(
        verbose_name='Preview Listing',
        db_index=True,
        default=False,
        help_text='Present tooltip with larger image preview.'
    )

    style = models.IntegerField(
        verbose_name='Presentation Style',
        choices=STYLE_CHOICES,
        default=1
    )

    layer = models.CharField(
        verbose_name='SVG Layer Identifier',
        max_length=255,
        null=True,
        blank=True,
        help_text='Enter the unique SVG layer identifier for this variety.'
    )

    seq = models.IntegerField(
        db_index=True,
        default=1,
        editable=False
    )


    def delete(self, *args, **kwargs):
        """
        Deleting a variety should delete all variety options individually in
        order to safely remove product SKUs (See delete handler for
        VarityOption).
        """
        # get list of products that would be affected
        products = list(get_product_model().objects.filter(
            product_sku__variety_options__variety=self
        ).distinct())

        # delete variety
        super(Variety, self).delete(*args, **kwargs)

        # check each product and remove any duplicates in SKU combinations
        for product in products:
            combinations = []
            skus = []
            for sku in ProductSKU.objects.filter(product=product).prefetch_related('variety_options').order_by('sku'):
                combination = [vo.pk for vo in sku.variety_options.all()]
                if combination not in combinations:
                    combinations.append(combination)
                else:
                    skus.append(sku.pk)

            if skus:
                ProductSKU.objects.filter(pk__in=skus).delete()


    @classmethod
    def get_form(cls):
        """
        Return the default form for editing varieties in the backend.
        """
        from cubane.ishop.apps.merchant.varieties.forms import VarietyForm
        return VarietyForm


    @property
    def is_attribute(self):
        """
        Return True, if this variety is treated as an attribute only, which
        means that customers cannot choose it when adding a product to the
        basket. It can only used to filter products by.
        """
        return self.style == Variety.STYLE_ATTRIBUTE


    def get_slug(self):
        """
        Return the slug for this variety.
        """
        return self.slug


    def format_variety_value(self, value):
        """
        Format given variety value based on the varity's unit.
        """
        if self.unit == self.UNIT_LENGTH:
            inch = Decimal(value)
            cm = inch_to_cm(inch)
            return '%.1f inch (%.1f cm)' % (inch, cm)
        else:
            try:
                return '%.1f' % value
            except TypeError:
                return value


    def get_options_display(self):
        """
        Return a string that represents all available variety options
        for display purposes as a list of comma-separated items, e.g.
        A, B, C ..., D, E, F
        """
        return ', '.join(
            option.title.strip() for option in self.options.all()
        )


    def get_options_excerpt_display(self):
        """
        Return a string that represents an excerpt of available variety options
        for display purposes as a list of comma-separated items, e.g.
        A, C, C ...
        """
        options = list(self.options.all())

        return ', '.join(
            option.title.strip() for option in options[:5]
        ) + (', ...' if len(options) > 5 else '')


    def get_product_count_display(self):
        """
        Return the count of distinct products this variety is currently assigned
        and a list of a few assigned product names.
        """
        # num_products is usually injected via .annotate
        if not hasattr(self, 'num_products'):
            self.num_products = VarietyAssignment.objects.filter(
                variety_option__variety=self
            ).values('product_id').distinct().count()
        return '%d' % self.num_products


    def __unicode__(self):
        return u'%s' % self.title


class VarietyOption(DateTimeBase):
    """
    Individual variety option for a variety (Many To Many).
    """
    class Meta:
        db_table            = 'ishop_variety_option'
        ordering            = ['seq']
        verbose_name        = 'Variety Option'
        verbose_name_plural = 'Variety Options'


    class Listing:
        columns = [
            'title',
            'variety__title|Variety',
            'default_offset_type|Offset Type',
            '-default_offset_value_display|Offset',
            'text_label',
            'enabled'
        ]
        edit_columns = [
            'title',
            'variety',
            'default_offset_type|Offset Type',
            'default_offset_value|Offset',
            'text_label',
            'enabled'
        ]
        sortable = True
        edit_view = True
        filter_by = [
            'title',
            'variety',
            'text_label',
            'enabled',
            'default_offset_type',
            'default_offset_value',
            'color',
        ]


    OFFSET_NONE    = 0
    OFFSET_VALUE   = 1
    OFFSET_PERCENT = 2
    OFFSET_CHOICES_WITHOUT_DEFAULT = (
        (OFFSET_VALUE,   'Value'),
        (OFFSET_PERCENT, 'Percent'),
    )
    OFFSET_CHOICES = (
        (OFFSET_NONE,    '---------'),
    ) + OFFSET_CHOICES_WITHOUT_DEFAULT


    title = models.CharField(
        db_index=True,
        max_length=255
    )

    variety = models.ForeignKey(
        Variety,
        verbose_name='Variety',
        related_name='options',
        help_text='The variety this option belongs to.'
    )

    enabled = models.BooleanField(
        verbose_name='Enabled',
        db_index=True,
        default=True,
        help_text='Enable, so that customers can choose this option.'
    )

    default_offset_type = models.IntegerField(
        verbose_name='Offset Type',
        null=True,
        blank=True,
        choices=OFFSET_CHOICES_WITHOUT_DEFAULT,
        help_text='Type of price offset relative to the base price of the product.'
    )

    default_offset_value = models.DecimalField(
        verbose_name='Offset',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Percentage or price offset relative to the base price of the product depending on offset type.'
    )

    image = models.ForeignKey(
        Media,
        null=True,
        blank=True,
        related_name='image_variety_option'
    )

    color = models.CharField(
        verbose_name='Colour',
        max_length=16,
        null=True,
        blank=True,
        help_text='In particular when using a kit builder, this colour information can be used to change parts of an vector-based product image.'
    )

    text_label = models.BooleanField(
        verbose_name='Text Label',
        default=False,
        help_text='Allow customers to enter custom text alongside this variety.'
    )

    text_label_placeholder = models.CharField(
        verbose_name='Placeholder',
        max_length=255,
        null=True,
        blank=True,
        help_text='Text that appears as placeholder text over the label text input field.'
    )

    text_label_help = models.CharField(
        verbose_name='Help Text',
        max_length=255,
        null=True,
        blank=True,
        help_text='Text that appears underneath the label text input field for additional help text.'
    )

    seq = models.IntegerField(
        db_index=True,
        default=1,
        editable=False
    )


    @classmethod
    def get_form(cls):
        from cubane.ishop.apps.merchant.varieties.forms import VarietyOptionBackendForm
        return VarietyOptionBackendForm


    @property
    def label(self):
        """
        Return the formatted variety label for this variety option based on
        the unit that is associated with the variety. E.g. for length one
        might get inches and cm conversions.
        """
        return self.variety.format_variety_value(self.title)


    @property
    def default_offset_value_display(self):
        """
        Return the formatted presentation of the default offset value,
        which might be percent or currency.
        """
        if self.default_offset_value is not None:
            if self.default_offset_type == self.OFFSET_VALUE:
                from cubane.ishop.templatetags.shop_tags import get_shop_price
                return get_shop_price(self.default_offset_value)
            elif self.default_offset_type == self.OFFSET_PERCENT:
                return '%s%%' % self.default_offset_value
        return self.default_offset_value


    @property
    def url_safe_color(self):
        """
        Return the colour attribute for this variety in a url-safe manner, so
        that it does not contain sharp symbols.
        """
        return self.color.replace('#', '')


    def delete(self, *args, **kwargs):
        """
        Deleting a variety option should also delete any product SKU that
        refers to this option
        """
        skus = ProductSKU.objects.filter(variety_options=self).distinct()
        skus.delete()
        super(VarietyOption, self).delete(*args, **kwargs)


    def __unicode__(self):
        if self.variety_id:
            return u'%s: %s' % (self.variety, self.title)
        else:
            return u'%s' % self.title


class VarietyAssignmentManager(models.Manager):
    """
    Variety Product Assignment.
    """
    def to_hierarchy(self, assignments, currentFilter, varieties=None):
        """
        Transform a linear list of matching variety filters and corresponding
        options into a nested structure, which is easier to render within a
        template.
        """
        if varieties is None:
            varieties = collections.OrderedDict()

        for a in assignments:
            _id = a.variety_option.variety.id
            if _id not in varieties:
                varieties[_id] = {
                    'id': _id,
                    'display_title': a.variety_option.variety.display_title,
                    'checked': 0,
                    'options': [],
                    'option_ids': [],
                    'arg': 'v'
                }

            if a.variety_option.id not in varieties[_id].get('option_ids'):
                varieties[_id].get('options').append({
                    'id': 'variety-%d' % a.variety_option.id,
                    'title': a.variety_option.title,
                    'value': a.variety_option.id,
                    'checked': a.variety_option.id in currentFilter,
                    'image': a.variety_option.image
                })
                varieties[_id].get('option_ids').append(a.variety_option.id)

        # determine which variety group has at least one option checked
        for k, v in varieties.items():
            v['checked'] = sum(
                [1 for o in v.get('options') if o.get('checked')]
            )

        return varieties


    def get_variety_filters_for_products(self, products, currentFilter, varieties=None):
        """
        Return all varieties and corresponding options as a hierarchical
        structure for all options that do apply for all given products.
        """
        assignments = VarietyAssignment.objects.select_related(
            'variety_option',
            'variety_option__image',
            'variety_option__variety',
            'product'
        ).filter(
            product__in=products
        ).distinct().order_by(
            'variety_option__variety__display_title',
            'variety_option__seq'
        )

        return self.to_hierarchy(assignments, currentFilter, varieties)


    def inject_product_variety_preview(self, products):
        """
        Inject a list of variety options that are available for all given
        products and the listing preview option is set to True.
        """
        assignments = VarietyAssignment.objects.select_related(
            'variety_option',
            'variety_option__variety',
            'variety_option__image'
        ).filter(
            product__in=products,
            variety_option__variety__preview_listing=True
        ).order_by(
            'variety_option__variety__title',
            'variety_option__seq'
        )

        for product in products:
            options = []
            for a in assignments:
                if a.product.id == product.id:
                    options.append((
                        a.variety_option.title,
                        a.variety_option.image
                    ))
            product.set_varity_preview(options)

        return len(assignments) > 0


class VarietyAssignment(models.Model):
    """
    Associates variety options with products.
    """
    class Meta:
        db_table            = 'ishop_variety_assignment'
        ordering            = ['id']
        verbose_name        = 'Variety Assignment'
        verbose_name_plural = 'Variety Assignments'
        unique_together     = ('product', 'variety_option')


    product = models.ForeignKey(
        get_product_model_name(),
        related_name='assignments'
    )

    variety_option = models.ForeignKey(
        VarietyOption,
        related_name='assignments'
    )

    offset_type = models.IntegerField(
        choices=VarietyOption.OFFSET_CHOICES,
        null=True,
        blank=True
    )

    offset_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )


    objects = VarietyAssignmentManager()


    @property
    def price(self):
        """
        Return the net price increase if this variety would apply for the
        corresponding product. The price is for the variety only and does not
        include the base price of the underlying product.
        """
        if self.offset_type == VarietyOption.OFFSET_NONE:
            value = Decimal('0.00')
        elif self.offset_type == VarietyOption.OFFSET_VALUE and \
             self.offset_value is not None:
            value = self.offset_value
        elif self.offset_type == VarietyOption.OFFSET_PERCENT and \
             self.offset_value is not None:
            value = self.product.price * (self.offset_value / Decimal('100.00'))
        else:
            value = Decimal('0.00')

        return value.quantize(Decimal('.01'))


    @property
    def label(self):
        """
        Return the label for this variety option assignment.
        """
        return self.variety_option.label


    def __unicode__(self):
        return '%s assigned to %s' % (
            self.variety_option,
            self.product
        )


class ProductDeliveryOption(models.Model):
    """
    Delivery Options per product.
    """
    class Meta:
        db_table            = 'ishop_product_delivery'
        ordering            = ['id']
        verbose_name        = 'Product Delivery Option'
        verbose_name_plural = 'Product Delivery Options'
        unique_together     = ('product', 'delivery_option')


    product = models.ForeignKey(
        get_product_model_name()
    )

    delivery_option = models.ForeignKey(
        DeliveryOption
    )

    uk = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    eu = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    world = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )


    def __unicode__(self):
        return u'%s via %s (%s, %s, %s)' % (
            self.product,
            self.delivery_option,
            self.uk,
            self.eu,
            self.world
        )


class RelatedProducts(models.Model):
    """
    Captures assignment of products to other products.
    """
    class Meta:
        ordering            = ['seq']
        verbose_name        = 'Related Products'
        verbose_name_plural = 'Related Products'


    from_product = models.ForeignKey(
        get_product_model_name(),
        related_name='source',
        null=False
    )

    to_product = models.ForeignKey(
        get_product_model_name(),
        related_name='target',
        null=False
    )

    seq = models.IntegerField(
        verbose_name='Sequence',
        db_index=True,
        default=0,
        editable=False,
        help_text='The sequence number determines the order in which ' + \
                  'products are presented.'
    )


    def __unicode__(self):
        return unicode(self.to_product_id)


class FinanceOption(DateTimeBase):
    """
    Represents a finance option to choose from as a custom.
    """
    class Meta:
        ordering            = ['seq']
        verbose_name        = 'Finance Option'
        verbose_name_plural = 'Finance Options'


    class Listing:
        columns = ['title', 'code', 'min_basket_value', 'per_product', 'enabled']
        filter_by = ['title', 'code', 'min_basket_value', 'per_product', 'enabled']
        edit_view = True
        sortable = True


    title = models.CharField(
        verbose_name='Title',
        max_length=255,
        db_index=True,
        unique=True,
        help_text='Unique name of this finance option.'
    )

    code = models.CharField(
        verbose_name='Product Code',
        max_length=255,
        help_text='The unique product code of this finance option as defined by your loan payment gateway.'
    )

    min_basket_value = models.DecimalField(
        verbose_name='Min. Basket Value',
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True,
        help_text='The minimum basket value that is required to qualify for this finance option.'
    )

    enabled = models.BooleanField(
        verbose_name='Enabled',
        db_index=True,
        default=True,
        help_text='Enable, so that this finance option is available to customers to choose.'
    )

    per_product = models.BooleanField(
        verbose_name='Assignment',
        help_text='If ticked, this finance option needs to be assigned on a per-product basis.'
    )

    seq = models.IntegerField(
        db_index=True,
        default=1,
        editable=False
    )


    @classmethod
    def get_form(cls):
        from cubane.ishop.apps.merchant.finance.forms import FinanceOptionForm
        return FinanceOptionForm


    def to_dict(self):
        return {
            'id': self.pk,
            'title': self.title,
        }


    def __unicode__(self):
        return '%s' % self.title


class ProductCategory(models.Model):
    """
    Associates a product with one or more categories and encodes the seq.
    order of the product within each category.
    """
    class Meta:
        db_table            = 'ishop_product_category'
        verbose_name        = 'Product Category'
        verbose_name_plural = 'Product Categories'
        unique_together     = ('product', 'category')


    product = models.ForeignKey(
        get_product_model_name(),
        related_name='category_assignments'
    )

    category = models.ForeignKey(
        get_category_model_name(),
        related_name='product_assignments'
    )

    seq = models.IntegerField(
        verbose_name='Sequence',
        db_index=True,
        default=0,
        editable=False,
        help_text='The sequence number determines the order in which ' + \
                  'the given product appears within the given category.'
    )


    def __unicode__(self):
        return '%s' % self.category.title


class ProductBase(DateTimeBase, ExcerptMixin, SEOMixin):
    """
    Shop Product Base Class.
    """
    class Meta:
        abstract = True
        ordering            = ['seq']
        verbose_name        = 'Product'
        verbose_name_plural = 'Products'


    class Listing:
        columns = [
            'title',
            'category',
            'categories_display|Categories',
            'price',
            '/stock',
            '/stocklevel'
        ]
        edit_view = True
        grid_view = True
        sortable = True
        filter_by = [
            'title',
            'category',
            'categories',
            'barcode',
            'price',
            'rrp',
            'previous_price',
            'feed_google',
            'feed_amazon',
            'stock',
            'stocklevel',
            'draft',
            'non_returnable',
            'collection_only',
            'pre_order',
            'exempt_from_free_delivery',
            'exempt_from_discount',
            'sku_enabled'
        ]


    class FTS:
        columns = {
            'fts_index': ['title', 'description']
        }


    # order
    ORDER_BY_RELEVANCE         = 'relevance'
    ORDER_BY_DATE_ADDED        = 'date-added'
    ORDER_BY_PRICE_HIGH_TO_LOW = 'price-high-low'
    ORDER_BY_PRICE_LOW_TO_HIGH = 'price-low-high'
    ORDER_BY_NAME              = 'name'
    ORDER_BY_CHOICES = (
        (ORDER_BY_RELEVANCE,         'Relevance'),
        (ORDER_BY_DATE_ADDED,        'Date Added'),
        (ORDER_BY_PRICE_LOW_TO_HIGH, 'Price (Low to High)'),
        (ORDER_BY_PRICE_HIGH_TO_LOW, 'Price (High to Low)'),
        (ORDER_BY_NAME,              'Alphabetically'),
    )
    ORDER_BY_DEFAULT_OPTIONS = ','.join([
        ORDER_BY_RELEVANCE,
        ORDER_BY_PRICE_HIGH_TO_LOW,
        ORDER_BY_PRICE_LOW_TO_HIGH
    ])


    # stock level
    STOCKLEVEL_AVAILABLE         = 1
    STOCKLEVEL_OUT_OF_STOCK      = 2
    STOCKLEVEL_AUTO              = 3
    STOCKLEVEL_MADE_TO_ORDER     = 4
    STOCKLEVEL_MSG_AVAILABLE     = 'In Stock'
    STOCKLEVEL_MSG_OUT_OF_STOCK  = 'Out Of Stock'
    STOCKLEVEL_MSG_AUTO          = 'Automatic'
    STOCKLEVEL_MSG_MADE_TO_ORDER = 'Made To Order'
    STOCKLEVEL_CHOICES = (
        (STOCKLEVEL_AVAILABLE,     STOCKLEVEL_MSG_AVAILABLE),
        (STOCKLEVEL_OUT_OF_STOCK,  STOCKLEVEL_MSG_OUT_OF_STOCK),
        (STOCKLEVEL_AUTO,          STOCKLEVEL_MSG_AUTO),
        (STOCKLEVEL_MADE_TO_ORDER, STOCKLEVEL_MSG_MADE_TO_ORDER),
    )


    title = models.CharField(
        verbose_name='Title',
        max_length=255,
        db_index=True
    )

    slug = models.SlugField(
        verbose_name='Slug',
        max_length=255,
        unique=True,
        db_index=True,
        help_text='Name of the product as part of the url, e.g. ' + \
                  'boots/black-knee-boots.html.'
    )

    category = models.ForeignKey(
        get_category_model_name(),
        verbose_name='Category',
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name='products'
    )

    categories = models.ManyToManyField(
        get_category_model_name(),
        verbose_name='Categories',
        through=ProductCategory,
        editable=False
    )

    varieties = models.ManyToManyField(
        VarietyOption,
        verbose_name='Varieties',
        through=VarietyAssignment
    )

    seq = models.IntegerField(
        db_index=True,
        default=1
    )

    rrp = models.DecimalField(
        verbose_name='RRP',
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True,
        help_text='Recommended Retail Price.'
    )

    previous_price = models.DecimalField(
        verbose_name='Previous Price',
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True,
        help_text='Previous price if the current price is discounted.'
    )

    price = models.DecimalField(
        verbose_name='Price',
        max_digits=12,
        decimal_places=2,
        db_index=True
    )

    deposit = models.DecimalField(
        verbose_name='Deposit',
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True
    )

    loan_exempt = models.BooleanField(
        verbose_name='Finance Exempt',
        db_index=True,
        default=False,
        help_text='Enable if this product is exempt from any finance option.'
    )

    finance_options = models.ManyToManyField(
        FinanceOption,
        verbose_name='Finance Options',
        blank=True,
        help_text='Choose the finance options for which this product qualifies.'
    )

    delivery_options = models.ManyToManyField(
        DeliveryOption,
        verbose_name='Delivery Options',
        through=ProductDeliveryOption
    )

    description = EditableHtmlField(
        verbose_name='Description',
        null=True,
        blank=True
    )

    barcode_system = models.CharField(
        verbose_name='Barcode System',
        max_length=8,
        null=True,
        blank=True,
        choices=get_barcode_choices(),
        help_text='Choose the type of barcode system that is used for this product.'
    )

    barcode = models.CharField(
        verbose_name='Barcode',
        max_length=32,
        null=True,
        blank=True,
        db_index=True,
        help_text='Product Barcode Number.'
    )

    part_number = models.CharField(
        verbose_name='Part Number',
        max_length=32,
        null=True,
        blank=True,
        db_index=True,
        help_text='Global Manufacturer Part Number (MPN)'
    )

    stocklevel = models.IntegerField(
        verbose_name='Stock Level',
        db_index=True,
        default=0
    )

    sku = models.CharField(
        verbose_name='SKU',
        max_length=255,
        db_index=True,
        null=True,
        blank=True,
        help_text='SKU (Stock-keeping unit). Unique product code.'
    )

    sku_enabled = models.BooleanField(
        verbose_name='SKU Enabled',
        db_index=True,
        default=False,
        help_text='Enable management of individual stock keeping units (SKUs).'
    )

    stock = models.IntegerField(
        verbose_name='Stock',
        choices=STOCKLEVEL_CHOICES,
        default=STOCKLEVEL_AVAILABLE
    )

    draft = models.BooleanField(
        verbose_name='Draft',
        default=False,
        db_index=True,
        help_text='If ticked then it will not be displayed to the ' + \
                  'general public.'
    )

    non_returnable = models.BooleanField(
        verbose_name='Non-Returnable',
        db_index=True,
        default=False,
        help_text='Check, if this product is not returnable.'
    )

    collection_only = models.BooleanField(
        verbose_name='Collection Only',
        db_index=True,
        default=False,
        help_text='Check, if this product is only collectible from store.'
    )

    pre_order = models.BooleanField(
        verbose_name='Pre-order',
        db_index=True,
        default=False,
        help_text='Check, if this product is pre-order.'
    )

    exempt_from_free_delivery = models.BooleanField(
        verbose_name='Exempt from Free Delivery',
        db_index=True,
        default=False,
        help_text='Check, if this product is exempt from free deliveries.'
    )

    exempt_from_discount = models.BooleanField(
        verbose_name='Exempt from Discount',
        db_index=True,
        default=False,
        help_text='Check, if this product is exempt from voucher discounts.'
    )

    legacy_url = models.CharField(
        verbose_name='Legacy Url',
        max_length=255,
        db_index=True,
        null=True,
        blank=True,
        help_text='Path only, no domain name. Alternate url for legacy ' + \
                  'purposes (only applies when migrating from an old website).'
    )

    feed_google = models.BooleanField(
        verbose_name='Google Feed',
        db_index=True,
        default=False,
        help_text='Include this product in Google Feed.'
    )

    feed_amazon = models.BooleanField(
        verbose_name='Amazon Feed',
        db_index=True,
        default=False,
        help_text='Include this product in Amazon Feed.'
    )

    image = models.ForeignKey(
        Media,
        verbose_name='Primary Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Choose the main image for this product that is used on the product listing page.'
    )

    gallery_images = GenericRelation(
        MediaGallery,
        content_type_field='content_type',
        object_id_field='target_id'
    )

    _related_products = models.ManyToManyField(
        get_product_model_name(),
        through=RelatedProducts,
        editable=False
    )


    @classmethod
    def get_form(cls):
        from cubane.ishop.apps.merchant.products.forms import ProductFormBase
        return ProductFormBase


    @classmethod
    def filter_legacy_url(cls, url):
        """
        Filter by legacy url.
        """
        return cls.objects.filter(legacy_url=url, draft=False)[0]


    @property
    def primary_category(self):
        """
        Return the primary category of this product.
        """
        if not hasattr(self, '_primary_category'):
            if settings.SHOP_MULTIPLE_CATEGORIES:
                self._primary_category = None
                category_model = get_category_model()
                for assignment in self.categories.all():
                    if isinstance(assignment, category_model):
                        category = assignment
                    else:
                        category = assignment.category

                    if category.enabled:
                        self._primary_category = category
                        break
            else:
                self._primary_category = self.category

        return self._primary_category


    def can_execute_action(self, action):
        """
        Return True, if we can perform the given action on this product
        within the backend.
        """
        view = action.get('view')

        if view == 'sku':
            return self.sku_enabled
        else:
            return True


    @property
    def deposit_only(self):
        """
        Return True, if this product is available for deposit only.
        """
        return self.is_pre_order and self.deposit is not None


    @property
    def variety_preview_options(self):
        """
        Return (cached) variety preview option record that was 'injected' into
        this product for the purpose of presenting variety option information
        alongside a product, for example on a product listing page.
        """
        if hasattr(self, '_variety_preview_options'):
            return self._variety_preview_options
        else:
            return None


    @property
    def stocklevel_display(self):
        """
        Return availability text depending on stock level for this product.
        """
        if self.stock == self.STOCKLEVEL_AVAILABLE:
            return self.STOCKLEVEL_MSG_AVAILABLE
        elif self.stock == self.STOCKLEVEL_OUT_OF_STOCK:
            return self.STOCKLEVEL_MSG_OUT_OF_STOCK
        elif self.stock == self.STOCKLEVEL_AUTO:
            if self.stocklevel > 0:
                return self.STOCKLEVEL_MSG_AVAILABLE
            else:
                return self.STOCKLEVEL_MSG_OUT_OF_STOCK
        elif self.stock == self.STOCKLEVEL_MADE_TO_ORDER:
            return self.STOCKLEVEL_MSG_MADE_TO_ORDER
        else:
            return ''


    @property
    def is_available(self):
        """
        Return True, if the product is available (in stock or made to order).
        """
        return (
            self.pre_order or
            self.stock == self.STOCKLEVEL_AVAILABLE or
            (self.stock == self.STOCKLEVEL_AUTO and self.stocklevel > 0) or \
            self.stock == self.STOCKLEVEL_MADE_TO_ORDER
        )


    def can_be_added_to_basket(self, request):
        """
        Return True, property to be override by external logic to prevent item
        from being added to basket.
        """
        return True


    @property
    def is_pre_order(self):
        """
        Return True, if this product is pre order only.
        """
        return self.pre_order


    @property
    def is_pre_order(self):
        """
        Return True, if the product is pre order
        """
        return self.pre_order


    @property
    def is_made_to_order(self):
        """
        Return True, if the product is made to order.
        """
        return self.stock == self.STOCKLEVEL_MADE_TO_ORDER or self.pre_order


    @property
    def available_display(self):
        """
        Return human-readable display value for availability, e.g.
        In Stock / Pre Order etc.
        """
        if self.is_available:
            if self.is_pre_order:
                return 'Pre-Order'
            else:
                return 'In Stock'
        else:
            return 'Out of Stock'


    @property
    def gallery(self):
        """
        Return a (cached) list of gallery images that are assigned to this
        product.
        """
        if not hasattr(self, '_cached_gallery'):
            media = self.gallery_images.select_related('media').order_by('seq')
            self._cached_gallery = list([m.media for m in media])
        return self._cached_gallery


    @property
    def has_varieties(self):
        """
        Return True, if this product has any varieties.
        """
        if not hasattr(self, '_has_varieties_cached'):
            self._has_varieties_cached = self.varieties.exclude(
                variety__style=Variety.STYLE_ATTRIBUTE
            ).filter(
                enabled=True,
                variety__enabled=True
            ).count() > 0
        return self._has_varieties_cached


    @property
    def related_products(self):
        """
        Return a (cached) list of related products that are assigned to this
        product.
        """
        if not hasattr(self, '_cached_related_products'):
            from cubane.ishop.views import get_shop
            shop = get_shop()

            if settings.SHOP_MULTIPLE_CATEGORIES:
                items = list(
                    shop.get_related_products()\
                        .prefetch_related(
                            Prefetch('to_product__categories', queryset=ProductCategory.objects.select_related('category').order_by('seq'))
                        )\
                        .filter(from_product=self.pk, to_product__draft=False)\
                        .order_by('seq')\
                        .distinct()
                )
            else:
                items = list(
                    shop.get_related_products()\
                        .filter(from_product=self.pk, to_product__draft=False)\
                        .order_by('seq')
                )

            self._cached_related_products = list([item.to_product for item in items])

        return self._cached_related_products


    @property
    def categories_display(self):
        """
        Return the display presentation of multiple categories assigned to
        this product.
        """
        display = ', '.join([unicode(assignment) for assignment in self.categories.all()])
        if not display:
            display = None
        return display


    def set_varity_preview(self, options):
        """
        Set cached variety preview option for this product. When listing
        products on a category page, some varieties may be presented on
        the listing page alongside each product. While such variety information
        is fetched outside of the product listing, it is then 'injected' into
        each product record as part of the listing using set_variety_preview().
        """
        self._variety_preview_options = options


    def get_slug(self):
        """
        Return the slug for this product.
        """
        return self.slug


    def get_filepath(self):
        """
        Return path to cache file for this page.
        """
        return get_filepath_from_url('shop.product', args=[self.slug, self.pk])


    def get_brand_title(self):
        """
        Virtual: Return the title of the brand for this product.
        """
        return None


    def to_dict(self, extras=None):
        """
        Return a dictionary representation of this product, which is primarily
        used to encode product information as JSON.
        """
        d = {
            'id': self.pk,
            'title': self.title,
            'slug': self.slug,
            'url': self.get_absolute_url()
        }

        if extras is not None:
            d.update(extras)

        return d


    def to_ga_dict(self, extras=None):
        """
        Return product information that is used for Google Analytics eCommerce
        Integration of this product.
        """
        category = self.category.title if self.category is not None else None

        d = {
            'id': self.id,
            'name': self.title,
            'category': category
        }

        if extras is not None:
            d.update(extras)

        return d


    def get_absolute_url(self):
        """
        Return the absolute url for the product page for this product including
        the slug of the product and its primary key.
        """
        return get_absolute_url('shop.product', [self.slug, self.pk])


    def __unicode__(self):
        return '%s' % self.title


class CategoryBase(
    DateTimeBase,
    NavigationMixin,
    HierarchyMixin,
    ExcerptMixin,
    SEOMixin
):
    """
    Base class for shop product categories.
    """
    class Meta:
        abstract = True
        ordering            = ['seq', 'title']
        verbose_name        = 'Category'
        verbose_name_plural = 'Categories'


    class Listing:
        columns = [
            'title',
            '_meta_description',
            'parent',
            'ordering_default|Product Ordering',
            'enabled'
        ]
        edit_view = True
        grid_view = True
        sortable = True
        filter_by = [
            'title',
            'slug',
            '_meta_title',
            '_meta_description',
            '_meta_keywords',
            'parent',
            '_nav',
            'navigation_title',
            'enabled',
            'google_product_category'
        ]
        data_export = True
        data_columns = [
            'id',
            'slug',
            'title',
            '_meta_title:as(meta_title)',
            '_meta_description:as(meta_description)',
            '_meta_keywords:as(keywords)',
            'parent',
            '_nav:as(navigation)',
            'navigation_title',
            'enabled',
            'google_product_category'
        ]


    title = models.CharField(
        verbose_name='Title',
        max_length=120,
        db_index=True
    )

    slug = models.SlugField(
        verbose_name='Slug',
        max_length=120,
        db_index=True,
        unique=True
    )

    description = EditableHtmlField(
        verbose_name='Description',
        null=True,
        blank=True
    )

    parent = models.ForeignKey(
        'self',
        verbose_name='Parent Category',
        null=True,
        blank=True,
        related_name='siblings'
    )

    _legacy_urls = models.TextField(
        verbose_name='Legacy Urls',
        db_column='legacy_urls',
        db_index=True,
        null=True,
        blank=True,
        help_text='Path only, no domain name. Alternate urls for legacy ' + \
                  'purposes (only applies when migrating from an old ' + \
                  'website). One URL per line.'
    )

    seq = models.IntegerField(
        verbose_name='Seq',
        db_index=True,
        default=1
    )

    navigation_title = models.CharField(
        verbose_name='Navigation Title',
        max_length=255,
        null=True,
        blank=True,
        help_text='Override the regular title that is used within the ' + \
                  'navigation of the website.'
    )

    enabled = models.BooleanField(
        verbose_name='Enabled',
        db_index=True,
        default=True,
        help_text='Only enabled categories are visible to customers.'
    )

    auth_required = models.BooleanField(
        verbose_name='Authentication required',
        default=False,
        help_text='Only registered shoppers can access this category and must be logged in to do so.'
    )

    ordering_default = models.CharField(
        verbose_name='Default Order',
        max_length=64,
        choices=ProductBase.ORDER_BY_CHOICES,
        null=True,
        blank=True,
        help_text='Select the default order in which products are presented, if a natural order cannot be used because products of sub-categories are listed as well.'
    )

    google_product_category = models.CharField(
        verbose_name='Google Product Category',
        max_length=255,
        null=True,
        blank=True,
        choices=get_google_categories(),
        help_text='Choose the most appropriate google product category that matches this category.'
    )

    image = models.ForeignKey(
        Media,
        verbose_name='Primary Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Select an image that is used to represent this entity ' +
                  'within a list of entities.'
    )

    gallery_images = GenericRelation(
        MediaGallery,
        content_type_field='content_type',
        object_id_field='target_id'
    )


    @classmethod
    def get_form(cls):
        """
        Return the default form for editing categories in the backend.
        """
        from cubane.ishop.apps.merchant.categories.forms import CategoryFormBase
        return CategoryFormBase


    @classmethod
    def filter_legacy_url(cls, url):
        """
        Filter by legacy url.
        """
        return cls.objects.filter(
            Q(_legacy_urls=url) |
            Q(_legacy_urls__endswith='\n%s' % url) |
            Q(_legacy_urls__startswith='%s\n' % url) |
            Q(_legacy_urls__contains='\n%s\n' % url),
            enabled=True
        )[0]


    def get_taxonomy_path(self):
        """
        Return a string that describes the taxonomy path of this category
        including all its parents starting from the root in the format
        a > b > ... > c.
        """
        return u' > '.join([c.title.strip() for c in self.get_path()])


    def get_absolute_url(self):
        """
        Return the absolute url for this category.
        """
        return get_absolute_url('shop.category', [self.slug, self.pk])


    def get_slug(self):
        """
        Return the slug for this category.
        """
        return self.slug


    def get_filepath(self):
        """
        Return path to cache file for this page.
        """
        return get_filepath_from_url('shop.category', args=[self.slug, self.pk])


    def get_title_and_parent_title(self):
        """
        Return the title of the parent category and this category, if this
        category has a parent in the format Parent > Category; otherwise
        only return the title of this category if there is no parent.
        """
        if self.parent_id:
            return '%s / %s' % (self.parent.title.strip(), self.title.strip())
        else:
            return '%s' % self.title.strip()


    def get_legacy_urls(self):
        """
        Return a list of legacy urls for this category.
        """
        if self._legacy_urls:
            return filter(
                lambda url: url,
                [url.strip() for url in self._legacy_urls.split('\n')]
            )
        else:
            return []


    def set_legacy_urls(self, legacy_urls):
        """
        Set the list of legacy urls for this category.
        """
        self._legacy_urls = '\n'.join(filter(
            lambda url: url,
            [url.strip() for url in legacy_urls])
        )


    legacy_urls = property(get_legacy_urls, set_legacy_urls)


    def to_dict(self, extras=None):
        """
        Return dictionary representation of this category.
        """
        d = {
            'id': self.pk,
            'title': self.title,
            'slug': self.slug,
            'url': self.get_absolute_url()
        }

        if extras != None:
            d.update(extras)

        return d


    def __unicode__(self):
        return self.title


class Voucher(DateTimeBase):
    """
    Discount Voucher Code.
    """
    class Listing:
        columns = [
            'title',
            'code',
            'valid_from',
            'valid_until',
            '/max_usage',
            '/used',
            'enabled'
        ]
        filter_by = [
            'title',
            'code',
            'valid_from',
            'valid_until',
            'max_usage',
            'discount_type',
            'discount_value',
            'enabled'
        ]
        edit_view = False
        data_export = True
        data_columns = [
            'title',
            'code',
            'valid_from',
            'valid_until',
            'max_usage',
            'discount_type',
            'discount_value',
            'enabled'
        ]


    DISCOUNT_PERCENTAGE    = 0
    DISCOUNT_PRICE         = 1
    DISCOUNT_FREE_DELIVERY = 2
    DISCOUNT_TYPE_CHOICES = (
        (DISCOUNT_PERCENTAGE,    'Percentage (%)'),
        (DISCOUNT_PRICE,         'Fixed Amount (£)'),
        (DISCOUNT_FREE_DELIVERY, 'Free Delivery')
    )
    DISCOUNT_VALUE_REQUIRED = [
        DISCOUNT_PERCENTAGE,
        DISCOUNT_PRICE
    ]


    title = models.CharField(
        verbose_name='Title',
        max_length=255,
        db_index=True,
        help_text='Presented to the customer when this voucher is redeemed.'
    )

    code = models.CharField(
        verbose_name='Code',
        max_length=255,
        db_index=True,
        unique=True,
        help_text='Unique code that must be entered by customers to ' + \
                  'redeem this voucher (No spaces, UPPERCASE).'
    )

    enabled = models.BooleanField(
        verbose_name='Enabled',
        default=True,
        db_index=True,
        help_text='Only enabled discount codes can be redeemed.'
    )

    max_usage = models.IntegerField(
        verbose_name='Max. Usage',
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text='Limit the amount of times this voucher can be redeemed. ' + \
                  'If no max. usage limit or zero (0) is given, the ' + \
                  'voucher can be used infinite times within the valid ' + \
                  'redemption period.',
    )

    valid_from = models.DateField(
        verbose_name='Valid From',
        db_index=True,
        null=True,
        blank=False,
        help_text='Optional: Start date (inclusive).'
    )

    valid_until = models.DateField(
        verbose_name='Valid Until',
        db_index=True,
        null=True,
        blank=False,
        help_text='Optional: End date (inclusive).'
    )

    discount_type = models.IntegerField(
        verbose_name='Type of Discount',
        choices=DISCOUNT_TYPE_CHOICES,
        default=DISCOUNT_PERCENTAGE,
        help_text='Type of discount: Percentage or Fixed Amount (Reduction).'
    )

    discount_value = models.DecimalField(
        verbose_name='Discount Value',
        max_digits=12,
        decimal_places=2,
        default=0,
        blank=True,
        help_text='Discount Amount (Percentage or Amount). For percentage ' + \
                  'enter 10 for 10% for example.'
    )

    categories = models.ManyToManyField(
        get_category_model_name(),
        verbose_name='Categories',
        blank=True,
        help_text='Limit products for which this voucher may apply per ' + \
                  'category. Individual products may not qualify for discounts.'
    )

    delivery_countries = models.ManyToManyField(
        Country,
        verbose_name='Delivery Countries',
        blank=True,
        help_text='Limit delivery countries for which this voucher may apply.'
    )


    @property
    def used(self):
        """
        Return the amount of times this voucher has been used.
        """
        return self.orders.filter(status__in=OrderBase.SUCCESSFUL_STATUS).count()


    def is_available(self):
        """
        Return True, if the voucher is available in terms of its max. usage.
        """
        if self.max_usage is not None:
            return self.used < self.max_usage
        else:
            return True


    def is_restricted_by_countries(self):
        """
        Return True, if the voucher is restricted by delivery countries.
        """
        if not hasattr(self, '_restricted_by_countries'):
            self._restricted_by_countries = self.delivery_countries.count() > 0
        return self._restricted_by_countries


    def matches_delivery_country(self, delivery_country):
        """
        Return True, if the given delivery country matches the voucher's set
        of valid delivery countries.
        """
        if self.is_restricted_by_countries():
            if delivery_country:
                return self.delivery_countries.filter(pk=delivery_country.pk).count() > 0
            else:
                return False
        else:
            return True


    def __unicode__(self):
        return '%s' % self.title


class OrderManager(models.Manager):
    """
    Manager for shop orders.
    """
    def get_processing_orders(self, user, days=7):
        """
        Return all orders for the given user that have been updated in the
        last n days and are currently being processed.
        """
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        return self.filter(customer=user).filter(
            Q(status__in=OrderBase.USER_PROCESSING_STATUS) |
            Q(status__in=OrderBase.USER_PROCESSING_NOT_PAID_STATUS, updated_on__gte=start_date)
        ).order_by('-updated_on')


    def get_complete_orders(self, user):
        """
        Return all orders for the given user that have been completed and are no
        longer processed. An order is completed once the order has been fully
        shipped or fully collected.
        """
        return self.filter(customer=user).filter(status__in=OrderBase.USER_COMPLETED_STATUS).order_by('-updated_on')


class OrderBase(DateTimeBase):
    """
    Shop order.
    """
    class Meta:
        abstract            = True
        db_table            = 'ishop_orders'
        ordering            = ['-created_on']
        verbose_name        = 'Order'
        verbose_name_plural = 'Orders'
        unique_together     = ('order_id',)


    class Listing:
        columns = [
            'customer_email_display|Customer',
            'order_id',
            'status',
            'approval_status',
            '/payment_method|Payment',
            '/-total|Total|currency',
            'created_on'
        ]
        filter_by = [
            'order_id',
            'status',
            'approval_status',
            'finance_option',
            'loan_status',

            'delivery_quote',

            'full_name',
            'email',
            'telephone',

            'billing_company',
            'billing_address1',
            'billing_address2',
            'billing_address3',
            'billing_city',
            'billing_county',
            'billing_postcode',
            'billing_country',

            'delivery_name',
            'delivery_company',
            'delivery_address1',
            'delivery_address2',
            'delivery_address3',
            'delivery_city',
            'delivery_county',
            'delivery_postcode',
            'delivery_country',

            'voucher',
            'tracking_provider',
            'tracking_code',
            'basket_size',

            'filter_created_on_type',
            'filter_created_on',

            'is_invoice',
            'invoice_number'
        ]
        searchable = [
            'full_name',
            'email',
            'telephone',
            'postcode',
            'tracking_code',
            'invoice_number'
        ]
        default_view = 'list-compact'
        edit_view = False
        data_export = True
        data_columns = [
            'order_id',
            'get_status_display:as(order_status)',
            'get_approval_status_display:as(approval_status)',
            'delivery_quote',
            'full_name',
            'email',
            'telephone',
            'billing_company',
            'billing_address1',
            'billing_address2',
            'billing_address3',
            'billing_city',
            'billing_county',
            'billing_postcode',
            'billing_country',
            'delivery_name',
            'delivery_company',
            'delivery_address1',
            'delivery_address2',
            'delivery_address3',
            'delivery_city',
            'delivery_county',
            'delivery_postcode',
            'delivery_country',
            'voucher_code',
            'tracking_provider',
            'tracking_code',
            'basket_size',
            'special_requirements',
            'sub_total',
            'delivery',
            'total',
            'preauth',
            'settled',
            'aborted',
            'is_invoice',
            'invoice_number'
        ]


    # address components
    ADDRESS_COMPONENT_NAMES = [
        'address1',
        'address2',
        'address3',
        'city',
        'county',
        'postcode',
        'country'
    ]

    # payment status
    STATUS_PAYMENT_AWAITING     = 1
    STATUS_PAYMENT_CANCELLED    = 2
    STATUS_PAYMENT_DECLINED     = 3
    STATUS_PAYMENT_ERROR        = 4
    STATUS_PAYMENT_CONFIRMED    = 6
    STATUS_PLACED_INVOICE       = 7
    STATUS_PROCESSING           = 8
    STATUS_PARTIALLY_SHIPPED    = 10
    STATUS_SHIPPED              = 11
    STATUS_CHECKOUT             = 12
    STATUS_READY_TO_COLLECT     = 13
    STATUS_COLLECTED            = 14
    STATUS_CHECKOUT_INVOICE     = 15
    STATUS_NEW_ORDER            = 16
    STATUS_CHECKOUT_ZERO_AMOUNT = 17
    STATUS_PLACED_ZERO_AMOUNT   = 18
    STATUS_CHOICES = (
        (STATUS_CHECKOUT,             'Ready for Payment'),
        (STATUS_CHECKOUT_INVOICE,     'Ready for Placement (Invoice)'),
        (STATUS_CHECKOUT_ZERO_AMOUNT, 'Ready for Placement (Zero Amount)'),
        (STATUS_NEW_ORDER,            'New Order'),
        (STATUS_PAYMENT_AWAITING,     'Awaiting Payment'),
        (STATUS_PAYMENT_CANCELLED,    'Order Cancelled'),
        (STATUS_PAYMENT_DECLINED,     'Payment Declined'),
        (STATUS_PAYMENT_ERROR,        'Payment Error'),
        (STATUS_PAYMENT_CONFIRMED,    'Order Placed'),
        (STATUS_PLACED_INVOICE,       'Order Placed (Invoice)'),
        (STATUS_PLACED_ZERO_AMOUNT,   'Order Placed (Zero Amount)'),
        (STATUS_PROCESSING,           'Processing'),
        (STATUS_PARTIALLY_SHIPPED,    'Partially Shipped'),
        (STATUS_SHIPPED,              'Shipped'),
        (STATUS_READY_TO_COLLECT,     'Ready To Collect'),
        (STATUS_COLLECTED,            'Collected'),
    )

    @property
    def next_status(self):
        choices = []
        if self.status in [self.STATUS_NEW_ORDER, self.STATUS_CHECKOUT]:
            choices = [self.STATUS_PAYMENT_AWAITING]

        if self.status == self.STATUS_PAYMENT_AWAITING:
            choices = [self.STATUS_PAYMENT_AWAITING]

        if self.status in [self.STATUS_PAYMENT_CONFIRMED, self.STATUS_PLACED_INVOICE, self.STATUS_PLACED_ZERO_AMOUNT]:
            choices = [self.STATUS_PROCESSING]

        if self.status == self.STATUS_PROCESSING:
            if self.is_click_and_collect:
                choices = [self.STATUS_READY_TO_COLLECT]
            else:
                choices = [self.STATUS_PARTIALLY_SHIPPED, self.STATUS_SHIPPED]

        if self.status == self.STATUS_PARTIALLY_SHIPPED:
            choices = [self.STATUS_SHIPPED]

        if self.status == self.STATUS_READY_TO_COLLECT:
            choices = [self.STATUS_COLLECTED]

        # rejected
        if self.approval_status == self.APPROVAL_STATUS_REJECTED:
            choices = []

        results = None
        for choice in choices:
            if not results:
                results = []
            result = choice, get_choices_display(self.STATUS_CHOICES, choice)
            results.append(result)

        return results


    # map status to colour indication
    STATUS_INDICATORS = {
        STATUS_PAYMENT_AWAITING:   'warning',
        STATUS_PAYMENT_CANCELLED:  'error',
        STATUS_PAYMENT_DECLINED:   'error',
        STATUS_PAYMENT_ERROR:      'error',
        STATUS_PAYMENT_CONFIRMED:  'progress',
        STATUS_PLACED_INVOICE:     'progress',
        STATUS_PLACED_ZERO_AMOUNT: 'progress',
        STATUS_PROCESSING:         'progress',
        STATUS_PARTIALLY_SHIPPED:  'progress',
        STATUS_SHIPPED:            'success',
        STATUS_CHECKOUT:           'warning',
        STATUS_READY_TO_COLLECT:   'progress',
        STATUS_COLLECTED:          'success',
        STATUS_CHECKOUT_INVOICE:   'warning',
        STATUS_NEW_ORDER:          'warning',
    }

    # status description test
    STATUS_TEXT = {
        STATUS_PAYMENT_AWAITING: 'Your order is ready, in order to complete it please use our secure payment gateway by clicking the Pay Now button below.',
        STATUS_PAYMENT_CANCELLED: 'Your order has been cancelled. Please retry if you want to make your order again.',
        STATUS_PAYMENT_DECLINED: 'Sorry something went wrong and your order was declined. Please try again or come in store to make your purchase.',
        STATUS_PAYMENT_ERROR: 'There seems to have been an error with the payment. Please try again.',
        STATUS_PAYMENT_CONFIRMED: 'Your order has been placed and is currently being processed. Please come back later to see if your status has changed.',
        STATUS_PLACED_INVOICE: 'Your order has been placed and is currently being processed. Please come back later to see if your status has changed.',
        STATUS_PLACED_ZERO_AMOUNT: 'Your order has been placed and is currently being processed. Please come back later to see if your status has changed.',
        STATUS_PARTIALLY_SHIPPED: 'Some of your order has been shipped and will be with you shortly.',
        STATUS_SHIPPED: 'Your order has been shipped and should be with you shortly.',
        STATUS_CHECKOUT: 'Your order is ready, in order to complete it please use our secure payment gateway by clicking the Pay Now button below.',
        STATUS_CHECKOUT_INVOICE: 'Your order is ready to be placed. Click the button to continue. Your will be invoiced.',
        STATUS_CHECKOUT_ZERO_AMOUNT: 'Your order is ready to be placed. Click the button to continue. No payment is required for this order.',
        STATUS_NEW_ORDER: 'Your order is currently being created.',
        STATUS_READY_TO_COLLECT: 'Your order is now ready to collect from store.',
        STATUS_COLLECTED: 'Your order has been collected.',
        STATUS_PROCESSING: 'Your order is currently being processed.'
    }

    # processing order status (backend)
    PROCESSING_STATUS = [
        STATUS_PAYMENT_CONFIRMED,
        STATUS_PLACED_INVOICE,
        STATUS_PLACED_ZERO_AMOUNT,
        STATUS_PROCESSING,
        STATUS_PARTIALLY_SHIPPED,
        STATUS_READY_TO_COLLECT
    ]

    # processing order status (user)
    USER_PROCESSING_STATUS = [
        STATUS_PAYMENT_CONFIRMED,
        STATUS_PLACED_INVOICE,
        STATUS_PLACED_ZERO_AMOUNT,
        STATUS_PARTIALLY_SHIPPED,
        STATUS_READY_TO_COLLECT,
        STATUS_PROCESSING
    ]

    # not paid orders (user)
    USER_PROCESSING_NOT_PAID_STATUS = [
        STATUS_PAYMENT_AWAITING,
        STATUS_CHECKOUT,
    ]

    # Completed order status: An order does not need any further attention.
    # May contain orders with errors.
    USER_COMPLETED_STATUS = [
        STATUS_SHIPPED,
        STATUS_COLLECTED,
        STATUS_PAYMENT_CANCELLED,
        STATUS_PAYMENT_DECLINED,
        STATUS_PAYMENT_ERROR
    ]

    # Successful status: Any order that has been placed successfully.
    SUCCESSFUL_STATUS = [
        STATUS_PAYMENT_CONFIRMED,
        STATUS_PLACED_INVOICE,
        STATUS_PLACED_ZERO_AMOUNT,
        STATUS_PARTIALLY_SHIPPED,
        STATUS_SHIPPED,
        STATUS_READY_TO_COLLECT,
        STATUS_COLLECTED
    ]

    # order status where the order can still be edited in the backend
    # (e.g. no payment has been processed yet)
    NOT_FROZEN_STATUS = [
        STATUS_NEW_ORDER
    ]

    # successfully fulfilled
    FULFILLED_STATUS = [
        STATUS_SHIPPED,
        STATUS_COLLECTED
    ]

    # successfully canceled
    CANCELLED_STATUS = [
        STATUS_PAYMENT_CANCELLED
    ]

    # invoice-related only
    INVOICE_STATUS = [
        STATUS_CHECKOUT_INVOICE,
        STATUS_PLACED_INVOICE,
        STATUS_PAYMENT_CANCELLED,
        STATUS_PARTIALLY_SHIPPED,
        STATUS_SHIPPED,
        STATUS_READY_TO_COLLECT,
        STATUS_COLLECTED,
        STATUS_PROCESSING
    ]

    # zero amount checkout only
    ZERO_AMOUNT_CHECKOUT_STATUS = [
        STATUS_CHECKOUT_ZERO_AMOUNT,
        STATUS_PLACED_ZERO_AMOUNT,
        STATUS_PROCESSING,
        STATUS_PARTIALLY_SHIPPED,
        STATUS_SHIPPED,
        STATUS_READY_TO_COLLECT,
        STATUS_COLLECTED
    ]

    # payment-related only
    PAYMENT_STATUS = [
        STATUS_PAYMENT_AWAITING,
        STATUS_PAYMENT_CANCELLED,
        STATUS_PAYMENT_DECLINED,
        STATUS_PAYMENT_ERROR,
        STATUS_PAYMENT_CONFIRMED,
        STATUS_PARTIALLY_SHIPPED,
        STATUS_SHIPPED,
        STATUS_READY_TO_COLLECT,
        STATUS_COLLECTED,
        STATUS_PROCESSING
    ]

    # created via backend (customer not present)
    CUSTOMER_NOT_PRESENT_STATUS = [
        STATUS_NEW_ORDER,
        STATUS_PAYMENT_AWAITING,
        STATUS_PAYMENT_CANCELLED,
        STATUS_PAYMENT_DECLINED,
        STATUS_PAYMENT_ERROR,
        STATUS_PAYMENT_CONFIRMED,
        STATUS_PROCESSING,
        STATUS_PARTIALLY_SHIPPED,
        STATUS_SHIPPED,
        STATUS_READY_TO_COLLECT,
        STATUS_COLLECTED,
    ]

    # payment status (backend)
    BACKEND_STATUS_CHOICES_FILTER = (
        (STATUS_CHECKOUT,             'Ready for Payment'),
        (STATUS_CHECKOUT_INVOICE,     'Ready for Placement (Invoice)'),
        (STATUS_CHECKOUT_ZERO_AMOUNT, 'Ready for Placement (Zero Amount)'),
        (STATUS_NEW_ORDER,            'New Order'),
        (STATUS_PAYMENT_AWAITING,     'Payment: Awaiting'),
        (STATUS_PAYMENT_CANCELLED,    'Payment: Cancelled'),
        (STATUS_PAYMENT_DECLINED,     'Payment: Declined'),
        (STATUS_PAYMENT_ERROR,        'Payment: Error'),
        (STATUS_PAYMENT_CONFIRMED,    'Payment: Confirmed'),
        (STATUS_PLACED_INVOICE,       'Order Placed (Invoice)'),
        (STATUS_PLACED_ZERO_AMOUNT,   'Order Placed (Zero Amount)'),
        (STATUS_PROCESSING,           'Processing'),
        (STATUS_PARTIALLY_SHIPPED,    'Partially Shipped'),
        (STATUS_SHIPPED,              'Shipped'),
        (STATUS_READY_TO_COLLECT,     'Ready To Collect'),
        (STATUS_COLLECTED,            'Collected')
    )

    # approval status
    APPROVAL_STATUS_NONE     = 1
    APPROVAL_STATUS_WAITING  = 2
    APPROVAL_STATUS_APPROVED = 3
    APPROVAL_STATUS_REJECTED = 4
    APPROVAL_STATUS_TIMEOUT  = 5
    APPROVAL_STATUS_CHOICES = (
        (APPROVAL_STATUS_NONE,     'No approval'),
        (APPROVAL_STATUS_WAITING,  'Waiting for Approval'),
        (APPROVAL_STATUS_APPROVED, 'Approved'),
        (APPROVAL_STATUS_REJECTED, 'Rejected'),
        (APPROVAL_STATUS_TIMEOUT,  'Timeout'),
    )

    # loan status
    LOAN_STATUS_NONE                = 0
    LOAN_STATUS_PREDECLINE          = 1
    LOAN_STATUS_ACCEPT              = 2
    LOAN_STATUS_DECLINE             = 3
    LOAN_STATUS_REFER               = 4
    LOAN_STATUS_VERIFIED            = 5
    LOAN_STATUS_AMENDED             = 6
    LOAN_STATUS_FULFILLED           = 7
    LOAN_STATUS_COMPLETE            = 8
    LOAN_STATUS_CANCELLED           = 9
    LOAN_STATUS_ACTION_CUSTOMER     = 10
    LOAN_STATUS_ACTION_RETAILER     = 11
    LOAN_STATUS_INFO_NEEDED         = 12
    LOAN_STATUS_CHOICES = (
        (LOAN_STATUS_NONE, 'Pending'),
        (LOAN_STATUS_PREDECLINE, 'Predecline'),
        (LOAN_STATUS_ACCEPT, 'Accept'),
        (LOAN_STATUS_DECLINE, 'Decline'),
        (LOAN_STATUS_REFER, 'Refer'),
        (LOAN_STATUS_VERIFIED, 'Verified'),
        (LOAN_STATUS_AMENDED, 'Amended'),
        (LOAN_STATUS_FULFILLED, 'Fulfilled'),
        (LOAN_STATUS_COMPLETE, 'Complete'),
        (LOAN_STATUS_CANCELLED, 'Cancelled'),
        (LOAN_STATUS_ACTION_CUSTOMER, 'Action Customer'),
        (LOAN_STATUS_ACTION_RETAILER, 'Action Retailer'),
        (LOAN_STATUS_INFO_NEEDED, 'Info Needed'),
    )

    LOAN_STATUS_TEXT = {
        LOAN_STATUS_NONE: None,
        LOAN_STATUS_PREDECLINE: 'The credit application has been declined by CreditSentry.',
        LOAN_STATUS_ACCEPT: 'The credit application has been accepted for finance which is valid for 90 days.',
        LOAN_STATUS_DECLINE: 'The credit application has been declined for finance.',
        LOAN_STATUS_REFER: 'The credit application has been given a refer decision which requires manual decision from the lender to be either declined or accepted.',
        LOAN_STATUS_VERIFIED: 'The customer has successfully paid their deposit.',
        LOAN_STATUS_AMENDED: 'The credit application has been amended and is awaiting the consumer\'s approval.',
        LOAN_STATUS_FULFILLED: 'The retailer has notified Deko that they have fulfilled the order. Fulfilment is defined as the consumer having receipt of all items eg their complete order.',
        LOAN_STATUS_COMPLETE: 'The credit application has been included in a settlement payment from the lender to the retailer.',
        LOAN_STATUS_CANCELLED: 'The credit application has been cancelled and the deposit refunded if it was paid.',
        LOAN_STATUS_ACTION_CUSTOMER: 'The customer has been accepted, paid their deposit but the application requires an ID upload to proceed.',
        LOAN_STATUS_ACTION_RETAILER: 'The customer\'s identity document could not be validated and it is down to the lender to take action.',
        LOAN_STATUS_INFO_NEEDED: None,
    }


    # delivery type choices (backend)
    BACKEND_DELIVERY_TYPE_DELIVERY          = 1
    BACKEND_DELIVERY_TYPE_CLICK_AND_COLLECT = 2
    BACKEND_DELIVERY_TYPE_CHOICES = (
        (BACKEND_DELIVERY_TYPE_DELIVERY,          'Delivery'),
        (BACKEND_DELIVERY_TYPE_CLICK_AND_COLLECT, 'Click and Collect'),
    )


    # customer
    customer = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # order id and status
    secret_id = models.CharField(
        max_length=255,
        db_index=True,
        unique=True,
        null=True,
        blank=True,
        editable=False
    )

    order_id = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=True,
        editable=False
    )

    custom_order_id = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=True
    )

    status = models.IntegerField(
        choices=STATUS_CHOICES
    )

    approval_status = models.IntegerField(
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_STATUS_NONE,
        editable=False
    )

    loan_status = models.IntegerField(
        choices=LOAN_STATUS_CHOICES,
        default=LOAN_STATUS_NONE,
        editable=False
    )

    reject_msg = models.TextField(
        null=True,
        blank=True,
        editable=False
    )

    cancel_msg = models.TextField(
        null=True,
        blank=True,
        editable=False
    )

    finance_option = models.ForeignKey(
        FinanceOption,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    loan_deposit = models.IntegerField(
        verbose_name='Loan Deposit',
        db_index=True,
        null=True,
        blank=True
    )


    is_backend_payment = models.BooleanField(default=False, editable=False)


    # states
    customer_not_present = models.BooleanField(default=False, editable=False)
    cancelled = models.BooleanField(default=False)
    fulfilled = models.BooleanField(default=False)

    # billing, delivery address and products
    billing_address_json = models.TextField(
        null=True,
        editable=False
    )

    delivery_address_json = models.TextField(
        null=True,
        editable=False
    )

    basket_json = models.TextField(
        default='{}',
        editable=False
    )

    basket_json_v2 = models.TextField(
        null=True,
        editable=False
    )

    # delivery method
    delivery_option = models.ForeignKey(
        DeliveryOption,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    delivery_option_title = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    delivery_quote = models.BooleanField(
        default=False,
        db_index=True
    )

    click_and_collect = models.BooleanField(
        verbose_name='Click and Collect',
        default=False,
        db_index=True,
        help_text='Tick, if this order is a \'Click and Collect\' order.'
    )

    is_invoice = models.BooleanField(
        default=False,
        db_index=True,
        editable=False
    )

    invoice_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    is_zero_amount_checkout = models.BooleanField(
        default=False,
        db_index=True,
        editable=False
    )

    # general information (indexed)
    title = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    full_name = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=False
    )

    survey = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        editable=False
    )

    email = models.CharField(
        verbose_name='Email',
        max_length=255,
        db_index=True,
        null=True,
        blank=False,
        help_text='The email address of the customer.'
    )

    telephone = models.CharField(
        verbose_name='Telephone',
        max_length=40,
        db_index=True,
        null=True,
        blank=False,
        help_text='The telephone number of the customer.'
    )

    basket_size = models.IntegerField(
        db_index=True,
        default=0,
        editable=False
    )

    special_requirements = models.TextField(
        verbose_name='Special Requirements',
        null=True,
        blank=True,
        help_text='Special requirements for this order, for example instructions about delivery etc.'
    )

    # billing address (indexed)
    billing_company = models.CharField(
        verbose_name='Company',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    billing_address1 = models.CharField(
        verbose_name='Address 1',
        max_length=255,
        null=True,
        blank=False,
        db_index=True
    )

    billing_address2 = models.CharField(
        verbose_name='Address 2',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    billing_address3 = models.CharField(
        verbose_name='Address 3',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    billing_city = models.CharField(
        verbose_name='City',
        max_length=255,
        null=True,
        blank=False,
        db_index=True
    )

    billing_county = models.CharField(
        verbose_name='County',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    billing_postcode = models.CharField(
        verbose_name='Postcode',
        max_length=10,
        null=True,
        blank=False,
        db_index=True
    )

    billing_country = models.ForeignKey(
        Country,
        verbose_name='Country',
        null=True,
        blank=False,
        related_name='+'
    )

    # delivery address (indexed)
    delivery_name = models.CharField(
        verbose_name='Name',
        max_length=255,
        db_index=True,
        null=True,
        blank=True
    )

    delivery_company = models.CharField(
        verbose_name='Company',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    delivery_address1 = models.CharField(
        verbose_name='Address 1',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    delivery_address2 = models.CharField(
        verbose_name='Address 2',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    delivery_address3 = models.CharField(
        verbose_name='Address 3',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    delivery_city = models.CharField(
        verbose_name='City',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    delivery_county = models.CharField(
        verbose_name='County',
        max_length=255,
        null=True,
        blank=True,
        db_index=True
    )

    delivery_postcode = models.CharField(
        verbose_name='Postcode',
        max_length=10,
        null=True,
        blank=True,
        db_index=True
    )

    delivery_country = models.ForeignKey(
        Country,
        verbose_name='Country',
        null=True,
        blank=True,
        related_name='+'
    )

    free_delivery_to = models.BooleanField(
        default=False,
        editable=False
    )

    # voucher
    voucher_code = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    voucher_title = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    voucher_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
    )

    voucher = models.ForeignKey(
        Voucher,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders'
    )

    # money
    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_index=True,
        default=Decimal('0.00'),
        editable=False
    )

    sub_total_before_delivery = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_index=True,
        default=Decimal('0.00'),
        editable=False
    )

    delivery = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_index=True,
        default=Decimal('0.00'),
        editable=False
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        db_index=True,
        default=Decimal('0.00'),
        editable=False
    )

    # payment details
    transaction_id = models.CharField(
        max_length=255,
        null=True,
        db_index=True,
        editable=False
    )

    transaction_msg = models.TextField(
        null=True,
        blank=True,
        editable=False
    )

    preauth = models.BooleanField(
        default=False,
        db_index=True,
        editable=False
    )

    settled = models.BooleanField(
        default=False,
        db_index=True,
        editable=False
    )

    aborted = models.BooleanField(
        default=False,
        db_index=True,
        editable=False
    )

    preauth_transaction_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        editable=False
    )

    payment_confirmed_at = models.DateTimeField(
        db_index=True,
        null=True,
        editable=False
    )

    payment_gateway = models.IntegerField(
        db_index=True,
        null=True,
        blank=True,
        editable=False
    )

    _payment_details = models.TextField(
        null=True,
        blank=True,
        editable=False
    )

    # google analytics data sent
    ga_sent = models.BooleanField(
        default=False,
        db_index=True,
        editable=False
    )

    # delivery tracking
    tracking_provider = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    tracking_code = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )


    objects = OrderManager()


    @classmethod
    def get_form(cls):
        from cubane.ishop.apps.merchant.orders.forms import OrderForm
        return OrderForm


    @classmethod
    def get_filter_form(cls):
        """
        Return the form that is used by the backend to filter orders.
        """
        from cubane.ishop.apps.merchant.orders.forms import OrderFilterForm
        return OrderFilterForm


    @classmethod
    def create_empty_customer_not_present(cls, request):
        """
        Create a new (empty) order, usually this is used to create a new
        order via the backend. An empty order is marked as incomplete and must
        be completed before any notification emails are sent or the order can be
        processed.
        """
        # get shop
        from cubane.ishop.views import get_shop
        shop = get_shop()

        # create empty order
        order = get_order_model().objects.create(
            status = cls.STATUS_NEW_ORDER,
            customer_not_present = True,
            payment_gateway = shop.get_default_payment_gateway()
        )

        # generate identifiers
        order.order_id = request.context.generate_order_id(order)
        order.secret_id = request.context.generate_secret_order_id(order)
        order.save()

        return order


    @classmethod
    def create_from_basket(cls, request, basket, customer=None, order_id=None):
        """
        Create a new order based on the given basket and user with the given
        order reference id. If no reference id is given, a new order reference
        number is generated automatically. The initial status for the order
        is STATUS.CHECKOUT, which means that the order is in the process of
        being checked out. All major information, such as billing and delivery
        address information is taken from the basket.
        """
        # determine gateway to use for this basket
        from cubane.ishop.views import get_shop
        shop = get_shop()
        gateway = shop.get_payment_gateway_for_basket(basket)

        # initial order status
        if basket.is_invoice():
            initial_status = OrderBase.STATUS_CHECKOUT_INVOICE
        elif basket.total == Decimal('0.00'):
            initial_status = OrderBase.STATUS_CHECKOUT_ZERO_AMOUNT
        else:
            initial_status = OrderBase.STATUS_CHECKOUT

        # create order
        order = get_order_model()()

        # customer status and payment gateway
        order.customer = customer
        order.status = initial_status
        order.payment_gateway = gateway
        order.save()

        # save basket information
        order.save_basket(basket, create_order=True)

        # generate identifiers
        order.generate_identifiers(request, order_id)

        return order


    def save(self, *args, **kwargs):
        """
        Saves order state and invalidates cached information.
        """
        if hasattr(self, '_basket'): del self._basket
        if hasattr(self, '_billing_address'): del self._billing_address
        if hasattr(self, '_delivery_address'): del self._delivery_address

        super(OrderBase, self).save(*args, **kwargs)


    @property
    def remaining_balance(self):
        """
        Return the remaining balance for this order.
        """
        # invoice does not have a total
        if self.is_invoice:
            return Decimal('0.00')

        if self.payment_confirmed_at is None:
            # payment never happened, so remaining balance is total
            return self.total
        elif self.waits_for_approval():
            # payment happened (deferred), but order has not been approved yet
            return self.total
        elif self.is_rejected():
            # payment happened (deferred), but was then rejected
            return self.total
        else:
            # payment happened, remaining balance is
            return Decimal('0.00')


    @property
    def is_frozen(self):
        """
        An order becomes frozen whenever a money transaction has occurred. The
        basket content of a frozen order may not be altered. A new order is
        not frozen...
        """
        if self.pk:
            return (
                self.payment_confirmed_at is not None or
                self.status not in self.NOT_FROZEN_STATUS or
                self.fulfilled
            )
        else:
            return False


    @property
    def backend_basket_prefix(self):
        """
        Return the unique basket prefix that is used within the backend system
        to edit this order (the order might be a new order which has not been
        saved yet).
        """
        return self.pk if self.pk is not None else '__new__'


    @property
    def tax_total(self):
        """
        Return the total amount of tax based on a fixed percentage figure for
        VAT and the sub total of this order (excluding delivery charges).
        """
        from cubane.cms.views import get_cms
        settings = get_cms().settings

        if settings.tax_percent:
            return (settings.tax_percent * self.sub_total_before_delivery / Decimal('100.00')).quantize(Decimal('.01'))
        else:
            return Decimal('0.00')


    def get_status_text_display(self):
        """
        Return the description for the current order status.
        """
        return self.STATUS_TEXT.get(self.status, '')


    def get_tracking_provider_link(self):
        """
        Return the url for the tracking provider that is associated with this
        order or None.
        """
        for name, url in settings.TRACKING_PROVIDERS:
            if name == self.tracking_provider:
                return url
        return None


    @property
    def total_payment(self):
        """
        Return the total amount for payment.
        """
        return self.total


    @property
    def basket(self):
        """
        Return a non-persistent basket that represents this order.
        """
        if not hasattr(self, '_basket'):
            from cubane.ishop.basket import Basket
            self._basket = Basket.restore_from_order(self)
        return self._basket


    def save_basket(self, basket, create_order=False):
        """
        Save the content of the given basket in this order.
        """
        if create_order:
            # billing address
            billing_address = basket.billing_address
            if billing_address is None: billing_address = {}

            # delivery address
            delivery_address = basket.delivery_address
            if delivery_address is None: delivery_address = {}

            # full name
            full_name = '%s %s' % (
                billing_address.get('first_name'),
                billing_address.get('last_name')
            )

            # get county or state
            billing_country_iso = basket.billing_address_components.get('country-iso')
            if billing_country_iso == 'US':
                billing_county = basket.billing_address_components.get('state')
            else:
                billing_county = basket.billing_address_components.get('county')

            delivery_country_iso = basket.delivery_address_components.get('country-iso')
            if delivery_country_iso == 'US':
                delivery_county = basket.delivery_address_components.get('state')
            else:
                delivery_county = basket.delivery_address_components.get('county')

            # billing address
            self.full_name = full_name
            self.billing_company = basket.billing_address_components.get('company')
            self.billing_address1 = basket.billing_address_components.get('address1')
            self.billing_address2 = basket.billing_address_components.get('address2')
            self.billing_address3 = basket.billing_address_components.get('address3')
            self.billing_city = basket.billing_address_components.get('city')
            self.billing_county = billing_county
            self.billing_postcode = basket.billing_address_components.get('postcode')
            self.billing_country = basket.billing_address_components.get('country')

            # delivery address
            self.delivery_name = basket.delivery_address_components.get('name')
            self.delivery_company = basket.delivery_address_components.get('company')
            self.delivery_address1 = basket.delivery_address_components.get('address1')
            self.delivery_address2 = basket.delivery_address_components.get('address2')
            self.delivery_address3 = basket.delivery_address_components.get('address3')
            self.delivery_city = basket.delivery_address_components.get('city')
            self.delivery_county = delivery_county
            self.delivery_postcode = basket.delivery_address_components.get('postcode')
            self.delivery_country = basket.delivery_address_components.get('country')
            self.free_delivery_to = basket.free_delivery_to
        else:
            # billing
            if self.full_name:
                parts = self.full_name.split(' ', 1)
                if len(parts) == 2:
                    first_name = parts[0]
                    last_name = parts[1]
                else:
                    first_name = ''
                    last_name = parts[0]
            else:
                first_name = last_name = ''

            billing_address = {
                'first_name': first_name,
                'last_name': last_name,
                'company': self.billing_company,
                'address1': self.billing_address1,
                'address2': self.billing_address2,
                'address3': self.billing_address3,
                'city': self.billing_city,
                'postcode': self.billing_postcode,
                'country-iso': self.billing_country.iso if self.billing_country else None,
                'email': self.email,
                'telephone': self.telephone
            }
            if self.billing_country and self.billing_country.iso == 'US':
                billing_address['state'] = self.billing_county
            else:
                billing_address['county'] = self.billing_county

            # delivery
            delivery_address = {
                'name': self.delivery_name,
                'company': self.delivery_company,
                'address1': self.delivery_address1,
                'address2': self.delivery_address2,
                'address3': self.delivery_address3,
                'city': self.delivery_city,
                'postcode': self.delivery_postcode,
                'country-iso': self.delivery_country.iso if self.delivery_country else None,
            }
            if self.delivery_country and self.delivery_country.iso == 'US':
                delivery_address['state'] = self.delivery_county
            else:
                delivery_address['county'] = self.delivery_county

        # basket details and line items
        self.billing_address_json = to_json(billing_address)
        self.delivery_address_json = to_json(delivery_address)
        self.click_and_collect = basket.is_click_and_collect()
        self.basket_json_v2 = to_json(basket.save_to_dict(use_session=False))

        # basket frozen? -> Stop here
        if basket.is_frozen:
            return

        # basket details
        self.survey = '' if not basket.survey else basket.survey
        self.email = billing_address.get('email')
        self.telephone = billing_address.get('telephone')
        self.basket_size = basket.get_size()
        self.special_requirements = basket.get_special_requirements()

        # invoice
        self.is_invoice = basket.is_invoice()
        self.is_zero_amount_checkout = not self.is_invoice and basket.total == Decimal('0.00')
        self.invoice_number = basket.invoice_number

        # totals
        self.sub_total = basket.get_sub_total()
        self.sub_total_before_delivery = basket.get_total_before_delivery()
        self.delivery = basket.get_delivery()
        self.total = basket.get_total()

        # delivery option
        delivery_option = basket.get_delivery_option()
        if delivery_option:
            self.delivery_option_title = delivery_option.title
            self.delivery_option = delivery_option
            self.delivery_quote = basket.is_quote_only
        else:
            self.delivery_option_title = None
            self.delivery_option = None
            self.delivery_quote = False

        # voucher
        if basket.voucher:
            self.voucher_code  = basket.voucher_code
            self.voucher_title = basket.voucher_title
            self.voucher_value = basket.get_discount_value()
            self.voucher       = basket.voucher
        else:
            self.voucher_code = None
            self.voucher_title = ''
            self.voucher_value = Decimal('0.0')
            self.voucher = None

        # finance option
        if settings.SHOP_LOAN_ENABLED:
            self.finance_option = basket.finance_option
            self.loan_deposit = basket.loan_deposit


    def generate_identifiers(self, request, order_id=None):
        """
        Generate unique identifiers such as secret keys and order reference
        numbers for this order.
        """
        # secret identifier used to refer to the order
        self.secret_id = request.context.generate_secret_order_id(self)

        # public order number (given or auto-generated)
        if order_id:
            self.order_id = order_id
        else:
            self.order_id = request.context.generate_order_id(self)

        # save changes
        self.save()


    @property
    def billing_address(self):
        if not hasattr(self, '_billing_address'):
            if self.billing_address_json:
                self._billing_address = decode_json(self.billing_address_json)
            else:
                return None
        return self._billing_address


    @property
    def delivery_address(self):
        if not hasattr(self, '_delivery_address'):
            if self.delivery_address_json:
                self._delivery_address = decode_json(self.delivery_address_json)
            else:
                return None
        return self._delivery_address


    @property
    def billing_address_title_display(self):
        if self.billing_address:
            return get_customer_model().get_user_title_display(self.billing_address.get('title'))
        else:
            return None


    @property
    def is_click_and_collect(self):
        return self.click_and_collect


    @property
    def customer_display(self):
        if self.customer != None:
            return self.customer.full_name
        else:
            return 'Guest Checkout: %s' % self.full_name


    @property
    def billing_address_components(self):
        """
        Return the address components of the billing address.
        """
        return filter(lambda x: x, [getattr(self, 'billing_%s' % cname) for cname in self.ADDRESS_COMPONENT_NAMES])


    @property
    def delivery_address_components(self):
        """
        Return the address components of the delivery address.
        """
        return filter(lambda x: x, [getattr(self, 'delivery_%s' % cname) for cname in ['name'] + self.ADDRESS_COMPONENT_NAMES])


    @property
    def customer_email_display(self):
        """
        Format customer name and email.
        """
        def _format_customer_name_with_email(name, email):
            if name and email:
                return '%s <%s>' % (name, email)
            elif name:
                return name
            elif email:
                return '<%s>' % email
            else:
                return '<unnamed>'

        if self.customer != None:
            customer = self.customer
            return _format_customer_name_with_email(customer.full_name, customer.email)
        else:
            return 'Guest Checkout: %s' % _format_customer_name_with_email(self.full_name, self.email)


    @property
    def est_delivery_date(self):
        """
        Return the estimated delivery date.
        """
        if not hasattr(self, '_est_delivery_date'):
            has_preorder = self.basket.has_pre_order_item()
            self._est_delivery_date = self.get_est_delivery_date(has_preorder)
        return self._est_delivery_date


    @property
    def customer_name_display(self):
        """
        Format customer name (only name, no email)
        """
        if self.customer != None:
            return self.customer.full_name
        else:
            return 'Guest Checkout: %s' % self.full_name


    @property
    def customer_account(self):
        """
        Return the customer account record for this order.
        """
        if not hasattr(self, '_customer_account'):
            try:
                self._customer_account = get_customer_model().objects.get(user=self.customer_id)
            except get_customer_model().DoesNotExist:
                self._customer_account = None
        return self._customer_account


    def get_delivery_type(self):
        """
        Return the delivery type for this order.
        """
        return self.BACKEND_DELIVERY_TYPE_CLICK_AND_COLLECT if self.click_and_collect else self.BACKEND_DELIVERY_TYPE_DELIVERY


    @property
    def delivery_display(self):
        """
        Return the delivery type as display value.
        """
        return 'Click and Collect' if self.click_and_collect else 'Delivery'


    def set_delivery_type(self, delivery_type):
        """
        Set the delivery type, which in turn sets the click_and_collect flag.
        """
        self.click_and_collect = (delivery_type == self.BACKEND_DELIVERY_TYPE_CLICK_AND_COLLECT)


    delivery_type = property(get_delivery_type, set_delivery_type)


    def can_execute_action(self, action):
        """
        Return True, if we can perform the given action on an order entity
        in the backend.
        """
        view = action.get('view')
        if view in ['approve', 'reject']:
            return self.approval_status == self.APPROVAL_STATUS_WAITING
        elif view == 'cancel':
            return self.can_cancel
        else:
            return True


    def clone(self, request):
        """
        Duplicate this order. The new order will have a new unique secret id and
        order id but is otherwise identical to the order which was cloned.
        """
        # clone existing order
        order = copy.copy(self)
        order.id = None
        order.custom_order_id = None
        order.secret_id = None
        order.order_id = None
        order.status = OrderBase.STATUS_CHECKOUT
        order.save()

        # wait for order id to generate new order_id
        order.secret_id = request.context.generate_secret_order_id(order)
        order.order_id = request.context.generate_order_id(order)
        order.save()

        return order


    @property
    def can_moto(self):
        """
        Return True if order is not paid and the payment gateway can accept moto orders.
        """
        if not self.pk:
            return False

        gateway = self.get_payment_gateway()
        if gateway.can_moto():
            if self.can_be_registered_for_payment() or self.is_retry() or self.status == OrderBase.STATUS_NEW_ORDER:
                return True
        return False


    @property
    def can_cancel(self):
        """
        Return True, if this order can be cancelled.
        """
        gateway = self.get_payment_gateway()

        return (
            settings.SHOP_PREAUTH and
            not self.preauth and
            not self.cancelled and
            self.payment_gateway and
            gateway.has_cancel() and
            self.payment_confirmed_at
        )


    def approve(self, request):
        """
        Approve delivery for this order, settle payment and send a notification
        email to the customer.
        """
        if self.approval_status != self.APPROVAL_STATUS_WAITING:
            return (False, 'Order is not awaiting approval.')

        # settle payment
        gateway = self.get_payment_gateway()
        (success, msg) = gateway.payment_settle(self, self.total)
        if success:
            # approve this order
            self.approval_status = self.APPROVAL_STATUS_APPROVED
            self.save()

            if mail_customer_order_approved(request, self):
                messages.add_message(request, messages.SUCCESS, 'Email sent to customer: <em>%s</em>' % self.email)

        return (success, msg)


    def reject(self, request, reject_msg=None):
        """
        Reject delivery for this order, abort payment and send a notification
        email to the customer. Optionally the given rejection message is
        stored against the order and is embedded within the notification
        email.
        """
        if self.approval_status != self.APPROVAL_STATUS_WAITING:
            return (False, 'Order is not awaiting approval.')

        # abort payment
        gateway = self.get_payment_gateway()
        (success, msg) = gateway.payment_abort(self)
        if success:
            # reject this order
            self.approval_status = OrderBase.APPROVAL_STATUS_REJECTED
            self.reject_msg = reject_msg
            self.save()

            if mail_customer_order_rejected(request, self):
                messages.add_message(request, messages.SUCCESS, 'Email sent to customer: <em>%s</em>' % self.email)

        return (success, msg)


    def cancel(self, request, cancel_msg=None):
        """
        Cancel this order. This may communicate information back to the
        payment or load application system.
        """
        # cancel payment
        if not self.cancelled:
            gateway = self.get_payment_gateway()
            if gateway.has_cancel():
                (success, msg) = gateway.payment_cancel(self)
                if success:
                    self.status = self.STATUS_PAYMENT_CANCELLED
                    self.cancelled = True
                    self.cancel_msg = cancel_msg
                    self.save()

                    if mail_customer_order_cancelled(request, self):
                        messages.add_message(request, messages.SUCCESS, 'Email sent to customer: <em>%s</em>' % self.email)

                return (success, msg)

        return (True, None)


    def fulfill(self, request):
        """
        Send any information to payment systems to notify that the order has
        been fulfilled. For example for loan applications, it is important to
        notify order fulfilment, since the loan actually starts when the goods
        have been shipped or collected.
        """
        if not self.fulfilled:
            gateway = self.get_payment_gateway()
            if gateway.has_fulfilment():
                (success, msg) = gateway.payment_fulfilment(self)
                if success:
                    self.fulfilled = True
                    self.save()

                return (success, msg)

        return (True, None)


    def get_payment_gateway(self):
        """
        Return the correct instances of the payment gateways depending on
        the payment gateways configured.
        """
        from cubane.ishop.views import get_shop
        shop = get_shop()

        if settings.SHOP_TEST_MODE:
            identifier = settings.GATEWAY_TEST
        elif self.payment_gateway is None:
            identifier = settings.SHOP_DEFAULT_PAYMENT_GATEWAY
        else:
            identifier = self.payment_gateway

        return shop.get_payment_gateway_by_identifier(identifier)


    @property
    def has_payment_gateway(self):
        """
        Return True, if this order has a payment gateway attached.
        """
        return self.payment_gateway is not None


    @property
    def payment_method(self):
        """
        Return the name of the payment method that was used to place this order.
        """
        if self.has_payment_gateway:
            return self.payment_gateway_display
        else:
            return 'Invoice'


    @property
    def payment_gateway_display(self):
        return settings.GATEWAY_CHOICES[self.payment_gateway][1]


    def set_payment_details(self, payment_details):
        """
        Store payment details regarding a pending transaction with an external
        payment gateway to be used later once the outcome of the transaction
        has been determined.
        """
        self._payment_details = to_json(payment_details)


    def get_payment_details(self):
        """
        Return payment details associated with this order and a previous
        payment transaction concerning this order.
        """
        return decode_json(self._payment_details)


    payment_details = property(get_payment_details, set_payment_details)


    def is_checkout(self):
        """
        Return True, if this order is in checkout state.
        """
        return self.status == OrderBase.STATUS_CHECKOUT


    def is_checkout_invoice(self):
        """
        Return True, if the system is awaiting an invoice order to be placed.
        """
        return self.status == OrderBase.STATUS_CHECKOUT_INVOICE


    def is_payment_awaiting(self):
        """
        Return True, if the system is awaiting payment for this order.
        """
        return self.status == OrderBase.STATUS_PAYMENT_AWAITING


    def is_placed_invoice(self):
        """
        Return True, if this order has been placed as an invoice order.
        """
        return self.status == OrderBase.STATUS_PLACED_INVOICE


    def is_processing(self):
        """
        Return True, if this order is currently being processed.
        """
        return self.status == OrderBase.STATUS_PROCESSING


    def is_ready_to_collect(self):
        """
        Return True, if this order is ready to be collected.
        """
        return self.status == OrderBase.STATUS_READY_TO_COLLECT


    def is_collected(self):
        """
        Return True, if this order has been collected.
        """
        return self.status == OrderBase.STATUS_COLLECTED


    def get_loan_status_text_display(self):
        """
        Return the description for the current loan status.
        """
        return self.LOAN_STATUS_TEXT.get(self.loan_status, '')


    def is_loan_success(self):
        """
        Return True if loan is completed, verified.
        """
        return self.loan_status in [OrderBase.LOAN_STATUS_VERIFIED, OrderBase.LOAN_STATUS_COMPLETE, OrderBase.LOAN_STATUS_FULFILLED]


    def is_loan_fail(self):
        """
        Return True if loan is declined or cancelled.
        """
        return self.loan_status in [OrderBase.LOAN_STATUS_DECLINE, OrderBase.LOAN_STATUS_CANCELLED]


    def is_loan_pending(self):
        """
        Return True if system cannot determine if loan is success or fail.
        """
        return True if not self.is_loan_success() and not self.is_loan_fail() else False


    def is_payment_cancelled(self):
        """
        Return True, if the payment for this order has been cancelled.
        """
        return self.status == OrderBase.STATUS_PAYMENT_CANCELLED


    def is_payment_declined(self):
        """
        Return True, if payment for this order declined.
        """
        return self.status == OrderBase.STATUS_PAYMENT_DECLINED


    def is_payment_error(self):
        """
        Return True, if an error occurred during the last payment transactio
        regarding this order.
        """
        return self.status == OrderBase.STATUS_PAYMENT_ERROR


    def is_payment_confirmed(self):
        """
        Return True, if payment for this order has been confirmed.
        """
        return self.status == OrderBase.STATUS_PAYMENT_CONFIRMED


    def is_placed(self):
        """
        Return True, if the order has been placed successfully.
        """
        return self.status in [
            OrderBase.STATUS_PAYMENT_CONFIRMED,
            OrderBase.STATUS_PLACED_INVOICE,
            OrderBase.STATUS_PLACED_ZERO_AMOUNT
        ]


    def is_partially_shipped(self):
        """
        Return True, if this order has been partially shipped.
        """
        return self.status == OrderBase.STATUS_PARTIALLY_SHIPPED


    def is_shipped(self):
        """
        Return True, if this order has been (fully) shipped.
        """
        return self.status == OrderBase.STATUS_SHIPPED


    def waits_for_approval(self):
        """
        Return True, if the system is awaiting a manual approval of this order.
        Usually this means that payment has been reserved and will be settled
        once the order has been approved.
        """
        return self.approval_status == OrderBase.APPROVAL_STATUS_WAITING


    def is_approved(self):
        """
        Return True, if this order has been approved.
        """
        return self.approval_status == OrderBase.APPROVAL_STATUS_APPROVED


    def is_rejected(self):
        """
        Return True, if this order has been rejected. Usually payment has
        been aborted at this point.
        """
        return self.approval_status == OrderBase.APPROVAL_STATUS_REJECTED


    def is_timeout(self):
        """
        Return True, if the approval for this order has timed out, which means
        that this order has not been approved within a specific amount of time.
        """
        return self.approval_status == OrderBase.APPROVAL_STATUS_TIMEOUT


    def is_rejected_or_timeout(self):
        """
        Return True, if the approval status for this order indicates that this
        order has been rejected or the approval has timed out.
        """
        return self.approval_status in [
            OrderBase.APPROVAL_STATUS_REJECTED,
            OrderBase.APPROVAL_STATUS_TIMEOUT
        ]


    def has_approval_status(self):
        """
        Return True, if this order has an approval status.
        """
        return self.approval_status != OrderBase.APPROVAL_STATUS_NONE


    def can_change_payment_status(self):
        """
        Return True, if the status for this order can be changed through
        the backend.
        """
        return not self.is_rejected_or_timeout()


    def can_be_registered_for_payment(self):
        """
        Return True, if the status for this order indicates that the order can
        be registered for a new payment transaction. This is usually only
        possible if the order is in checkout state or a previous payment
        failed.
        """
        return self.status in [
            OrderBase.STATUS_CHECKOUT,
            OrderBase.STATUS_PAYMENT_AWAITING,
            OrderBase.STATUS_PAYMENT_ERROR
        ] and not self.payment_confirmed_at


    def can_be_placed_via_invoice(self):
        """
        Return True, if this order is via invoice only and can be placed and
        has not been placed already.
        """
        return self.status == OrderBase.STATUS_CHECKOUT_INVOICE


    def can_be_placed_zero_amount(self):
        """
        Return True, if this order can be placed via zero amount without payment.
        """
        return self.status == OrderBase.STATUS_CHECKOUT_ZERO_AMOUNT


    def is_retry(self):
        """
        Return True, if the order can be processed for another payment after
        a previous payment has been declined or an error occurred.
        """
        return self.status in [
            OrderBase.STATUS_PAYMENT_DECLINED,
            OrderBase.STATUS_PAYMENT_ERROR
        ]


    def get_est_shipping_date(self, has_preorder):
        """
        Return the estimated shipping date depending on the order. The shipping
        date is the date when we ship the order out.
        This is usually the same day, unless we are outside of the working
        hours, in which case it is the next day. For preorder item, we
        would allow up to 3 working days before we ship.
        """
        d = self.created_on.date()

        if has_preorder:
            d += datetime.timedelta(days=3)
        else:
            time4oclock = self.created_on.replace(
                hour=16,
                minute=0,
                second=0,
                microsecond=0
            )
            if self.created_on >= time4oclock:
                d += datetime.timedelta(days=1)

        return d


    def get_est_delivery_date(self, has_preorder):
        """
        Return the estimated delivery date, which is usually 5 working days
        after shipping. The delivery date is the date when the customer will
        receive the goods.
        """
        return (
            self.get_est_shipping_date(has_preorder) +
            datetime.timedelta(days=5)
        )


    def get_order_backend_properties(self):
        """
        Return additional properties presented within the backend system.
        """
        return None


    def update_stock_levels(self):
        """
        Decrease stock level for each product within this order where the stock
        level control is set to automatic.
        """
        for item in self.basket.items:
            if item.product is not None:
                if item.product.stock == ProductBase.STOCKLEVEL_AUTO:
                    item.product.stocklevel -= item.quantity
                    item.product.save()


    def get_absolute_url(self):
        """
        Return the absolute url for this order, which contains a secret hash
        that prevents anyone from guessing the url for an order.
        """
        if self.secret_id:
            return get_absolute_url('shop.order.status', [self.secret_id])
        else:
            return None


    @property
    def listing_annotation(self):
        """
        Return status indication (color annotation)
        """
        if self.is_rejected_or_timeout():
            # rejected order is always error
            return 'error'
        else:
            return self.STATUS_INDICATORS.get(self.status)


    def __unicode__(self):
        return u'%s (%s)' % (self.order_id, self.get_status_display())


class ProductSKUManager(models.Manager):
    def get_by_variety_options(self, product, variety_options):
        """
        Find a matching product SKU record for the given product and given
        combination of varieties.
        """
        try:
            variety_options = filter(lambda x: x.variety.sku, variety_options)

            if len(variety_options) > 0:
                q = self.filter(product=product)
                for variety_option in variety_options:
                    q = q.filter(variety_options=variety_option)
                return q[0]
            else:
                return None
        except IndexError:
            return None


class ProductSKU(models.Model):
    """
    Defines distinct stock-keeping units (SKU), which is a unique
    combinations of varieties for a particular product and defines a distinct
    price and stock level for that combination of variety options.
    Not all possible combinations may be defined. Undefined combinations simply
    do not exist and cannot be chosen when making a purchase.
    """
    can_merge = False
    #can_add = False
    #can_delete = False


    class Meta:
        db_table            = 'ishop_product_sku'
        ordering            = ['sku']
        verbose_name        = 'Product SKU'
        verbose_name_plural = 'Product SKUs'


    class Listing:
        columns = [
            'sku',
            'product',
            'variety_options_display|Varieties',
            'barcode',
            '/price',
            '/stocklevel',
            '/enabled'
        ]
        filter_by = [
            'sku',
            'product',
            'variety_options_display|Varieties',
            'barcode',
            'price',
            'stocklevel',
            'enabled'
        ]
        edit_view = True


    enabled = models.BooleanField(
        verbose_name='Enabled',
        db_index=True,
        default=True,
        help_text='This SKU variant is available for customers to choose.'
    )

    sku = models.CharField(
        verbose_name='SKU',
        max_length=255,
        db_index=True,
        null=True
    )

    barcode = models.CharField(
        verbose_name='Barcode',
        max_length=32,
        null=True,
        blank=True,
        db_index=True,
        help_text='Barcode Number.'
    )

    product = models.ForeignKey(
        get_product_model_name(),
        verbose_name='Product',
        related_name='product_sku'
    )

    price = models.DecimalField(
        verbose_name='Price',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True
    )

    stocklevel = models.IntegerField(
        verbose_name='Stocklevel',
        db_index=True,
        default=0
    )

    variety_options = models.ManyToManyField(
        VarietyOption,
        verbose_name='Variety Options',
        related_name='sku'
    )


    objects = ProductSKUManager()


    @classmethod
    def get_form(cls):
        from cubane.ishop.apps.merchant.inventory.forms import InventoryForm
        return InventoryForm


    @property
    def variety_options_display(self):
        display = ', '.join(['%s' % option for option in self.variety_options.order_by('variety__id', 'title')])
        if not display:
            display = None
        return display


    @property
    def sku_or_barcode(self):
        """
        Return the SKU number and/or barcode of this SKU.
        """
        if self.sku and self.barcode:
            return '%s (%s)' % (self.sku, self.barcode)
        elif self.sku:
            return '%s' % self.sku
        elif self.barcode:
            return '%s' % self.barcode
        else:
            return ''


    def __unicode__(self):
        return '%s' % (self.sku if self.sku else '')


class FeaturedItemBase(DateTimeBase):
    """
    Featured Items, for example on homepage.
    """
    class Meta:
        verbose_name        = 'Featured Item'
        verbose_name_plural = 'Featured Items'
        abstract            = True


    class Listing:
        columns = ['title', 'product', 'category', 'enabled']
        edit_view = True
        grid_view = True
        sortable = True
        filter_by = [
            'title',
            'description',
            'product',
            'category',
            'enabled'
        ]


    featured_set_section = models.CharField(
        db_index=True,
        editable=False,
        choices=settings.FEATURED_SET_CHOICES,
        null=True,
        max_length=255
    )

    title = models.CharField(
        max_length=255,
        db_index=True
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text='Write a description for this item.'
    )

    call_to_action = models.CharField(
        verbose_name='Call to Action Label',
        max_length=255,
        null=True,
        blank=True,
        help_text='Override default call to action label.'
    )

    enabled = models.BooleanField(
        db_index=True,
        default=True,
        help_text='Only enabled featured items are visible to customers.'
    )

    product = models.ForeignKey(
        get_product_model_name(),
        null=True,
        blank=True
    )

    category = models.ForeignKey(
        get_category_model_name(),
        null=True,
        blank=True
    )

    page = models.ForeignKey(
        get_page_model_name(),
        null=True,
        blank=True
    )

    image = models.ForeignKey(
        Media,
        verbose_name='Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Select an image that is used to represent this ' + \
                  'featured item.'
    )

    seq = models.IntegerField(
        verbose_name='Sequence',
        db_index=True,
        default=0,
        editable=False,
        help_text='The sequence number determines the order in which ' + \
                  'featured items are presented.'
    )


    @classmethod
    def get_form(cls):
        from cubane.ishop.featured.forms import FeaturedItemBaseForm
        return FeaturedItemBaseForm


    @property
    def has_product(self):
        return not self.product_id == None


    @property
    def url(self):
        if self.product_id:
            return self.product.get_absolute_url()
        elif self.category_id:
            return self.category.get_absolute_url()
        elif self.page_id:
            return self.page.get_absolute_url()
        else:
            return ''


    @property
    def featured_image(self):
        """
        Return the image associated with this featured item or the image
        of the underlying business object, such as a product.
        """
        if self.image_id:
            return self.image
        elif self.product_id:
            return self.product.image
        elif self.category_id:
            return self.category.image
        elif self.page_id:
            return self.page.image
        else:
            return None


    @property
    def related_image(self):
        """
        Return the image of the related entity (such as product, category or
        page) if available; otherwise None.
        """
        if self.product_id:
            return self.product.image
        elif self.category_id:
            return self.category.image
        elif self.page_id:
            return self.page.image
        else:
            return None


    def __unicode__(self):
        return '%s' % self.title


class CustomerBase(models.Model):
    """
    Represents customer details.
    """
    class Meta:
        abstract = True


    class Listing:
        columns = [
            'email',
            'last_name',
            'first_name',
            'postcode'
        ]
        filter_by = [
            'email',
            'last_name',
            'first_name',
            'company',
            'address1',
            'address2',
            'address3',
            'city',
            'county',
            'postcode',
            'country',
            'telephone',
            'newsletter',
        ]
        default_view = 'list-compact'
        data_export = True
        data_columns = [
            'user',
            'title',
            'first_name',
            'last_name',
            'company',
            'address1',
            'address2',
            'address3',
            'city',
            'county',
            'postcode',
            'country',
            'email',
            'telephone',
            'newsletter',
        ]


    TITLE_MR   = 1
    TITLE_MRS  = 2
    TITLE_MS   = 3
    TITLE_MISS = 4
    TITLE_CHOICES = (
        (TITLE_MR,   'Mr'),
        (TITLE_MRS,  'Mrs'),
        (TITLE_MS,   'Ms'),
        (TITLE_MISS, 'Miss'),
    )


    user = models.OneToOneField(
        User,
        related_name='user',
        editable=False
    )

    title = models.IntegerField(
        choices=TITLE_CHOICES,
        null=True,
        blank=True
    )

    first_name = models.CharField(
        max_length=30,
        db_index=True,
        null=True,
        blank=True
    )

    last_name = models.CharField(
        max_length=30,
        db_index=True,
        null=True,
        blank=True
    )

    company = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=True
    )

    address1 = models.CharField(
        max_length=255,
        db_index=True
    )

    address2 = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    address3 = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    city = models.CharField(
        max_length=255
    )

    county = models.CharField(
        max_length=255
    )

    postcode = models.CharField(
        max_length=10
    )

    country = models.ForeignKey(
        Country
    )

    email = models.CharField(
        max_length=255,
        db_index=True,
        unique=True
    )

    telephone = models.CharField(
        max_length=40
    )

    newsletter = models.BooleanField(
        default=False,
        help_text='Marketing Agreement given.'
    )

    legacy_pw = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=True
    )


    @classmethod
    def get_user_title_display(cls, title):
        """
        Return the human-readable title for a given customer with the encoded
        title of the given value.
        """
        return dict(cls.TITLE_CHOICES).get(int(title), '')


    def save(self, *args, **kwargs):
        """
        Maintains underlying user account for this customer.
        """
        if hasattr(self, 'user'):
            self.user.first_name = self.first_name
            self.user.last_name = self.last_name
            self.user.email = self.email
            self.user.save()
        else:
            # create user account
            md5 = hashlib.md5()
            md5.update(self.email)
            user = User.objects.create(
                username = md5.hexdigest()[:30],
                first_name = self.first_name,
                last_name = self.last_name,
                email = self.email
            )
            user.username = unicode(user.id)
            user.save()
            self.user = user

        super(CustomerBase, self).save(*args, **kwargs)


    def delete(self, *args, **kwargs):
        """
        Deletes underlying account for this customer.
        """
        if self.user:
            self.user.delete()

        super(CustomerBase, self).delete(*args, **kwargs)


    def __unicode__(self):
        return u'%s' % self.email


class DeliveryAddress(models.Model):
    """
    Represents one (of many) stored delivery addresses for a customer.
    """
    class Meta:
        db_table            = 'ishop_delivery_address'
        ordering            = []
        verbose_name        = 'Delivery Address'
        verbose_name_plural = 'Delivery Addresses'


    user = models.ForeignKey(
        User,
        related_name='delivery_addresses'
    )

    name = models.CharField(
        max_length=255,
        null=True,
        db_index=True
    )

    company = models.CharField(
        max_length=255,
        db_index=True
    )

    address1 = models.CharField(
        max_length=255,
        db_index=True
    )

    address2 = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    address3 = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    city = models.CharField(
        max_length=255
    )

    county = models.CharField(
        max_length=255
    )

    postcode = models.CharField(
        max_length=10
    )

    country = models.ForeignKey(
        Country
    )


    def get_parts(self):
        """
        Return a list of all address components that are not None.
        """
        return filter(lambda x: x, [
            self.name,
            self.company,
            self.address1,
            self.address2,
            self.address3,
            self.city,
            self.county,
            self.postcode,
            self.country.printable_name if self.country_id else None
        ])


    def __unicode__(self):
        return ', '.join(self.get_parts())


class ShopSettings(SettingsBase):
    """
    Abstract base class for shop settings. Contains default CMS settings and
    adds shop-specific settings.
    """
    class Meta:
        abstract = True


    # order refernece number format and prefix
    order_id = models.CharField(
        verbose_name='Order Reference Format',
        max_length=16,
        default='numeric',
        choices=(
            ('numeric', 'Numeric (including year and month)'),
            ('seq',     'Numeric (sequential)'),
            ('alpha',   'Alphanumeric'),
        ),
        help_text='Choose the format who order reference numbers are generated.'
    )

    order_id_prefix = models.CharField(
        verbose_name='Order Reference Prefix',
        max_length=32,
        null=True,
        blank=True,
        help_text='Optional: Enter some text that is inserted before the order reference number.'
    )

    order_id_suffix = models.CharField(
        verbose_name='Order Reference Suffix',
        max_length=32,
        null=True,
        blank=True,
        help_text='Optional: Enter some text that is inserted after the order reference number.'
    )

    # pagination
    products_per_page = models.IntegerField(
        verbose_name='Products per Page',
        default=9,
        help_text='The total number of products listed per page.'
    )

    max_products_per_page = models.IntegerField(
        verbose_name='Products per Page (Max)',
        default=100,
        help_text='The maximum number of products listed when viewing ' + \
                  'all products.'
    )

    related_products_to_show = models.IntegerField(
        verbose_name='Related Products',
        default=5,
        help_text='The maximum number of products presented as ' +
                  '\'Related Products\'.'
    )

    # add to basket options
    max_quantity = models.IntegerField(
        verbose_name='Max Quanity',
        default=10,
        validators=[
            MaxValueValidator(9999),
            MinValueValidator(1)
        ],
        help_text='The max. quantity that can be added to the basket at once. The max. quantity per basket item is 9999.'
    )

    # shop behaviour
    guest_checkout = models.BooleanField(
        verbose_name='Guest Checkout',
        default=True,
        help_text='Allow customers to checkout without having to create ' + \
                  'a permanent account.'
    )

    # stock levels
    stocklevel = models.BooleanField(
        verbose_name='Stock Level',
        default=False,
        help_text='Enable support for basic stock level control.'
    )

    # special requirements
    special_requirements = models.BooleanField(
        verbose_name='Special Requirements',
        default=True,
        help_text='Provide the ability to customers to specify special requirements regarding orders.'
    )

    tax_percent = models.IntegerField(
        verbose_name='Tax (Percentage)',
        null=True,
        blank=True,
        help_text='Enter the percentage used for tax calculations.'
    )

    # email addresses
    mail_subject_prefix = models.CharField(
        verbose_name='Mail Subject Prefix',
        max_length=255,
        null=True,
        blank=True,
        help_text='Prefix for the subject line for email sent to customers.'
    )

    mail_notify_address = models.CharField(
        verbose_name='Mail Notification',
        max_length=255,
        null=True,
        blank=False,
        help_text='Email address that is used for notification of new orders.'
    )

    mail_from_address = models.CharField(
        verbose_name='Email from address',
        max_length=255,
        null=True,
        blank=False,
        help_text='From email address.'
    )

    # default t&c's and placeholder image
    terms_page = models.ForeignKey(
        get_page_model_name(),
        verbose_name='T&C Page',
        null=True,
        blank=True,
        help_text='Page that represents the terms and conditions of the shop.'
    )

    image_placeholder = models.ForeignKey(
        Media,
        verbose_name='Image Placeholder',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text='Choose an image that is presented as a placeholder ' + \
                  'image in case we are unable to present an image, ' + \
                  'for example a missing category or product image.'
    )

    # SKU and default barcode system
    sku_is_barcode = models.BooleanField(
        verbose_name='Use SKU as barcode',
        default=False,
        help_text='User SKU number as barcode (requires default barcode system).'
    )

    barcode_system = models.CharField(
        verbose_name='Default Barcode System',
        max_length=8,
        null=True,
        blank=True,
        choices=get_barcode_choices(),
        help_text='Choose the type of barcode system that is used by default.'
    )

    # survey
    survey = models.TextField(
        verbose_name='Survey Options',
        null=True,
        blank=True,
        help_text='List of survey options (e.g. How did you hear about us)'
    )

    shop_email_template = models.ForeignKey(
        get_page_model_name(),
        verbose_name='Shop Email Template',
        related_name='+',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Select the page that is used to send the shop email ' + \
                  'to customers who are using the shopping system ' + \
                  'on the website.'
    )

    # product listing order options
    ordering_options = MultiSelectField(
        verbose_name='Available Options',
        choices=ProductBase.ORDER_BY_CHOICES,
        default=ProductBase.ORDER_BY_DEFAULT_OPTIONS,
        blank=True,
        help_text='Select a number of order options for customers to ' + \
                  'choose from when ordering products on the website.'
    )

    ordering_default = models.CharField(
        verbose_name='Default Order',
        max_length=64,
        choices=ProductBase.ORDER_BY_CHOICES,
        default=ProductBase.ORDER_BY_RELEVANCE,
        blank=True,
        help_text='Select the default order in which products are presented.'
    )


    @property
    def has_terms(self):
        """
        Return True, if a terms and conditions page is configured.
        """
        return self.terms_page != None


    def get_barcode_system(self, product=None):
        """
        Return the barcode system that applies for the given product or in
        general or None.
        """
        barcode_system = self.barcode_system
        if product is not None:
            if product.barcode_system is not None:
                barcode_system = product.barcode_system
        return barcode_system


    def get_terms(self):
        """
        Return the absolute url of the terms and conditions page as configured
        by settings. If no terms and conditions page is configured, return None.
        """
        return self.terms_page.get_absolute_url() if self.terms_page else None


    def get_survey_options(self):
        """
        Return a list of unique survey options or the empty list.
        """
        if self.survey == None: return []
        options = filter(
            lambda x: len(x) > 0,
            [line.strip() for line in self.survey.split('\n')]
        )

        # remove duplicates without affecting order
        seen = set()
        return [x for x in options if not (x in seen or seen.add(x))]


    @property
    def has_survey(self):
        """
        Return True, if at least one survey option is configured.
        """
        return len(self.get_survey_options()) > 0


    def get_survey_choices(self):
        """
        Return a list of choices for all survey options configured.
        """
        return [('', 'Where Did You Hear About Us?...')] + [
            (v, v) for v in self.get_survey_options()
        ]


    @property
    def has_voucher_codes(self):
        """
        Return True, if at least one enabled voucher code is available in
        the system.
        """
        return Voucher.objects.filter(enabled=True).count() > 0


    def get_product_ordering_choices(self, has_subcategories=False):
        """
        Return a set of choices that can be chosen from to order products on
        the product listing page.
        """
        choices = []
        for choice in ProductBase.ORDER_BY_CHOICES:
            if choice[0] in self.ordering_options:
                choices.append(choice)

        return choices


class UserMixin(object):
    """
    Extending default User type.
    """
    @property
    def full_name(user):
        """
        Return the full name of the user in the format <firstname> <lastname>.
        """
        return ' '.join(filter(lambda x: x, [
            user.first_name,
            user.last_name
        ]))


    @property
    def full_name_email(user):
        """
        Return the full name of the user including email address.
        """
        fn = user.full_name
        if fn: fn = fn.strip().title()

        email = user.email
        if email: email = email.strip().lower()

        if fn and email:
            return '%s <%s>' % (fn, email)
        elif fn:
            return fn
        elif email:
            return '<%s>' % email
        else:
            return '<unnamed>'


User.full_name = UserMixin.full_name
User.full_name_email = UserMixin.full_name_email
