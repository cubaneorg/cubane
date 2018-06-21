# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.forms import widgets, fields
from django.forms.utils import ErrorList
from django.forms.formsets import BaseFormSet, formset_factory
from django.template.defaultfilters import slugify
from cubane.forms import BaseForm, BaseModelForm, BootstrapTextInput, StaticTextWidget, NumberInput
from cubane.backend.forms import ModelCollectionField, RelatedListingField
from cubane.cms.forms import MetaPreviewWidget
from cubane.backend.forms import GalleryField
from cubane.media.forms import BrowseImagesField
from cubane.media.models import Media
from cubane.lib.barcodes import verify_barcode, BarcodeError
from cubane.ishop import get_product_model, get_category_model
from cubane.ishop.forms import clean_price
from cubane.ishop.apps.merchant.forms import ProductSKUFormMixin
from cubane.ishop.apps.merchant.categories.forms import BrowseCategoryField
from cubane.ishop.apps.merchant.inventory.views import InventoryView
from cubane.ishop.models import ShopSettings, FinanceOption, ProductSKU
import re
import decimal


class ProductFormBase(BaseModelForm):
    class Meta:
        model = get_product_model()
        exclude = [
            'seq',
            'varieties',
            'delivery_options',
            '_related_products'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'slugify', 'autocomplete': 'off'}),
            'slug': forms.TextInput(attrs={'class': 'slug', 'autocomplete': 'off'}),
            'price': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
            'deposit': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
            'rrp': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
            'previous_price': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
            'finance_options': forms.CheckboxSelectMultiple()
        }
        tabs = [
            {
                'title': 'Title',
                'fields': [
                    'title',
                    'slug',
                    'category',
                    'categories',
                    'legacy_url',
                    'excerpt',

                    '_meta_title',
                    '_meta_description',
                    '_meta_keywords',

                    '_meta_preview'
                ]
            }, {
                'title': 'Content',
                'fields': [
                    '_excerpt',
                    'description'
                ]
            }, {
                'title': 'Price and Availability',
                'fields': [
                    'rrp',
                    'previous_price',
                    'price',
                    'draft',
                    'non_returnable',
                    'collection_only',

                    'pre_order',
                    'deposit',

                    'loan_exempt',
                    'finance_options',

                    'exempt_from_free_delivery',
                    'exempt_from_discount',
                    'feed_google',
                    'feed_amazon',

                    'stock',
                    'stocklevel',
                    'sku_enabled',
                    'sku',

                    'barcode_system',
                    'barcode',
                    'part_number',
                ]
            }, {
                'title': 'Gallery',
                'fields': [
                    'image',
                    '_gallery_images'
                ]
            }, {
                'title': 'Related Products',
                'fields': [
                    '_related_products_collection'
                ]
            }, {
                'title': 'SKU / Inventory',
                'fields': [
                    '_inventory'
                ]
            }
        ]
        sections = {
            'title': 'Product Data',
            '_excerpt': 'Excerpt',
            '_meta_title': 'Meta Data',
            'barcode_system': 'Identification',
            'stock': 'Stock',
            'sku_enabled': 'SKU / Inventory',
            '_meta_preview': 'Search Result Preview',
            'rrp': 'Price',
            'draft': 'Options',
            'pre_order': 'Pre-order',
            'loan_exempt': 'Finance',
            'exempt_from_free_delivery': 'Exemption',
            'feed_google': 'Channel Feeds',
            'image': 'Product Images'
        }


    category = BrowseCategoryField(
        required=True,
        help_text='The category this product is listed under.'
    )

    _meta_preview = fields.Field(
        label=None,
        required=False,
        help_text='This preview is for demonstration purposes only ' +\
            'and the actual search result may differ from the preview.',
    )

    image = BrowseImagesField(
        required=False,
        help_text='Choose the main image for this product that is used on the product listing page.'
    )

    _gallery_images = GalleryField(
        label='Image Gallery',
        required=False,
        queryset=Media.objects.filter(is_image=True),
        help_text='Add an arbitrarily number of images that are presented on the product details page.'
    )

    _related_products_collection = ModelCollectionField(
        label='Related Products',
        required=False,
        queryset=get_product_model().objects.all(),
        url='/admin/products/',
        title='Products',
        model_title='Products',
        help_text='Add an arbitrarily number of related products to this product.'
    )

    categories = ModelCollectionField(
        label='Categories',
        add_label='Add Category',
        required=True,
        queryset=get_category_model().objects.all(),
        url='/admin/categories/',
        title='Categories',
        model_title='Categories',
        viewmode=ModelCollectionField.VIEWMODE_LIST,
        allow_duplicates=False,
        sortable=False,
        help_text='Add an arbitrarily number of categories this product is listed under.'
    )

    _inventory = RelatedListingField(
        view = InventoryView()
    )


    def configure(self, request, instance, edit):
        super(ProductFormBase, self).configure(request, instance, edit)

        # meta preview control
        self.fields['_meta_preview'].widget = MetaPreviewWidget(attrs={
            'class': 'no-label',
            'path': request.path_info,
            'form': self
        })

        # excerpt
        self.fields['_excerpt'].help_text = 'Provide your elevator pitch to the customer (max. %d characters)' % settings.CMS_EXCERPT_LENGTH

        if request.settings.barcode_system and request.settings.sku_is_barcode:
            self.remove_field('sku')
            self.fields['barcode'].label = 'SKU / Barcode'
            self.fields['barcode'].help_text = 'SKU / Barcode (%s)' % request.settings.barcode_system.upper()

        # multiple categories
        if settings.SHOP_MULTIPLE_CATEGORIES:
            self.remove_field('category')
        else:
            self.remove_field('categories')

        # loan applications
        if settings.SHOP_LOAN_ENABLED:
            queryset = FinanceOption.objects.filter(enabled=True, per_product=True).order_by('seq')
            self.fields['finance_options'].queryset = queryset

            if queryset.count() == 0:
                self.remove_field('finance_options')
                self.update_sections()
        else:
            self.remove_field('finance_options')
            self.remove_field('loan_exempt')

        # SKU / inventory
        if not (instance and instance.sku_enabled):
            self.remove_tab('SKU / Inventory')

        self.update_sections()



    def clean_slug(self):
        slug = self.cleaned_data.get('slug')

        if slug:
            products = get_product_model().objects.filter(slug=slug)
            if self._edit and self._instance:
                products = products.exclude(pk=self._instance.pk)
            if products.count() > 0:
                raise forms.ValidationError('This slug is already used. Please choose a different slug.')

        return slug


    def clean_excerpt(self):
        excerpt = self.cleaned_data.get('_excerpt')

        if excerpt:
            if len(excerpt) > settings.CMS_EXCERPT_LENGTH:
                raise forms.ValidationError('The maximum allowed length is %d characters.' % settings.CMS_EXCERPT_LENGTH)

        return excerpt


    def clean_price(self):
        return clean_price(self, 'price', self.cleaned_data)


    def clean_rrp(self):
        return clean_price(self, 'rrp', self.cleaned_data)


    def clean_previous_price(self):
        return clean_price(self, 'previous_price', self.cleaned_data)


    def clean(self):
        d = super(ProductFormBase, self).clean()

        barcode_system = d.get('barcode_system')
        barcode = d.get('barcode')

        if barcode_system is None:
            barcode_system = self._request.settings.barcode_system

        # verify that the barcode is correct...
        if barcode and barcode_system:
            try:
                d['barcode'] = verify_barcode(barcode_system, barcode)
            except BarcodeError, e:
                self.field_error('barcode', e.msg)

        return d


class DeliveryOptionForm(BaseForm):
    """
    Delivery changes for different world regions for certain for a set of
    delivery options for an individual product.
    """
    title = forms.CharField(
        required=False,
        max_length=255,
        widget=StaticTextWidget()
    )

    uk = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        label='UK',
        widget=BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'rounded input-mini'})
    )

    eu = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        label='EU',
        widget=BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'rounded input-mini'})
    )

    world = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        label='Non-EU',
        widget=BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'rounded input-mini'})
    )

    option_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    _id = forms.IntegerField(required=False, widget=forms.HiddenInput())


    def __init__(self, *args, **kwargs):
        super(DeliveryOptionForm, self).__init__(*args, **kwargs)

        self.fields['title'].widget = StaticTextWidget(text=self.initial.get('title'))

        # hide fields that do not apply
        for prefix in ['uk', 'eu', 'world']:
            if not self.initial.get('deliver_%s' % prefix):
                self.fields[prefix].widget.attrs['readonly'] = 'readonly'
                self.fields[prefix].required = False


class BaseDeliveryOptionFormset(BaseFormSet):
    def configure(self, client):
        pass
DeliveryOptionFormset = formset_factory(DeliveryOptionForm, formset=BaseDeliveryOptionFormset, can_delete=False, extra=0)


class ProductSKUForm(BaseForm, ProductSKUFormMixin):
    """
    Form for controlling product SKU details.
    """
    _id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )

    enabled = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput()
    )

    sku = forms.CharField(
        required=False,
        max_length=255,
        label='SKU',
        widget=forms.TextInput(attrs={'class': 'input-medium'}),
        help_text='SKU (Stock-keeping unit). Unique product code.'
    )

    barcode = forms.CharField(
        required=False,
        max_length=32,
        label='Barcode',
        widget=forms.TextInput(attrs={'class': 'input-small'}),
        help_text='Barcode'
    )

    price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        label='Price',
        widget=BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'rounded input-mini'})
    )

    stocklevel = forms.IntegerField(
        required=False,
        label='Stock Level',
        initial=0,
        widget=NumberInput()
    )


    def configure(self, request, barcode_system):
        self._barcode_system = barcode_system

        if barcode_system:
            if request.settings.sku_is_barcode:
                self.remove_field('sku')
                self.fields['barcode'].label = 'SKU / Barcode'
                self.fields['barcode'].help_text = 'SKU / Barcode (%s)' % barcode_system.upper()
            else:
                self.fields['barcode'].help_text = 'Barcode (%s)' % barcode_system.upper()
        else:
            self.remove_field('barcode')