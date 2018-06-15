# coding=UTF-8
from __future__ import unicode_literals
from django.core.urlresolvers import reverse_lazy
from cubane.lib.barcodes import verify_barcode, BarcodeError
from cubane.backend.forms import BrowseField
from cubane.ishop import get_product_model
from cubane.ishop.forms import clean_price


class BrowseProductField(BrowseField):
    """
    Simplified version of browse folder field for browsing shop products.
    """
    def __init__(self, *args, **kwargs):
        model = get_product_model()
        kwargs['queryset'] = get_product_model().objects.filter(draft=False)
        kwargs['name'] = 'Products'
        kwargs['browse'] = reverse_lazy('cubane.ishop.products.index')
        kwargs['create'] = reverse_lazy('cubane.ishop.products.create')
        super(BrowseProductField, self).__init__(*args, **kwargs)


class ProductSKUFormMixin(object):
    """
    Mixin validation for barcode and price.
    """
    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')

        if barcode:
            try:
                barcode = verify_barcode(self._barcode_system, barcode)
            except BarcodeError, e:
                self.field_error('barcode', e.msg)

        return barcode


    def clean_price(self):
        return clean_price(self, 'price', self.cleaned_data)