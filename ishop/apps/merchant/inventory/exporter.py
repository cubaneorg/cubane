# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.files.temp import NamedTemporaryFile
from cubane.ishop import get_product_model
import cubane.lib.ucsv as csv
import tempfile


class ShopInventoryExporter(object):
    def export_to_temp_file(self, encoding='utf-8'):
        """
        Export all shop inventory to a named temporary file and return
        the file handler of the temporary file created.
        """
        f = NamedTemporaryFile()
        self.export_to_stream(f, encoding)
        f.seek(0)
        return f


    def export_to_stream(self, stream, encoding='utf-8'):
        """
        Export all shop inventory to a CSV file (output stream).
        """
        # create CSV writer
        writer = csv.writer(
            stream,
            delimiter=b',',
            quotechar=b'"',
            quoting=csv.QUOTE_ALL,
            encoding=encoding
        )

        # generate header line
        self._write_headers(writer)

        # generate data rows
        self._write_data(writer)


    def _write_headers(self, writer):
        """
        Write first row of CSV file to be the headers.
        """
        writer.writerow(['SKU', 'Description', 'Price Inc VAT', 'Stock Qty', 'Barcode', 'On Website'])


    def _write_data(self, writer):
        """
        Write all shop inventory data rows.
        """
        # process each product
        product_model = get_product_model()
        products = product_model.objects.filter(draft=False)
        for product in products:
            # SKU-enabled?
            if product.sku_enabled:
                # multiple SKU's. Generate one row for each stockable variant
                skus = product.product_sku.filter(sku__isnull=False).exclude(variety_options=None)
                for sku in skus:
                    if sku.sku:
                        self._write_row(writer, self._sku_to_value_list(product, sku))
            else:
                # single product record without varieties
                if product.sku:
                    self._write_row(writer, self._product_to_value_list(product))


    def _product_to_value_list(self, product):
        """
        Generate single entry for the product itself (no variants).
        """
        yield product.sku
        yield product.title
        yield product.price
        yield product.stocklevel
        yield product.barcode
        yield 'YES'


    def _sku_to_value_list(self, product, sku):
        """
        Generate single entry for the given SKU entry of the given product.
        """
        yield sku.sku
        yield product.title
        yield sku.price
        yield sku.stocklevel
        yield sku.barcode
        yield 'YES'


    def _write_row(self, writer, row):
        """
        Write row of CSV values.
        """
        writer.writerow(map(lambda v: self._csv_value(v), row))


    def _csv_value(self, value, default_value=''):
        """
        Convert None to empty space.
        """
        if value is None:
            value = default_value
        return value