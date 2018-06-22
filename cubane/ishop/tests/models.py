# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.contrib.auth.models import User
from cubane.tests.base import CubaneTestCase
from cubane.cms.models import Page
from cubane.cms.views import get_cms
from cubane.ishop.api.context import IShopClientContext
from cubane.ishop.models import *
from cubane.ishop.basket import Basket
from cubane.ishop.tests.basket import TestBasketMixin
from cubane.testapp.models import Settings
from cubane.testapp.models import Brand, BrandWithImage, BrandWithGroup
from cubane.testapp.models import Category
from cubane.testapp.models import Product
from cubane.testapp.models import Order
from cubane.testapp.models import Customer
from cubane.testapp.models import FeaturedItem
from datetime import datetime, date, timedelta
from decimal import Decimal
from freezegun import freeze_time
from mock import Mock


#
# ShopSettings
#
class IShopModelsShopSettingsHasTermsTestCase(CubaneTestCase):
    def test_has_terms_should_return_false_if_no_terms_page_is_configured(self):
        s = Settings()
        self.assertFalse(s.has_terms)


    def test_has_terms_should_return_true_if_terms_page_has_been_configured(self):
        s = Settings(terms_page=Page())
        self.assertTrue(s.has_terms)


class IShopModelsShopSettingsGetTermsTestCase(CubaneTestCase):
    def test_should_return_none_if_no_terms_page_is_configured(self):
        s = Settings()
        self.assertIsNone(s.get_terms())


    def test_should_return_url_to_terms_page_if_terms_page_has_been_configured(self):
        s = Settings(terms_page=Page(slug='terms'))
        self.assertEqual('http://www.testapp.cubane.innershed.com/terms/', s.get_terms())


class IShopModelsShopSettingsSurveyBaseTestCase(CubaneTestCase):
    SURVEY = """
        Radio
        Television
        Newspaper Advertisment

        Website

        Email Newsletter
        Website

    """


class IShopModelsShopSettingsGetSurveyOptionsTestCase(IShopModelsShopSettingsSurveyBaseTestCase):
    def test_should_return_empty_list_if_no_options_are_copnfigured(self):
        self.assertEqual([], Settings().get_survey_options())


    def test_should_return_unique_list_of_survey_options_configured(self):
        self.assertEqual([
            'Radio',
            'Television',
            'Newspaper Advertisment',
            'Website',
            'Email Newsletter'
        ], Settings(survey=self.SURVEY).get_survey_options())


class IShopModelsShopSettingsHasSurveyTestCase(IShopModelsShopSettingsSurveyBaseTestCase):
    def test_should_return_false_if_no_survey_options_are_configured(self):
        self.assertFalse(Settings().has_survey)


    def test_should_return_true_if_survey_options_are_configured(self):
        self.assertTrue(Settings(survey=self.SURVEY).has_survey)


class IShopModelsShopSettingsGetSurveyChoicesTestCase(IShopModelsShopSettingsSurveyBaseTestCase):
    def test_should_return_empty_choices_if_survey_is_not_configured(self):
        self.assertEqual(
            [('', 'Where Did You Hear About Us?...')],
            Settings().get_survey_choices()
        )


    def test_should_return_choices_for_surveys_configured(self):
        self.assertEqual([
            ('', 'Where Did You Hear About Us?...'),
            ('Radio', 'Radio'),
            ('Television', 'Television'),
            ('Newspaper Advertisment', 'Newspaper Advertisment'),
            ('Website', 'Website'),
            ('Email Newsletter', 'Email Newsletter')
        ], Settings(survey=self.SURVEY).get_survey_choices())


class IShopModelsShopOrderGetPaymentGatewayTestCase(CubaneTestCase):
    @override_settings(DEBUG=False, SHOP_TEST_MODE=False)
    def test_should_return_default_gateway_if_not_known(self):
        from cubane.payment.sagepay import SagepayPaymentGateway
        self.assertIsInstance(Order(payment_gateway=None).get_payment_gateway(), SagepayPaymentGateway)


    @override_settings(DEBUG=False, SHOP_TEST_MODE=False)
    def test_should_return_test_gateway(self):
        from cubane.payment.test_gateway import TestPaymentGateway
        self.assertIsInstance(Order(payment_gateway=settings.GATEWAY_TEST).get_payment_gateway(), TestPaymentGateway)


    @override_settings(DEBUG=False, SHOP_TEST_MODE=False)
    def test_should_return_sagepay_gateway(self):
        from cubane.payment.sagepay import SagepayPaymentGateway
        self.assertIsInstance(Order(payment_gateway=settings.GATEWAY_SAGEPAY).get_payment_gateway(), SagepayPaymentGateway)


    @override_settings(DEBUG=False, SHOP_TEST_MODE=False)
    def test_should_return_paypal_gateway(self):
        from cubane.payment.paypal import PaypalPaymentGateway
        self.assertIsInstance(Order(payment_gateway=settings.GATEWAY_PAYPAL).get_payment_gateway(), PaypalPaymentGateway)


    @override_settings(DEBUG=False, SHOP_TEST_MODE=False)
    def test_should_return_stripe_gateway(self):
        from cubane.payment.stripe_gateway import StripePaymentGateway
        self.assertIsInstance(Order(payment_gateway=settings.GATEWAY_STRIPE).get_payment_gateway(), StripePaymentGateway)


    @override_settings(DEBUG=False, SHOP_TEST_MODE=False)
    def test_should_return_stripe_gateway(self):
        from cubane.payment.deko import DekoPaymentGateway
        self.assertIsInstance(Order(payment_gateway=settings.GATEWAY_DEKO).get_payment_gateway(), DekoPaymentGateway)


    @override_settings(DEBUG=False, SHOP_TEST_MODE=True)
    def test_should_return_test_gateway_regadless_of_payment_system_that_was_used_originally(self):
        from cubane.payment.test_gateway import TestPaymentGateway
        self.assertIsInstance(Order(payment_gateway=settings.GATEWAY_DEKO).get_payment_gateway(), TestPaymentGateway)


class IShopModelsShopSettingsHasVoucherCodesTestCase(CubaneTestCase):
    def test_should_return_false_if_no_voucher_codes_are_available(self):
        self.assertFalse(Settings().has_voucher_codes)


    def test_should_return_false_if_no_enabled_voucher_code_is_available(self):
        voucher = Voucher.objects.create(enabled=False, code='TEST')
        try:
            self.assertFalse(Settings().has_voucher_codes)
        finally:
            voucher.delete()


    def test_should_return_true_if_voucher_codes_are_available(self):
        voucher = Voucher.objects.create(enabled=True, code='TEST')
        try:
            self.assertTrue(Settings().has_voucher_codes)
        finally:
            voucher.delete()


#
# ShopEntityManage
#
class IShopModelsShopEntityManagerTestCase(CubaneTestCase):
    def test_should_select_related_images_if_model_has_image_reference(self):
        self.assertEqual({'image': {}}, BrandWithImage.objects.all().query.select_related)


    def test_should_not_select_related_images_if_model_does_not_have_image_reference(self):
        self.assertFalse(Brand.objects.all().query.select_related)


#
# ShopEntity
#
class IShopModelsShopEntityGetBackendSectionGroupTestCase(CubaneTestCase):
    def test_should_return_none_if_no_group_is_defined(self):
        self.assertIsNone(Brand.get_backend_section_group())


    def test_should_return_group_name_if_group_is_defined(self):
        self.assertEqual('Foo', BrandWithGroup.get_backend_section_group())


#
# DeliveryOption
#
class IShopModelsDeliveryOptionGetFormTestCase(CubaneTestCase):
    def test_should_return_delivery_option_form(self):
        from cubane.ishop.apps.merchant.delivery.forms import DeliveryOptionForm
        self.assertEqual(DeliveryOptionForm, DeliveryOption.get_form())


class IShopModelsDeliveryOptionGetDefaultsTestCase(CubaneTestCase):
    def test_should_return_default_delivery_charges(self):
        self.assertEqual(
            (
                Decimal('1.00'),
                Decimal('2.00'),
                Decimal('3.00')
            ),
            DeliveryOption(
                uk_def=Decimal('1.00'),
                eu_def=Decimal('2.00'),
                world_def=Decimal('3.00')
            ).get_defaults()
        )


#
# CategoryBase
#
class IShopModelsCategoryTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopModelsCategoryTestCase, cls).setUpClass()
        # get_taxonomy_path() should trim titles
        cls.a = Category.objects.create(title=' A ', slug='a')
        cls.b = Category.objects.create(title=' B ', slug='b', parent=cls.a)
        cls.c = Category.objects.create(title=' C ', slug='c', parent=cls.b)


    @classmethod
    def tearDownClass(cls):
        for c in [cls.c, cls.b, cls.a]:
            c.delete()
        super(IShopModelsCategoryTestCase, cls).tearDownClass()


    #
    # get_form()
    #
    def test_get_form_should_return_default_category_form(self):
        from cubane.ishop.apps.merchant.categories.forms import CategoryFormBase
        from cubane.ishop.models import CategoryBase
        self.assertEqual(CategoryFormBase, CategoryBase.get_form())


    #
    # get_taxonomy_path()
    #
    def test_get_taxonomy_path_should_return_title_of_self_for_root_category(self):
        self.assertEqual('A', self.a.get_taxonomy_path())


    def test_get_taxonomy_path_should_return_title_path_of_direct_parent(self):
        self.assertEqual('A > B', self.b.get_taxonomy_path())


    def test_get_taxonomy_path_should_return_title_path_of_all_parents(self):
        self.assertEqual('A > B > C', self.c.get_taxonomy_path())


    #
    # get_absolute_url()
    #
    def test_get_absolute_url_should_return_absolute_url_of_category_page(self):
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/shop/category/a-%d/' % self.a.pk,
            self.a.get_absolute_url()
        )


    #
    # get_slug()
    #
    def test_get_slug_should_return_category_slug(self):
        self.assertEqual('foo', Category(slug='foo').get_slug())


    #
    # get_title_and_parent_title()
    #
    def test_get_title_and_parent_title_should_return_title_of_root_category(self):
        self.assertEqual('A', self.a.get_title_and_parent_title())


    def test_get_title_and_parent_title_should_return_title_of_parent(self):
        self.assertEqual('A / B', self.b.get_title_and_parent_title())


    #
    # get_legacy_urls()
    #
    def test_get_legacy_urls_should_return_empty_list_if_legacy_field_is_none(self):
        self.assertEqual([], Category().get_legacy_urls())


    def test_get_legacy_urls_should_return_list_of_one_element_if_legacy_field_contains_one_line(self):
        self.assertEqual(['/foo/'], Category(_legacy_urls=' /foo/ ').get_legacy_urls())


    def test_get_legacy_urls_should_return_list_of_legacy_urls_filtered_and_trimmed(self):
        self.assertEqual([
            '/foo/',
            '/bar/'
        ], Category(_legacy_urls='\n  /foo/ \n\n  \n  /bar/\n\n').get_legacy_urls())


    #
    # set_legacy_urls()
    #
    def test_set_legacy_urls_should_encode_empty_list(self):
        c = Category()
        c.set_legacy_urls([])
        self.assertEqual([], c.get_legacy_urls())


    def test_set_legacy_urls_should_encode_single_item(self):
        c = Category()
        c.set_legacy_urls(['/foo/'])
        self.assertEqual(['/foo/'], c.get_legacy_urls())


    def test_set_legacy_urls_should_encode_list_of_items(self):
        c = Category()
        c.set_legacy_urls(['/foo/', '/bar/'])
        self.assertEqual(['/foo/', '/bar/'], c.get_legacy_urls())


    #
    # to_dict()
    #
    def test_to_dict_should_encode_category_as_dictionary(self):
        self.assertEqual(
            {
                'url': 'http://www.testapp.cubane.innershed.com/shop/category/c-%d/' % self.c.pk,
                'slug': 'c',
                'id': self.c.pk,
                'title': ' C '
            },
            self.c.to_dict()
        )


    def test_to_dict_should_encode_category_as_dictionary_with_extra_fields(self):
        self.assertEqual(
            {
                'url': 'http://www.testapp.cubane.innershed.com/shop/category/c-%d/' % self.c.pk,
                'slug': 'c',
                'foo': 'bar',
                'id': self.c.pk,
                'title': ' C '
            },
            self.c.to_dict({'foo': 'bar'})
        )


#
# Variety
#
class IShopModelsVarietyTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopModelsVarietyTestCase, cls).setUpClass()
        cls.empty_variety = Variety.objects.create(
            title='Empty', slug='empty', enabled=True
        )

        cls.length = Variety.objects.create(
            title='Empty', slug='empty', unit=Variety.UNIT_LENGTH, enabled=True
        )
        cls.length_5_inch = VarietyOption.objects.create(
            title=' 5 Inch ', variety=cls.length
        )

        cls.colour = Variety.objects.create(
            title='Colour', slug='colour', enabled=True
        )
        cls.option_red = VarietyOption.objects.create(
            title=' Red ', seq=1, variety=cls.colour
        )
        cls.option_green = VarietyOption.objects.create(
            title=' Green ', seq=2, variety=cls.colour
        )

        cls.product_a = Product.objects.create(title=' A ', slug='a', price=Decimal('4.99'))
        cls.product_b = Product.objects.create(title=' B ', slug='b', price=Decimal('9.99'))
        cls.assignment_a = VarietyAssignment.objects.create(
            product=cls.product_a, variety_option=cls.length_5_inch
        )
        cls.assignment_b = VarietyAssignment.objects.create(
            product=cls.product_a, variety_option=cls.option_red
        )
        cls.assignment_c = VarietyAssignment.objects.create(
            product=cls.product_b, variety_option=cls.option_green
        )


    @classmethod
    def tearDownClass(cls):
        for v in [
            cls.assignment_c,
            cls.assignment_b,
            cls.assignment_a,
            cls.product_b,
            cls.product_a,
            cls.option_green,
            cls.option_red,
            cls.colour,
            cls.length_5_inch,
            cls.length,
            cls.empty_variety
        ]:
            v.delete()
        super(IShopModelsVarietyTestCase, cls).tearDownClass()


    #
    # get_form()
    #
    def test_get_form_should_return_default_form(self):
        from cubane.ishop.apps.merchant.varieties.forms import VarietyForm
        self.assertEqual(VarietyForm, Variety.get_form())


    #
    # is_attribute
    #
    def test_is_attribute_should_return_false_if_not_attribute(self):
        self.assertFalse(Variety().is_attribute)


    def test_is_attribute_should_return_true_if_attribute(self):
        self.assertTrue(Variety(style=Variety.STYLE_ATTRIBUTE).is_attribute)


    #
    # get_slug()
    #
    def test_get_slug_should_return_slug(self):
        self.assertEqual('foo', Variety(slug='foo').get_slug())


    #
    # format_variety_value()
    #
    def test_format_variety_value_should_return_length_with_unit_with_one_digit_precision(self):
        self.assertEqual(
            '3.5 inch (9.0 cm)',
            Variety(unit=Variety.UNIT_LENGTH).format_variety_value(Decimal('3.55'))
        )


    def test_format_variety_value_should_return_value_for_non_unit_with_one_digit_precision(self):
        self.assertEqual(
            '3.5',
            Variety().format_variety_value(Decimal('3.55'))
        )



    def test_format_variety_value_should_return_value_for_non_unit_without_formating_if_no_a_number(self):
        self.assertEqual(
            'Red',
            Variety().format_variety_value('Red')
        )


    #
    # get_options_display()
    #
    def test_get_options_display_should_return_empty_string_for_empty_list_of_options(self):
        self.assertEqual('', self.empty_variety.get_options_display())


    def test_get_options_display_should_return_single_option(self):
        self.assertEqual('5 Inch', self.length.get_options_display())


    def test_get_options_display_should_return_comma_seperated_list_of_options(self):
        self.assertEqual('Red, Green', self.colour.get_options_display())


    #
    # get_product_count_display()
    #
    def test_get_product_count_display_should_return_zero_for_unassigned_variety(self):
        self.assertEqual('0', self.empty_variety.get_product_count_display())


    def test_get_product_count_display_should_return_single_product(self):
        self.assertEqual('1', self.length.get_product_count_display())


    def test_get_product_count_display_should_return_multiple_products(self):
        self.assertEqual('2', self.colour.get_product_count_display())


#
# Variety Option
#
class IShopModelsVarietyOptionTestCase(CubaneTestCase):
    def test_label_should_format_variety_option_value(self):
        v = Variety(title='Colour', slug='colour', enabled=True)
        vo = VarietyOption(variety=v, title='Red')
        self.assertEqual('Red', vo.label)


    def test_label_should_format_variety_option_length_value(self):
        v = Variety(title='Length', slug='length', unit=Variety.UNIT_LENGTH, enabled=True)
        vo = VarietyOption(variety=v, title='5.00')
        self.assertEqual('5.0 inch (12.7 cm)', vo.label)


#
# ProductBase
#
class IShopModelsProductBaseTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopModelsProductBaseTestCase, cls).setUpClass()
        cls.cms = get_cms()

        # products
        cls.p1 = Product.objects.create(title='Foo', slug='foo', price=Decimal('4.99'))
        cls.p2 = Product.objects.create(title='Bar', slug='bar', price=Decimal('9.99'))
        cls.p3 = Product.objects.create(title='Alice', slug='alice', price=Decimal('14.99'))
        cls.p4 = Product.objects.create(title='Bob', slug='bob', price=Decimal('19.99'))
        cls.p5 = Product.objects.create(title='Joe', slug='joe', price=Decimal('24.99'))

        # media (product 2)
        cls.img1 = Media.objects.create(caption='Image 1', filename='image1.jpg')
        cls.img2 = Media.objects.create(caption='Image 2', filename='image2.jpg')
        cls.cms.add_media_to_gallery(cls.p2, [cls.img1, cls.img2])

        # attributes (product 2)
        cls.variety1 = Variety.objects.create(
            title='Variety1',
            slug='variety1',
            style=Variety.STYLE_ATTRIBUTE,
            enabled=True
        )
        cls.attr1 = VarietyOption.objects.create(
            title='Attr1', variety=cls.variety1
        )
        cls.assignment_attr1 = VarietyAssignment.objects.create(
            product=cls.p2, variety_option=cls.attr1
        )

        # disabled varieties (product 3)
        cls.variety2 = Variety.objects.create(
            title='Variety2',
            slug='variety2',
            enabled=False
        )
        cls.attr2 = VarietyOption.objects.create(
            title='Attr2', variety=cls.variety2
        )
        cls.assignment_attr2 = VarietyAssignment.objects.create(
            product=cls.p3, variety_option=cls.attr2
        )

        # disabled variety option (product 4)
        cls.variety3 = Variety.objects.create(
            title='Variety3',
            slug='variety3',
            enabled=True
        )
        cls.attr3 = VarietyOption.objects.create(
            title='Attr3', variety=cls.variety3, enabled=False
        )
        cls.assignment_attr3 = VarietyAssignment.objects.create(
            product=cls.p4, variety_option=cls.attr3
        )

        # varieties (product 5)
        cls.variety4 = Variety.objects.create(
            title='Variety4',
            slug='variety4',
            enabled=True
        )
        cls.attr4 = VarietyOption.objects.create(
            title='Attr4', variety=cls.variety4
        )
        cls.assignment_attr4 = VarietyAssignment.objects.create(
            product=cls.p5, variety_option=cls.attr4
        )

        # related products (p2)
        cls.related1 = RelatedProducts.objects.create(from_product=cls.p2, to_product=cls.p1, seq=1)
        cls.related2 = RelatedProducts.objects.create(from_product=cls.p2, to_product=cls.p3, seq=2)


    @classmethod
    def tearDownClass(cls):
        # related products
        cls.related2.delete()
        cls.related1.delete()

        # varieties
        cls.assignment_attr1.delete()
        cls.assignment_attr2.delete()
        cls.assignment_attr3.delete()
        cls.assignment_attr4.delete()
        cls.variety1.delete()
        cls.variety2.delete()
        cls.variety3.delete()
        cls.variety4.delete()
        cls.attr1.delete()
        cls.attr2.delete()
        cls.attr3.delete()
        cls.attr4.delete()

        # images
        cls.cms.clear_media_gallery(cls.p2)
        cls.img1.delete()
        cls.img2.delete()

        # products
        cls.p1.delete()
        cls.p2.delete()
        cls.p3.delete()
        cls.p4.delete()
        cls.p5.delete()
        super(IShopModelsProductBaseTestCase, cls).tearDownClass()


    #
    # get_form()
    #
    def test_get_form_should_return_default_backend_form_class(self):
        from cubane.ishop.apps.merchant.products.forms import ProductFormBase
        self.assertEqual(ProductFormBase, ProductBase.get_form())


    #
    # variety_preview_options() and set_varity_preview()
    #
    def test_variety_preview_options_should_return_none_initially(self):
        p = Product()
        self.assertIsNone(p.variety_preview_options)


    def test_set_varity_preview_should_set_variety_preview(self):
        p = Product()
        p.set_varity_preview('foo')
        self.assertEqual('foo', p.variety_preview_options)


    #
    # stocklevel_display()
    #
    def test_stocklevel_display_should_return_empty_string_for_unknown_stock_mode(self):
        p = Product(stock=-1)
        self.assertEqual('', p.stocklevel_display)


    def test_stocklevel_display_should_match_stock_available(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AVAILABLE)
        self.assertEqual(ProductBase.STOCKLEVEL_MSG_AVAILABLE, p.stocklevel_display)


    def test_stocklevel_display_should_match_out_of_stock(self):
        p = Product(stock=ProductBase.STOCKLEVEL_OUT_OF_STOCK)
        self.assertEqual(ProductBase.STOCKLEVEL_MSG_OUT_OF_STOCK, p.stocklevel_display)


    def test_stocklevel_display_should_match_available_if_stock_level_greater_zero(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AUTO, stocklevel=3)
        self.assertEqual(ProductBase.STOCKLEVEL_MSG_AVAILABLE, p.stocklevel_display)


    def test_stocklevel_display_should_match_out_of_stock_if_stock_level_equal_zero(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AUTO, stocklevel=0)
        self.assertEqual(ProductBase.STOCKLEVEL_MSG_OUT_OF_STOCK, p.stocklevel_display)


    def test_stocklevel_display_should_match_out_of_stock_if_stock_level_lower_than_zero(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AUTO, stocklevel=-3)
        self.assertEqual(ProductBase.STOCKLEVEL_MSG_OUT_OF_STOCK, p.stocklevel_display)


    def test_stocklevel_display_should_match_made_to_order(self):
        p = Product(stock=ProductBase.STOCKLEVEL_MADE_TO_ORDER)
        self.assertEqual(ProductBase.STOCKLEVEL_MSG_MADE_TO_ORDER, p.stocklevel_display)


    #
    # is_available()
    #
    def test_is_available_should_return_true_if_available(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AVAILABLE)
        self.assertTrue(p.is_available)


    def test_is_available_should_return_false_if_out_of_stock(self):
        p = Product(stock=ProductBase.STOCKLEVEL_OUT_OF_STOCK)
        self.assertFalse(p.is_available)


    def test_is_available_should_return_true_if_level_greater_than_zero(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AUTO, stocklevel=3)
        self.assertTrue(p.is_available)


    def test_is_available_should_return_false_if_level_is_zero(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AUTO, stocklevel=0)
        self.assertFalse(p.is_available)


    def test_is_available_should_return_false_if_level_lower_than_zero(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AUTO, stocklevel=-3)
        self.assertFalse(p.is_available)


    def test_is_available_should_return_true_if_made_to_order(self):
        p = Product(stock=ProductBase.STOCKLEVEL_MADE_TO_ORDER)
        self.assertTrue(p.is_available)


    def test_is_available_should_return_true_if_out_of_stock_but_pre_order(self):
        p = Product(stock=ProductBase.STOCKLEVEL_OUT_OF_STOCK, pre_order=True)
        self.assertTrue(p.is_available)


    def test_is_available_should_return_true_if_not_available_but_pre_order(self):
        p = Product(stock=ProductBase.STOCKLEVEL_AUTO, stocklevel=0, pre_order=True)
        self.assertTrue(p.is_available)


    #
    # is_pre_order()
    #
    def test_is_pre_order_should_return_true_if_pre_order_is_set(self):
        self.assertTrue(Product(pre_order=True).is_pre_order)


    def test_is_pre_order_should_return_false_if_pre_order_is_not_set(self):
        self.assertFalse(Product(pre_order=False).is_pre_order)


    #
    # is_made_to_order()
    #
    def test_is_made_to_order_should_return_true_if_stock_mode_is_made_to_order(self):
        self.assertTrue(Product(stock=ProductBase.STOCKLEVEL_MADE_TO_ORDER).is_made_to_order)


    def test_is_made_to_order_should_return_false_if_stock_mode_is_not_made_to_order(self):
        self.assertFalse(Product(stock=ProductBase.STOCKLEVEL_AVAILABLE).is_made_to_order)
        self.assertFalse(Product(stock=ProductBase.STOCKLEVEL_AUTO).is_made_to_order)
        self.assertFalse(Product(stock=ProductBase.STOCKLEVEL_OUT_OF_STOCK).is_made_to_order)


    #
    # available_display()
    #
    def test_available_display_should_return_pre_order_if_avalable_and_pre_order(self):
        self.assertEqual('Pre-Order', Product(pre_order=True).available_display)


    def test_available_display_should_return_in_stock_if_avalable_and_not_pre_order(self):
        self.assertEqual('In Stock', Product().available_display)


    def test_available_display_should_return_out_of_stock_if_out_of_stock(self):
        self.assertEqual('Out of Stock', Product(stock=ProductBase.STOCKLEVEL_OUT_OF_STOCK).available_display)


    #
    # gallery()
    #
    def test_gallery_should_return_empty_list_for_product_without_images(self):
        self.assertEqual([], self.p1.gallery)


    def test_gallery_should_return_empty_list_of_assigned_media(self):
        self.assertEqual([self.img1, self.img2], self.p2.gallery)


    def test_gallery_should_cache_assigned_media(self):
        self.assertEqual([self.img1, self.img2], self.p2.gallery)

        img3 = Media.objects.create(caption='Image 3', filename='image3.jpg')
        try:
            self.cms.add_media_to_gallery(self.p2, img3)
            self.assertEqual([self.img1, self.img2], self.p2.gallery)
        finally:
            img3.delete()


    #
    # has_varieties()
    #
    def test_has_varieties_should_return_false_if_no_varieties_are_assigned_to_product(self):
        self.assertFalse(self.p1.has_varieties)


    def test_has_varieties_should_return_false_if_only_attributes_are_assigned_to_product(self):
        self.assertFalse(self.p2.has_varieties)


    def test_has_varieties_should_return_false_if_varieties_are_assigned_to_product_but_disabled(self):
        self.assertFalse(self.p3.has_varieties)


    def test_has_varieties_should_return_false_if_variety_options_are_disabled(self):
        self.assertFalse(self.p4.has_varieties)


    def test_has_varieties_should_return_true_if_varieties_are_assigned_to_product(self):
        self.assertTrue(self.p5.has_varieties)


    #
    # related_products()
    #
    def test_related_products_should_return_empty_list_if_no_related_products_are_defined(self):
        self.assertEqual([], self.p1.related_products)


    def test_related_products_should_return_list_of_related_products(self):
        self.assertEqual([self.p1, self.p3], self.p2.related_products)


    def test_related_products_should_cache(self):
        self.assertEqual([self.p1, self.p3], self.p2.related_products)
        related = None
        try:
            related = RelatedProducts.objects.create(from_product=self.p2, to_product=self.p4, seq=3)

            # not changed, cached!
            self.assertEqual([self.p1, self.p3], self.p2.related_products)
        finally:
            if related:
                related.delete()


    #
    # get_slug()
    #
    def test_get_slug_should_return_empty_string_if_slug_is_not_set(self):
        self.assertEqual('', Product().get_slug())


    def test_get_slug_should_return_slug(self):
        self.assertEqual('foo', Product(slug='foo').get_slug())


    #
    # to_dict()
    #
    def test_to_dict_should_return_dict_representation_of_product(self):
        self.assertEqual(
            {
                'id': self.p1.pk,
                'slug': 'foo',
                'title': 'Foo',
                'url': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/' % self.p1.pk
            },
            self.p1.to_dict()
        )


    def test_to_dict_should_return_dict_representation_of_product_and_additional_information_as_given(self):
        self.assertEqual(
            {
                'id': self.p1.pk,
                'slug': 'foo',
                'title': 'Bar',
                'url': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/' % self.p1.pk
            },
            self.p1.to_dict({'title': 'Bar'})
        )


    #
    # to_ga_dict()
    #
    def test_to_ga_dict_should_return_dict_representation_of_product(self):
        self.assertEqual(
            {
                'category': None,
                'id': self.p1.pk,
                'name': 'Foo'
            },
            self.p1.to_ga_dict()
        )


    def test_to_ga_dict_should_return_dict_representation_of_product_and_additional_information_as_given(self):
        self.assertEqual(
            {
                'category': None,
                'id': self.p1.pk,
                'name': 'Bar'
            },
            self.p1.to_ga_dict({'name': 'Bar'})
        )


    #
    # get_absolute_url()
    #
    def test_get_absolute_url_should_return_absolute_url_of_product_page(self):
        product = Product()
        product.id = 1
        product.slug = 'foo'
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/' % product.pk,
            product.get_absolute_url()
        )


#
# ProductDeliveryOption
#
class IShopModelsVoucherTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopModelsVoucherTestCase, cls).setUpClass()
        zero = Decimal('0.00')
        order_model = get_order_model()
        cls.order1 = order_model.objects.create(
            status=OrderBase.STATUS_PAYMENT_CONFIRMED,
            sub_total=zero,
            sub_total_before_delivery=zero,
            delivery=zero,
            total=zero
        )
        cls.order2 = order_model.objects.create(
            status=OrderBase.STATUS_PAYMENT_CONFIRMED,
            sub_total=zero,
            sub_total_before_delivery=zero,
            delivery=zero,
            total=zero
        )

        cls.voucher = Voucher.objects.create(
            title='Test',
            code='TEST',
            valid_from=date(2017, 1, 1),
            valid_until=date(2017, 12, 31)
        )
        cls.voucher.orders = [cls.order1, cls.order2]

        cls.GB = Country.objects.get(iso='GB')
        cls.DE = Country.objects.get(iso='DE')
        cls.US = Country.objects.get(iso='US')
        cls.country_voucher = Voucher.objects.create(title='Country', code='COUNTRY')
        cls.country_voucher.delivery_countries = [cls.GB, cls.DE]


    @classmethod
    def tearDownClass(cls):
        cls.voucher.delete()
        cls.order1.delete()
        cls.order2.delete()
        super(IShopModelsVoucherTestCase, cls).tearDownClass()


    #
    # used()
    #
    def test_used_should_return_zero_for_unused_voucher(self):
        self.assertEqual(0, Voucher().used)


    def test_used_should_return_count_of_orders_assigned_to(self):
        self.assertEqual(2, self.voucher.used)


    #
    # is_available()
    #
    def test_is_available_should_return_true_for_voucher_without_max_usage_limitation(self):
        self.assertTrue(self.voucher.is_available())


    def test_is_available_should_return_true_for_voucher_used_less_than_usage_limitation(self):
        try:
            self.voucher.max_usage = 3
            self.assertTrue(self.voucher.is_available())
        finally:
            self.voucher.max_usage = None


    def test_is_available_should_return_false_for_voucher_used_equal_than_usage_limitation(self):
        try:
            self.voucher.max_usage = 2
            self.assertFalse(self.voucher.is_available())
        finally:
            self.voucher.max_usage = None


    def test_is_available_should_return_false_for_voucher_used_greater_than_usage_limitation(self):
        try:
            self.voucher.max_usage = 1
            self.assertFalse(self.voucher.is_available())
        finally:
            self.voucher.max_usage = None


    #
    # is_restricted_by_countries()
    #
    def test_is_restricted_by_countries_should_return_true_if_delivery_countries_are_defined(self):
        self.assertTrue(self.country_voucher.is_restricted_by_countries())


    def test_is_restricted_by_countries_should_return_false_if_delivery_countries_are_not_defined(self):
        self.assertFalse(self.voucher.is_restricted_by_countries())


    #
    # matches_delivery_country()
    #
    def test_matches_delivery_country_should_return_true_if_given_country_matches_valid_countries(self):
        self.assertTrue(self.country_voucher.matches_delivery_country(self.GB))
        self.assertTrue(self.country_voucher.matches_delivery_country(self.DE))


    def test_matches_delivery_country_should_return_false_if_given_country_does_not_match_valid_countries(self):
        self.assertFalse(self.country_voucher.matches_delivery_country(self.US))


    def test_matches_delivery_country_should_return_false_if_delivery_country_is_unknown(self):
        self.assertFalse(self.country_voucher.matches_delivery_country(None))


    def test_matches_delivery_country_should_return_true_if_voucher_does_not_restrict_countries_for_given_country(self):
        self.assertTrue(self.voucher.matches_delivery_country(self.US))


    def test_matches_delivery_country_should_return_true_if_voucher_does_not_restrict_countries_for_unknown_country(self):
        self.assertTrue(self.voucher.matches_delivery_country(None))


#
# OrderManager
#
@freeze_time('2016-06-01')
class IShopModelsOrderManagerTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopModelsOrderManagerTestCase, cls).setUpClass()
        cls.user = User.objects.create_user('foo', 'foo@bar.com', 'password')
        for status, label in OrderBase.STATUS_CHOICES:
            cls._create_order(cls.user, label, status, 3)


    @classmethod
    def tearDownClass(cls):
        for order in get_order_model().objects.all():
            order.delete()
        cls.user.delete()
        super(IShopModelsOrderManagerTestCase, cls).tearDownClass()


    @classmethod
    def _create_order(cls, user, order_id, status, days):
        zero = Decimal('0.00')
        updated_on = datetime(2016, 6, 1) - timedelta(days=days)
        return get_order_model().objects.create(
            customer=user,
            order_id=order_id,
            status=status,
            sub_total=zero,
            sub_total_before_delivery=zero,
            delivery=zero,
            total=zero,
            updated_on=updated_on
        )

    def test_get_processing_orders_should_return_all_orders_not_completed_within_last_n_days(self):
        self.assertEqual(
            [
                'Ready for Payment',
                'Awaiting Payment',
                'Order Placed',
                'Order Placed (Invoice)',
                'Order Placed (Zero Amount)',
                'Processing',
                'Partially Shipped',
                'Ready To Collect'
            ],
            [order.order_id for order in get_order_model().objects.get_processing_orders(self.user)]
        )


    def test_get_complete_orders_should_return_all_orders_completed_within_last_n_days(self):
        self.assertEqual(
            [
                'Order Cancelled',
                'Payment Declined',
                'Payment Error',
                'Shipped',
                'Collected'
            ],
            [order.order_id for order in get_order_model().objects.get_complete_orders(self.user)]
        )


#
# Order
#
@freeze_time('2016-06-01')
class IShopModelsOrderTestCase(CubaneTestCase, TestBasketMixin):
    @classmethod
    def setUpClass(cls):
        super(IShopModelsOrderTestCase, cls).setUpClass()
        cls.GB = Country.objects.get(iso='GB')
        cls.DE = Country.objects.get(iso='DE')
        cls.user = User.objects.create_user('foo', 'foo@bar.com', 'password')
        cls.user.first_name = 'Foo'
        cls.user.last_name = 'Bar'
        cls.user.save()
        cls.product = Product.objects.create(title='Foo', slug='foo', description='Bar', price=Decimal('50.00'))
        cls.voucher = Voucher.objects.create(title='Test', code='TEST', enabled=True, discount_type=Voucher.DISCOUNT_PRICE, discount_value=Decimal('15.00'), valid_from=date(2016, 1, 1), valid_until=date(2016, 12, 31))
        cls.delivery_eu = DeliveryOption.objects.create(title='Delivery Option EU', enabled=True, deliver_eu=True, eu_def=Decimal('7.00'))
        cls.email_page = cls._create_email_page()
        cls.settings = cls._create_settings(cls.email_page)


    @classmethod
    def tearDownClass(cls):
        cls.product.delete()
        cls.user.delete()
        cls.voucher.delete()
        cls.delivery_eu.delete()
        cls.email_page.delete()
        cls.settings.delete()
        super(IShopModelsOrderTestCase, cls).tearDownClass()


    #
    # get_filter_form()
    #
    def test_get_filter_form_should_return_filter_from(self):
        from cubane.ishop.apps.merchant.orders.forms import OrderFilterForm
        self.assertEqual(OrderFilterForm, Order().get_filter_form())


    #
    # create_from_basket()
    #
    def test_create_from_basket_should_create_order_from_given_basket(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)

        self.assertEqual(self.user, order.customer)
        self.assertEqual(OrderBase.STATUS_CHECKOUT, order.status)
        self.assertEqual(to_json(basket.billing_address), order.billing_address_json)
        self.assertEqual(to_json(basket.delivery_address), order.delivery_address_json)
        self.assertEqual(to_json(basket.save_to_dict(use_session=False)), order.basket_json_v2)
        self.assertEqual('Foo Bar', order.full_name)
        self.assertEqual('Survey', order.survey)
        self.assertEqual('foo@bar.com', order.email)
        self.assertEqual('12345678', order.telephone)
        self.assertEqual(1, order.basket_size)
        self.assertEqual('Special Requirements', order.special_requirements)
        self.assertFalse(order.click_and_collect)

        # billing
        self.assertEqual('Foo Ltd.', order.billing_company)
        self.assertEqual('Address1', order.billing_address1)
        self.assertEqual('Address2', order.billing_address2)
        self.assertEqual('Address3', order.billing_address3)
        self.assertEqual('City', order.billing_city)
        self.assertEqual('County', order.billing_county)
        self.assertEqual('NR13 6PZ', order.billing_postcode)
        self.assertEqual(self.GB, order.billing_country)

        # delivery
        self.assertEqual('Delivery Ltd.', order.delivery_company)
        self.assertEqual('Delivery Address1', order.delivery_address1)
        self.assertEqual('Delivery Address2', order.delivery_address2)
        self.assertEqual('Delivery Address3', order.delivery_address3)
        self.assertEqual('Delivery City', order.delivery_city)
        self.assertEqual('Delivery County', order.delivery_county)
        self.assertEqual('28274', order.delivery_postcode)
        self.assertEqual(self.DE, order.delivery_country)

        # PRODUCT   50.00   1    50.00
        # ----------------------------
        # SUB                    50.00
        # DISCOUNT (15.00)      -15.00
        # ----------------------------
        # SUB                    35.00
        # DELIVERY                7.00
        # ----------------------------
        #                        42.00
        self.assertEqual(Decimal('50.00'), order.sub_total)
        self.assertEqual(Decimal('7.00'), order.delivery)
        self.assertEqual(Decimal('42.00'), order.total)

        # delivery option
        self.assertEqual('Delivery Option EU', order.delivery_option_title)
        self.assertEqual(self.delivery_eu, order.delivery_option)
        self.assertFalse(order.delivery_quote)

        # identifiers
        self.assertEqual(56, len(order.secret_id))
        self.assertEqual(10, len(order.order_id))

        # voucher
        self.assertEqual('Test', order.voucher_title)
        self.assertEqual(Decimal('15.00'), order.voucher_value)


    def test_create_from_basket_should_create_order_from_given_basketwith_custom_id(self):
        request = self._create_request()
        basket = self._create_basket()
        order = OrderBase.create_from_basket(request, basket, self.user, 'foo')
        self.assertEqual('foo', order.order_id)


    #
    # tax_total()
    #
    def test_tax_total_should_return_zero_if_no_tax_is_configured(self):
        request = self._create_request()
        basket = self._create_basket()
        try:
            order = OrderBase.create_from_basket(request, basket, self.user)
            self.assertEqual(Decimal('0.00'), order.tax_total)
        finally:
            order.delete()


    def test_tax_total_should_return_percentage_of_sub_total(self):
        self.settings.tax_percent = 10
        self.settings.save()
        basket = self._create_basket()
        order = OrderBase.create_from_basket(basket.request, basket, self.user)
        try:
            self.assertEqual(Decimal('35.00'), order.sub_total_before_delivery)
            self.assertEqual(Decimal('3.50'), order.tax_total)
        finally:
            order.delete()
            self.settings.tax_percent = None
            self.settings.save()


    #
    # get_status_display()
    #
    def test_get_status_display_should_return_display_text_repr_order_status(self):
        self.assertEqual('Awaiting Payment', Order(status=OrderBase.STATUS_PAYMENT_AWAITING).get_status_display())


    #
    # get_status_text_display()
    #
    def test_get_status_text_display_should_return_current_order_status_description_text(self):
        for status, _ in OrderBase.STATUS_CHOICES:
            self.assertEqual(OrderBase.STATUS_TEXT.get(status), Order(status=status).get_status_text_display())


    def test_get_status_text_display_should_return_empty_string_for_unknown_status(self):
        self.assertEqual('', Order(status=999).get_status_text_display())


    #
    # get_tracking_provider_link()
    #
    @override_settings(TRACKING_PROVIDERS=(('foo', 'foo.com'),))
    def test_get_tracking_provider_link_should_return_link_to_tracking_provider(self):
        self.assertEqual('foo.com', Order(tracking_provider='foo').get_tracking_provider_link())


    @override_settings(TRACKING_PROVIDERS=())
    def test_get_tracking_provider_link_should_return_none_if_tracking_provider_is_unknown(self):
        self.assertIsNone(Order(tracking_provider='foo').get_tracking_provider_link())


    @override_settings(TRACKING_PROVIDERS=())
    def test_get_tracking_provider_link_should_return_none_if_tracking_provider_is_none(self):
        self.assertIsNone(Order().get_tracking_provider_link())


    #
    # total_payment()
    #
    def test_total_payment_should_return_zero_for_empty_order(self):
        request = self._create_request()
        basket = self._create_empty_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        try:
            self.assertEqual(Decimal('0.00'), order.total_payment)
        finally:
            order.delete()


    def test_total_payment_should_return_total_amount_including_delivery(self):
        basket = self._create_basket()
        order = get_order_model().create_from_basket(basket.request, basket, self.user)
        try:
            # PRODUCT   50.00   1    50.00
            # ----------------------------
            # SUB                    50.00
            # DISCOUNT (15.00)      -15.00
            # ----------------------------
            # SUB                    35.00
            # DELIVERY                7.00
            # ----------------------------
            #                        42.00
            self.assertEqual(Decimal('42.00'), order.total_payment)
        finally:
            order.delete()


    #
    # basket()
    #
    def test_basket_should_return_basket_instance_from_order(self):
        request = self._create_request()
        _basket = self._create_basket()
        order = get_order_model().create_from_basket(request, _basket, self.user)
        basket = order.basket
        try:
            self.assertIsInstance(basket, Basket)
            self.assertFalse(basket.persistent)
            self.assertIsNone(basket.request)
            self.assertEqual(Decimal('7.00'), basket.delivery)
            self.assertEqual(Decimal('15.00'), basket.discount_value)
            self.assertEqual(1, len(basket.items))
            self.assertEqual(1, basket.items[0].quantity)
            self.assertEqual(Decimal('50.00'), basket.items[0].product_price)
            self.assertEqual(Decimal('50.00'), basket.items[0].total)
            self.assertEqual(self.product.pk, basket.items[0].product_id)
            self.assertEqual(Decimal('50.00'), basket.sub_total)
            self.assertEqual(Decimal('42.00'), basket.total)
            self.assertEqual(1, basket.quantity)
            self.assertEqual('TEST', basket.voucher.code)
        finally:
            order.delete()


    #
    # billing_address()
    #
    def test_billing_address_should_return_none_if_billing_address_is_not_set(self):
        basket = self._create_blank_basket()
        self.assertIsNone(Order().billing_address)


    def test_billing_address_should_return_billing_address(self):
        request = self._create_request()
        basket = self._create_empty_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        try:
            self.assertEqual(
                {
                    'address1': 'Address1',
                    'address2': 'Address2',
                    'address3': 'Address3',
                    'city': 'City',
                    'company': 'Foo Ltd.',
                    'country': {
                        'flag_state': False,
                        'iso': 'GB',
                        'iso3': 'GBR',
                        'landlocked': False,
                        'name': 'UNITED KINGDOM',
                        'numcode': 826,
                        'calling_code': '44',
                        'printable_name': 'United Kingdom'
                    },
                    'country-iso': 'GB',
                    'county': 'County',
                    'email': 'foo@bar.com',
                    'first_name': 'Foo',
                    'last_name': 'Bar',
                    'postcode': 'NR13 6PZ',
                    'telephone': '12345678',
                    'title': Customer.TITLE_MR
                },
                order.billing_address
            )
        finally:
            order.delete()


    #
    # delivery_address()
    #
    def test_delivery_address_should_return_none_if_delivery_address_is_not_set(self):
        basket = self._create_blank_basket()
        self.assertIsNone(Order().delivery_address)


    def test_delivery_address_should_reutrn_delivery_address(self):
        request = self._create_request()
        basket = self._create_empty_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        try:
            self.assertEqual(
                {
                    'address1': 'Delivery Address1',
                    'address2': 'Delivery Address2',
                    'address3': 'Delivery Address3',
                    'city': 'Delivery City',
                    'company': 'Delivery Ltd.',
                    'country': {
                        'flag_state': False,
                        'iso': 'DE',
                        'iso3': 'DEU',
                        'landlocked': False,
                        'name': 'GERMANY',
                        'numcode': 276,
                        'calling_code': '49',
                        'printable_name': 'Germany'
                    },
                    'country-iso': 'DE',
                    'county': 'Delivery County',
                    'name': 'Delivery Name',
                    'postcode': '28274'
                },
                order.delivery_address
            )
        finally:
            order.delete()


    #
    # billing_address_title_display()
    #
    def test_billing_address_title_display_should_return_title_display_for_customer(self):
        for pk, label in Customer.TITLE_CHOICES:
            order = Order(billing_address_json=to_json({'title': pk}))
            self.assertEqual(label, order.billing_address_title_display)


    def test_billing_address_title_display_should_return_empty_string_for_unknown_title(self):
        order = Order(billing_address_json=to_json({'title': 999}))
        self.assertEqual('', order.billing_address_title_display)


    #
    # is_click_and_collect()
    #
    def test_is_click_and_collect_should_return_false_if_not_click_and_collect(self):
        self.assertFalse(Order(click_and_collect=False).is_click_and_collect)


    def test_is_click_and_collect_should_return_true_if_click_and_collect(self):
        self.assertTrue(Order(click_and_collect=True).is_click_and_collect)


    #
    # customer_display()
    #
    def test_customer_display_should_return_guest_checkout_name_if_customer_is_unknown(self):
        self.assertEqual('Guest Checkout: Foo', Order(full_name='Foo').customer_display)


    def test_customer_display_should_return_name_of_customer(self):
        self.assertEqual('Foo Bar', Order(customer=self.user).customer_display)


    #
    # billing_address_components()
    #
    def test_billing_address_components_should_return_address_components_as_list(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        self.assertEqual([
            'Address1',
            'Address2',
            'Address3',
            'City',
            'County',
            'NR13 6PZ',
            self.GB
        ], order.billing_address_components)


    def test_billing_address_components_should_obmit_empty_components(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        order.billing_address2 = ''
        order.billing_address3 = None
        self.assertEqual([
            'Address1',
            'City',
            'County',
            'NR13 6PZ',
            self.GB
        ], order.billing_address_components)


    #
    # delivery_address_components()
    #
    def test_delivery_address_components_should_return_address_components_as_list(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        self.assertEqual([
            'Delivery Name',
            'Delivery Address1',
            'Delivery Address2',
            'Delivery Address3',
            'Delivery City',
            'Delivery County',
            '28274',
            self.DE
        ], order.delivery_address_components)


    def test_delivery_address_components_should_obmit_empty_components(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        order.delivery_address2 = ''
        order.delivery_address3 = None
        self.assertEqual([
            'Delivery Name',
            'Delivery Address1',
            'Delivery City',
            'Delivery County',
            '28274',
            self.DE
        ], order.delivery_address_components)


    #
    # customer_email_display()
    #
    def test_customer_email_display_should_return_guest_checkout_name_if_customer_is_unknown(self):
        self.assertEqual('Guest Checkout: Foo <foo@bar.com>', Order(full_name='Foo', email='foo@bar.com').customer_email_display)


    def test_customer_email_display_should_return_name_if_customer(self):
        self.assertEqual('Foo Bar <foo@bar.com>', Order(customer=self.user).customer_email_display)


    #
    # get_delivery_type()
    #
    def test_get_delivery_type_should_return_click_and_collect_for_click_and_collect_orders(self):
        self.assertEqual(
            OrderBase.BACKEND_DELIVERY_TYPE_CLICK_AND_COLLECT,
            Order(click_and_collect=True).get_delivery_type()
        )


    def test_get_delivery_type_should_return_delivery_for_delivery_orders(self):
        self.assertEqual(
            OrderBase.BACKEND_DELIVERY_TYPE_DELIVERY,
            Order(click_and_collect=False).get_delivery_type()
        )


    #
    # set_delivery_type()
    #
    def test_set_delivery_type_should_set_click_and_collect(self):
        order = Order()
        order.set_delivery_type(OrderBase.BACKEND_DELIVERY_TYPE_CLICK_AND_COLLECT)
        self.assertEqual(OrderBase.BACKEND_DELIVERY_TYPE_CLICK_AND_COLLECT, order.get_delivery_type())
        self.assertTrue(order.is_click_and_collect)


    def test_set_delivery_type_should_set_delivery(self):
        order = Order()
        order.set_delivery_type(OrderBase.BACKEND_DELIVERY_TYPE_DELIVERY)
        self.assertEqual(OrderBase.BACKEND_DELIVERY_TYPE_DELIVERY, order.get_delivery_type())
        self.assertFalse(order.is_click_and_collect)


    #
    # can_execute_action()
    #
    def test_can_execute_action_should_return_true_for_approve_or_reject_if_waiting_for_approval(self):
        order = Order(approval_status=OrderBase.APPROVAL_STATUS_WAITING)
        self.assertTrue(order.can_execute_action({'view': 'approve'}))
        self.assertTrue(order.can_execute_action({'view': 'reject'}))


    def test_can_execute_action_should_return_false_for_approve_or_reject_if_not_waiting_for_approval(self):
        order = Order(approval_status=OrderBase.APPROVAL_STATUS_APPROVED)
        self.assertFalse(order.can_execute_action({'view': 'approve'}))
        self.assertFalse(order.can_execute_action({'view': 'reject'}))


    def test_can_execute_action_should_return_true_for_unknown_actions(self):
        order = Order(approval_status=OrderBase.APPROVAL_STATUS_WAITING)
        self.assertTrue(order.can_execute_action({'view': 'foo'}))


    #
    # clone()
    #
    def test_clone_should_clone_order_with_new_secret_key_and_order_id(self):
        request = self._create_request()
        _basket = self._create_basket()
        order = get_order_model().create_from_basket(request, _basket, self.user, 'foo')
        cloned_order = order.clone(request)
        basket = cloned_order.basket
        try:
            self.assertIsNone(cloned_order.custom_order_id)
            self.assertNotEqual(order.order_id, cloned_order.order_id)
            self.assertNotEqual(order.secret_id, cloned_order.secret_id)
            self.assertEqual(OrderBase.STATUS_CHECKOUT, cloned_order.status)

            self.assertEqual(Decimal('15.00'), basket.discount_value)
            self.assertEqual(1, basket.quantity)
            self.assertEqual(Decimal('42.00'), basket.total)
        finally:
            cloned_order.delete()
            order.delete()


    #
    # approve()
    #
    def test_approve_should_return_false_if_order_is_not_approvable(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        try:
            self.assertEqual(
                (False, 'Order is not awaiting approval.'),
                order.approve(request)
            )
        finally:
            order.delete()


    def test_approve_should_settle_payment_and_send_notification_email(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        order.payment_gateway = settings.GATEWAY_TEST
        order.approval_status = OrderBase.APPROVAL_STATUS_WAITING
        try:
            # should settle payment
            self.assertEqual(
                (True, 'Test payment settled successfully.'),
                order.approve(request)
            )
            self.assertEqual(OrderBase.APPROVAL_STATUS_APPROVED, order.approval_status)

            # notification email
            m = self.get_latest_email()
            self.assertTrue('foo@bar.com' in m.to)
            self.assertIn('Order approved', m.subject)
            self.assertIn('<h1>Test</h1>', m.message().as_string())
        finally:
            order.delete()


    #
    # reject()
    #
    def test_reject_should_return_false_if_order_is_not_rejectable(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        order.payment_gateway = settings.GATEWAY_TEST
        try:
            self.assertEqual(
                (False, 'Order is not awaiting approval.'),
                order.reject(request)
            )
        finally:
            order.delete()


    def test_reject_should_abort_payment_and_send_notification_email(self):
        request = self._create_request()
        basket = self._create_basket()
        order = get_order_model().create_from_basket(request, basket, self.user)
        order.payment_gateway = settings.GATEWAY_TEST
        order.approval_status = OrderBase.APPROVAL_STATUS_WAITING
        try:
            # should abort payment
            self.assertEqual(
                (True, 'Test payment aborted successfully.'),
                order.reject(request, 'Reject Message')
            )
            self.assertEqual(OrderBase.APPROVAL_STATUS_REJECTED, order.approval_status)
            self.assertEqual('Reject Message', order.reject_msg)

            # notification email
            m = self.get_latest_email()
            self.assertTrue('foo@bar.com' in m.to)
            self.assertIn('Order rejected', m.subject)
            self.assertIn('<h1>Test</h1>', m.message().as_string())
        finally:
            order.delete()


    #
    # set_payment_details() and get_payment_details()
    #
    def test_set_payment_details_should_set_payment_details(self):
        order = Order()
        order.set_payment_details({'foo': 'bar'})
        self.assertEqual({'foo': 'bar'}, order.get_payment_details())


    #
    # is_checkout()
    #
    def test_is_checkout_should_return_true_if_status_is_checkout(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_CHECKOUT).is_checkout())


    def test_is_checkout_should_return_false_if_status_is_not_checkout(self):
        self.assertFalse(self._create_order_status(-1).is_checkout())


    #
    # is_payment_awaiting()
    #
    def test_is_payment_awaiting_should_return_true_if_status_is_payment_awaiting(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_AWAITING).is_payment_awaiting())


    def test_is_payment_awaiting_should_return_false_if_status_is_not_payment_awaiting(self):
        self.assertFalse(self._create_order_status(-1).is_payment_awaiting())


    #
    # is_payment_cancelled()
    #
    def test_is_payment_cancelled_should_return_true_if_status_is_payment_cancelled(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_CANCELLED).is_payment_cancelled())


    def test_is_payment_cancelled_should_return_false_if_status_is_not_payment_cancelled(self):
        self.assertFalse(self._create_order_status(-1).is_payment_cancelled())


    #
    # is_payment_declined()
    #
    def test_is_payment_declined_should_return_true_if_status_is_payment_declined(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_DECLINED).is_payment_declined())


    def test_is_payment_declined_should_return_false_if_status_is_not_payment_declined(self):
        self.assertFalse(self._create_order_status(-1).is_payment_declined())


    #
    # is_payment_error()
    #
    def test_is_payment_error_should_return_true_if_status_is_payment_error(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_ERROR).is_payment_error())


    def test_is_payment_error_should_return_false_if_status_is_not_payment_error(self):
        self.assertFalse(self._create_order_status(-1).is_payment_error())


    #
    # is_payment_confirmed()
    #
    def test_is_payment_confirmed_should_return_true_if_status_is_payment_confirmed(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_CONFIRMED).is_payment_confirmed())


    def test_is_payment_confirmed_should_return_false_if_status_is_not_payment_confirmed(self):
        self.assertFalse(self._create_order_status(-1).is_payment_confirmed())


    #
    # is_partially_shipped()
    #
    def test_is_partially_shipped_should_return_true_if_status_is_partially_shipped(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PARTIALLY_SHIPPED).is_partially_shipped())


    def test_is_partially_shipped_should_return_false_if_status_is_not_partially_shipped(self):
        self.assertFalse(self._create_order_status(-1).is_partially_shipped())


    #
    # is_shipped()
    #
    def test_is_shipped_should_return_true_if_status_is_shipped(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_SHIPPED).is_shipped())


    def test_is_shipped_should_return_false_if_status_is_not_shipped(self):
        self.assertFalse(self._create_order_status(-1).is_shipped())


    #
    # waits_for_approval()
    #
    def test_waits_for_approval_should_return_true_if_status_is_waits_for_approval(self):
        self.assertTrue(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_WAITING).waits_for_approval())


    def test_waits_for_approval_should_return_false_if_status_is_waits_for_approval(self):
        self.assertFalse(self._create_order_approval_status(-1).waits_for_approval())


    #
    # is_approved()
    #
    def test_is_approved_should_return_true_if_approval_status_is_approved(self):
        self.assertTrue(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_APPROVED).is_approved())


    def test_is_approved_should_return_false_if_approval_status_is_not_approved(self):
        self.assertFalse(self._create_order_approval_status(-1).is_approved())


    #
    # is_rejected()
    #
    def test_is_rejected_should_return_true_if_approval_status_is_rejected(self):
        self.assertTrue(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_REJECTED).is_rejected())


    def test_is_rejected_should_return_false_if_approval_status_is_not_rejected(self):
        self.assertFalse(self._create_order_approval_status(-1).is_rejected())


    #
    # is_timeout()
    #
    def test_is_timeout_should_return_true_if_approval_status_is_timeout(self):
        self.assertTrue(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_TIMEOUT).is_timeout())


    def test_is_timeout_should_return_false_if_approval_status_is_not_timeout(self):
        self.assertFalse(self._create_order_approval_status(-1).is_timeout())


    #
    # is_rejected_or_timeout()
    #
    def test_is_rejected_or_timeout_should_return_true_if_approval_status_is_rejected(self):
        self.assertTrue(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_REJECTED).is_rejected_or_timeout())


    def test_is_rejected_or_timeout_should_return_true_if_approval_status_is_timeout(self):
        self.assertTrue(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_TIMEOUT).is_rejected_or_timeout())


    def test_is_rejected_or_timeout_should_return_false_if_approval_status_is_not_rejected_nor_timeout(self):
        self.assertFalse(self._create_order_approval_status(-1).is_rejected_or_timeout())


    #
    # can_change_payment_status()
    #
    def test_can_change_payment_status_should_return_true_if_approval_status_is_not_rejected_or_timeout(self):
        self.assertTrue(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_APPROVED).can_change_payment_status())


    def test_can_change_payment_status_should_return_false_if_approval_status_is_rejected(self):
        self.assertFalse(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_REJECTED).can_change_payment_status())


    def test_can_change_payment_status_should_return_false_if_approval_status_is_timeout(self):
        self.assertFalse(self._create_order_approval_status(OrderBase.APPROVAL_STATUS_TIMEOUT).can_change_payment_status())


    #
    # can_be_registered_for_payment()
    #
    def test_can_be_registered_for_payment_should_return_true_if_state_is_checkout(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_CHECKOUT).can_be_registered_for_payment())


    def test_can_be_registered_for_payment_should_return_true_if_state_is_payment_awaiting(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_AWAITING).can_be_registered_for_payment())


    def test_can_be_registered_for_payment_should_return_true_if_state_is_payment_error(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_ERROR).can_be_registered_for_payment())


    def test_can_be_registered_for_payment_should_return_false_if_state_is_payment_confirmed(self):
        self.assertFalse(self._create_order_status(OrderBase.STATUS_PAYMENT_CONFIRMED).can_be_registered_for_payment())


    #
    # is_retry()
    #
    def test_is_retry_should_return_true_if_status_is_payment_declined(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_DECLINED).is_retry())


    def test_is_retry_should_return_true_if_status_is_payment_error(self):
        self.assertTrue(self._create_order_status(OrderBase.STATUS_PAYMENT_ERROR).is_retry())


    def test_is_retry_should_return_false_if_status_is_payment_confirmed(self):
        self.assertFalse(self._create_order_status(OrderBase.STATUS_PAYMENT_CONFIRMED).is_retry())


    #
    # get_est_shipping_date() and get_est_delivery_date()
    #
    def test_get_est_shipping_date_should_be_same_day_when_ordered_before_4(self):
        o = Order(created_on=datetime(2016, 1, 29, 12, 0))
        self.assertEqual(date(2016, 1, 29), o.get_est_shipping_date(False))
        self.assertEqual(date(2016, 2, 3), o.get_est_delivery_date(False))


    def test_get_est_shipping_date_should_be_next_day_when_ordered_after_4(self):
        o = Order(created_on=datetime(2016, 1, 29, 16, 0))
        self.assertEqual(date(2016, 1, 30), o.get_est_shipping_date(False))
        self.assertEqual(date(2016, 2, 4), o.get_est_delivery_date(False))


    def test_get_est_shipping_date_should_be_3_days_for_preorder(self):
        o = Order(created_on=datetime(2016, 1, 29, 16, 0))
        self.assertEqual(date(2016, 2, 1), o.get_est_shipping_date(True))
        self.assertEqual(date(2016, 2, 6), o.get_est_delivery_date(True))


    #
    # update_stock_levels()
    #
    def test_update_stock_levels_should_change_stocklevel(self):
        request = self.make_request('get', '/')
        order = Order()
        p1 = Product.objects.create(title='P1', stock=ProductBase.STOCKLEVEL_AVAILABLE, stocklevel=3, price=Decimal('5.00'), slug='p1')
        p2 = Product.objects.create(title='P2', stock=ProductBase.STOCKLEVEL_OUT_OF_STOCK, stocklevel=3, price=Decimal('5.00'), slug='p2')
        p3 = Product.objects.create(title='P3', stock=ProductBase.STOCKLEVEL_AUTO, stocklevel=3, price=Decimal('5.00'), slug='p3')
        p4 = Product.objects.create(title='P4', stock=ProductBase.STOCKLEVEL_MADE_TO_ORDER, stocklevel=3, price=Decimal('5.00'), slug='p4')
        try:
            basket = Basket(request)
            basket.add_item(p1, quantity=4)
            basket.add_item(p2, quantity=4)
            basket.add_item(p3, quantity=4)
            basket.add_item(p4, quantity=4)
            order.save_basket(basket)

            # test update stock
            order.update_stock_levels()

            # load products again
            p1 = Product.objects.get(slug='p1')
            p2 = Product.objects.get(slug='p2')
            p3 = Product.objects.get(slug='p3')
            p4 = Product.objects.get(slug='p4')

            # p1, p2 and p4 should be untouched
            for p in [p1, p2, p4]:
                self.assertEqual(3, p.stocklevel)

            # p3 should have been updated
            self.assertEqual(-1, p3.stocklevel)
        finally:
            p1.delete()
            p2.delete()
            p3.delete()
            p4.delete()


    #
    # get_absolute_url()
    #
    def test_get_absolute_url_should_return_secret_url_to_order_including_hash(self):
        order = Order()
        order.secret_id = 'abcdef'
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/shop/order/status/abcdef/',
            order.get_absolute_url()
        )


    #
    # Helpers
    #
    @classmethod
    def _create_email_page(cls):
        page = Page()
        page.title = 'Test Page'
        page.slug = 'test'
        page.template = 'testapp/mail/enquiry_visitor.html'
        page.set_slot_content('content', '<h1>Test</h1>')
        page.save()
        return page


    @classmethod
    def _create_settings(cls, email_page):
        settings = Settings()
        settings.shop_email_template = email_page
        settings.save()
        return settings


    def _create_basket(self):
        basket = self._create_empty_basket()
        basket.survey = 'Survey'
        basket.add_item(self.product)
        basket.set_delivery_option(self.delivery_eu)
        basket.set_special_requirements('Special Requirements')
        basket.set_voucher('TEST')
        return basket


    def _create_empty_basket(self):
        basket = self._create_blank_basket()
        self._set_billing_address(basket)
        self._set_delivery_address(basket)
        return basket


    def _create_blank_basket(self):
        request = self._create_request()
        basket = Basket(request)
        return basket


    def _create_request(self):
        request = self.make_request('get', '/')
        request.context = IShopClientContext(request)
        request.settings = self.settings
        return request


    def _create_order_status(self, status):
        order = Order()
        order.status = status
        return order


    def _create_order_approval_status(self, approval_status):
        order = Order()
        order.approval_status = approval_status
        return order


class IShopModelsVarietyAssignmentManagerTestCase(CubaneTestCase):
    #
    # to_hierarchy()
    #
    @classmethod
    def setUpClass(cls):
        super(IShopModelsVarietyAssignmentManagerTestCase, cls).setUpClass()
        # Colour (Red, Green)
        cls.colour = Variety.objects.create(
            title='Colour',
            display_title='Colour',
            slug='colour',
            enabled=True,
            preview_listing=True
        )
        cls.option_red = VarietyOption.objects.create(
            title='Red', seq=1, variety=cls.colour
        )
        cls.option_green = VarietyOption.objects.create(
            title='Green', seq=2, variety=cls.colour
        )

        # Size (14, 16)
        cls.size = Variety.objects.create(
            title='Dress Size', display_title='Size', slug='size', enabled=True
        )
        cls.option_14 = VarietyOption.objects.create(
            title='14', seq=1, variety=cls.size
        )
        cls.option_16 = VarietyOption.objects.create(
            title='16', seq=2, variety=cls.size
        )

        cls.product_a = Product.objects.create(title=' A ', slug='a', price=Decimal('4.99'))
        cls.product_b = Product.objects.create(title=' B ', slug='b', price=Decimal('9.99'))
        cls.assignment_a = VarietyAssignment.objects.create(
            product=cls.product_a, variety_option=cls.option_red
        )
        cls.assignment_b = VarietyAssignment.objects.create(
            product=cls.product_a, variety_option=cls.option_green
        )
        cls.assignment_c = VarietyAssignment.objects.create(
            product=cls.product_b, variety_option=cls.option_red
        )
        cls.assignment_d = VarietyAssignment.objects.create(
            product=cls.product_b, variety_option=cls.option_16
        )
        cls.assignments = [
            cls.assignment_a,
            cls.assignment_b,
            cls.assignment_c,
            cls.assignment_d,
        ]
        cls.checked = [
            cls.option_red.pk,
            cls.option_14.pk
        ]


    @classmethod
    def tearDownClass(cls):
        for v in [
            cls.assignment_d,
            cls.assignment_c,
            cls.assignment_b,
            cls.assignment_a,
            cls.product_b,
            cls.product_a,
            cls.option_16,
            cls.option_14,
            cls.option_green,
            cls.option_red,
            cls.size,
            cls.colour,
        ]:
            v.delete()
        super(IShopModelsVarietyAssignmentManagerTestCase, cls).tearDownClass()


    #
    # to_hierarchy()
    #
    def test_to_hierarchy_should_return_varieties_and_corresponding_options(self):
        m = VarietyAssignmentManager()
        self.assertEqual(
            {
                self.colour.pk: {
                    'id': self.colour.pk,
                    'checked': 1,
                    'display_title': 'Colour',
                    'options': [
                        {'image': None, 'checked': True, 'id': 'variety-%d' % self.option_red.pk, 'value': self.option_red.pk, 'title': 'Red'},
                        {'image': None, 'checked': False, 'id': 'variety-%d' % self.option_green.pk, 'value': self.option_green.pk, 'title': 'Green'}
                    ],
                    'option_ids': [self.option_red.pk, self.option_green.pk],
                    'arg': 'v'
                },
                self.size.pk: {
                    'id': self.size.pk,
                    'checked': 0,
                    'display_title': 'Size',
                    'options': [
                        {'image': None, 'checked': False, 'id': 'variety-%d' % self.option_16.pk, 'value': self.option_16.pk, 'title': '16'}
                    ],
                    'option_ids': [self.option_16.pk],
                    'arg': 'v'
                }
            },
            m.to_hierarchy(self.assignments, self.checked)
        )


    #
    # get_variety_filters_for_products()
    #
    def test_get_variety_filters_for_products_should_return_varieties_and_options_for_products(self):
        m = VarietyAssignmentManager()
        self.assertEqual(
            {
                self.colour.pk: {
                    'id': self.colour.pk,
                    'checked': 1,
                    'display_title': 'Colour',
                    'options': [
                        {'image': None, 'checked': True, 'id': 'variety-%d' % self.option_red.pk, 'value': self.option_red.pk, 'title': 'Red'},
                        {'image': None, 'checked': False, 'id': 'variety-%d' % self.option_green.pk, 'value': self.option_green.pk, 'title': 'Green'}
                    ],
                    'option_ids': [self.option_red.pk, self.option_green.pk],
                    'arg': 'v'
                }
            },
            m.get_variety_filters_for_products([self.product_a], self.checked)
        )


    #
    # inject_product_variety_preview()
    #
    def test_inject_product_variety_preview_should_inject_varieties_with_preview_enabled(self):
        m = VarietyAssignmentManager()
        m.inject_product_variety_preview([self.product_a, self.product_b])
        self.assertEqual(
            [('Red', None), ('Green', None)],
            self.product_a.variety_preview_options
        )


class IShopModelsVarietyAssignmentTestCase(CubaneTestCase):
    #
    # label()
    #
    def test_label_should_return_label_of_variety_option(self):
        va = VarietyAssignment()
        va.variety_option = VarietyOption()
        va.variety_option.title = 'Foo'
        va.variety_option.variety = Variety()
        self.assertEqual('Foo', va.label)


class IShopModelsProductSKUManagerTestCase(CubaneTestCase):
    def setUp(self):
        # Colour (Red, Green)
        self.colour = Variety.objects.create(
            title='Colour',
            display_title='Colour',
            slug='colour',
            sku=True,
            enabled=True,
        )
        self.option_red = VarietyOption.objects.create(
            title='Red', seq=1, variety=self.colour
        )
        self.option_blue = VarietyOption.objects.create(
            title='Blue', seq=2, variety=self.colour
        )

        # Size (12, 14)
        self.size = Variety.objects.create(
            title='Dress Size',
            display_title='Size',
            slug='size',
            sku=True,
            enabled=True
        )
        self.option_12 = VarietyOption.objects.create(
            title='12', seq=1, variety=self.size
        )
        self.option_14 = VarietyOption.objects.create(
            title='14', seq=2, variety=self.size
        )

        self.product = Product.objects.create(title='Foo', slug='foo', price=Decimal('4.99'))
        self.variety_assignments = [
            VarietyAssignment.objects.create(product=self.product, variety_option=self.option_red),
            VarietyAssignment.objects.create(product=self.product, variety_option=self.option_blue),
            VarietyAssignment.objects.create(product=self.product, variety_option=self.option_12),
            VarietyAssignment.objects.create(product=self.product, variety_option=self.option_14)
        ]
        self.sku_red_12 = ProductSKU.objects.create(product=self.product, sku='RED12', price=Decimal('1.00'))
        self.sku_red_12.variety_options.add(self.option_red, self.option_12)

        self.sku_red_14 = ProductSKU.objects.create(product=self.product, sku='RED14', price=Decimal('2.00'))
        self.sku_red_14.variety_options.add(self.option_red, self.option_14)

        self.sku_blue_14 = ProductSKU.objects.create(product=self.product, sku='BLUE14', price=Decimal('4.00'))
        self.sku_blue_14.variety_options.add(self.option_blue, self.option_14)


    def tearDown(self):
        for v in self.variety_assignments + [
            self.sku_red_12,
            self.sku_red_14,
            self.sku_blue_14,
            self.product,
            self.option_14,
            self.option_12,
            self.option_blue,
            self.option_red,
            self.size,
            self.colour,
        ]:
            try:
                v.delete()
            except:
                pass


    #
    # ProductSKUManager.get_by_variety_options()
    #
    def test_get_by_variety_options_should_return_matching_sku(self):
        sku = ProductSKU.objects.get_by_variety_options(self.product, [self.option_red, self.option_14])
        self.assertEqual('RED14', sku.sku)
        self.assertEqual(Decimal('2.00'), sku.price)


    def test_get_by_variety_options_should_return_first_match_with_incomplete_list_of_varieties(self):
        sku = ProductSKU.objects.get_by_variety_options(self.product, [self.option_red])
        self.assertEqual('RED12', sku.sku)


    def test_get_by_variety_options_should_return_none_if_no_match_is_found(self):
        sku = ProductSKU.objects.get_by_variety_options(self.product, [self.option_blue, self.option_12])
        self.assertIsNone(sku)


    #
    # Variety.delete()
    #
    def test_deleting_variety_should_unlink_skus_delete_duplicate_combinations_and_delete_assignments(self):
        self.size.delete()
        self.assertEqual(['Blue', 'Red'], self._get_assignments())
        self.assertEqual([
            ('BLUE14', ['Blue']),
            ('RED12', ['Red'])
        ], self._get_skus())


    #
    # VarietyOption.delete()
    #
    def test_deleting_variety_option_should_delete_skus_and_assignments(self):
        self.option_blue.delete()
        self.assertEqual(['12', '14', 'Red'], self._get_assignments())
        self.assertEqual([
            ('RED12', ['12', 'Red']),
            ('RED14', ['14', 'Red'])
        ], self._get_skus())


    def _get_assignments(self):
        assignments = VarietyAssignment.objects.filter(product=self.product).order_by('variety_option__title')
        return [a.variety_option.title for a in assignments]


    def _get_skus(self):
        skus = ProductSKU.objects.filter(product=self.product).order_by('sku')
        return [
            (sku.sku, [vo.title for vo in sku.variety_options.all().order_by('title')])
            for sku in skus
        ]


class IShopModelsFeaturedItemBaseTestCase(CubaneTestCase):
    #
    # get_form
    #
    def test_get_form_should_return_default_featured_item_form(self):
        from cubane.ishop.featured.forms import FeaturedItemBaseForm
        self.assertEqual(FeaturedItemBaseForm, FeaturedItemBase.get_form())


    #
    # has_product()
    #
    def test_has_product_should_return_false_if_no_product_is_assigned(self):
        self.assertFalse(FeaturedItem().has_product)


    def test_has_product_should_return_true_if_product_is_assigned(self):
        item = FeaturedItem()
        item.product_id = 1
        self.assertTrue(item.has_product)


    #
    # url()
    #
    def test_url_should_return_product_url_if_product_is_assigned(self):
        item = FeaturedItem()
        item.product = Product()
        item.product.pk = 1
        item.product.slug = 'foo'
        item.product_id = item.product.pk
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/shop/product/foo-1/',
            item.url
        )


    def test_url_should_return_category_url_if_category_is_assigned(self):
        item = FeaturedItem()
        item.category = Category()
        item.category.pk = 1
        item.category.slug = 'foo'
        item.category_id = item.category.pk
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/shop/category/foo-1/',
            item.url
        )


    def test_url_should_return_page_url_if_page_is_assigned(self):
        item = FeaturedItem()
        item.page = Page()
        item.page.pk = 1
        item.page.slug = 'foo'
        item.page_id = item.page.pk
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/foo/',
            item.url
        )


    def test_url_should_return_empty_string_if_no_valid_url_can_be_determined(self):
        item = FeaturedItem()
        self.assertEqual('', item.url)


    #
    # featured_image()
    #
    def test_featured_image_should_return_image_if_assigned(self):
        item = FeaturedItem()
        image = Media()
        image.pk = 1
        item.image_id = image.pk
        item.image = image
        self.assertEqual(image, item.featured_image)


    def test_featured_image_should_return_product_image_if_item_image_is_not_available(self):
        item = FeaturedItem()
        image = Media()
        image.pk = 1
        product = Product()
        product.pk = 1
        product.image = image
        item.product_id = product.pk
        item.product = product
        self.assertEqual(image, item.featured_image)


    def test_featured_image_should_return_category_image_if_item_image_is_not_available(self):
        item = FeaturedItem()
        image = Media()
        image.pk = 1
        category = Category()
        category.pk = 1
        category.image = image
        item.category_id = category.pk
        item.category = category
        self.assertEqual(image, item.featured_image)


    def test_featured_image_should_return_page_image_if_item_image_is_not_available(self):
        item = FeaturedItem()
        image = Media()
        image.pk = 1
        page = Page()
        page.pk = 1
        page.image = image
        item.page_id = page.pk
        item.page = page
        self.assertEqual(image, item.featured_image)


    def test_featured_image_should_return_none_if_no_image_is_available(self):
        self.assertIsNone(FeaturedItem().featured_image)


    #
    # related_image()
    #
    def test_related_image_should_return_product_image_if_available(self):
        item = FeaturedItem()
        image = Media()
        image.pk = 1
        product = Product()
        product.pk = 1
        product.image = image
        item.product_id = product.pk
        item.product = product
        self.assertEqual(image, item.related_image)


    def test_related_image_should_return_category_image_if_available(self):
        item = FeaturedItem()
        image = Media()
        image.pk = 1
        category = Category()
        category.pk = 1
        category.image = image
        item.category_id = category.pk
        item.category = category
        self.assertEqual(image, item.related_image)


    def test_related_image_should_return_page_image_if_available(self):
        item = FeaturedItem()
        image = Media()
        image.pk = 1
        page = Page()
        page.pk = 1
        page.image = image
        item.page_id = page.pk
        item.page = page
        self.assertEqual(image, item.related_image)


    def test_related_image_should_return_none_if_no_related_object_is_available(self):
        self.assertIsNone(FeaturedItem().related_image)


class IShopModelsCustomerTestCase(CubaneTestCase):
    #
    # get_user_title_display()
    #
    def test_get_user_title_display_should_return_title_display_value(self):
        self.assertEqual('Mrs', Customer.get_user_title_display(Customer.TITLE_MRS))


    def test_get_user_title_display_should_return_empty_string_for_unknown_title_encoding(self):
        self.assertEqual('', Customer.get_user_title_display(-1))


    #
    # save()
    #
    def test_save_should_create_and_update_underlying_user_account_details(self):
        # account should have been created
        customer = Customer()
        customer.first_name = 'Foo'
        customer.last_name = 'Bar'
        customer.email = 'foo@bar.com'
        customer.country = Country.objects.get(iso='GB')
        customer.save()
        self.assertEqual('Foo', customer.user.first_name)
        self.assertEqual('Bar', customer.user.last_name)
        self.assertEqual('foo@bar.com', customer.user.email)

        # changing customer details should maintain user record
        customer.first_name = 'Foo 2'
        customer.last_name = 'Bar 2'
        customer.email = 'foo2@bar2.com'
        customer.save()
        self.assertEqual('Foo 2', customer.user.first_name)
        self.assertEqual('Bar 2', customer.user.last_name)
        self.assertEqual('foo2@bar2.com', customer.user.email)

        # deleting customer should delete underlying user account as well
        customer.delete()
        self.assertEqual(0, User.objects.filter(email='foo2@bar2.com').count())
        self.assertEqual(0, Customer.objects.filter(email='foo2@bar2.com').count())


class IShopModelsDeliveryAddressTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopModelsDeliveryAddressTestCase, cls).setUpClass()
        cls.user = User.objects.create_user('foo', 'password', 'foo@bar.com')
        cls.address = DeliveryAddress.objects.create(
            user=cls.user,
            company='Company',
            address1='Address1',
            address2='Address2',
            address3='Address3',
            city='City',
            county='County',
            postcode='Postcode',
            country=Country.objects.get(iso='GB')
        )


    @classmethod
    def tearDownClass(cls):
        cls.address.delete()
        cls.user.delete()
        super(IShopModelsDeliveryAddressTestCase, cls).tearDownClass()


    #
    # get_parts()
    #
    def test_get_parts_should_return_empty_list_for_empty_address(self):
        self.assertEqual([], DeliveryAddress().get_parts())


    def test_get_parts_should_return_address_components(self):
        self.assertEqual([
            'Company',
            'Address1',
            'Address2',
            'Address3',
            'City',
            'County',
            'Postcode',
            'United Kingdom'
        ], self.address.get_parts())


    def test_get_parts_should_obmit_missing_components(self):
        address = DeliveryAddress.objects.get(pk=self.address.pk)
        address.company = None
        address.address2 = None
        address.address3 = ''
        self.assertEqual([
            'Address1',
            'City',
            'County',
            'Postcode',
            'United Kingdom'
        ], address.get_parts())


class IShopModelsUserMixinTestCase(CubaneTestCase):
    #
    # full_name()
    #
    def test_full_name_should_return_empty_string_if_no_name_is_available(self):
        self.assertEqual('', User().full_name)


    def test_full_name_should_return_obmit_first_name_if_missing(self):
        user = User()
        user.last_name = 'Bar'
        self.assertEqual('Bar', user.full_name)


    def test_full_name_should_return_obmit_last_name_if_missing(self):
        user = User()
        user.first_name = 'Foo'
        self.assertEqual('Foo', user.full_name)


    def test_full_name_should_return_first_name_and_last_name(self):
        user = User()
        user.first_name = 'Foo'
        user.last_name = 'Bar'
        self.assertEqual('Foo Bar', user.full_name)
