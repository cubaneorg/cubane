# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.barcodes import (
    BarcodeError,
    get_barcode_systems,
    get_barcode_choices,
    verify_barcode,
    render_barcode_image
)


class LibBarcodesBarcodeErrorTestCase(CubaneTestCase):
    """
    cubane.lib.barcodes.BarcodeError()
    """
    def test_ctor_should_take_error_message(self):
        error = BarcodeError('Foo')
        self.assertEqual('Foo', error.msg)
        self.assertEqual('Foo', str(error))
        self.assertEqual('Foo', unicode(error))


class LibBarcodesGetBarcodeSystemsTestCase(CubaneTestCase):
    """
    cubane.lib.barcodes.get_barcode_systems()
    """
    EXPECTED_BARCODE_SYSTEMS = [
        'code39',
        'ean',
        'ean13',
        'ean8',
        'gs1',
        'gtin',
        'isbn',
        'isbn10',
        'isbn13',
        'issn',
        'jan',
        'pzn',
        'upc',
        'upca'
    ]


    def test_should_return_list_of_supported_barcode_systems(self):
        barcode_systems = get_barcode_systems()
        for barcode_system in self.EXPECTED_BARCODE_SYSTEMS:
            self.assertIn(barcode_system, barcode_systems)


class LibBarcodesGetBarcodeChoicesTestCase(CubaneTestCase):
    """
    cubane.lib.barcodes.get_barcode_choices()
    """
    EXPECTED_BARCODE_CHOICES = [
        ('code39', 'CODE39'),
        ('ean', 'EAN'),
        ('ean13', 'EAN13'),
        ('ean8', 'EAN8'),
        ('gs1', 'GS1'),
        ('gtin', 'GTIN'),
        ('isbn', 'ISBN'),
        ('isbn10', 'ISBN10'),
        ('isbn13', 'ISBN13'),
        ('issn', 'ISSN'),
        ('jan', 'JAN'),
        ('pzn', 'PZN'),
        ('upc', 'UPC'),
        ('upca', 'UPCA')
    ]


    def test_should_return_list_of_barcode_choices(self):
        barcode_choices = get_barcode_choices()
        for choice in self.EXPECTED_BARCODE_CHOICES:
            self.assertIn(choice, barcode_choices)


class LibBarcodesVerifyBarcodeTestCase(CubaneTestCase):
    """
    cubane.lib.barcodes.verify_barcode()
    """
    def test_should_raise_error_if_barcode_is_none(self):
        with self.assertRaisesRegexp(BarcodeError, 'The barcode must have at least 6 digits'):
            verify_barcode('ean', None)


    def test_should_raise_error_if_barcode_is_empty(self):
        with self.assertRaisesRegexp(BarcodeError, 'The barcode must have at least 6 digits'):
            verify_barcode('ean', '')


    def test_should_raise_error_if_barcode_is_too_short(self):
        with self.assertRaisesRegexp(BarcodeError, 'The barcode must have at least 6 digits'):
            verify_barcode('isbn', '978')


    def test_should_raise_error_if_checksum_digit_is_missing(self):
        with self.assertRaisesRegexp(BarcodeError, 'The barcode checksum is invalid\. Missing digits: 5\?'):
            verify_barcode('isbn', '978059680948')


    def test_should_raise_error_if_checksum_digit_is_incorrect(self):
        with self.assertRaisesRegexp(BarcodeError, 'The barcode checksum is invalid\. Missing digits: 5\?'):
            verify_barcode('isbn', '9780596809480')


    def test_should_raise_error_if_checksum_digit_is_missing_with_formatting(self):
        with self.assertRaisesRegexp(BarcodeError, 'The barcode checksum is invalid\. Missing digits: 5\?'):
            verify_barcode('isbn', '978-0-596-80948')


    def test_should_raise_error_if_given_barcode_system_is_not_valid(self):
        with self.assertRaisesRegexp(BarcodeError, 'The barcode system \'foo\' is not known or invalid'):
            verify_barcode('foo', '9780596809485')


    def test_should_raise_error_if_barcode_decoder_cannot_decode_barcode(self):
        with self.assertRaisesRegexp(BarcodeError, 'ISBN must start with 978 or 979'):
            verify_barcode('isbn', '123456789')


    def test_should_return_full_unformatted_barcode_if_valid_plain_barcode_was_given(self):
        bc = verify_barcode('isbn', '9780596809485')
        self.assertEqual('9780596809485', bc)


    def test_should_return_full_unformatted_barcode_if_valid_formatted_barcode_was_given(self):
        bc = verify_barcode('isbn', '978-0-596-809485')
        self.assertEqual('9780596809485', bc)


class LibBarcodesRenderBarcodeImageTestCase(CubaneTestCase):
    """
    cubane.lib.barcodes.render_barcode_image()
    """
    def test_should_return_svg_markup_representing_barcode(self):
        markup = render_barcode_image('isbn', '978-0-596-809485')
        self.assertIn('<svg', markup)


    def test_should_return_empty_string_for_invalid_barcode(self):
        markup = render_barcode_image('isbn', '12345678')
        self.assertEqual('', markup)