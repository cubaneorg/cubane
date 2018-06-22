# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.test.client import RequestFactory
from cubane.tests.base import CubaneTestCase
from cubane.models import Country
from cubane.cms.models import Page
from cubane.lib.libjson import decode_json
from cubane.testapp.models import Settings, Product, Category, Customer
from cubane.media.models import Media
from cubane.ishop import get_order_model
from cubane.ishop.api.context import IShopClientContext
from cubane.ishop.models import OrderBase
from cubane.ishop.models import Variety, VarietyOption, VarietyAssignment
from cubane.ishop.models import Voucher, DeliveryOption
from cubane.ishop.basket import *
from decimal import Decimal
from freezegun import freeze_time
from mock import patch, Mock
import datetime
import copy


class IShopBasketGetHashTestCase(CubaneTestCase):
    def test_should_return_unique_hash_for_product(self):
        self.assertNotEqual(get_hash(Product(id=1)), get_hash(Product(id=2)))


    def test_should_return_same_hash_for_same_product(self):
        self.assertEqual(get_hash(Product(id=1)), get_hash(Product(id=1)))


    def test_should_return_same_hash_for_product_with_single_variety(self):
        self.assertEqual(
            get_hash(Product(id=1), VarietyAssignment(id=1)),
            get_hash(Product(id=1), VarietyAssignment(id=1))
        )


    def test_should_return_unique_hash_for_variety(self):
        self.assertNotEqual(
            get_hash(Product(id=1), [VarietyAssignment(id=1)]),
            get_hash(Product(id=1), [VarietyAssignment(id=2)])
        )


    def test_should_return_same_hash_for_variety(self):
        self.assertEqual(
            get_hash(Product(id=1), [VarietyAssignment(id=1)]),
            get_hash(Product(id=1), [VarietyAssignment(id=1)])
        )


    def test_should_return_unique_hash_for_varieties(self):
        self.assertNotEqual(
            get_hash(Product(id=1), [VarietyAssignment(id=1), VarietyAssignment(id=2)]),
            get_hash(Product(id=1), [VarietyAssignment(id=1), VarietyAssignment(id=3)])
        )


    def test_should_return_same_hash_for_varieties(self):
        self.assertEqual(
            get_hash(Product(id=1), [VarietyAssignment(id=1), VarietyAssignment(id=2)]),
            get_hash(Product(id=1), [VarietyAssignment(id=1), VarietyAssignment(id=2)])
        )


    def test_should_return_same_hash_for_varieties_independent_of_order_given(self):
        self.assertEqual(
            get_hash(Product(id=1), [VarietyAssignment(id=1), VarietyAssignment(id=2)]),
            get_hash(Product(id=1), [VarietyAssignment(id=2), VarietyAssignment(id=1)])
        )


    def test_should_return_unique_hash_for_custom_properties(self):
        self.assertNotEqual(
            get_hash(Product(id=1), [VarietyAssignment(id=1)], {'foo': 'bar'}),
            get_hash(Product(id=1), [VarietyAssignment(id=1)], {'foo': 'alice'})
        )


    def test_should_return_same_hash_for_custom_properties(self):
        self.assertEqual(
            get_hash(Product(id=1), [VarietyAssignment(id=1)], {'foo': 'bar'}),
            get_hash(Product(id=1), [VarietyAssignment(id=1)], {'foo': 'bar'})
        )


    def test_should_return_same_hash_for_custom_properties_independent_of_order_given(self):
        self.assertEqual(
            get_hash(Product(id=1), [VarietyAssignment(id=1)], {'A': 'a', 'B': 'b'}),
            get_hash(Product(id=1), [VarietyAssignment(id=1)], {'B': 'b', 'A': 'a'})
        )


class IShopBasketGetAddToBasketPriceHtmlTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopBasketGetAddToBasketPriceHtmlTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')


    def test_should_return_product_price_html(self):
        self.assertIn(
            '<span class="price">\xa314.99</span>',
            get_add_to_basket_price_html(self.request, Product(id=1, price=Decimal('14.99')))
        )


class IShopBasketGetBasketVarietyUpdateTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopBasketGetBasketVarietyUpdateTestCase, cls).setUpClass()
        cls.factory = RequestFactory()


    def test_should_return_html_on_success(self):
        json = self._get_json({'product_id': 1, 'quantity': 1})
        self.assertTrue(json.get('success'))
        self.assertFalse(json.get('errors'))
        self.assertIn('<span class="price">\xa314.99</span>', json.get('html'))


    def test_should_return_error_message_on_failure(self):
        json = self._get_json({'product_id': 1, 'quantity': 4})
        self.assertFalse(json.get('success'))
        self.assertEqual({'quantity': ['Select a valid choice. 4 is not one of the available choices.']}, json.get('errors'))
        self.assertEqual('', json.get('html'))


    def _get_json(self, request_data):
        request = self.factory.post('/', request_data)
        request.settings = Settings(max_quantity=3)
        return decode_json(
            get_basket_variety_update(request, Product(id=1, price=Decimal('14.99'))).content
        )


class IShopCreateBasketItemTestCase(CubaneTestCase):
    def test_should_store_product_details(self):
        product = Product(id=1, collection_only=True)
        variety = Variety(id=1)
        variety_options = [
            VarietyOption(id=1, variety=variety),
            VarietyOption(id=2, variety=variety)
        ]
        deposit_only = False
        custom = {'foo': 'bar'}
        quantity = 1

        item = BasketItem(product, variety_options, quantity, custom)

        self.assertEqual(product, item.product)
        self.assertEqual(variety_options, item.variety_options)
        self.assertEqual(custom, item.custom)
        self.assertEqual(quantity, item.quantity)
        self.assertEqual(deposit_only, item.deposit_only)
        self.assertEqual(get_hash(product, variety_options, custom), item.hash)
        self.assertEqual(product.id, item.product_id)
        self.assertEqual([option.id for option in variety_options], item.variety_option_ids)
        self.assertEqual(product.collection_only, item.is_collection_only)


    def test_should_accept_default_values(self):
        product = Product(id=1, collection_only=False)
        item = BasketItem(product)

        self.assertEqual(product, item.product)
        self.assertEqual([], item.variety_options)
        self.assertEqual(None, item.custom)
        self.assertEqual(1, item.quantity)
        self.assertEqual(get_hash(product), item.hash)
        self.assertEqual(product.id, item.product_id)
        self.assertEqual([], item.variety_option_ids)
        self.assertEqual(product.collection_only, item.is_collection_only)


    def test_should_accept_single_variety_assignment(self):
        variety = Variety(id=1)
        variety_option = VarietyOption(id=1, variety=variety)
        item = BasketItem(Product(id=1), variety_option)
        self.assertEqual([variety_option], item.variety_options)


class IShopCreateBasketItemSKUTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopCreateBasketItemSKUTestCase, cls).setUpClass()
        cls.colour = Variety.objects.create(title='Colour', sku=True)
        cls.option_red = VarietyOption.objects.create(title='Red', variety=cls.colour)
        cls.option_blue = VarietyOption.objects.create(title='Blue', variety=cls.colour)

        cls.size = Variety.objects.create(title='Size', sku=True)
        cls.option_12 = VarietyOption.objects.create(title='12', variety=cls.size)
        cls.option_14 = VarietyOption.objects.create(title='14', variety=cls.size)

        # label DOES NOT take part in SKU
        cls.label = Variety.objects.create(title='Label', sku=False)
        cls.option_no_label = VarietyOption.objects.create(title='No Label', variety=cls.label)
        cls.option_with_label = VarietyOption.objects.create(title='With Label', variety=cls.label)

        cls.category = Category.objects.create(title='Category', slug='category')
        cls.product = Product.objects.create(title='Foo', slug='foo', description='Bar', price=Decimal('50.00'), category=cls.category)
        cls.variety_assignments = [
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.option_red),
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.option_blue),
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.option_12),
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.option_14),
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.option_no_label),
            VarietyAssignment.objects.create(
                product=cls.product,
                variety_option=cls.option_with_label,
                offset_type=VarietyOption.OFFSET_VALUE,
                offset_value=decimal.Decimal('1.50')
            )
        ]
        cls.sku_red_12 = ProductSKU.objects.create(product=cls.product, sku='RED12', price=Decimal('1.00'))
        cls.sku_red_12.variety_options.add(cls.option_red, cls.option_12)

        cls.sku_red_14 = ProductSKU.objects.create(product=cls.product, sku='RED14', price=Decimal('2.00'))
        cls.sku_red_14.variety_options.add(cls.option_red, cls.option_14)

        cls.sku_blue_12 = ProductSKU.objects.create(product=cls.product, sku='BLUE12', price=Decimal('3.00'))
        cls.sku_blue_12.variety_options.add(cls.option_blue, cls.option_12)

        cls.sku_blue_14 = ProductSKU.objects.create(product=cls.product, sku='BLUE14', price=Decimal('4.00'))
        cls.sku_blue_14.variety_options.add(cls.option_blue, cls.option_14)


    @classmethod
    def tearDownClass(cls):
        cls.option_red.delete()
        cls.option_blue.delete()
        cls.colour.delete()

        cls.size.delete()
        cls.option_12.delete()
        cls.option_14.delete()

        cls.label.delete()
        cls.option_no_label.delete()
        cls.option_with_label.delete()

        [a.delete() for a in cls.variety_assignments]
        cls.sku_red_12.delete()
        cls.sku_red_14.delete()
        cls.sku_blue_12.delete()
        cls.sku_blue_14.delete()
        cls.product.delete()
        cls.category.delete()
        super(IShopCreateBasketItemSKUTestCase, cls).tearDownClass()


    def test_should_identify_sku(self):
        item = BasketItem(self.product, [
            self.option_red,
            self.option_12,
            self.option_with_label
        ], quantity=3)
        self.assertEqual(Decimal('50.00'), item.product_price)
        self.assertEqual(Decimal('1.50'), item.total_varieties)
        self.assertEqual(Decimal('2.50'), item.total_product)
        self.assertEqual(Decimal('7.50'), item.total)
        self.assertIsNotNone(item.sku)
        self.assertEqual('RED12', item.sku.sku)


class IShopBasketItemRestoreTestCase(CubaneTestCase):
    def setUp(self):
        self.product = Product(id=1, collection_only=True)
        self.variety = Variety(id=1)
        self.variety_options = [
            VarietyOption(id=1, variety=self.variety),
            VarietyOption(id=2, variety=self.variety)
        ]
        self.item = BasketItem(self.product, self.variety_options)
        self.item.product = None
        self.item.variety_options = None
        self.item.sku_price = None


    def test_should_return_true_when_restoring_product_and_varieties_successfully(self):
        self.assertTrue(self.item.restore([self.product], self.variety_options))
        self.assertEqual(self.product, self.item.product)
        self.assertEqual(self.variety_options, self.item.variety_options)
        self.assertEqual(get_hash(self.product, self.variety_options), self.item.hash)
        self.assertEqual(self.product.id, self.item.product_id)
        self.assertEqual([a.id for a in self.variety_options], self.item.variety_option_ids)
        self.assertEqual(self.product.collection_only, self.item.is_collection_only)


    def test_should_return_false_if_product_cannot_be_restored(self):
        self.assertFalse(self.item.restore([], self.variety_options))
        self.assertIsNone(self.item.product)


    def test_should_update_collection_only_property(self):
        self.product.collection_only = False
        self.assertTrue(self.item.restore([self.product], self.variety_options))
        self.assertFalse(self.item.is_collection_only)


    def test_should_remove_varieties_that_could_not_be_restored(self):
        self.assertFalse(self.item.restore([self.product], self.variety_options[:1]))
        self.assertEqual(self.variety_options[:1], self.item.variety_options)
        self.assertEqual([self.variety_options[0].id], self.item.variety_option_ids)


class IShopBasketItemProductPropertyTestCase(CubaneTestCase):
    def setUp(self):
        self.product = Product(id=1, collection_only=True)
        self.item = BasketItem(self.product)


    def test_getter_should_return_product(self):
        self.assertEqual(self.product, self.item.product)


    def test_setter_should_update_product_and_associated_data(self):
        new_product = Product(id=2, collection_only=False)
        self.item.product = new_product
        self.assertEqual(new_product, self.item.product)
        self.assertEqual(new_product.id, self.item.product_id)
        self.assertEqual(new_product.collection_only, self.item.is_collection_only)


    def test_setter_should_ignore_associated_data_if_product_is_none(self):
        self.item.product = None
        self.assertIsNone(self.item.product)
        self.assertEqual(self.product.id, self.item.product_id)


class IShopBasketItemPropertiesTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopBasketItemPropertiesTestCase, cls).setUpClass()
        cls.product = Product(id=1, title='Foo', description='Bar')
        cls.product.image = Media(id=1)
        cls.item = BasketItem(cls.product)


    def test_image_property_should_return_product_image(self):
        self.assertEqual(self.product.image, self.item.image)


    def test_title_property_should_return_product_title(self):
        self.assertEqual(self.product.title, self.item.title)


    def test_description_property_should_return_product_description(self):
        self.assertEqual(self.product.description, self.item.description)


    def test_excerpt_property_should_return_product_excerpt(self):
        self.assertEqual('Bar', self.item.excerpt)


class IShopBasketItemCustomPropertiesTestCase(CubaneTestCase):
    def test_should_return_empty_list_if_cutsom_properties_are_not_defined(self):
        item = BasketItem(Product(id=1))
        self.assertEqual([], item.custom_properties)


    def test_should_return_list_of_custom_properties(self):
        item = BasketItem(Product(id=1), custom={'foo': 'bar'})
        self.assertEqual(
            [{
                'label': 'Foo',
                'name': 'foo',
                'unit': '',
                'value': 'bar'
            }],
            item.custom_properties
        )


    def test_should_augment_list_of_custom_properties_with_additional_information_from_settings(self):
        item = BasketItem(Product(id=1), custom={'left-calf': 32.5, 'right-calf': 33})
        self.assertEqual(
            [
                {
                    'label': 'Left Calf',
                    'name': 'left-calf',
                    'unit': 'cm',
                    'value': 32.5
                }, {
                    'label': 'Right Calf',
                    'name': 'right-calf',
                    'unit': 'cm',
                    'value': 33
                }
            ],
            item.custom_properties
        )


class IShopBasketItemProductPriceTestCase(CubaneTestCase):
    def test_should_return_the_price_of_the_product(self):
        price = Decimal('19.99')
        item = BasketItem(Product(id=1, price=price))
        self.assertEqual(price, item.product_price)


class IShopBasketItemTotalProductTestCase(CubaneTestCase):
    def test_should_return_product_price_if_no_sku_is_defined(self):
        product = Product(id=1, price=Decimal('50.0'))
        variety = Variety(id=1)
        variety_options = [
            VarietyOption(id=1, variety=variety),
            VarietyOption(id=2, variety=variety)
        ]
        item = BasketItem(product, variety_options, 3)
        self.assertEqual(Decimal('50.00'), item.total_product)


    def test_should_return_sku_price_if_sku_is_defined(self):
        product = Product(id=1, price=Decimal('50.0'))
        variety = Variety(id=1)
        variety_options = [
            VarietyOption(id=1, variety=variety),
            VarietyOption(id=2, variety=variety)
        ]
        item = BasketItem(product, variety_options, 3)
        item.sku_price = Decimal('55.00')
        self.assertEqual(Decimal('55.00'), item.total_product)


class IShopBasketItemTotalTestCase(CubaneTestCase):
    def test_should_return_product_of_quantity_and_total_product(self):
        product = Product(id=1, price=Decimal('50.0'))
        variety = Variety(id=1)
        variety_options = [
            VarietyOption(id=1, variety=variety),
            VarietyOption(id=2, variety=variety)
        ]
        item = BasketItem(product, variety_options, 3)
        self.assertEqual(Decimal('150.00'), item.total)


class IShopBasketItemMatchesHashTestCase(CubaneTestCase):
    def test_should_return_false_if_hash_does_not_match(self):
        item = BasketItem(Product(id=1))
        self.assertFalse(item.matches_hash('does-not-match'))


    def test_should_return_true_if_hash_matches(self):
        product = Product(id=1)
        item = BasketItem(product)
        self.assertTrue(item.matches_hash(get_hash(product)))


class IShopBasketItemIncreaseQuantityByTestCase(CubaneTestCase):
    def test_should_increase_quantity_by_given_amount(self):
        item = BasketItem(Product(id=1))
        item.increase_quantity_by(2)
        self.assertEqual(3, item.quantity)


    def test_should_not_increase_quantity_if_amount_is_zero(self):
        item = BasketItem(Product(id=1))
        item.increase_quantity_by(0)
        self.assertEqual(1, item.quantity)


    def test_should_not_change_quantity_if_amount_is_negative(self):
        item = BasketItem(Product(id=1))
        item.increase_quantity_by(-3)
        self.assertEqual(1, item.quantity)


class IShopBasketItemGetAbsoluteUrlTestCase(CubaneTestCase):
    def test_should_return_absolute_url_for_corresponding_product(self):
        item = BasketItem(Product(id=1, slug='foo'))
        self.assertEqual('http://www.testapp.cubane.innershed.com/shop/product/foo-1/', item.get_absolute_url())


class IShopBasketItemGetTotalDiscountableTestCase(CubaneTestCase):
    def test_should_return_zero_if_product_is_excluded_from_discount(self):
        item = BasketItem(Product(id=1, price=Decimal('50.0'), exempt_from_discount=True))
        self.assertEqual(Decimal('0.00'), item.get_total_discountable())


    def test_should_return_product_total_if_no_discountable_catogories_are_given(self):
        item = BasketItem(Product(id=1, price=Decimal('50.0')), quantity=3)
        self.assertEqual(Decimal('150.00'), item.get_total_discountable(None))
        self.assertEqual(Decimal('150.00'), item.get_total_discountable([]))


    def test_should_return_product_total_if_product_matches_given_category_ids(self):
        item = BasketItem(Product(id=1, category_id=2, price=Decimal('50.0')), quantity=3)
        self.assertEqual(Decimal('150.00'), item.get_total_discountable([1, 2]))


    def test_should_return_zero_if_product_does_not_match_given_category_ids(self):
        item = BasketItem(Product(id=1, category_id=2, price=Decimal('50.0')), quantity=3)
        self.assertEqual(Decimal('0.00'), item.get_total_discountable([1, 3]))


class IShopBasketItemAsDictTestCase(CubaneTestCase):
    def setUp(self):
        self.variety = Variety.objects.create(id=1, title='Colour', slug='colour', display_title='COLOUR')
        self.option_red = VarietyOption.objects.create(id=1, title='Red', variety=self.variety)
        self.option_blue = VarietyOption.objects.create(id=2, title='Blue', variety=self.variety)
        self.category = Category.objects.create(id=1, title='Category')
        self.product = Product.objects.create(id=1, price=Decimal('50.0'), slug='foo', title='Foo', description='Bar', category=self.category)
        self.assignment_red = VarietyAssignment.objects.create(product=self.product, variety_option=self.option_red),
        self.assignment_blue = VarietyAssignment.objects.create(product=self.product, variety_option=self.option_blue)
        variety_options = [self.option_red, self.option_blue]
        self.item = BasketItem(self.product, variety_options, 3, {'foo': 'bar'})


    def teasrDown(self):
        for obj in [self.assignment_blue, self.assignment_red, self.product, self.category, self.option_blue, self.option_red, self.variety]:
            obj.delete()


    def test_as_dict_should_return_dict_respresentation(self):
        self.assertEqual(
            {
                'custom_properties': [{
                    'label': 'Foo',
                    'name': 'foo',
                    'unit': '',
                    'value': 'bar'
                }],
                'deposit_only': False,
                'excerpt': 'Bar',
                'icon_url': None,
                'image_attribute_url': None,
                'product_id': 1,
                'product_price': Decimal('50.00'),
                'quantity': 3,
                'sku': {
                    'id': None,
                    'code': None,
                    'barcode': None,
                    'price': None
                },
                'title': 'Foo',
                'total': Decimal('150.00'),
                'total_product': Decimal('50.00'),
                'total_product_without_deposit': Decimal('50.00'),
                'total_without_deposit': Decimal('150.00'),
                'url': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/' % self.item.product.pk,
                'get_absolute_url': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/' % self.item.product.pk,
                'get_absolute_url_with_varieties': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/?colour=%d' % (self.item.product.pk, self.option_blue.pk),
                'labels': None,
                'varieties': [{
                    'variety_option': {
                        'title': 'Red',
                        'text_label': False,
                        'text_label_value': None,
                        'price': Decimal('0.00'),
                        'variety': {
                            'title': 'Colour',
                            'display_title': 'COLOUR'
                        }
                    }
                }, {
                    'variety_option': {
                        'title': 'Blue',
                        'text_label': False,
                        'text_label_value': None,
                        'price': Decimal('0.00'),
                        'variety': {
                            'title': 'Colour',
                            'display_title': 'COLOUR'
                        }
                    }
                }],
                'variety_option_ids': [1, 2]
            },
            self.item.as_legacy_dict()
        )


    def test_to_ga_dict_should_return_dict_respresentation(self):
        self.assertEqual(
            {
                'category': 'Category',
                'foo': 'bar',
                'id': 1,
                'name': 'Foo',
                'price': Decimal('50.00'),
                'quantity': 3,
                'variant': 'Red, Blue'
            },
            self.item.to_ga_dict({'foo': 'bar'})
        )


class TestBasketMixin(object):
    def _set_billing_address(self, basket):
        basket.set_billing_address(
            title=Customer.TITLE_MR,
            first_name='Foo',
            last_name='Bar',
            email='foo@bar.com',
            telephone='12345678',
            company='Foo Ltd.',
            address1='Address1',
            address2='Address2',
            address3='Address3',
            city='City',
            country=self.GB,
            county='County',
            postcode='NR13 6PZ'
        )


    def _set_delivery_address(self, basket):
        basket.set_delivery_address(
            name='Delivery Name',
            company='Delivery Ltd.',
            address1='Delivery Address1',
            address2='Delivery Address2',
            address3='Delivery Address3',
            city='Delivery City',
            country=self.DE,
            county='Delivery County',
            postcode='28274'
        )


    def _set_signup(self, basket):
        basket.set_signup(
            email='foo@bar.innershed.com',
            first_name='FirstName',
            last_name='LastName',
            password='password'
        )


class IShopBasketTestCase(CubaneTestCase, TestBasketMixin):
    @classmethod
    def setUpClass(cls):
        super(IShopBasketTestCase, cls).setUpClass()

        # page
        cls.page = Page()
        cls.page.title = 'Test Page'
        cls.page.slug = 'test'
        cls.page.template = 'testapp/mail/enquiry_visitor.html'
        cls.page.set_slot_content('content', '<h1>Test</h1>')
        cls.page.save()

        # settings
        cls.settings = Settings()
        cls.settings.shop_email_template = cls.page
        cls.settings.save()

        # countries
        cls.US = Country.objects.get(iso='US')
        cls.GB = Country.objects.get(iso='GB')
        cls.DE = Country.objects.get(iso='DE')

        # variety: colour
        cls.variety = Variety.objects.create(title='Colour', slug='colour')
        cls.option_red = VarietyOption.objects.create(title='Red', variety=cls.variety)
        cls.option_blue = VarietyOption.objects.create(title='Blue', variety=cls.variety)

        # variety: size (+ additional price)
        cls.size_variety = Variety.objects.create(title='Size', slug='size')
        cls.size_small = VarietyOption.objects.create(title='Small', variety=cls.size_variety)
        cls.size_large = VarietyOption.objects.create(title='Large', variety=cls.size_variety)

        # categories and products
        cls.category = Category.objects.create(title='Category', slug='category')
        cls.second_category = Category.objects.create(title='Second Category', slug='second-category')
        cls.product = Product.objects.create(title='Foo', slug='foo', description='Bar', _excerpt='Foo Bar', price=Decimal('50.00'), category=cls.category)
        cls.second_product = Product.objects.create(title='Bar', slug='bar', description='Foo', price=Decimal('35.00'), category=cls.category)
        cls.third_product = Product.objects.create(title='Alice', slug='alice', description='Alice', price=Decimal('5.00'), exempt_from_discount=True, category=cls.second_category)
        cls.fourth_product = Product.objects.create(title='Bob', slug='bob', description='Bob', price=Decimal('3.00'), exempt_from_free_delivery=True, category=cls.second_category)
        cls.click_and_collect_product = Product.objects.create(title='Click and Collect', slug='click-and-collect', description='Click and Collect', price=Decimal('11.00'), collection_only=True, category=cls.category)
        cls.pre_order_product = Product.objects.create(title='Pre Order Product', slug='pre-order-product', description='Pre Order Product', price=Decimal('13.00'), pre_order=True, category=cls.category)

        # assign: colour
        cls.variety_assignments = [
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.option_red),
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.option_blue)
        ]
        cls.variety_options = [cls.option_red, cls.option_blue]

        # assign size
        cls.variety_assignments_size = [
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.size_small),
            VarietyAssignment.objects.create(product=cls.product, variety_option=cls.size_large, offset_type=VarietyOption.OFFSET_VALUE, offset_value=Decimal('10.00'))
        ]

        # vouchers
        cls.voucher = Voucher.objects.create(title='Test', code='TEST', enabled=True, discount_type=Voucher.DISCOUNT_PRICE, discount_value=Decimal('15.00'))
        cls.max_usage_voucher = Voucher.objects.create(title='Max Usage', code='MAX', enabled=True, discount_type=Voucher.DISCOUNT_PRICE, discount_value=Decimal('10.00'), max_usage=1)
        cls.date_voucher = Voucher.objects.create(title='Date', code='DATE', enabled=True, discount_type=Voucher.DISCOUNT_PRICE, discount_value=Decimal('5.00'), valid_from=datetime.date(2016, 12, 1), valid_until=datetime.date(2016, 12, 31))
        cls.percentage_voucher = Voucher.objects.create(title='Percentage', code='PERCENTAGE', enabled=True, discount_type=Voucher.DISCOUNT_PERCENTAGE, discount_value=Decimal('40.00'))
        cls.free_delivery_voucher = Voucher.objects.create(title='Free Delivery', code='FREE_DELIVERY', enabled=True, discount_type=Voucher.DISCOUNT_FREE_DELIVERY, discount_value=Decimal('0.00'))
        cls.free_delivery_de_only_voucher = Voucher.objects.create(title='Free Delivery Germany Only', code='FREE_DELIVERY_DE', enabled=True, discount_type=Voucher.DISCOUNT_FREE_DELIVERY, discount_value=Decimal('0.00'))
        cls.free_delivery_de_only_voucher.delivery_countries = [cls.DE]
        cls.category_voucher = Voucher.objects.create(title='Category', code='CATEGORY', enabled=True, discount_type=Voucher.DISCOUNT_PERCENTAGE, discount_value=Decimal('10.00'))
        cls.category_voucher.categories=[cls.second_category]
        cls.vouchers = [
            cls.voucher,
            cls.max_usage_voucher,
            cls.date_voucher,
            cls.percentage_voucher,
            cls.free_delivery_voucher,
            cls.free_delivery_de_only_voucher,
            cls.category_voucher
        ]
        cls.enabled_vouchers = filter(lambda v: v.enabled, cls.vouchers)

        # delivery options
        cls.delivery_uk = DeliveryOption.objects.create(title='Delivery Option UK', enabled=True, deliver_uk=True, uk_def=Decimal('7.00'), free_delivery=True, free_delivery_threshold=Decimal('100.00'))
        cls.delivery_eu = DeliveryOption.objects.create(title='Delivery Option EU', enabled=True, deliver_eu=True, eu_def=Decimal('9.00'))
        cls.delivery_world = DeliveryOption.objects.create(title='Delivery Option World', enabled=True, deliver_world=True, world_def=Decimal('14.00'))
        cls.delivery_uk_eu = DeliveryOption.objects.create(title='Delivery Option UK/EU', enabled=True, deliver_uk=True, uk_def=Decimal('10.00'), deliver_eu=True, eu_def=Decimal('20.00'))
        cls.delivery_disabled = DeliveryOption.objects.create(title='Delivery Option UK Disabled', enabled=False, deliver_uk=True, uk_def=Decimal('3.00'))
        cls.delivery_world_quote = DeliveryOption.objects.create(title='Delivery Option World Quote', enabled=True, quote_world=True)
        cls.second_product_uk_delivery = ProductDeliveryOption.objects.create(product=cls.second_product, delivery_option=cls.delivery_uk, uk=Decimal('15.00'))
        cls.second_product_eu_delivery = ProductDeliveryOption.objects.create(product=cls.second_product, delivery_option=cls.delivery_eu, eu=Decimal('16.00'))
        cls.second_product_world_delivery = ProductDeliveryOption.objects.create(product=cls.second_product, delivery_option=cls.delivery_world, world=Decimal('17.00'))
        cls.third_product_uk_delivery = ProductDeliveryOption.objects.create(product=cls.third_product, delivery_option=cls.delivery_uk, uk=Decimal('18.00'))
        cls.third_product_eu_delivery = ProductDeliveryOption.objects.create(product=cls.third_product, delivery_option=cls.delivery_eu, eu=Decimal('19.00'))
        cls.third_product_world_delivery = ProductDeliveryOption.objects.create(product=cls.third_product, delivery_option=cls.delivery_world, world=Decimal('20.00'))
        cls.fourth_product_uk_delivery = ProductDeliveryOption.objects.create(product=cls.fourth_product, delivery_option=cls.delivery_uk, uk=Decimal('21.00'))
        cls.fourth_product_eu_delivery = ProductDeliveryOption.objects.create(product=cls.fourth_product, delivery_option=cls.delivery_eu, eu=Decimal('22.00'))
        cls.fourth_product_world_delivery = ProductDeliveryOption.objects.create(product=cls.fourth_product, delivery_option=cls.delivery_world, world=Decimal('23.00'))


    @classmethod
    def tearDownClass(cls):
        cls.fourth_product_world_delivery.delete()
        cls.fourth_product_eu_delivery.delete()
        cls.fourth_product_uk_delivery.delete()
        cls.third_product_world_delivery.delete()
        cls.third_product_eu_delivery.delete()
        cls.third_product_uk_delivery.delete()
        cls.second_product_world_delivery.delete()
        cls.second_product_eu_delivery.delete()
        cls.second_product_uk_delivery.delete()
        cls.delivery_world_quote.delete()
        cls.delivery_disabled.delete()
        cls.delivery_uk_eu.delete()
        cls.delivery_world.delete()
        cls.delivery_eu.delete()
        cls.delivery_uk.delete()
        cls.voucher.delete()
        cls.percentage_voucher.delete()
        cls.category_voucher.delete()
        [a.delete() for a in cls.variety_assignments]
        [a.delete() for a in cls.variety_assignments_size]
        cls.product.delete()
        cls.second_product.delete()
        cls.third_product.delete()
        cls.fourth_product.delete()
        cls.click_and_collect_product.delete()
        cls.pre_order_product.delete()
        cls.category.delete()
        cls.second_category.delete()
        cls.option_blue.delete()
        cls.option_red.delete()
        cls.variety.delete()
        cls.size_small.delete()
        cls.size_large.delete()
        cls.size_variety.delete()
        cls.settings.delete()
        cls.page.delete()
        super(IShopBasketTestCase, cls).tearDownClass()


    def setUp(self):
        self.request = self.make_request('get', '/')
        self.request.context = IShopClientContext(self.request)
        self.request.settings = self.settings


    #
    # __init__()
    #
    def test_ctor_should_create_empty_basket_if_no_session(self):
        basket = Basket(self.request)
        self.assertEqual([], basket.items)


    def test_ctor_should_load_basket_from_session(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.save()

        new_basket = Basket(self.request)
        self.assertEqual(1, len(new_basket.items))


    def test_ctor_should_not_load_from_session_if_no_request_is_given(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.save()

        new_basket = Basket()
        self.assertEqual([], new_basket.items)


    #
    # restore_from_legacy_dict()
    #
    def test_restore_from_legacy_dict_should_restore_empty_data(self):
        restored = Basket.restore_from_legacy_dict({})
        self.assertEqual({
            'items': [],
            'can_deliver': True,
            'has_pre_order_item': False,
            'finance_option': None,
            'finance_option_id': None
        }, restored)


    def test_restore_from_legacy_dict_should_restore_empty_basket(self):
        basket = Basket(self.request)
        restored = Basket.restore_from_legacy_dict(basket.as_legacy_dict())
        self.assertEqual({
            'is_quote_only': False,
            'has_pre_order_item': False,
            'items': [],
            'sub_total': Decimal('0.00'),
            'totals': {
                'delivery': Decimal('0.00'),
                'difference_between_deposit_and_full_amount': Decimal('0.00'),
                'total': Decimal('0.00'),
                'sub_total': Decimal('0.00'),
                'quantity': 0
            },
            'delivery': Decimal('0.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00'),
            'voucher': None,
            'can_deliver': True,
            'discount_value': Decimal('0.00'),
            'finance_option': None,
            'finance_option_id': None,
            'is_available_for_loan': False,
            'is_invoice': False,
            'invoice_number': None,
            'total': Decimal('0.00'),
            'loan_deposit': None,
            'quantity': 0
        }, restored)


    def test_restore_from_legacy_dict_should_restore_products_and_varieties(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options, quantity=2)
        basket.add_item(self.click_and_collect_product)
        basket.add_item(self.pre_order_product)
        restored = Basket.restore_from_legacy_dict(basket.as_legacy_dict())
        self.assertEqual({
            'can_deliver': True,
            'delivery': Decimal('0.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00'),
            'discount_value': Decimal('0.00'),
            'finance_option': None,
            'finance_option_id': None,
            'has_pre_order_item': True,
            'is_available_for_loan': False,
            'is_click_and_collect': True,
            'is_quote_only': False,
            'is_invoice': False,
            'invoice_number': None,
            'items': [
                {
                    'custom_properties': [],
                    'deposit_only': False,
                    'excerpt': 'Foo Bar',
                    'icon_url': None,
                    'image_attribute_url': None,
                    'image': None,
                    'product': self.product,
                    'product_id': 1,
                    'product_price': Decimal('50.00'),
                    'quantity': 2,
                    'sku': {
                        'id': None,
                        'code': None,
                        'barcode': None,
                        'price': None
                    },
                    'title': 'Foo',
                    'total': Decimal('100.00'),
                    'total_product': Decimal('50.00'),
                    'total_product_without_deposit': Decimal('50.00'),
                    'total_without_deposit': Decimal('100.00'),
                    'url': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/' % self.product.pk,
                    'get_absolute_url': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/' % self.product.pk,
                    'get_absolute_url_with_varieties': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%d/?colour=%d' % (self.product.pk, self.option_blue.pk),
                    'labels': None,
                    'varieties': [
                        {
                            'variety_option': {
                                'title': 'Red',
                                'text_label': False,
                                'text_label_value': None,
                                'price': Decimal('0.00'),
                                'variety': {'title': 'Colour', 'display_title': 'Colour'}
                            }
                        }, {
                            'variety_option': {
                                'title': 'Blue',
                                'text_label': False,
                                'text_label_value': None,
                                'price': Decimal('0.00'),
                                'variety': {'title': 'Colour', 'display_title': 'Colour'}
                            }
                        }
                    ],
                    'variety_option_ids': [a.pk for a in self.variety_options],
                    'variety_options': [
                        {
                            'title': 'Red',
                            'text_label': False,
                            'text_label_value': None,
                            'price': Decimal('0.00'),
                            'variety': {'title': 'Colour', 'display_title': 'Colour'}
                        }, {
                            'title': 'Blue',
                            'text_label': False,
                            'text_label_value': None,
                            'price': Decimal('0.00'),
                            'variety': {'title': 'Colour', 'display_title': 'Colour'}
                        }
                    ],
                    'variety_assignments': [
                        {
                            'price': Decimal('0.00'),
                            'variety_option': {
                                'price': Decimal('0.00'),
                                'text_label': False,
                                'text_label_value': None,
                                'title': 'Red',
                                'variety': {'title': 'Colour', 'display_title': 'Colour'}
                            }
                        }, {
                            'price': Decimal('0.00'),
                            'variety_option': {
                                'price': Decimal('0.00'),
                                'text_label': False,
                                'text_label_value': None,
                                'title': 'Blue',
                                'variety': {'title': 'Colour', 'display_title': 'Colour'}
                            }
                        }
                    ]
                }, {
                    'custom_properties': [],
                    'deposit_only': False,
                    'excerpt': 'Click and Collect',
                    'icon_url': None,
                    'image_attribute_url': None,
                    'image': None,
                    'product': self.click_and_collect_product,
                    'product_id': 5,
                    'product_price': Decimal('11.00'),
                    'quantity': 1,
                    'sku': {
                        'id': None,
                        'code': None,
                        'barcode': None,
                        'price': None
                    },
                    'title': 'Click and Collect',
                    'total': Decimal('11.00'),
                    'total_product': Decimal('11.00'),
                    'total_product_without_deposit': Decimal('11.00'),
                    'total_without_deposit': Decimal('11.00'),
                    'url': 'http://www.testapp.cubane.innershed.com/shop/product/click-and-collect-%s/' % self.click_and_collect_product.pk,
                    'get_absolute_url': 'http://www.testapp.cubane.innershed.com/shop/product/click-and-collect-%s/' % self.click_and_collect_product.pk,
                    'get_absolute_url_with_varieties': 'http://www.testapp.cubane.innershed.com/shop/product/click-and-collect-%s/' % self.click_and_collect_product.pk,
                    'labels': None,
                    'varieties': [],
                    'variety_assignments': [],
                    'variety_option_ids': [],
                    'variety_options': []
                }, {
                    'custom_properties': [],
                    'deposit_only': False,
                    'excerpt': 'Pre Order Product',
                    'icon_url': None,
                    'image_attribute_url': None,
                    'image': None,
                    'product': self.pre_order_product,
                    'product_id': 6,
                    'product_price': Decimal('13.00'),
                    'quantity': 1,
                    'sku': {
                        'id': None,
                        'code': None,
                        'barcode': None,
                        'price': None
                    },
                    'title': 'Pre Order Product',
                    'total': Decimal('13.00'),
                    'total_product': Decimal('13.00'),
                    'total_product_without_deposit': Decimal('13.00'),
                    'total_without_deposit': Decimal('13.00'),
                    'url': 'http://www.testapp.cubane.innershed.com/shop/product/pre-order-product-%d/' % self.pre_order_product.pk,
                    'get_absolute_url': 'http://www.testapp.cubane.innershed.com/shop/product/pre-order-product-%d/' % self.pre_order_product.pk,
                    'get_absolute_url_with_varieties': 'http://www.testapp.cubane.innershed.com/shop/product/pre-order-product-%d/' % self.pre_order_product.pk,
                    'labels': None,
                    'varieties': [],
                    'variety_assignments': [],
                    'variety_option_ids': [],
                    'variety_options': []
                }
            ],
            'loan_deposit': None,
            'quantity': 4,
            'sub_total': Decimal('124.00'),
            'total': Decimal('124.00'),
            'totals': {
                'delivery': Decimal('0.00'),
                'difference_between_deposit_and_full_amount': Decimal('0.00'),
                'quantity': 4,
                'sub_total': Decimal('124.00'),
                'total': Decimal('124.00')
            },
            'voucher': None
        }, restored)


    #
    # has_voucher()
    #
    def test_has_voucher_should_return_false_if_no_voucher_is_applied(self):
        basket = Basket(self.request)
        self.assertFalse(basket.has_voucher)


    def test_has_voucher_should_return_true_if_a_voucher_is_applied(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        self.assertTrue(basket.has_voucher)


    #
    # can_deliver()
    #
    def test_can_deliver_should_return_true_if_there_is_a_valid_delivery_option(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        basket.set_delivery_country(self.GB)
        basket.set_delivery_option(self.delivery_uk)
        self.assertTrue(basket.can_deliver)


    def test_can_deliver_should_return_false_if_there_is_no_valid_delivery_option(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        basket.set_delivery_country(self.US)
        basket.set_delivery_option(self.delivery_uk)
        self.assertFalse(basket.can_deliver)


    def test_can_deliver_should_fall_back_to_default_delivery_option_if_no_delivery_option_is_set(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        self.assertTrue(basket.can_deliver)


    def test_can_deliver_should_return_false_if_no_delivery_option_is_available(self):
        self.delivery_world.enabled=False
        self.delivery_world.save()
        self.delivery_world_quote.enabled=False
        self.delivery_world_quote.save()
        try:
            basket = Basket(self.request)
            basket.add_item(self.second_product)
            basket.set_delivery_country(self.US)
            self.assertFalse(basket.can_deliver)
        finally:
            self.delivery_world.enabled=True
            self.delivery_world.save()
            self.delivery_world_quote.enabled=True
            self.delivery_world_quote.save()


    #
    # is_quote_only()
    #
    def test_is_quote_only_should_return_true_if_the_order_is_quote_only(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        basket.set_delivery_country(self.US)
        basket.set_delivery_option(self.delivery_world_quote)
        self.assertTrue(basket.is_quote_only)


    def test_is_quote_only_should_return_false_if_the_order_is_for_delivery(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        basket.set_delivery_country(self.GB)
        basket.set_delivery_option(self.delivery_uk)
        self.assertFalse(basket.is_quote_only)


    def test_is_quote_only_should_fall_back_to_default_delivery_option_if_no_delivery_option_is_set(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        self.assertFalse(basket.is_quote_only)


    def test_is_quote_only_should_return_false_if_no_delivery_options_are_available(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        state = {}
        try:
            # disable all delivery options
            for option in DeliveryOption.objects.all():
                state[option.pk] = option.enabled
                option.enabled = False
                option.save()

            # no delivery options active in the system, this should return false
            self.assertFalse(basket.is_quote_only)
        finally:
            # re-activate previous state
            for option in DeliveryOption.objects.all():
                state[option.pk] = option.enabled
                option.enabled = state.get(option.pk, True)
                option.save()


    #
    # save()
    #
    def test_save_should_not_save_if_no_request(self):
        basket = Basket()
        basket.add_item(self.product)
        basket.save()

        new_basket = Basket(self.request)
        self.assertEqual(0, len(new_basket.items))


    #
    # load() (from session)
    #
    def test_load_should_not_load_if_basket_has_no_request(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.save()

        new_basket = Basket()
        new_basket.load()
        self.assertEqual([], new_basket.items)


    def test_load_should_not_restore_products_that_no_longer_exist(self):
        basket = Basket(self.request)
        basket.add_item(Product(id=999, slug='product'))
        basket.save()

        new_basket = Basket(self.request)
        self.assertEqual([], new_basket.items)


    def test_load_should_restore_billing_address_removing_none_values(self):
        basket = Basket(self.request)
        basket.billing_address = {'address2': 'bar', 'bar': None}
        basket.save()

        new_basket = Basket(self.request)
        self.assertEqual({'address2': 'bar'}, new_basket.billing_address)


    def test_load_should_restore_delivery_address_removing_none_values(self):
        basket = Basket(self.request)
        basket.delivery_address = {'address2': 'bar', 'bar': None}
        basket.save()

        new_basket = Basket(self.request)
        self.assertEqual({'address2': 'bar'}, new_basket.delivery_address)


    def test_load_should_load_basket_as_unfrozen(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.save()

        new_basket = Basket(self.request)
        new_basket.load()
        self.assertFalse(basket.is_frozen)


    #
    # save() and load()
    #
    def test_save_and_load_should_restore_billing_address(self):
        basket = Basket(self.request)
        self._set_billing_address(basket)
        basket.save()
        b = Basket(self.request)
        self.assertEqual(
            {
                'title': Customer.TITLE_MR,
                'first_name': 'Foo',
                'last_name': 'Bar',
                'email': 'foo@bar.com',
                'telephone': '12345678',
                'company': 'Foo Ltd.',
                'address1': 'Address1',
                'address2': 'Address2',
                'address3': 'Address3',
                'city': 'City',
                'country': self.GB,
                'country-iso': self.GB.iso,
                'county': 'County',
                'postcode': 'NR13 6PZ',
            }, b.billing_address
        )


    def test_save_and_load_should_restore_delivery_address(self):
        basket = Basket(self.request)
        self._set_delivery_address(basket)
        basket.save()
        b = Basket(self.request)
        self.assertEqual(
            {
                'company': 'Delivery Ltd.',
                'address1': 'Delivery Address1',
                'address2': 'Delivery Address2',
                'address3': 'Delivery Address3',
                'city': 'Delivery City',
                'country': self.DE,
                'country-iso': self.DE.iso,
                'county': 'Delivery County',
                'name': 'Delivery Name',
                'postcode': '28274'
            }, b.delivery_address
        )


    def test_save_and_load_should_restore_signup_details(self):
        basket = Basket(self.request)
        self._set_signup(basket)
        basket.save()
        b = Basket(self.request)
        self.assertEqual(
            {
                'email': 'foo@bar.innershed.com',
                'first_name': 'FirstName',
                'last_name': 'LastName',
                'password': 'password'
            }, b.signup
        )


    def test_save_and_load_should_restore_customer_options(self):
        basket = Basket(self.request)
        basket.newsletter = True
        basket.set_special_requirements('Special Requirements')
        basket.survey = 'Survey'
        basket.click_and_collect = True
        basket.terms = True
        basket.update_profile = True
        basket.save()
        b = Basket(self.request)
        self.assertTrue(b.newsletter)
        self.assertEqual('Special Requirements', b.special_req)
        self.assertEqual('Survey', b.survey)
        self.assertTrue(b.click_and_collect)
        self.assertTrue(b.terms)
        self.assertTrue(b.update_profile)


    def test_save_and_load_should_restore_voucher(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.save()
        b = Basket(self.request)
        self.assertEqual('TEST', b.voucher.code)


    def test_save_and_load_should_not_restore_unknown_voucher_code(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.save()

        try:
            self.voucher.code = 'CHANGED'
            self.voucher.save()
            b = Basket(self.request)
            self.assertIsNone(b.voucher)
        finally:
            self.voucher.code = 'TEST'
            self.voucher.save()


    def test_save_and_load_should_not_restore_disabled_voucher_code(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.save()

        try:
            self.voucher.enabled = False
            self.voucher.save()
            b = Basket(self.request)
            self.assertIsNone(b.voucher)
        finally:
            self.voucher.enabled = True
            self.voucher.save()


    def test_save_and_load_should_restore_delivery_option(self):
        basket = Basket(self.request)
        basket.set_delivery_option(self.delivery_uk)
        basket.save()
        b = Basket(self.request)
        self.assertEqual(self.delivery_uk.id, b.delivery_option.id)


    def test_save_and_load_should_not_restore_delivery_option_if_unknown(self):
        basket = Basket(self.request)
        pk = self.delivery_uk.id
        try:
            self.delivery_uk.id = 999
            basket.set_delivery_option(self.delivery_uk)
            basket.save()
            b = Basket(self.request)
            self.assertIsNone(b.delivery_option)
        finally:
            self.delivery_uk.id = pk


    def test_save_and_load_should_not_restore_delivery_option_if_disabled(self):
        basket = Basket(self.request)
        basket.set_delivery_option(self.delivery_uk)
        basket.save()
        try:
            self.delivery_uk.enabled = False
            self.delivery_uk.save()

            b = Basket(self.request)
            self.assertIsNone(b.delivery_option)
        finally:
            self.delivery_uk.enabled = True
            self.delivery_uk.save()


    #
    # restore_from_order
    #
    def _create_test_order(self, variety_options=[], quantity=1, delivery_option=None, voucher_code=None, is_frozen=True):
        basket = Basket(self.request)
        basket.add_item(self.product, variety_options, quantity=quantity)
        if delivery_option:
            basket.set_delivery_option(delivery_option)
        if voucher_code:
            basket.set_voucher(voucher_code)
        basket.save()
        order = OrderBase.create_from_basket(self.request, basket)

        if not is_frozen:
            order.status = OrderBase.STATUS_NEW_ORDER

        return order


    def test_restore_from_order_should_freeze_basket_if_product_cannot_be_restored(self):
        order = self._create_test_order(is_frozen=False)
        try:
            # set product to draft mode
            self.product.draft = True
            self.product.save()

            # restore basket from order should not be able to restore product,
            # because it is in draft mode...
            basket = Basket.restore_from_order(order)
            self.assertTrue(basket.is_frozen)
            self.assertEqual(1, basket.quantity)
            self.assertEqual(Decimal('50'), basket.items[0].product_price)
        finally:
            self.product.draft = False
            self.product.save()


    def test_restore_from_order_should_freeze_basket_if_variety_cannot_be_restored(self):
        order = self._create_test_order([self.size_large], is_frozen=False)
        try:
            # set product to draft mode
            self.size_variety.enabled = False
            self.size_variety.save()

            # restore basket from order should not be able to restore variety,
            # because it is disabled...
            basket = Basket.restore_from_order(order)
            self.assertTrue(basket.is_frozen)
            self.assertEqual(1, basket.quantity)
            self.assertEqual(Decimal('50'), basket.items[0].product_price)

            # variety is still in place even though the variety is disabled
            self.assertEqual(Decimal('10'), basket.items[0].total_varieties)
        finally:
            self.size_variety.enabled = True
            self.size_variety.save()


    def test_restore_from_order_should_freeze_basket_if_delivery_option_cannot_be_restored(self):
        order = self._create_test_order(delivery_option=self.delivery_uk, is_frozen=False)
        try:
            # set product to draft mode
            self.delivery_uk.enabled = False
            self.delivery_uk.save()

            # restore basket from order should not be able to restore
            # delivery option, because it is disabled...
            basket = Basket.restore_from_order(order)
            self.assertTrue(basket.is_frozen)
            self.assertEqual(1, basket.quantity)
            self.assertEqual(Decimal('50'), basket.items[0].product_price)

            # delivery price is still in place even though the delivery option
            # has been disabled...
            self.assertEqual(Decimal('7'), basket.delivery)
        finally:
            self.delivery_uk.enabled = True
            self.delivery_uk.save()


    @freeze_time('2017-12-07')
    def test_restore_from_order_should_freeze_basket_if_voucher_cannot_be_restored(self):
        v = copy.deepcopy(self.voucher)
        try:
            # make voucher work for today's date
            self.voucher.valid_from = datetime.date(2017, 1, 1)
            self.voucher.valid_until = datetime.date(2017, 12, 31)
            self.voucher.save()

            # create basket from order
            order = self._create_test_order(voucher_code=self.voucher.code, is_frozen=False)

            # disable voucher
            self.voucher.enabled = False
            self.voucher.save()

            # restore basket from order should not be able to restore
            # the voucher because it is out of date...
            basket = Basket.restore_from_order(order)
            self.assertTrue(basket.is_frozen)
            self.assertEqual(1, basket.quantity)
            self.assertEqual(Decimal('50'), basket.items[0].product_price)

            # voucher option should still be in place even though the voucher
            # has expired...
            self.assertEqual(Decimal('15'), basket.discount_value)
        finally:
            self.voucher.valid_from = v.valid_from
            self.voucher.valid_until = v.valid_until
            self.voucher.enabled = True
            self.voucher.save()


    #
    # load_from_order / frozen basket
    #
    def test_load_from_order_should_restore_items_from_order(self):
        order = self._create_test_order(is_frozen=True)
        basket = Basket.restore_from_order(order)
        self.assertTrue(basket.is_frozen)
        self.assertEqual(1, len(basket.items))
        self.assertEqual(self.product.pk, basket.items[0].product.pk)


    def test_load_from_order_should_freeze_basket_if_order_is_paid(self):
        order = self._create_test_order(is_frozen=True)
        basket = Basket.restore_from_order(order)
        self.assertTrue(basket.is_frozen)


    def test_load_from_order_should_not_freeze_basket_if_order_is_not_paid(self):
        order = self._create_test_order(is_frozen=False)
        basket = Basket.restore_from_order(order)
        self.assertFalse(basket.is_frozen)


    @freeze_time('2017-12-07')
    def test_frozen_should_maintain_original_product_price(self):
        assignment = self.variety_assignments_size[1]
        p = copy.deepcopy(self.product)
        a = copy.deepcopy(assignment)
        v = copy.deepcopy(self.voucher)
        d = copy.deepcopy(self.delivery_uk)

        try:
            # make voucher work for today's date
            self.voucher.valid_from = datetime.date(2017, 1, 1)
            self.voucher.valid_until = datetime.date(2017, 12, 31)
            self.voucher.save()

            # create a new order from a new basket with given properties
            order = self._create_test_order(
                [self.size_large],
                quantity=2,
                delivery_option=self.delivery_uk,
                voucher_code=self.voucher.code,
                is_frozen=True
            )

            # we are changing a number of connected items that would affect
            # pricing of the basket content including product price,
            # varieties, discount and delivery changes...
            self.product.title = 'Renamed Product'
            self.product.slug = 'renamed-product'
            self.product.price = Decimal('100.00')
            self.product._excerpt = 'Changed excerpt'
            self.product.save()

            assignment.offset_value = Decimal('20.00')
            assignment.save()

            self.voucher.discount_value = Decimal('30.00')
            self.voucher.save()

            self.delivery_uk.free_delivery_threshold = Decimal('1000.00')
            self.delivery_uk.uk_def = Decimal('17.00')
            self.delivery_uk.save()

            # the original basket (not frozen) should be affected by
            # changes made to underlying items:
            #
            # P1         100.00  2  200.00
            # P1 (Large)  20.00  2   40.00
            # ----------------------------
            # SUB                   240.00
            # DELIVERY (UK)           7.00
            # DISCOUNT               30.00
            # TOTAL                 217.00
            original_basket = Basket(self.request)
            item = original_basket.items[0]
            self.assertEqual('Renamed Product', item.title)
            self.assertEqual('Changed excerpt', item.excerpt)
            self.assertEqual({'size': self.size_large.pk}, item.variety_data)
            self.assertEqual(Decimal('100.00'), item.product_price)
            self.assertEqual(Decimal('20.00'), item.total_varieties)
            self.assertEqual(Decimal('120.00'), item.total_product)
            self.assertEqual(Decimal('120.00'), item.total_product_without_deposit)
            self.assertEqual(Decimal('240.00'), item.total)
            self.assertEqual(Decimal('240.00'), item.total_without_deposit)
            self.assertEqual(Decimal('240.00'), item.total_discountable)
            self.assertEqual('http://www.testapp.cubane.innershed.com/shop/product/renamed-product-1/', item.get_absolute_url())
            self.assertEqual('http://www.testapp.cubane.innershed.com/shop/product/renamed-product-1/?size=%d' % self.size_large.pk, item.get_absolute_url_with_varieties())
            self.assertEqual('http://www.testapp.cubane.innershed.com/shop/product/renamed-product-1/', item.url)
            self.assertEqual(Decimal('240.00'), original_basket.sub_total)
            self.assertEqual(Decimal('17.00'), original_basket.delivery)
            self.assertEqual(Decimal('30.00'), original_basket.discount_value)
            self.assertEqual(Decimal('227.00'), original_basket.total)
            self.assertEqual(2, original_basket.quantity)

            # create basket from order, which should be frozen
            basket = Basket.restore_from_order(order)
            self.assertEqual(1, len(basket.items))

            # even through we changed details of the underlying product,
            # the basket is still responding to the original values when
            # the order was created originally...
            #
            # P1          50.00  2  100.00
            # P1 (Large)  10.00  2   20.00
            # ----------------------------
            # SUB                   120.00
            # DELIVERY (UK)           0.00 (free delivery over 100.00)
            # DISCOUNT               15.00
            # TOTAL                 112.00
            item = basket.items[0]
            self.assertEqual('Foo', item.title)
            self.assertEqual('Foo Bar', item.excerpt)
            self.assertEqual({'size': self.size_large.pk}, item.variety_data)
            self.assertEqual(Decimal('50.00'), item.product_price)
            self.assertEqual(Decimal('10.00'), item.total_varieties)
            self.assertEqual(Decimal('60.00'), item.total_product)
            self.assertEqual(Decimal('60.00'), item.total_product_without_deposit)
            self.assertEqual(Decimal('120.00'), item.total)
            self.assertEqual(Decimal('120.00'), item.total_without_deposit)
            self.assertEqual(Decimal('120.00'), item.total_discountable)
            self.assertEqual('http://www.testapp.cubane.innershed.com/shop/product/foo-1/', item.get_absolute_url())
            self.assertEqual('http://www.testapp.cubane.innershed.com/shop/product/foo-1/?size=%d' % self.size_large.pk, item.get_absolute_url_with_varieties())
            self.assertEqual('http://www.testapp.cubane.innershed.com/shop/product/foo-1/', item.url)
            self.assertEqual(Decimal('120.00'), basket.sub_total)
            self.assertEqual(Decimal('0.00'), basket.delivery)
            self.assertEqual(Decimal('15.00'), basket.discount_value)
            self.assertEqual(Decimal('105.00'), basket.total)
            self.assertEqual(2, basket.quantity)
        finally:
            self.product.title = p.title
            self.product.slug = p.slug
            self.product.price = p.price
            self.product._excerpt = p._excerpt
            self.product.save()

            assignment.offset_value = a.offset_value
            assignment.save()

            self.voucher.discount_value = v.discount_value
            self.voucher.valid_from = v.valid_from
            self.voucher.valid_until = v.valid_until
            self.voucher.save()

            self.delivery_uk.free_delivery_threshold = d.free_delivery_threshold
            self.delivery_uk.uk_def = d.uk_def
            self.delivery_uk.save()


    #
    # is_empty()
    #
    def test_is_empty_should_return_true_if_empty(self):
        basket = Basket(self.request)
        self.assertTrue(basket.is_empty())


    def test_is_empty_should_return_false_if_not_empty(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        self.assertFalse(basket.is_empty())


    #
    # get_size()
    #
    def test_get_size_should_return_zero_if_basket_is_empty(self):
        basket = Basket(self.request)
        self.assertEqual(0, basket.get_size())


    def test_get_size_should_return_sum_of_quantity_for_all_basket_items(self):
        basket = Basket(self.request)
        basket.add_item(self.product, quantity=3)
        basket.add_item(self.second_product, quantity=5)
        self.assertEqual(8, basket.get_size())


    #
    # get_special_requirements() and set_special_requirements()
    #
    def test_get_special_requirements_should_return_none_if_not_set(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.get_special_requirements())


    def test_get_special_requirements_should_return_special_requirements(self):
        basket = Basket(self.request)
        basket.set_special_requirements('Foo')
        self.assertEqual('Foo', basket.get_special_requirements())


    #
    # get_items()
    #
    def test_get_items_should_return_empty_list_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual([], basket.get_items())


    def test_get_items_should_return_list_of_basket_items(self):
        basket = Basket(self.request)
        basket.add_item(self.product, quantity=3)
        basket.add_item(self.second_product, quantity=5)
        self.assertEqual(2, len(basket.get_items()))


    #
    # get_click_and_collect_items()
    #
    def test_get_click_and_collect_items_should_return_empty_list_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual([], basket.get_click_and_collect_items())


    def test_get_click_and_collect_items_should_return_empty_list_for_basket_without_any_click_and_collect_items(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        self.assertEqual([], basket.get_click_and_collect_items())


    def test_get_click_and_collect_items_should_return_list_of_items_that_are_click_and_collect(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.add_item(self.click_and_collect_product)
        self.assertEqual([basket.items[1]], basket.get_click_and_collect_items())


    #
    # get_ga_items()
    #
    def test_get_ga_items_should_return_empty_list_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual([], basket.get_ga_items())


    def test_get_ga_items_should_return_ga_information_for_every_basket_item(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        basket.add_item(self.second_product, quantity=2)

        self.assertEqual([
            {
                'category': 'Category',
                'id': 1,
                'name': 'Foo',
                'price': Decimal('50.00'),
                'quantity': 1,
                'variant': 'Red, Blue'
            }, {
                'category': 'Category',
                'id': 2,
                'name': 'Bar',
                'price': Decimal('35.00'),
                'quantity': 2,
                'variant': ''
            }
        ], basket.get_ga_items())


    #
    # get_product_ids()
    #
    def test_get_product_ids_should_return_empty_list_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual([], basket.get_product_ids())


    def test_get_product_ids_should_return_unique_list_of_product_ids(self):
        # add same product but with different variety option, therefore
        # resulting in two basket items with the same product identifier
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options[0])
        basket.add_item(self.product, self.variety_options[1])
        self.assertEqual([self.product.id], basket.get_product_ids())


    #
    # get_variety_option_ids()
    #
    def test_get_variety_option_ids_should_return_empty_list_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual([], basket.get_variety_option_ids())


    def test_get_variety_option_ids_should_return_empty_list_for_basket_without_varieties(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        self.assertEqual([], basket.get_variety_option_ids())


    def test_get_variety_option_ids_should_return_unique_list_of_variety_options(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options[0])
        basket.add_item(self.second_product, self.variety_options)
        self.assertEqual(
            [option.id for option in self.variety_options],
            basket.get_variety_option_ids()
        )


    #
    # clear
    #
    def test_clear_should_reset_basket_and_remove_all_items(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options[0])
        basket.add_item(self.second_product, self.variety_options)
        basket.set_voucher('TEST')
        self._set_billing_address(basket)
        self._set_delivery_address(basket)
        self._set_signup(basket)
        basket.set_delivery_option(self.delivery_uk)
        basket.newsletter = True
        basket.set_special_requirements('Special Requirements')
        basket.survey = 'Survey'
        basket.click_and_collect = True
        basket.terms = True
        basket.update_profile = True
        basket.clear()

        self.assertEqual([], basket.get_items())
        self.assertIsNone(basket.voucher)
        self.assertIsNone(basket.billing_address)
        self.assertIsNone(basket.delivery_address)
        self.assertFalse(basket.newsletter)
        self.assertIsNone(basket.special_req)
        self.assertIsNone(basket.survey)
        self.assertIsNone(basket.signup)
        self.assertFalse(basket.update_profile)
        self.assertIsNone(basket.get_delivery_option())
        self.assertFalse(basket.terms)
        self.assertFalse(basket.click_and_collect)


    #
    # get_item_by_hash()
    #
    def test_get_item_by_hash_should_return_none_for_unknown_hash(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.get_item_by_hash('not a known hash'))


    def test_get_item_by_hash_should_return_item_by_given_hash(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        item = basket.get_item_by_hash(get_hash(self.product))
        self.assertEqual(self.product, item.product)


    #
    # get_item_by_product()
    #
    def test_get_item_by_product_should_return_none_for_unknown_product(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.get_item_by_product(self.product))


    def test_get_item_by_product_should_return_item_by_given_prdouct(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        item = basket.get_item_by_product(self.product)
        self.assertEqual(self.product, item.product)


    def test_get_item_by_product_and_variety_should_return_item_by_given_prdouct(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        item = basket.get_item_by_product(self.product, self.variety_options)
        self.assertEqual(self.product, item.product)


    #
    # add_item()
    #
    def test_add_item_should_ignore_non_integer_quantity(self):
        basket = Basket(self.request)
        basket.add_item(self.product, quantity='no integer')
        self.assertTrue(basket.is_empty())


    def test_add_item_should_floor_non_integer_number_for_quantity(self):
        basket = Basket(self.request)
        basket.add_item(self.product, quantity=2.8)
        self.assertEqual(2, basket.get_size())


    def test_add_item_should_not_add_to_basket_with_negative_quantity(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.add_item(self.product, quantity=-3))
        self.assertTrue(basket.is_empty())


    def test_add_item_should_not_add_to_basket_with_zero_quantity(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.add_item(self.product, quantity=0))
        self.assertTrue(basket.is_empty())


    def test_item_should_not_subtract_quantity_with_existing_item(self):
        basket = Basket(self.request)
        basket.add_item(self.product, quantity=3)
        basket.add_item(self.product, quantity=-3)
        self.assertEqual(3, basket.get_size())


    def test_add_item_should_increase_quantity_when_adding_same_product(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.add_item(self.product)
        self.assertEqual(1, len(basket.get_items()))
        self.assertEqual(2, basket.get_size())


    def test_add_item_should_increase_quantity_when_adding_same_product_with_same_varieties(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        basket.add_item(self.product, self.variety_options)
        self.assertEqual(1, len(basket.get_items()))
        self.assertEqual(2, basket.get_size())


    def test_add_item_should_increase_quantity_when_adding_same_product_with_same_varieties_independent_of_order_given(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        basket.add_item(self.product, list(reversed(self.variety_options)))
        self.assertEqual(1, len(basket.get_items()))
        self.assertEqual(2, basket.get_size())


    def test_add_item_should_increase_quantity_when_adding_same_product_with_same_varieties_and_custom_properties(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options, custom={'foo': 'bar'})
        basket.add_item(self.product, self.variety_options, custom={'foo': 'bar'})
        self.assertEqual(1, len(basket.get_items()))
        self.assertEqual(2, basket.get_size())


    def test_add_item_should_increase_quantity_when_adding_same_product_with_same_varieties_and_custom_properties_independent_of_order_given(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options, custom={'A': 'a', 'B': 'b'})
        basket.add_item(self.product, self.variety_options, custom={'B': 'b', 'A': 'a'})
        self.assertEqual(1, len(basket.get_items()))
        self.assertEqual(2, basket.get_size())


    def test_add_item_should_add_seperate_products(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.add_item(self.second_product)
        self.assertEqual(2, len(basket.get_items()))


    def test_add_item_should_add_seperate_product_if_they_differ_in_varieties(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options[0])
        basket.add_item(self.product, self.variety_options[1])
        self.assertEqual(2, len(basket.get_items()))


    def test_add_item_should_add_seperate_product_if_they_differ_in_custom_properties(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options, custom={'foo': 'bar'})
        basket.add_item(self.product, self.variety_options, custom={'bar': 'foo'})
        self.assertEqual(2, len(basket.get_items()))


    def test_add_item_should_not_add_item_if_product_cannot_be_added_to_basket(self):
        basket = Basket(self.request)
        product = Mock()
        def can_be_added_to_basket(request):
            return False
        product.can_be_added_to_basket = can_be_added_to_basket
        self.assertIsNone(basket.add_item(product))
        self.assertTrue(basket.is_empty())


    #
    # set_voucher()
    #
    def test_set_voucher_should_return_true_if_correwct_voucher_was_set(self):
        basket = Basket(self.request)
        self.assertTrue(basket.set_voucher('TEST'))
        self.assertEqual('TEST', basket.get_voucher_code())


    def test_set_voucher_should_return_true_if_voucher_code_matches_ignoring_uppercase_lowercase(self):
        basket = Basket(self.request)
        self.assertTrue(basket.set_voucher('test'))


    def test_set_voucher_should_return_false_if_voucher_code_does_not_match(self):
        basket = Basket(self.request)
        self.assertFalse(basket.set_voucher('does-not-match'))


    def test_set_voucher_should_return_false_if_voucher_is_disabled(self):
        basket = Basket(self.request)
        try:
            self.voucher.enabled = False
            self.voucher.save()
            self.assertFalse(basket.set_voucher('TEST'))
        finally:
            self.voucher.enabled = True
            self.voucher.save()


    @freeze_time('2016-06-20')
    def test_set_voucher_should_return_true_if_voucher_is_valid_from_today(self):
        basket = Basket(self.request)
        try:
            today = datetime.date(2016, 6, 20)
            self.voucher.valid_from = today
            self.voucher.save()
            self.assertTrue(basket.set_voucher('TEST'))
        finally:
            self.voucher.valid_from = None
            self.voucher.save()


    @freeze_time('2016-06-20')
    def test_set_voucher_should_return_false_if_voucher_is_not_valid_yet(self):
        basket = Basket(self.request)
        try:
            tomorrow = datetime.date(2016, 6, 21)
            self.voucher.valid_from = tomorrow
            self.voucher.save()
            self.assertFalse(basket.set_voucher('TEST'))
        finally:
            self.voucher.valid_from = None
            self.voucher.save()


    @freeze_time('2016-06-20')
    def test_set_voucher_should_return_true_if_voucher_is_valid_until_today(self):
        basket = Basket(self.request)
        try:
            today = datetime.date(2016, 6, 20)
            self.voucher.valid_until = today
            self.voucher.save()
            self.assertTrue(basket.set_voucher('TEST'))
        finally:
            self.voucher.valid_until = None
            self.voucher.save()


    @freeze_time('2016-06-20')
    def test_set_voucher_should_return_false_if_voucher_is_not_valid_anymore(self):
        basket = Basket(self.request)
        try:
            yesterday = datetime.date(2016, 6, 19)
            self.voucher.valid_until = yesterday
            self.voucher.save()
            self.assertFalse(basket.set_voucher('TEST'))
        finally:
            self.voucher.valid_until = None
            self.voucher.save()


    #
    # remove_voucher()
    #
    def test_remove_voucher_should_remove_voucher(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.remove_voucher()
        self.assertIsNone(basket.voucher)


    #
    # get_voucher_code()
    #
    def test_get_voucher_code_should_return_none_if_no_voucher_is_set(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.get_voucher_code())


    def test_get_voucher_code_should_return_voucher_code_uppercase(self):
        basket = Basket(self.request)
        try:
            self.voucher.code = 'test'
            self.voucher.save()
            basket.set_voucher('test')
            self.assertEqual('TEST', basket.get_voucher_code())
        finally:
            self.voucher.code = 'TEST'
            self.voucher.save()


    #
    # get_voucher_title()
    #
    def test_get_voucher_title_should_return_none_if_voucher_is_not_set(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.get_voucher_title())


    def test_get_voucher_title_should_return_title_of_voucher(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        self.assertEqual('Test', basket.get_voucher_title())


    #
    # set_click_and_collect() and is_click_and_collect()
    #
    def test_set_click_and_collect_should_set_click_and_collect(self):
        basket = Basket(self.request)
        self.assertFalse(basket.is_click_and_collect())
        basket.set_click_and_collect(True)
        self.assertTrue(basket.is_click_and_collect())
        basket.set_click_and_collect(False)
        self.assertFalse(basket.is_click_and_collect())


    #
    # set_invoice() and is_invoice()
    #
    def test_should_be_none_invoice_order_by_default(self):
        basket = Basket(self.request)
        self.assertFalse(basket.is_invoice())


    def test_should_enable_invoice_with_invoice_number(self):
        basket = Basket(self.request)
        basket.set_invoice(True, '12345678')
        self.assertTrue(basket.is_invoice())
        self.assertEqual('12345678', basket.invoice_number)


    def test_should_not_overwrite_invoice_number_if_not_set(self):
        basket = Basket(self.request)
        basket.set_invoice(True, '12345678')
        basket.set_invoice(True)
        self.assertTrue(basket.is_invoice())
        self.assertEqual('12345678', basket.invoice_number)


    def test_should_disable_invoice(self):
        basket = Basket(self.request)
        basket.set_invoice(True)
        self.assertTrue(basket.is_invoice())

        basket.set_invoice(False)
        self.assertFalse(basket.is_invoice())


    def test_should_clear_invoice_number_if_order_is_not_by_invoice_anymore(self):
        basket = Basket(self.request)
        basket.set_invoice(True, '12345678')
        self.assertTrue(basket.is_invoice())
        self.assertEqual('12345678', basket.invoice_number)

        basket.set_invoice(False)
        self.assertFalse(basket.is_invoice())
        self.assertIsNone(basket.invoice_number)


    #
    # default_delivery() and is_default_delivery()
    #
    def test_should_be_disabled_by_default(self):
        basket = Basket(self.request)
        self.assertFalse(basket.is_default_delivery())


    def test_should_enable(self):
        basket = Basket(self.request)
        basket.set_default_delivery(True)
        self.assertTrue(basket.is_default_delivery())


    def test_should_disable(self):
        basket = Basket(self.request)
        basket.set_default_delivery(True)
        self.assertTrue(basket.is_default_delivery())

        basket.set_default_delivery(False)
        self.assertFalse(basket.is_default_delivery())


    #
    # remove_item_by_hash()
    #
    def test_remove_item_by_hash_should_return_none_if_hash_does_not_exist(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.remove_item_by_hash('does-not-exist'))


    def test_remove_item_by_hash_should_remove_and_return_item(self):
        basket = Basket(self.request)
        item = basket.add_item(self.product)
        self.assertEqual(item, basket.remove_item_by_hash(get_hash(self.product)))
        self.assertTrue(basket.is_empty())


    #
    # update_quantity_by_hash()
    #
    def test_should_return_false_if_item_does_not_exist(self):
        basket = Basket(self.request)
        self.assertFalse(basket.update_quantity_by_hash('does-not-exist', 1))


    def test_should_return_false_when_updating_quantity_for_existing_item(self):
        basket = Basket(self.request)
        item = basket.add_item(self.product)
        self.assertFalse(basket.update_quantity_by_hash(get_hash(self.product), 3))
        self.assertEqual(3, basket.get_size())


    def test_should_return_true_when_removing_item_due_to_zero_quantity(self):
        basket = Basket(self.request)
        item = basket.add_item(self.product)
        self.assertTrue(basket.update_quantity_by_hash(get_hash(self.product), 0))
        self.assertTrue(basket.is_empty())


    def test_should_return_true_when_removing_item_due_to_negative_quantity(self):
        basket = Basket(self.request)
        item = basket.add_item(self.product)
        self.assertTrue(basket.update_quantity_by_hash(get_hash(self.product), -3))
        self.assertTrue(basket.is_empty())


    def test_should_return_true_when_removing_item_due_to_not_a_number_for_quantity(self):
        basket = Basket(self.request)
        item = basket.add_item(self.product)
        self.assertTrue(basket.update_quantity_by_hash(get_hash(self.product), 'not a number'))
        self.assertTrue(basket.is_empty())


    #
    # has_billing_address()
    #
    def test_has_billing_address_should_return_false_if_no_billing_address_has_been_set(self):
        basket = Basket(self.request)
        self.assertFalse(basket.has_billing_address())


    def test_has_billing_address_should_return_true_if_billing_address_has_been_set(self):
        basket = Basket(self.request)
        self._set_billing_address(basket)
        self.assertTrue(basket.has_billing_address())


    #
    # set_billing_address()
    #
    def test_set_billing_address_should_set_billing_address(self):
        basket = Basket(self.request)
        self._set_billing_address(basket)
        self.assertEqual(
            {
                'title': Customer.TITLE_MR,
                'first_name': 'Foo',
                'last_name': 'Bar',
                'email': 'foo@bar.com',
                'telephone': '12345678',
                'company': 'Foo Ltd.',
                'address1': 'Address1',
                'address2': 'Address2',
                'address3': 'Address3',
                'city': 'City',
                'country': self.GB,
                'country-iso': self.GB.iso,
                'county': 'County',
                'postcode': 'NR13 6PZ',
            },
            basket.billing_address
        )


    def test_set_billing_address_should_set_us_state_for_us_billing_address(self):
        basket = Basket(self.request)
        basket.set_billing_address(
            title='Mr.',
            first_name='Foo',
            last_name='Bar',
            email='foo.bar@innershed.com',
            telephone='12345678',
            company='Foo Ltd.',
            address1='Address1',
            address2='Address2',
            address3='Address3',
            city='City',
            country=self.US,
            county='CA',
            postcode='NR13 6PZ'
        )
        self.assertEqual(
            {
                'title': 'Mr.',
                'first_name': 'Foo',
                'last_name': 'Bar',
                'email': 'foo.bar@innershed.com',
                'telephone': '12345678',
                'company': 'Foo Ltd.',
                'address1': 'Address1',
                'address2': 'Address2',
                'address3': 'Address3',
                'city': 'City',
                'country': self.US,
                'country-iso': self.US.iso,
                'county': None,
                'state': 'CA',
                'postcode': 'NR13 6PZ',
            },
            basket.billing_address
        )


    #
    # has_delivery_address()
    #
    def test_has_delivery_address_should_return_false_if_no_delivery_address_has_been_set(self):
        basket = Basket(self.request)
        self.assertFalse(basket.has_delivery_address())


    def test_has_delivery_address_should_return_true_if_delivery_address_has_been_set(self):
        basket = Basket(self.request)
        self._set_delivery_address(basket)
        self.assertTrue(basket.has_delivery_address())


    #
    # set_delivery_address()
    #
    def test_set_delivery_address_should_set_delivery_address(self):
        basket = Basket(self.request)
        self._set_delivery_address(basket)
        self.assertEqual(
            {
                'company': 'Delivery Ltd.',
                'address1': 'Delivery Address1',
                'address2': 'Delivery Address2',
                'address3': 'Delivery Address3',
                'city': 'Delivery City',
                'country': self.DE,
                'country-iso': self.DE.iso,
                'county': 'Delivery County',
                'name': 'Delivery Name',
                'postcode': '28274'
            },
            basket.delivery_address
        )


    def test_set_delivery_address_should_set_us_state_for_us_delivery_address(self):
        basket = Basket(self.request)
        basket.set_delivery_address(
            name='Delivery Name',
            company='Delivery Ltd.',
            address1='Delivery Address1',
            address2='Delivery Address2',
            address3='Delivery Address3',
            city='Delivery City',
            country=self.US,
            county='TX',
            postcode='28274'
        )
        self.assertEqual(
            {
                'name': 'Delivery Name',
                'company': 'Delivery Ltd.',
                'address1': 'Delivery Address1',
                'address2': 'Delivery Address2',
                'address3': 'Delivery Address3',
                'city': 'Delivery City',
                'country': self.US,
                'country-iso': self.US.iso,
                'county': None,
                'state': 'TX',
                'postcode': '28274'
            },
            basket.delivery_address
        )


    def test_set_delivery_address_should_remove_null_fields(self):
        basket = Basket(self.request)
        basket.set_delivery_address(
            name='Delivery Name',
            company='Delivery Ltd.',
            address1='Delivery Address1',
            address2=None,
            address3=None,
            city='Delivery City',
            county=None,
            postcode='28274',
            country=self.GB,
        )
        self.assertEqual(
            {
                'name': 'Delivery Name',
                'company': 'Delivery Ltd.',
                'address1': 'Delivery Address1',
                'city': 'Delivery City',
                'country': self.GB,
                'country-iso': self.GB.iso,
                'postcode': '28274'
            },
            basket.delivery_address
        )


    #
    # set_delivery_country()
    #
    def test_set_delivery_country_should_change_country(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.DE)
        self.assertTrue(basket.has_delivery_address())
        self.assertEqual(
            {
                'country': self.DE,
                'country-iso': self.DE.iso
            },
            basket.delivery_address
        )


    #
    # get_billing_address_components()
    #
    def test_get_billing_address_components_should_return_default_if_no_billing_address_is_set(self):
        basket = Basket(self.request)
        self.assertEqual(
            {
                'title': None,
                'first_name': None,
                'last_name': None,
                'email': None,
                'telephone': None,
                'company': None,
                'address1': None,
                'address2': None,
                'address3': None,
                'city': None,
                'country': None,
                'country-iso': None,
                'county': None,
                'state': None,
                'postcode': None,
            },
            basket.get_billing_address_components()
        )


    def test_get_billing_address_components_should_return_address_components_set(self):
        basket = Basket(self.request)
        self._set_billing_address(basket)
        self.assertEqual(
            {
                'title': Customer.TITLE_MR,
                'first_name': 'Foo',
                'last_name': 'Bar',
                'email': 'foo@bar.com',
                'telephone': '12345678',
                'company': 'Foo Ltd.',
                'address1': 'Address1',
                'address2': 'Address2',
                'address3': 'Address3',
                'city': 'City',
                'country': self.GB,
                'country-iso': self.GB.iso,
                'county': 'County',
                'state': None,
                'postcode': 'NR13 6PZ',
            },
            basket.get_billing_address_components()
        )


    def test_set_billing_address_should_remove_null_fields(self):
        basket = Basket(self.request)
        basket.set_billing_address(
            title = Customer.TITLE_MR,
            first_name = 'Foo',
            last_name = 'Bar',
            email = 'foo@bar.com',
            telephone = '12345678',
            company = None,
            address1 = 'Address1',
            address2 = None,
            address3 = None,
            city = 'City',
            country = self.GB,
            county = None,
            postcode = 'NR13 6PZ',
        )
        self.assertEqual(
            {
                'title': Customer.TITLE_MR,
                'first_name': 'Foo',
                'last_name': 'Bar',
                'email': 'foo@bar.com',
                'telephone': '12345678',
                'address1': 'Address1',
                'city': 'City',
                'country': self.GB,
                'country-iso': self.GB.iso,
                'postcode': 'NR13 6PZ',
            },
            basket.billing_address
        )


    #
    # get_delivery_address_components()
    #
    def test_get_delivery_address_components_should_return_default_if_no_delivery_address_is_set(self):
        basket = Basket(self.request)
        self.assertEqual(
            {
                'company': None,
                'address1': None,
                'address2': None,
                'address3': None,
                'city': None,
                'country': None,
                'country-iso': None,
                'county': None,
                'name': None,
                'state': None,
                'postcode': None
            },
            basket.get_delivery_address_components()
        )


    def test_get_delivery_address_components_should_return_address_components_set(self):
        basket = Basket(self.request)
        self._set_delivery_address(basket)
        self.assertEqual(
            {
                'company': 'Delivery Ltd.',
                'address1': 'Delivery Address1',
                'address2': 'Delivery Address2',
                'address3': 'Delivery Address3',
                'city': 'Delivery City',
                'country': self.DE,
                'country-iso': self.DE.iso,
                'county': 'Delivery County',
                'name': 'Delivery Name',
                'state': None,
                'postcode': '28274'
            },
            basket.get_delivery_address_components()
        )


    #
    # set_signup()
    #
    def test_set_signup_should_set_signup_data(self):
        basket = Basket(self.request)
        basket.set_signup('foo@bar.com', 'foo', 'bar', 'password')
        self.assertEqual(
            {
                'email': 'foo@bar.com',
                'first_name': 'foo',
                'last_name': 'bar',
                'password': 'password'
            },
            basket.signup
        )


    #
    # is_collection_only()
    #
    def test_is_collection_only_should_return_false_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertFalse(basket.is_collection_only())


    def test_is_collection_only_should_return_false_for_standard_delivery_orders(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        self.assertFalse(basket.is_collection_only())


    def test_is_collection_only_should_return_true_if_any_product_is_for_collection_only(self):
        basket = Basket(self.request)
        try:
            self.product.collection_only = True
            self.product.save()
            basket.add_item(self.product)
            basket.add_item(self.second_product)
            self.assertTrue(basket.is_collection_only())
        finally:
            self.product.collection_only = False
            self.product.save()


    #
    # has_pre_order_item()
    #
    def test_has_pre_order_item_should_return_false_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertFalse(basket.has_pre_order_item())


    def test_has_pre_order_item_should_return_false_for_standard_delivery_orders(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        self.assertFalse(basket.has_pre_order_item())


    def test_has_pre_order_item_should_return_true_if_any_product_is_pre_order(self):
        basket = Basket(self.request)
        try:
            self.product.pre_order = True
            self.product.save()
            basket.add_item(self.product)
            basket.add_item(self.second_product)
            self.assertTrue(basket.has_pre_order_item())
        finally:
            self.product.pre_order = False
            self.product.save()


    #
    # get_delivery_options()
    #
    @override_settings(SHOP_DEFAULT_DELIVERY_COUNTRY_ISO='DE')
    def test_get_delivery_options_should_assume_default_delivery_if_no_delivery_option_is_set(self):
        basket = Basket(self.request)
        self.assertEqual([self.delivery_eu, self.delivery_uk_eu], basket.get_delivery_options())


    def test_get_delivery_options_should_not_yield_disabled_options(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertEqual([self.delivery_uk, self.delivery_uk_eu], basket.get_delivery_options())


    def test_get_delivery_options_for_uk_should_only_yield_options_for_delivery_to_uk(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertEqual([self.delivery_uk, self.delivery_uk_eu], basket.get_delivery_options())


    def test_get_delivery_options_for_eu_should_only_yield_options_for_delivery_to_eu(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.DE)
        self.assertEqual([self.delivery_eu, self.delivery_uk_eu], basket.get_delivery_options())


    def test_get_delivery_options_for_world_should_only_yield_options_for_delivery_to_world(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.US)
        self.assertEqual(
            [self.delivery_world, self.delivery_world_quote],
            basket.get_delivery_options()
        )


    #
    # get_delivery_choices()
    #
    @override_settings(SHOP_DEFAULT_DELIVERY_COUNTRY_ISO='GB')
    def test_get_delivery_choices_should_return_delivery_options_as_choices(self):
        basket = Basket(self.request)
        self.assertEqual([
            (self.delivery_uk.pk, self.delivery_uk.title),
            (self.delivery_uk_eu.pk, self.delivery_uk_eu.title)
        ], basket.get_delivery_choices())


    #
    # set_delivery_option()
    #
    def test_set_delivery_option_should_set_delivery_option(self):
        basket = Basket(self.request)
        basket.set_delivery_option(self.delivery_uk)
        self.assertEqual(self.delivery_uk, basket.get_delivery_option())


    #
    # delivery_to()
    #
    def test_delivery_to_should_return_true_if_delivery_country_matches_argument(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertTrue(basket.delivery_to('GB'))


    @override_settings(SHOP_DEFAULT_DELIVERY_COUNTRY_ISO='DE')
    def test_delivery_to_should_assume_default_delivery_country_from_settings_if_no_delivery_country_has_been_set(self):
        basket = Basket(self.request)
        self.assertTrue(basket.delivery_to('DE'))


    def test_delivery_to_should_return_true_if_delivery_country_matches_list_argument(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertTrue(basket.delivery_to(['GB', 'DE']))


    def test_delivery_to_should_return_false_if_delivery_country_does_not_match_argument(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertFalse(basket.delivery_to('DE'))


    def test_delivery_to_should_return_false_if_delivery_country_does_not_match_list_argument(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertFalse(basket.delivery_to(['DE', 'FR']))


    #
    # delivery_to_uk()
    #
    def test_delivery_to_uk_should_return_false_if_delivery_country_is_not_uk(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.DE)
        self.assertFalse(basket.delivery_to_uk())


    def test_delivery_to_uk_should_return_true_if_delivery_country_is_uk(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertTrue(basket.delivery_to_uk())


    #
    # delivery_to_eu()
    #
    def test_delivery_to_eu_should_return_false_if_delivery_country_is_not_eu(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.US)
        self.assertFalse(basket.delivery_to_eu())


    def test_delivery_to_eu_should_return_true_if_delivery_country_is_eu(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.DE)
        self.assertTrue(basket.delivery_to_eu())


    #
    # delivery_to_world()
    #
    def test_delivery_to_world_should_return_false_if_delivery_country_is_uk(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertFalse(basket.delivery_to_world())


    def test_delivery_to_world_should_return_false_if_delivery_country_is_eu(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.DE)
        self.assertFalse(basket.delivery_to_world())


    def test_delivery_to_world_should_return_true_if_delivery_country_is_not_uk_nor_eu(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.US)
        self.assertTrue(basket.delivery_to_world())


    #
    # get_delivery_option()
    #
    def test_get_delivery_option_should_return_none_if_no_delivery_option_has_been_set(self):
        basket = Basket(self.request)
        self.assertIsNone(basket.get_delivery_option())


    def test_get_delivery_option_should_return_delivery_option(self):
        basket = Basket(self.request)
        basket.set_delivery_option(self.delivery_uk)
        self.assertEqual(self.delivery_uk, basket.get_delivery_option())


    #
    # get_delivery_option_or_default()
    #
    def test_get_delivery_option_or_default_should_return_delivery_option_if_set(self):
        basket = Basket(self.request)
        basket.set_delivery_option(self.delivery_eu)
        self.assertEqual(self.delivery_eu, basket.get_delivery_option_or_default())


    def test_get_delivery_option_or_default_should_return_default_delivery_option_if_not_set(self):
        basket = Basket(self.request)
        self.assertEqual(self.delivery_uk, basket.get_delivery_option_or_default())


    #
    # get_default_delivery_option()
    #
    def test_get_default_delivery_option_should_return_first_delivery_option_available_for_uk(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.GB)
        self.assertEqual(self.delivery_uk, basket.get_default_delivery_option())


    def test_get_default_delivery_option_should_return_first_delivery_option_available_for_eu(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.DE)
        self.assertEqual(self.delivery_eu, basket.get_default_delivery_option())


    def test_get_default_delivery_option_should_return_first_delivery_option_available_for_world(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.US)
        self.assertEqual(self.delivery_world, basket.get_default_delivery_option())


    def test_get_default_delivery_option_should_return_none_if_no_delivery_option_is_available(self):
        basket = Basket(self.request)
        basket.set_delivery_country(self.US)
        try:
            self.delivery_world.enabled = False
            self.delivery_world.save()
            self.delivery_world_quote.enabled = False
            self.delivery_world_quote.save()
            self.assertIsNone(basket.get_default_delivery_option())
        finally:
            self.delivery_world.enabled = True
            self.delivery_world.save()
            self.delivery_world_quote.enabled = True
            self.delivery_world_quote.save()


    #
    # get_delivery_details()
    #
    def test_get_delivery_details_should_calc_delivery_price_for_uk(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.set_delivery_country(self.GB)
        d = basket.get_delivery_details(self.delivery_uk)
        self.assertEqual(Decimal('7.00'), d.get('total'))
        self.assertTrue(d.get('can_deliver'))


    def test_get_delivery_details_should_calc_delivery_price_for_eu(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.set_delivery_country(self.DE)
        d = basket.get_delivery_details(self.delivery_eu)
        self.assertEqual(Decimal('9.00'), d.get('total'))
        self.assertTrue(d.get('can_deliver'))


    def test_get_delivery_details_should_calc_delivery_price_for_world(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.set_delivery_country(self.US)
        d = basket.get_delivery_details(self.delivery_world)
        self.assertEqual(Decimal('14.00'), d.get('total'))
        self.assertTrue(d.get('can_deliver'))


    def test_get_delivery_details_should_indicate_if_delivery_is_not_possible(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.set_delivery_country(self.GB)
        d = basket.get_delivery_details(self.delivery_eu)
        self.assertFalse(d.get('can_deliver'))


    def test_get_delivery_details_should_indicate_free_delivery(self):
        basket = Basket(self.request)
        basket.add_item(self.product, quantity=2)
        basket.set_delivery_country(self.GB)
        d = basket.get_delivery_details(self.delivery_uk)
        self.assertTrue(d.get('free_delivery'))
        self.assertEqual(Decimal('100.00'), d.get('free_delivery_threshold'))
        self.assertEqual(Decimal('0.00'), d.get('total'))


    def test_get_delivery_details_should_indicate_quote(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        basket.set_delivery_country(self.US)
        d = basket.get_delivery_details(self.delivery_world_quote)
        self.assertTrue(d.get('is_quote_only'))
        self.assertEqual(Decimal('0.00'), d.get('total'))


    def test_get_delivery_details_should_determine_max_delivery_cost_for_all_basket_items_for_uk(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        basket.add_item(self.third_product)
        basket.add_item(self.fourth_product)
        basket.set_delivery_country(self.GB)
        d = basket.get_delivery_details(self.delivery_uk)
        self.assertEqual(Decimal('21.00'), d.get('total'))


    def test_get_delivery_details_should_determine_max_delivery_cost_for_all_basket_items_for_eu(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        basket.add_item(self.third_product)
        basket.add_item(self.fourth_product)
        basket.set_delivery_country(self.DE)
        d = basket.get_delivery_details(self.delivery_eu)
        self.assertEqual(Decimal('22.00'), d.get('total'))


    def test_get_delivery_details_should_determine_max_delivery_cost_for_all_basket_items_for_world(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        basket.add_item(self.third_product)
        basket.add_item(self.fourth_product)
        basket.set_delivery_country(self.US)
        d = basket.get_delivery_details(self.delivery_world)
        self.assertEqual(Decimal('23.00'), d.get('total'))


    #
    # can_present_voucher()
    #
    def _test_voucher_visibility(self, basket, voucher, expected_visibility):
        for v in self.vouchers:
            if v != voucher:
                v.enabled = False
                v.save()
        try:
            self.assertEqual(expected_visibility, basket.can_present_voucher())
        finally:
            for v in self.enabled_vouchers:
                v.enabled = True
                v.save()


    def test_can_present_voucher_should_return_false_if_no_vouchers_are_enabled(self):
        basket = Basket(self.request)
        self._test_voucher_visibility(basket, None, False)


    def test_can_present_voucher_should_return_true_if_at_least_one_voucher_is_enabled(self):
        basket = Basket(self.request)
        self._test_voucher_visibility(basket, self.voucher, True)


    @freeze_time('2016-11-01')
    def test_can_present_voucher_should_return_false_if_time_interval_does_not_match(self):
        basket = Basket(self.request)
        self._test_voucher_visibility(basket, self.date_voucher, False)


    @freeze_time('2016-12-24')
    def test_can_present_voucher_should_return_true_if_time_interval_does_match(self):
        basket = Basket(self.request)
        self._test_voucher_visibility(basket, self.date_voucher, True)


    def test_can_present_voucher_should_return_false_if_categories_do_not_match(self):
        basket = Basket(self.request)
        basket.add_item(self.second_product)
        self._test_voucher_visibility(basket, self.category_voucher, False)


    def test_can_present_voucher_should_return_true_if_categories_do_match(self):
        basket = Basket(self.request)
        basket.add_item(self.third_product)
        self._test_voucher_visibility(basket, self.category_voucher, True)


    def test_can_present_voucher_should_return_false_if_max_usage_has_been_reached(self):
        basket = Basket(self.request)
        order = get_order_model().objects.create(
            status=OrderBase.STATUS_PAYMENT_CONFIRMED,
            sub_total_before_delivery=Decimal('10.00'),
            delivery=Decimal('0.00'),
            sub_total=Decimal('10.00'),
            total=Decimal('10.00'),
            voucher=self.max_usage_voucher
        )
        try:
            self._test_voucher_visibility(basket, self.max_usage_voucher, False)
        finally:
            order.delete()


    def test_can_present_voucher_should_return_true_if_max_usage_has_not_been_reached_yet(self):
        basket = Basket(self.request)
        self._test_voucher_visibility(basket, self.max_usage_voucher, True)


    #
    # clear_signup()
    #
    def test_clear_signup_should_clear_signup_information(self):
        basket = Basket(self.request)
        self._set_signup(basket)
        basket.clear_signup()
        self.assertIsNone(basket.signup)


    #
    # get_sub_total()
    #
    def test_get_sub_total_should_return_sum_of_all_line_items_including_quantity(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options, quantity=2)
        basket.add_item(self.second_product, quantity=2)
        basket.add_item(self.third_product, quantity=1)

        # P1        50.00   2   100.00
        # P2        35.00   2    70.00
        # P3         5.00   1     5.00
        # ----------------------------
        #                       175.00
        self.assertEqual(Decimal('175.00'), basket.get_sub_total())


    def test_get_sub_total_should_return_zero_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual(Decimal('0.00'), basket.get_sub_total())


    #
    # get_sub_total_discountable()
    #
    def test_get_sub_total_discountable_should_return_sum_of_all_discountable_line_items(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options, quantity=2)
        basket.add_item(self.second_product, quantity=2)

        # P1        50.00   2   100.00
        # P2        35.00   2    70.00
        # ----------------------------
        #                       170.00
        self.assertEqual(Decimal('170.00'), basket.get_sub_total_discountable())


    def test_get_sub_total_discountable_should_exclude_product_exempt_from_discount(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options, quantity=2)
        basket.add_item(self.second_product, quantity=2)
        basket.add_item(self.third_product, quantity=1)

        # P1        50.00   2   100.00
        # P2        35.00   2    70.00
        # P3         5.00   1     0.00 (exempt from discount)
        # ----------------------------
        #                       170.00
        self.assertEqual(Decimal('170.00'), basket.get_sub_total_discountable())


    def test_get_sub_total_discountable_should_exclude_products_excluded_by_category(self):
        basket = Basket(self.request)
        basket.set_voucher('CATEGORY')
        basket.add_item(self.product, self.variety_options, quantity=2)
        basket.add_item(self.second_product, quantity=2)
        basket.add_item(self.third_product, quantity=1)
        basket.add_item(self.fourth_product, quantity=1)

        # P1        50.00   2     0.00 (excluded by category)
        # P1 (Red)   3.00   2     0.00 -"-
        # P1 (Blue)  2.00   2     0.00 -"-
        # P2        35.00   2     0.00 (excluded by category)
        # P3         5.00   1     0.00 (exempt from discount)
        # P4         3.00   1     3.00
        # ----------------------------
        #                         3.00
        self.assertEqual(Decimal('3.00'), basket.get_sub_total_discountable())


    def test_get_sub_total_discountable_should_return_zero_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual(Decimal('0.00'), basket.get_sub_total_discountable())


    #
    # get_delivery()
    #
    def test_get_delivery_should_return_zero_for_click_and_collect_order(self):
        basket = Basket(self.request)
        basket.set_click_and_collect(True)
        basket.add_item(self.product, self.variety_options, quantity=2)
        self.assertEqual(Decimal('0.00'), basket.get_delivery())


    def test_get_delivery_should_return_total_delivery_charge_for_default_delivery_if_no_option_is_set(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        self.assertEqual(Decimal('7.00'), basket.get_delivery())


    def test_get_delivery_should_return_total_delivery_charge(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        basket.set_delivery_option(self.delivery_uk)
        self.assertEqual(Decimal('7.00'), basket.get_delivery())


    def test_get_delivery_should_return_zero_if_no_delivery_option_is_available(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        try:
            DeliveryOption.objects.all().update(enabled=False)
            self.assertEqual(Decimal('0.00'), basket.get_delivery())
        finally:
            DeliveryOption.objects.all().exclude(pk=self.delivery_disabled.pk).update(enabled=True)


    #
    # get_discount_value()
    #
    def test_get_discount_value_should_return_zero_for_empty_basket(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        self.assertEqual(Decimal('0.00'), basket.get_discount_value())


    def test_get_discount_value_should_return_zero_if_no_voucher_is_applied(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        self.assertEqual(Decimal('0.00'), basket.get_discount_value())


    def test_get_discount_value_should_return_total_fixed_discount(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.add_item(self.product, self.variety_options)

        # P1        50.00   1    50.00
        # P1 (Red)   3.00   1     3.00
        # P1 (Blue)  2.00   1     2.00
        # ----------------------------
        # SUB                    55.00
        # DISCOUNT              -15.00
        self.assertEqual(Decimal('15.00'), basket.get_discount_value())


    def test_get_discount_value_should_return_total_fixed_discountable_if_discount_is_bigger_than_basket_value(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.add_item(self.third_product)
        basket.add_item(self.fourth_product)

        # P3         5.00   1     5.00 (exempt from discount)
        # P4         3.00   1     3.00
        # ----------------------------
        # DISCOUNTABLE SUB        3.00
        # DISCOUNT GIVEN          3.00
        self.assertEqual(Decimal('8.00'), basket.get_sub_total())
        self.assertEqual(Decimal('3.00'), basket.get_sub_total_discountable())
        self.assertEqual(Decimal('3.00'), basket.get_discount_value())


    def test_get_discount_value_should_return_percentage_discount_value(self):
        basket = Basket(self.request)
        basket.set_voucher('PERCENTAGE')
        basket.add_item(self.product, self.variety_options)

        # P1        50.00   1    50.00
        # ----------------------------
        # SUB                    50.00
        # DISCOUNT (40%)         20.00
        self.assertEqual(Decimal('20.00'), basket.get_discount_value())


    def test_get_discount_value_should_return_delivery_amount_for_free_delivery_voucher(self):
        basket = Basket(self.request)
        basket.set_voucher('FREE_DELIVERY')
        basket.add_item(self.product, self.variety_options)

        # P1        50.00   1    50.00
        # ----------------------------
        # SUB                    50.00
        # DELIVERY (UK)           7.00
        # DISCOUNT               -7.00
        # TOTAL                  50.00
        self.assertEqual(Decimal('50.00'), basket.get_sub_total())
        self.assertEqual(Decimal('7.00'), basket.get_delivery())
        self.assertEqual(Decimal('7.00'), basket.get_discount_value())
        self.assertEqual(Decimal('50.00'), basket.get_total())


    def test_get_discount_value_should_return_zero_for_free_delivery_voucher_if_excluded_in_calculation(self):
        basket = Basket(self.request)
        basket.set_voucher('FREE_DELIVERY')
        basket.add_item(self.product, self.variety_options)
        self.assertEqual(Decimal('0.00'), basket.get_discount_value(exclude_free_delivery=True))


    def test_get_discount_value_should_return_zero_for_free_delivery_voucher_if_country_does_not_match(self):
        basket = Basket(self.request)
        basket.set_voucher('FREE_DELIVERY_DE')
        basket.set_delivery_country(self.GB)
        basket.add_item(self.product, self.variety_options)

        # P1        50.00   1    50.00
        # ----------------------------
        # SUB                    50.00
        # DELIVERY (UK)           7.00
        # DISCOUNT                0.00
        # TOTAL                  57.00
        self.assertEqual(Decimal('50.00'), basket.get_sub_total())
        self.assertEqual(Decimal('7.00'), basket.get_delivery())
        self.assertEqual(Decimal('0.00'), basket.get_discount_value())
        self.assertEqual(Decimal('57.00'), basket.get_total())


    def test_get_discount_value_should_return_delivery_charge_as_free_delivery_voucher_if_country_matches(self):
        basket = Basket(self.request)
        basket.set_voucher('FREE_DELIVERY_DE')
        basket.set_delivery_country(self.DE)
        basket.add_item(self.product, self.variety_options)

        # P1        50.00   1    50.00
        # ----------------------------
        # SUB                    50.00
        # DELIVERY (DE)           9.00
        # DISCOUNT                9.00
        # TOTAL                  50.00
        self.assertEqual(Decimal('50.00'), basket.get_sub_total())
        self.assertEqual(Decimal('9.00'), basket.get_delivery())
        self.assertEqual(Decimal('9.00'), basket.get_discount_value())
        self.assertEqual(Decimal('50.00'), basket.get_total())


    #
    # some_products_exempt_from_discount()
    #
    def test_some_products_exempt_from_discount_should_return_false_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertFalse(basket.some_products_exempt_from_discount())


    def test_some_products_exempt_from_discount_should_return_false_if_no_product_is_exempt_from_discount(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        self.assertFalse(basket.some_products_exempt_from_discount())


    def test_some_products_exempt_from_discount_should_return_true_if_at_least_on_product_is_exempt_from_discount(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        basket.add_item(self.third_product)  # exempt_from_discount
        self.assertTrue(basket.some_products_exempt_from_discount())


    def test_some_products_exempt_from_discount_should_return_true_if_at_some_products_are_exempt_from_discount_via_category(self):
        basket = Basket(self.request)
        basket.set_voucher('CATEGORY')
        basket.add_item(self.product, self.variety_options)
        basket.add_item(self.fourth_product)  # exempt by voucher category
        self.assertTrue(basket.some_products_exempt_from_discount())


    #
    # some_products_exempt_from_free_delivery()
    #
    def test_some_products_exempt_from_free_delivery_should_return_false_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertFalse(basket.some_products_exempt_from_free_delivery())


    def test_some_products_exempt_from_free_delivery_should_return_false_if_delivery_is_not_free(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options)
        self.assertFalse(basket.some_products_exempt_from_free_delivery())


    def test_some_products_exempt_from_free_delivery_should_return_false_if_delivery_is_for_free_but_no_product_is_exempt(self):
        basket = Basket(self.request)
        basket.add_item(self.product, self.variety_options, quantity=10)
        self.assertFalse(basket.some_products_exempt_from_free_delivery())


    @patch('cubane.ishop.basket.Basket.get_delivery_option_or_default')
    def test_some_products_exempt_from_free_delivery_should_return_false_if_no_delivery_options_are_available(self, get_delivery_option_or_default):
        get_delivery_option_or_default.return_value = None
        basket = Basket(self.request)
        basket.add_item(self.fourth_product)
        self.assertFalse(basket.some_products_exempt_from_free_delivery())


    def test_some_products_exempt_from_free_delivery_should_return_true_if_delivery_for_free_is_exempt_by_at_least_one_product(self):
        basket = Basket(self.request)
        basket.add_item(self.fourth_product)
        self.assertTrue(basket.some_products_exempt_from_free_delivery())


    #
    # contains_items_exempt_from_free_delivery()
    #
    def test_contains_items_exempt_from_free_delivery_should_return_false_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertFalse(basket.contains_items_exempt_from_free_delivery())


    def test_contains_items_exempt_from_free_delivery_should_return_false_for_basket_with_no_product_that_is_exempt(self):
        basket = Basket(self.request)
        basket.add_item(self.product)
        self.assertFalse(basket.contains_items_exempt_from_free_delivery())


    def test_contains_items_exempt_from_free_delivery_should_return_true_for_basket_containing_product_that_is_exempt(self):
        basket = Basket(self.request)
        basket.add_item(self.fourth_product)
        self.assertTrue(basket.contains_items_exempt_from_free_delivery())


    #
    # get_total_before_delivery()
    #
    def test_get_total_before_delivery_should_return_zero_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual(Decimal('0.00'), basket.get_total_before_delivery())


    def test_get_total_before_delivery_should_return_total_basket_value_excluding_delivery(self):
        basket = Basket(self.request)
        basket.add_item(self.product)

        # P1        50.00   1    50.00
        # ----------------------------
        #                        50.00 (excluding delivery)
        self.assertEqual(Decimal('50.00'), basket.get_total_before_delivery())


    def test_get_total_before_delivery_should_return_total_basket_value_reduced_by_discount_excluding_delivery(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.add_item(self.product)

        # P1        50.00   1    50.00
        # DISCOUNT              -15.00
        # ----------------------------
        #                        35.00 (excluding delivery)
        self.assertEqual(Decimal('35.00'), basket.get_total_before_delivery())


    #
    # get_total()
    #
    def test_get_total_should_return_zero_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual(Decimal('0.00'), basket.get_total())


    def test_get_total_should_return_total_with_free_delivery_no_discount(self):
        basket = Basket(self.request)
        basket.add_item(self.product, quantity=2)

        # P1        50.00   1   100.00
        # DELIVERY                0.00
        # ----------------------------
        #                       100.00
        self.assertEqual(Decimal('100.00'), basket.get_total())


    def test_get_total_should_return_total_with_free_delivery_with_discount(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.add_item(self.product, quantity=3)

        # P1        50.00   3   150.00
        # DISCOUNT              -15.00
        # ----------------------------
        #                       135.00
        self.assertEqual(Decimal('135.00'), basket.get_total())


    def test_get_total_should_return_total_with_delivery_no_discount(self):
        basket = Basket(self.request)
        basket.add_item(self.product)

        # P1        50.00   1    50.00
        # DELIVERY                7.00
        # ----------------------------
        #                        57.00
        self.assertEqual(Decimal('57.00'), basket.get_total())


    def test_get_total_should_return_total_with_delivery_with_discount(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.add_item(self.product, quantity=2)

        # P1        50.00   2   100.00
        # DISCOUNT              -15.00
        # DELIVERY                7.00
        # ----------------------------
        #                        92.00
        self.assertEqual(Decimal('92.00'), basket.get_total())


    def test_get_total_should_return_total_with_click_and_collect_no_discount(self):
        basket = Basket(self.request)
        basket.set_click_and_collect(True)
        basket.add_item(self.product)

        # P1        50.00   1    50.00
        # ----------------------------
        #                        50.00
        self.assertEqual(Decimal('50.00'), basket.get_total())


    def test_get_total_should_return_total_with_click_and_collect_with_discount(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.set_click_and_collect(True)
        basket.add_item(self.product)

        # P1        50.00   1    50.00
        # DISCOUNT              -15.00
        # ----------------------------
        #                        35.00
        self.assertEqual(Decimal('35.00'), basket.get_total())


    #
    # get_totals()
    #
    def test_get_totals_for_empty_basket_should_return_basket_totals_of_zero(self):
        basket = Basket(self.request)
        self.assertEqual({
            'quantity': 0,
            'sub_total': Decimal('0.00'),
            'discount': Decimal('0.00'),
            'delivery': Decimal('0.00'),
            'total': Decimal('0.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00')
        }, basket.get_totals())


    def test_get_totals_should_return_total_with_free_delivery_no_discount(self):
        basket = Basket(self.request)
        basket.add_item(self.product, quantity=2)

        # P1        50.00   1   100.00
        # DELIVERY                0.00
        # ----------------------------
        #                       100.00
        self.assertEqual({
            'quantity': 2,
            'sub_total': Decimal('100.00'),
            'discount': Decimal('0.00'),
            'delivery': Decimal('0.00'),
            'total': Decimal('100.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00')
        }, basket.get_totals())


    def test_get_totals_should_return_total_with_free_delivery_with_discount(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.add_item(self.product, quantity=3)

        # P1        50.00   3   150.00
        # DISCOUNT              -15.00
        # ----------------------------
        #                       135.00
        self.assertEqual({
            'quantity': 3,
            'sub_total': Decimal('150.00'),
            'discount': Decimal('15.00'),
            'delivery': Decimal('0.00'),
            'total': Decimal('135.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00')
        }, basket.get_totals())


    def test_get_totals_should_return_total_with_delivery_no_discount(self):
        basket = Basket(self.request)
        basket.add_item(self.product)

        # P1        50.00   1    50.00
        # DELIVERY                7.00
        # ----------------------------
        #                        57.00
        self.assertEqual({
            'quantity': 1,
            'sub_total': Decimal('50.00'),
            'discount': Decimal('0.00'),
            'delivery': Decimal('7.00'),
            'total': Decimal('57.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00')
        }, basket.get_totals())


    def test_get_totals_should_return_total_with_delivery_with_discount(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.add_item(self.product, quantity=2)

        # P1        50.00   2   100.00
        # DISCOUNT              -15.00
        # DELIVERY                7.00
        # ----------------------------
        #                        92.00
        self.assertEqual({
            'quantity': 2,
            'sub_total': Decimal('100.00'),
            'discount': Decimal('15.00'),
            'delivery': Decimal('7.00'),
            'total': Decimal('92.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00')
        }, basket.get_totals())


    def test_get_totals_should_return_total_with_click_and_collect_no_discount(self):
        basket = Basket(self.request)
        basket.set_click_and_collect(True)
        basket.add_item(self.product)

        # P1        50.00   1    50.00
        # ----------------------------
        #                        50.00
        self.assertEqual({
            'quantity': 1,
            'sub_total': Decimal('50.00'),
            'delivery': Decimal('0.00'),
            'discount': Decimal('0.00'),
            'total': Decimal('50.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00')
        }, basket.get_totals())


    def test_get_totals_should_return_total_with_click_and_collect_with_discount(self):
        basket = Basket(self.request)
        basket.set_voucher('TEST')
        basket.set_click_and_collect(True)
        basket.add_item(self.product)

        # P1        50.00   1    50.00
        # DISCOUNT              -15.00
        # ----------------------------
        #                        35.00
        self.assertEqual({
            'quantity': 1,
            'sub_total': Decimal('50.00'),
            'delivery': Decimal('0.00'),
            'discount': Decimal('15.00'),
            'total': Decimal('35.00'),
            'difference_between_deposit_and_full_amount': Decimal('0.00')
        }, basket.get_totals())


    #
    # as_legacy_dict()
    #
    def test_as_dict_should_return_empty_structure_for_empty_basket(self):
        basket = Basket(self.request)
        self.assertEqual({
            'discount_value': Decimal('0.00'),
            'finance_option_id': None,
            'is_available_for_loan': False,
            'is_quote_only': False,
            'loan_deposit': None,
            'products': [],
            'voucher': None,
            'is_invoice': False,
            'invoice_number': None,
            'totals': {
                'delivery': Decimal('0.00'),
                'total': Decimal('0.00'),
                'difference_between_deposit_and_full_amount': Decimal('0.00'),
                'sub_total': Decimal('0.00'),
                'quantity': 0
            }
        }, basket.as_legacy_dict())


    def test_as_dict_should_return_structure_representing_given_basket(self):
        basket = Basket(self.request)
        basket.set_voucher('PERCENTAGE')
        basket.add_item(self.product, self.variety_options)
        basket.add_item(self.second_product, quantity=2)

        # P1        50.00   1    50.00
        # P2        35.00   2    70.00 (UK delivery: 15.00)
        # ----------------------------
        # SUB                   120.00
        # DISCOUNT (40%)        -48.00
        # ----------------------------
        # SUB                    72.00
        # DELIVERY               15.00
        # ----------------------------
        #                        83.00
        self.assertEqual(Decimal('120.00'), basket.get_sub_total())
        self.assertEqual(Decimal('72.00'), basket.get_total_before_delivery())
        self.assertEqual(Decimal('15.00'), basket.get_delivery())
        self.assertEqual(Decimal('87.00'), basket.get_total())
        self.assertEqual({
            'discount_value': Decimal('48.00'),
            'finance_option_id': None,
            'is_available_for_loan': False,
            'is_quote_only': False,
            'loan_deposit': None,
            'is_invoice': False,
            'invoice_number': None,
            'products': [
                {
                    'custom_properties': [],
                    'deposit_only': False,
                    'excerpt': 'Foo Bar',
                    'icon_url': None,
                    'image_attribute_url': None,
                    'product_id': self.product.pk,
                    'product_price': Decimal('50.00'),
                    'quantity': 1,
                    'sku': {
                        'id': None,
                        'code': None,
                        'barcode': None,
                        'price': None
                    },
                    'title': 'Foo',
                    'total': Decimal('50.00'),
                    'total_product': Decimal('50.00'),
                    'total_product_without_deposit': Decimal('50.00'),
                    'total_without_deposit': Decimal('50.00'),
                    'url': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%s/' % self.product.pk,
                    'get_absolute_url': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%s/' % self.product.pk,
                    'get_absolute_url_with_varieties': 'http://www.testapp.cubane.innershed.com/shop/product/foo-%s/?colour=%d' % (self.product.pk, self.option_blue.pk),
                    'labels': None,
                    'varieties': [
                        {'variety_option': {
                            'title': 'Red',
                            'text_label': False,
                            'text_label_value': None,
                            'price': Decimal('0.00'),
                            'variety': {'title': 'Colour', 'display_title': ''}}
                        },
                        {'variety_option': {
                            'title': 'Blue',
                            'text_label': False,
                            'text_label_value': None,
                            'price': Decimal('0.00'),
                            'variety': {'title': 'Colour', 'display_title': ''}}
                        }
                    ],
                    'variety_option_ids': [a.pk for a in self.variety_options]
                }, {
                    'custom_properties': [],
                    'deposit_only': False,
                    'excerpt': 'Foo',
                    'icon_url': None,
                    'image_attribute_url': None,
                    'product_id': self.second_product.pk,
                    'product_price': Decimal('35.00'),
                    'quantity': 2,
                    'sku': {
                        'id': None,
                        'code': None,
                        'barcode': None,
                        'price': None
                    },
                    'title': 'Bar',
                    'total': Decimal('70.00'),
                    'total_product': Decimal('35.00'),
                    'total_product_without_deposit': Decimal('35.00'),
                    'total_without_deposit': Decimal('70.00'),
                    'url': 'http://www.testapp.cubane.innershed.com/shop/product/bar-%d/' % self.second_product.pk,
                    'get_absolute_url': 'http://www.testapp.cubane.innershed.com/shop/product/bar-%d/' % self.second_product.pk,
                    'get_absolute_url_with_varieties': 'http://www.testapp.cubane.innershed.com/shop/product/bar-%d/' % self.second_product.pk,
                    'labels': None,
                    'varieties': [],
                    'variety_option_ids': []
                }
            ],
            'totals': {
                'delivery': Decimal('15.00'),
                'difference_between_deposit_and_full_amount': Decimal('0.00'),
                'quantity': 3,
                'sub_total': Decimal('120.00'),
                'total': Decimal('87.00')
            },
            'voucher': {
                'code': 'PERCENTAGE',
                'title': 'Percentage'
            }
        }, basket.as_legacy_dict())


    #
    # Private
    #
    def _assertIsClean(self, basket):
        self.assertIsNone(basket.request)
        self.assertEqual(1, len(basket.items))
        self.assertIsNone(basket.items[0].product)
        self.assertIsNone(basket.items[0].variety_options)
