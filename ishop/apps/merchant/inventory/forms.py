# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from cubane.forms import BaseForm, BaseModelForm, DataImportForm, DataExportForm, BootstrapTextInput
from cubane.backend.forms import ModelCollectionField
from cubane.lib.utf8 import ENCODING_CHOICES, DEFAULT_ENCOPDING
from cubane.lib.barcodes import verify_barcode, BarcodeError
from cubane.ishop import get_product_model
from cubane.ishop.models import ProductSKU
from cubane.ishop.apps.merchant.forms import ProductSKUFormMixin
from cubane.ishop.models import VarietyOption
from cubane.ishop.apps.merchant.forms import BrowseProductField
import decimal


class InventoryForm(BaseModelForm, ProductSKUFormMixin):
    class Meta:
        model = ProductSKU
        fields = '__all__'
        widgets = {
            'price': BootstrapTextInput(prepend=settings.CURRENCY, attrs={'class': 'input-medium'}),
        }
        sections = {
            'enabled': 'SKU',
            'price': 'Price and Stock Level'
        }


    product = BrowseProductField()


    variety_options = ModelCollectionField(
        label='Variety Options',
        add_label='Add Variety Option',
        required=True,
        queryset=VarietyOption.objects.all(),
        url='/admin/variety-options/',
        title='Variety Options',
        model_title='Variety Option',
        viewmode=ModelCollectionField.VIEWMODE_LIST,
        allow_duplicates=False,
        sortable=False,
        help_text='Add the number of unique variety options that this Stock Keeping Unit (SKU) represents.'
    )


    def configure(self, request, instance, edit):
        super(InventoryForm, self).configure(request, instance, edit)

        # barcode system
        try:
            product = instance.product
        except:
            product = None

        self._barcode_system = request.settings.get_barcode_system(product)

        if self._barcode_system:
            if request.settings.sku_is_barcode:
                self.remove_field('sku')
                self.fields['barcode'].label = 'SKU / Barcode'
                self.fields['barcode'].help_text = 'SKU / Barcode (%s)' % self._barcode_system.upper()
            else:
                self.fields['barcode'].help_text = 'Barcode (%s)' % self._barcode_system.upper()
        else:
            self.remove_field('barcode')


    def clean(self):
        """
        Verify that SKU is unique and valid.
        """
        d = super(InventoryForm, self).clean()

        product_model = get_product_model()

        # SKU
        sku = d.get('sku')
        if sku:
            # SKU must be unique across all product SKUs
            x = ProductSKU.objects.filter(sku=sku)
            if self._edit: x = x.exclude(pk=self._instance.pk)
            if x.count() > 0:
                self.field_error('sku', 'This SKU number already exists.')

            # SKU cannot match any product-specific SKU
            products = product_model.objects.filter(sku=sku)
            if products.count() > 0:
                self.field_error('sku', 'This SKU number already exists for product: %s' % products[0])

        # barcode
        barcode = d.get('barcode')
        if barcode:
            # barcode must be unique across all product SKUs
            x = ProductSKU.objects.filter(barcode=barcode)
            if self._edit: x = x.exclude(pk=self._instance.pk)
            if x.count() > 0:
                self.field_error('barcode', 'This barcode number already exists.')

            # barcode cannot match any product-specific barcode
            products = product_model.objects.filter(barcode=barcode)
            if products.count() > 0:
                self.field_error('barcode', 'This barcode number already exists for product: %s' % products[0])

        product = d.get('product')
        if product:
            # product must be SKU enabled
            if not product.sku_enabled:
                self.field_error('product', 'This product is not enabled for SKU numbers.')

            variety_options = d.get('variety_options')
            if variety_options:
                # all varieties must be enabled for SKU usage
                for variety_option in variety_options:
                    if not variety_option.variety.sku:
                        self.field_error('variety_options', 'The variety \'%s\' is not enabled for SKU numbers (\'%s\').' % (
                            variety_option.variety,
                            variety_option
                        ))

                # all variety options must have a different variety. We cannot
                # map to multiple options of the same variety...
                variety_ids = [option.variety.pk for option in variety_options]
                if len(set(variety_ids)) != len(variety_ids):
                    self.field_error('variety_options', 'A SKU number must be a unique combination of varieties and cannot map to multiple options of the same variety.')

                # combination of variety options must match all required
                # varieties
                x = ProductSKU.objects.filter(product=product, enabled=True)
                if self._edit: x = x.exclude(pk=self._instance.pk)
                if x.count() > 0:
                    # all required varieties must be assigned...
                    required_varieties = [variety_option.variety for variety_option in x[0].variety_options.all()]
                    required_variety_ids = [v.pk for v in required_varieties]
                    varieties = [option.variety for option in variety_options]
                    variety_ids = [v.pk for v in varieties]
                    for required_variety in required_varieties:
                        if required_variety.pk not in variety_ids:
                            self.field_error('variety_options', 'This SKU number must map to the required variety: \'%s\'.' % (
                                required_variety
                            ))

                    # we cannot have a variety that is not allowed...
                    for variety_option in variety_options:
                        if variety_option.variety.pk not in required_variety_ids:
                            self.field_error('variety_options', 'Variety option \'%s\' does not belong to \'%s\'.' % (
                                variety_option,
                                ' or '.join(['%s' % v for v in required_varieties])
                            ))

                # combination of variety options must be unique for this product
                x = ProductSKU.objects.filter(product=product, enabled=True)
                for variety_option in variety_options:
                    x = x.filter(variety_options=variety_option)
                if self._edit: x = x.exclude(pk=self._instance.pk)
                if x.count() > 0:
                    self.field_error('variety_options', 'This combination of variety options already exists.')

        return d


class ShopInventoryImportForm(DataImportForm):
    """
    Form for uploading shop data for importing products, SKUs, stock-level,
    pricing and categories all in one go.
    """
    pass


class ShopInventoryExportForm(DataExportForm):
    """
    Form for downloading shop inventory data.
    """
    pass
