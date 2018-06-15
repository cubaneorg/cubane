# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.libjson import to_json
from cubane.lib.libjson import decode_json
from cubane.lib.libjson import modellist_to_json
from cubane.lib.libjson import modellist_to_json_response
from cubane.lib.libjson import to_json_response
from cubane.lib.libjson import jsonp_response
from cubane.models import Country
from cubane.testapp.models import TestModel, TestModelWithJsonFields
from datetime import datetime, date, timedelta
from decimal import Decimal
import re


class CustomDataType(object):
    pass


class LibJsonTestCase(CubaneTestCase):
    def _create_object(self, _id, title, save=True, model=TestModel):
        m = model()
        m.id = _id
        m.title = title
        if save:
            m.save()
        return m


class LibJsonToJsonTestCase(LibJsonTestCase):
    """
    cubane.lib.libjson.to_json()
    """
    def test_should_encode_compact(self):
        s = to_json({'foo': 'bar'})
        self.assertTrue(len(re.findall(r'[\n\s]', s)) == 0)


    def test_should_encode_human_readable(self):
        s = to_json({'foo': 'bar'}, compact=False)
        self.assertFalse(len(re.findall(r'[\n\s]', s)) == 0)


    def test_encode_none_should_be_null(self):
        s = to_json(None)
        self.assertEqual(s, 'null')


    def test_encode_string_should_be_string(self):
        s = to_json('Foo')
        self.assertEqual(s, '"Foo"')


    def test_encode_int_should_be_number(self):
        s = to_json(34)
        self.assertEqual(s, '34')


    def test_encode_float_should_be_number(self):
        s = to_json(float(34.1))
        self.assertEqual(s, '34.1')


    def test_encode_decimal_should_be_number(self):
        s = to_json(Decimal('34.1'))
        self.assertEqual(s, '34.1')


    def test_encode_datetime_should_be_string_in_correct_datetime_format(self):
        s = to_json(datetime(2041, 5, 3, 14, 16, 55))
        self.assertEqual(s, '"2041-05-03 14:16:55"')


    def test_encode_date_should_be_string_in_correct_date_format(self):
        s = to_json(date(2041, 5, 3))
        self.assertEqual(s, '"2041-05-03"')


    def test_encode_timedelta_should_be_string_in_correct_timedelta_format(self):
        s = to_json(timedelta(days=1))
        self.assertEqual(s, '"1 day, 0:00:00"')


    def test_encode_list_should_be_list(self):
        s = to_json(['a', 'b', 'c'])
        self.assertEqual(s, '["a","b","c"]')


    def test_encode_dict_should_be_object_literal(self):
        s = to_json({'a': 'X', 'b': 'Y'})
        self.assertEqual(s, '{"a":"X","b":"Y"}')


    def test_encode_country_instance_should_encode_country_properties(self):
        s = to_json(Country.objects.get(iso='GB'))
        self.assertEqual(
            '{"calling_code":"44","flag_state":false,"landlocked":false,"name":"UNITED KINGDOM","printable_name":"United Kingdom","numcode":826,"iso3":"GBR","iso":"GB"}',
            s
        )


    def test_encode_model_instance_should_be_object_literal(self):
        m = self._create_object(123, 'Foo', save=False)
        s = to_json(m)
        self.assertEqual(s,
            '{"updated_by":null,"seq":0,"title":"Foo","text":null,"image":null,"created_by":null,' + \
            '"deleted_on":null,"created_on":null,"updated_on":null,' + \
            '"deleted_by":null,"id":123}'
        )


    def test_encode_model_instance_with_fields_should_only_encode_given_fields(self):
        m = self._create_object(123, 'Foo', save=False)
        s = to_json(m, fields=['id', 'title'])
        self.assertEqual(s, '{"id":123,"title":"Foo"}')


    def test_encode_queryset_should_be_list_of_object_literals(self):
        m1 = self._create_object(1, 'Foo')
        m2 = self._create_object(2, 'Bar')

        m = TestModel.objects.order_by('id')
        s = to_json(m, fields=['id', 'title'])
        self.assertEqual(s, '[{"id":1,"title":"Foo"},{"id":2,"title":"Bar"}]')

        m1.delete()
        m2.delete()


    def test_encode_list_of_models_should_be_list_of_object_literals(self):
        m1 = self._create_object(1, 'Foo')
        m2 = self._create_object(2, 'Bar')

        m = list(TestModel.objects.order_by('id'))
        s = to_json(m, fields=['id', 'title'])
        self.assertEqual(s, '[{"id":1,"title":"Foo"},{"id":2,"title":"Bar"}]')

        m1.delete()
        m2.delete()


    def test_encode_raw_queryset_should_be_list_of_object_literals(self):
        m1 = self._create_object(1, 'Foo')
        m2 = self._create_object(2, 'Bar')

        m = TestModel.objects.raw('select * from testapp_testmodel')
        s = to_json(m, fields=['id', 'title'])
        self.assertEqual(s, '[{"id":1,"title":"Foo"},{"id":2,"title":"Bar"}]')

        m1.delete()
        m2.delete()


    def test_encode_model_getter(self):
        m = self._create_object(1, 'foo')
        s = to_json(m, fields=['id', 'get_uppercase_title()'])
        self.assertEqual(s, '{"id":1,"get_uppercase_title()":"FOO"}')


    def test_encode_model_attribute_path(self):
        m = self._create_object(1, 'foo')
        s = to_json(m, fields=['id', '_meta.verbose_name'])
        self.assertEqual(s, '{"_meta.verbose_name":"Test Model","id":1}')


    def test_encode_model_with_get_json_fieldnames(self):
        m = self._create_object(1, 'Foo', model=TestModelWithJsonFields)
        s = to_json(m)
        self.assertEqual(s, '{"id":1,"title":"Foo"}')


    def test_encode_model_rewrite_attribute_names(self):
        m = self._create_object(1, 'Foo')
        s = to_json(m, fields={'id':'identifier', 'title': 'name'})
        self.assertEqual(s, '{"identifier":1,"name":"Foo"}')


    def test_encode_model_with_incorrect_fields(self):
        m = self._create_object(1, 'Foo')
        s = to_json(m, fields='bar')
        self.assertEqual(s, '{}')


    def test_encode_model_with_model_as_member(self):
        m = self._create_object(1, 'Foo')
        s = to_json(m, fields=['id', 'parent_model', 'title'])
        self.assertEqual(s, '{"parent_model":{"updated_by":null,"seq":0,"title":"Bar","text":null,"image":null,"created_by":null,"deleted_on":null,"created_on":null,"updated_on":null,"deleted_by":null,"id":null},"id":1,"title":"Foo"}')


    def test_encode_custom_datatype_fallback(self):
        with self.assertRaises(TypeError):
            to_json(CustomDataType())


class LibJsonDecodeJsonTestCase(LibJsonTestCase):
    """
    cubane.lib.libjson.decode_json()
    """
    def test_should_decode_null(self):
        self.assertEqual(decode_json('null'), None)


    def test_should_decode_string(self):
        self.assertEqual(decode_json('"foo"'), 'foo')


    def test_should_decode_int(self):
        self.assertEqual(decode_json('34'), 34)


    def test_should_decode_float(self):
        self.assertEqual(decode_json('34.1'), Decimal('34.1'))


    def test_should_decode_datetime_as_string(self):
        self.assertEqual(
            decode_json('"2041-05-03 14:16:55"'),
            '2041-05-03 14:16:55'
        )


    def test_should_decode_list(self):
        self.assertEqual(decode_json('["a","b","c"]'), ['a', 'b', 'c'])


    def test_should_decode_object_literal_as_dict(self):
        self.assertEqual(decode_json('{"a":"X","b":"Y"}'), {'a': 'X', 'b': 'Y'})


class LibJsonModellistToJsonTestCase(LibJsonTestCase):
    """
    cubane.lib.libjson.modellist_to_json()
    """
    def test_should_encode_list_of_models(self):
        m1 = self._create_object(1, 'Foo')
        m2 = self._create_object(2, 'Bar')

        m = TestModel.objects.order_by('id')
        s = modellist_to_json(m, fields=['id', 'title'])
        self.assertEqual(s, '[{"id":1,"title":"Foo"},{"id":2,"title":"Bar"}]')

        m1.delete()
        m2.delete()


class LibJsonModellistToJsonResponseTestCase(LibJsonTestCase):
    """
    cubane.lib.libjson.modellist_to_json_response()
    """
    def test_should_return_http_response_with_content_type_javascript(self):
        m1 = self._create_object(1, 'Foo')
        m2 = self._create_object(2, 'Bar')

        m = TestModel.objects.order_by('id')
        r = modellist_to_json_response(m, fields=['id', 'title'])

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/javascript')
        self.assertEqual(
            r.content,
            '[{"id":1,"title":"Foo"},{"id":2,"title":"Bar"}]'
        )


class LibJsonToJsonResponseTestCase(LibJsonTestCase):
    """
    cubane.lib.libjson.to_json_response()
    """
    def test_should_return_json_response_with_content_type_javascript(self):
        r = to_json_response({'foo': 'bar'})
        self.assertEqual(200, r.status_code)
        self.assertEqual('text/javascript', r['Content-Type'])
        self.assertEqual('{"foo":"bar"}', r.content)


    def test_should_support_deprecated_argument_mimetype(self):
        r = to_json_response({'foo': 'bar'}, content_type='a', mimetype='b')
        self.assertEqual('b', r['Content-Type'])


class LibJsonJsonpResponseTestCase(LibJsonTestCase):
    """
    cubane.lib.libjson.jsonp_response()
    """
    def test_should_return_jsonp_response_with_content_type_javascript(self):
        r = jsonp_response({'foo': 'bar'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/javascript')
        self.assertEqual(r.content, 'jsonp({"foo":"bar"});')