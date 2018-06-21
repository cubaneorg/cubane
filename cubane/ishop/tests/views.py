# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from django.template.defaultfilters import slugify
from cubane.tests.base import CubaneTestCase
from cubane.ishop.views import get_shop
from cubane.testapp.models import Product
import cubane.ishop.views as shop_views


class IShopViewsTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(IShopViewsTestCase, cls).setUpClass()
        cls.create_products()


    @classmethod
    def tearDownClass(cls):
        Product.objects.all().delete()
        super(IShopViewsTestCase, cls).tearDownClass()


    @classmethod
    def create_products(cls):
        for i in range(0, 2):
            title = 'Product %s' % i
            product = cls.create_product(title)


    @classmethod
    def create_product(cls, title):
        p = Product(
            title=title,
            price=1.00,
            slug=slugify(title)
        )
        p.save()
        return p


    @property
    def testapp_shop_class(self):
        from cubane.testapp.views import TestAppShop
        return TestAppShop


class IShopViewsShopTestCase(IShopViewsTestCase):
    def test_get_shop_should_return_shop_class_instance(self):
        shop = get_shop()
        self.assertIsInstance(shop, self.testapp_shop_class)


    def test_get_shop_should_return_new_instances_every_time(self):
        shop = get_shop()
        self.assertNotEqual(shop, get_shop())


    @override_settings(SHOP=None)
    def test_get_shop_should_raise_if_not_configured(self):
        shop_views.SHOP_CLASS=None
        with self.assertRaises(ValueError):
            get_shop()


    @override_settings(SHOP='does-not-exist-class-name')
    def test_get_shop_should_raise_if_class_does_not_exist(self):
        shop_views.SHOP_CLASS=None
        with self.assertRaises(ImportError):
            get_shop()
