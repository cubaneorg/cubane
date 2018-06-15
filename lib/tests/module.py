# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.module import module_exists
from cubane.lib.module import get_module_by_name
from cubane.lib.module import get_class_from_string
from cubane.testapp.models import Enquiry


class CubaneLibModuleExistsTestCase(CubaneTestCase):
    """
    cubane.lib.module.module_exists()
    """
    def test_should_return_true_if_module_exists(self):
        self.assertTrue(module_exists('cubane'))


    def test_should_return_false_if_module_exists(self):
        self.assertFalse(module_exists('module-does-not-exist'))


class CubaneLibModuleGetModuleByNameTestCase(CubaneTestCase):
    """
    cubane.lib.module.get_module_by_name()
    """
    def test_should_return_mobule_if_exists(self):
        m = get_module_by_name('cubane')
        self.assertIsNotNone(m)
        self.assertEqual(m.__class__.__name__, 'module')


    def test_should_raise_if_module_does_not_exist(self):
        with self.assertRaises(ImportError):
            get_module_by_name('module-does-not-exist')


class CubaneLibModuleGetClassFromStringTestCase(CubaneTestCase):
    """
    cubane.lib.module.get_class_from_string()
    """
    def test_should_return_class_that_exists(self):
        self.assertEqual(get_class_from_string('cubane.testapp.models.Enquiry'), Enquiry)


    def test_should_raise_if_not_exists_in_module(self):
        with self.assertRaises(AttributeError):
            get_class_from_string('cubane.testapp.models.DoesNotExist')


    def test_should_raise_if_model_does_not_exist(self):
        with self.assertRaises(ImportError):
            get_class_from_string('cubane.testapp.does-not-exists.DoesNotExist')


    def test_should_raise_if_empty_string(self):
        with self.assertRaises(ImportError):
            get_class_from_string('')


    def test_should_raise_if_none(self):
        with self.assertRaises(ImportError):
            get_class_from_string(None)