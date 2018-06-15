# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.attribute_tags import (
    has_attr,
    get_dict_item,
    get_class
)


class ModelMock(object):
    def __init__(self, value=None):
        self.value = value


class AttributeTagsHasAttrTestCase(CubaneTestCase):
    """
    cubane.templatetags.attribute_tags.has_attr()
    """
    def setUp(self):
        self.model = ModelMock('5')


    def test_should_return_true_if_attribute_exists(self):
        self.assertEqual(has_attr(self.model, 'value'), True)


    def test_should_return_false_if_attribute_does_not_exists(self):
        self.assertEqual(has_attr(self.model, 'non_value'), False)


class AttributeTagsGetDictItemTestCase(CubaneTestCase):
    """
    cubane.templatetags.attribute_tags.get_dict_item()
    """
    def test_should_return_value_for_key_if_exists(self):
        self.assertEqual(get_dict_item({'name': 'John'}, 'name'), 'John')


    def test_should_return_none_if_key_does_not_exist(self):
        self.assertEqual(get_dict_item({}, 'name'), None)


class AttributeTagsGetClassTestCase(CubaneTestCase):
    """
    cubane.templatetags.attribute_tags.get_class()
    """
    def test_should_class_name_of_object_instnce(self):
        self.assertEqual(get_class(ModelMock()), 'ModelMock')