# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from django.test.utils import override_settings
from django.core.urlresolvers import NoReverseMatch
from django.urls.resolvers import RegexURLResolver
from cubane.lib.url import *
from mock import patch


class LibNormaliseSlugTestCase(CubaneTestCase):
    """
    cubane.lib.url.normalise_slug()
    """
    def test_should_return_slug_without_leading_and_trailing_characters(self):
        self.assertEqual(normalise_slug('/slug/'), 'slug')


    def test_should_keep_intermediate_slashes(self):
        self.assertEqual(normalise_slug('/foo/bar/'), 'foo/bar')


    def test_single_slash_should_not_be_trimmed(self):
        self.assertEqual(normalise_slug('/'), '/')


    def test_double_slash_should_not_be_trimmed(self):
        self.assertEqual(normalise_slug('//'), '//')


    def test_multiple_slashes_should_not_be_trimmed(self):
        self.assertEqual(normalise_slug('//////'), '//////')


class LibURLAppendSlashTestCase(CubaneTestCase):
    """
    cubane.lib.url.url_append_slash()
    """
    def test_url_with_GET_args_should_append_slash_before_question_mark(self):
        self.assertEqual(url_append_slash('/slug?arg=value'), '/slug/?arg=value')


    def test_url_with_trailing_slash_should_not_append_slash(self):
        self.assertEqual(url_append_slash('/slug/?arg=value'), '/slug/?arg=value')


    def test_url_without_GET_args_should_append_slash(self):
        self.assertEqual(url_append_slash('/slug'), '/slug/')


class LibURLJoinTestCase(CubaneTestCase):
    """
    cubane.lib.url.url_join()
    """
    def test_url_should_start_with_slash(self):
        self.assertEqual(url_join('test', 'test'), '/test/test')


    def test_should_return_query_string(self):
        self.assertEqual(url_join('?param=value', 'test', 'test'), '/test/test?param=value')


class LibDomainWithoutPortTestCase(CubaneTestCase):
    """
    cubane.lib.url.domain_without_port()
    """
    def test_domain_none_should_return_none(self):
        self.assertIsNone(domain_without_port(None))


    def test_domain_without_port_should_return_domain(self):
        self.assertEqual(domain_without_port('test.com'), 'test.com')


    def test_domain_with_port_should_return_domain(self):
        self.assertEqual(domain_without_port('test.com:80'), 'test.com')


class LibURLWithoutPortTestCase(CubaneTestCase):
    """
    cubane.lib.url.url_without_port()
    """
    def test_url_should_return_url_without_port(self):
        self.assertEqual(url_without_port('//www.test.com:80/test'), '//www.test.com/test')


class LibGetURLPatterns(CubaneTestCase):
    """
    cubane.lib.url.get_url_patterns()
    """
    def test_should_return_reverse_lookup(self):
        from cubane.testapp.urls import urlpatterns

        pattern = None
        for p in urlpatterns:
            if isinstance(p, RegexURLResolver):
                if p.regex.pattern == '^dummy/':
                    pattern = p
                    break

        self.assertIsNotNone(pattern, 'Pattern /dummy not found in testapp.')
        self.assertEqual({
            'dummy.create': '/dummy/create/',
            'dummy.preview': '/dummy/preview/',
            'dummy.edit': '/dummy/edit/',
            'dummy.index': '/dummy/index/'
        }, get_url_patterns([pattern]))


class LibIsExternalUrl(CubaneTestCase):
    """
    cubane.lib.url.is_external_url()
    """
    def test_should_return_false_for_local_path(self):
        self.assertFalse(is_external_url('/foo/'))


    def test_should_return_false_for_path_component(self):
        self.assertFalse(is_external_url('foo'))


    def test_should_return_false_for_full_internal_url(self):
        self.assertFalse(is_external_url('http://%s/foo/' % settings.DOMAIN_NAME))


    def test_should_return_false_for_full_internal_ssl_url(self):
        self.assertFalse(is_external_url('https://%s/foo/' % settings.DOMAIN_NAME))


    def test_should_return_false_for_full_internal_url_with_www(self):
        self.assertFalse(is_external_url('http://www.%s/foo/' % settings.DOMAIN_NAME))


    def test_should_return_false_for_full_internal_ssl_url_with_www(self):
        self.assertFalse(is_external_url('https://www.%s/foo/' % settings.DOMAIN_NAME))


    def test_should_return_false_for_full_internal_url_of_given_domain(self):
        self.assertFalse(is_external_url('http://bar.com/foo/', domain='bar.com'))


    def test_should_return_false_for_full_internal_ssl_url_of_given_domain(self):
        self.assertFalse(is_external_url('https://bar.com/foo/', domain='bar.com'))


    def test_should_return_false_for_url_other_than_http(self):
        self.assertFalse(is_external_url('mailto:jan.kueting@innershed.com'))


    def test_should_return_false_for_inpage_reference(self):
        self.assertFalse(is_external_url('#foo'))


    def test_should_return_false_for_empty_url(self):
        self.assertFalse(is_external_url(''))


    def test_should_return_false_for_none(self):
        self.assertFalse(is_external_url(None))


    def test_should_return_true_for_external_url(self):
        self.assertTrue(is_external_url('http://www.innershed.com'))


class LibMakeAbsoluteURL(CubaneTestCase):
    """
    cubane.lib.url.make_absolute_url()
    """
    def test_should_return_absolute_url(self):
        self.assertEqual(make_absolute_url('/test/'), 'http://www.%s/test/' % settings.DOMAIN_NAME)


    def test_should_prepend_slashes(self):
        self.assertEqual(make_absolute_url('test/'), 'http://www.%s/test/' % settings.DOMAIN_NAME)


    @override_settings(APPEND_SLASH=True)
    def test_should_append_slashes(self):
        self.assertEqual(make_absolute_url('/test'), 'http://www.%s/test/' % settings.DOMAIN_NAME)


    @override_settings(APPEND_SLASH=False)
    def test_should_not_append_slash_if_not_configured(self):
        self.assertEqual(make_absolute_url('/test'), 'http://www.%s/test' % settings.DOMAIN_NAME)


    @override_settings(SSL=True)
    def test_should_use_https_if_configured(self):
        self.assertEqual(make_absolute_url('/test/'), 'https://%s/test/' % settings.DOMAIN_NAME)


    @override_settings(PREPEND_WWW=True)
    def test_should_use_https_if_configured(self):
        self.assertEqual(make_absolute_url('/test/'), 'http://www.%s/test/' % settings.DOMAIN_NAME)


    def test_should_add_slash(self):
        self.assertEqual(make_absolute_url('test/'), 'http://www.%s/test/' % settings.DOMAIN_NAME)


    def test_should_not_add_slash_for_filenames_with_extensions(self):
        self.assertEqual(make_absolute_url('test.xml'), 'http://www.%s/test.xml' % settings.DOMAIN_NAME)
        self.assertEqual(make_absolute_url('test.html'), 'http://www.%s/test.html' % settings.DOMAIN_NAME)


    def test_should_add_domain_to_url(self):
        self.assertEqual(make_absolute_url('/test/', 'test.com'), 'http://www.test.com/test/')


    def test_should_return_https_in_absolute_url(self):
        self.assertEqual(make_absolute_url('/test/', https=True), 'https://www.%s/test/' % settings.DOMAIN_NAME)


    def test_should_ignore_absolute_url(self):
        self.assertEqual(make_absolute_url('http://www.innershed.com/'), 'http://www.innershed.com/')


    def test_should_not_append_slash_to_querystring_but_before(self):
        self.assertEqual(make_absolute_url('/test?test=test', 'test.com'), 'http://www.test.com/test/?test=test')


    def test_should_ignore_appending_slash_if_slash_present_before_querystring(self):
        self.assertEqual(make_absolute_url('/test/?test=test', 'test.com'), 'http://www.test.com/test/?test=test')


    def test_should_append_slash_before_querystring_if_root_element(self):
        self.assertEqual(make_absolute_url('/?test=test', 'test.com'), 'http://www.test.com/?test=test')


    @override_settings(DEBUG=True)
    def test_should_return_path_only_in_debug_mode(self):
        self.assertEqual(make_absolute_url('/test/'), '/test/')


    def test_should_ignore_external_url(self):
        self.assertEqual('http://www.innershed.com/', make_absolute_url('http://www.innershed.com/'))


    def test_should_ignore_external_url_without_ending_slash(self):
        self.assertEqual('http://www.innershed.com', make_absolute_url('http://www.innershed.com'))


    def test_should_return_absolute_url_for_homepage(self):
        self.assertEqual(make_absolute_url('/'), 'http://www.%s/' % settings.DOMAIN_NAME)


    @override_settings(APPEND_SLASH=True)
    def test_should_return_absolute_url_for_homepage_with_append_slash(self):
        self.assertEqual(make_absolute_url('/'), 'http://www.%s/' % settings.DOMAIN_NAME)


    @override_settings(SSL=True)
    def test_should_return_absolute_url_for_homepage_with_ssl(self):
        self.assertEqual(make_absolute_url('/'), 'https://www.%s/' % settings.DOMAIN_NAME)


    @override_settings(PREPEND_WWW=True)
    def test_should_return_absolute_url_for_homepage_with_www(self):
        self.assertEqual(make_absolute_url('/'), 'http://www.%s/' % settings.DOMAIN_NAME)


class LibGetAbsoluteURLTestCase(CubaneTestCase):
    """
    cubane.lib.url.get_absolute_url()
    """
    def test_reverse_name_should_return_absolute_url(self):
        self.assertEqual(
            get_absolute_url('test_get_absolute_url', ['value'], https=True),
            'https://www.%s/test-get-absolute-url/value/' % settings.DOMAIN_NAME
        )


class LibGetCompatibleUrlTestCase(CubaneTestCase):
    """
    cubane.lib.url.get_compatible_url()
    """
    def test_should_return_none_if_url_is_none(self):
        self.assertIsNone(get_compatible_url(None))


    @override_settings(SSL=False)
    def test_should_return_url_as_is_if_ssl_is_not_enabled(self):
        self.assertEqual(
            'http://www.innershed.com',
            get_compatible_url('http://www.innershed.com')
        )


    @override_settings(SSL=True)
    def test_should_return_https_if_ssl_is_enabled(self):
        self.assertEqual(
            'https://www.innershed.com',
            get_compatible_url('http://www.innershed.com')
        )


    @override_settings(SSL=True)
    def test_should_return_url_as_is_if_https_argument_is_false_ignoring_settings(self):
        self.assertEqual(
            'http://www.innershed.com',
            get_compatible_url('http://www.innershed.com', https=False)
        )


    @override_settings(SSL=False)
    def test_should_return_https_if_https_argument_is_true_ignoring_settings(self):
        self.assertEqual(
            'https://www.innershed.com',
            get_compatible_url('http://www.innershed.com', https=True)
        )


    def test_should_trim_url_if_url_has_not_been_changed(self):
        self.assertEqual(
            'http://www.innershed.com',
            get_compatible_url('  http://www.innershed.com  ', https=False)
        )


    def test_should_trim_url_if_url_has_been_changed(self):
        self.assertEqual(
            'https://www.innershed.com',
            get_compatible_url('  http://www.innershed.com  ', https=True)
        )


    def test_should_not_change_protocol_independent_url(self):
        self.assertEqual(
            '//www.innershed.com',
            get_compatible_url('//www.innershed.com', https=True)
        )


class LibURLWithArgTestCase(CubaneTestCase):
    """
    cubane.lib.lurl.url_with_arg()
    """
    def test_url_should_return_url_with_arg(self):
        self.assertEqual(url_with_arg('test.com', 'key', 'value'), 'test.com?key=value')


    def test_url_should_return_url_with_existing_arg(self):
        self.assertEqual(url_with_arg('test.com?foo=bar', 'key', 'value'), 'test.com?foo=bar&key=value')


    def test_url_should_return_replace_existing_arg(self):
        self.assertEqual(url_with_arg('test.com?foo=bar', 'foo', 'foobar'), 'test.com?foo=foobar')


class LibURLWithArgsTestCase(CubaneTestCase):
    """
    cubane.lib.url.url_with_args()
    """
    def test_should_encode_args(self):
        self.assertEqual(url_with_args('test.com', {'k1': 'v1', 'k2': 'v2'}), 'test.com?k2=v2&k1=v1')


    def test_should_ignore_none(self):
        self.assertEqual(url_with_args('test.com', None), 'test.com')


    def test_should_ignore_empty_args(self):
        self.assertEqual(url_with_args('test.com', {}), 'test.com')


    def test_should_overwrite_existing_args(self):
        self.assertEqual(
            url_with_args('test.com?k1=v1&k2=v2', {'k1': '1', 'k2': '2'}),
            'test.com?k2=2&k1=1'
        )


    def test_should_keep_empty_arguments(self):
        self.assertEqual(
            url_with_args('test.com?foo', {'key': 'value'}),
            'test.com?foo=&key=value'
        )


    def test_should_reassamble_all_url_components(self):
        self.assertEqual(
            url_with_args('https://admin:password@www.test.com:8000/bar.html;arg=value?foo=bar#header', {'bar': 'foo'}),
            'https://admin:password@www.test.com:8000/bar.html;arg=value?foo=bar&bar=foo#header'
        )


class LibNoCacheURLTestCase(CubaneTestCase):
    """
    cubane.lib.url.url_without_port()
    """
    def test_url_should_return_timestamp_as_get_param(self):
        self.assertRegexpMatches(no_cache_url('www.test.com'), r'www\.test\.com\?_=\d+')


class LibURLWithHTTPTestCase(CubaneTestCase):
    """
    cubane.lib.url.url_with_http()
    """
    def test_url_without_scheme_should_return_url_with_http(self):
        self.assertEqual(url_with_http('www.test.com'), 'http://www.test.com')


    def test_url_with_http_should_return_url_with_http(self):
        self.assertEqual(url_with_http('http://www.test.com'), 'http://www.test.com')


class LibURLToLegacyUrlTestCase(CubaneTestCase):
    """
    cubane.lib.url.to_legacy_url()
    """
    def test_should_return_none_for_none_argument(self):
        self.assertIsNone(to_legacy_url(None))


    def test_should_return_none_for_none_basestring_argument(self):
        self.assertIsNone(to_legacy_url([]))


    def test_should_return_none_for_empty_string(self):
        self.assertIsNone(to_legacy_url(''))
        self.assertIsNone(to_legacy_url('     '))


    def test_should_return_none_for_data_urls(self):
        self.assertIsNone(to_legacy_url('data:image/gif;base64,R0lGODlhyAAiALMDfD0QAADs='))


    def test_should_remove_domain_name(self):
        self.assertEqual('/foo/', to_legacy_url('www.bar.com/foo/'))
        self.assertEqual('/foo/', to_legacy_url('  www.bar.com/foo/  '))


    def test_should_remove_domain_name_and_port(self):
        self.assertEqual('/foo/', to_legacy_url('www.bar.com:8000/foo/'))
        self.assertEqual('/foo/', to_legacy_url('  www.bar.com:8000/foo/  '))


    def test_should_remove_protocol_and_domain_name(self):
        self.assertEqual('/foo/', to_legacy_url('http://www.bar.com/foo/'))
        self.assertEqual('/foo/', to_legacy_url('  http://www.bar.com/foo/  '))


    def test_should_remove_protocal_domain_name_and_port(self):
        self.assertEqual('/foo/', to_legacy_url('http://www.bar.com:8000/foo/'))
        self.assertEqual('/foo/', to_legacy_url('  http://www.bar.com:8000/foo/  '))


    def test_should_remove_generic_protocol_and_domain_name(self):
        self.assertEqual('/foo/', to_legacy_url('//www.bar.com/foo/'))


    def test_should_remove_generic_protocol_domain_name_and_port(self):
        self.assertEqual('/foo/', to_legacy_url('//www.bar.com:8000/foo/'))


    def test_should_remove_domain_name_from_url_with_empty_path(self):
        self.assertEqual('/', to_legacy_url('www.bar.com'))


    def test_should_remove_protocol_and_domain_name_from_url_with_empty_path(self):
        self.assertEqual('/', to_legacy_url('http://www.bar.com'))


    def test_should_remove_protocol_domain_name_and_port_from_url_with_empty_path(self):
        self.assertEqual('/', to_legacy_url('http://www.bar.com:8000'))


    def test_should_not_require_path_with_ending_slash(self):
        self.assertEqual('/foo', to_legacy_url('http://www.bar.com/foo'))


    def test_should_retain_query_string(self):
        self.assertEqual('/foo/?q=bar&r=1', to_legacy_url('www.bar.com/foo/?q=bar&r=1'))


    def test_should_remove_fragment(self):
        self.assertEqual('/foo/', to_legacy_url('www.bar.com/foo/#bar'))


    def test_should_prepend_missing_slash_for_path(self):
        self.assertEqual('/foo/bar/', to_legacy_url('foo/bar/'))


    def test_should_return_path_if_path_is_given(self):
        self.assertEqual('/', to_legacy_url('/'))
        self.assertEqual('/foo/', to_legacy_url('/foo/'))


class LibURLGetFilepathFromUrlTestCase(CubaneTestCase):
    """
    cubane.lib.url.get_filepath_from_url()
    """
    def test_should_return_relative_filepath_from_reverse_lookup(self):
        self.assertEqual('test-get-absolute-url/foo/index.html', get_filepath_from_url('test_get_absolute_url', args=['foo']))


    @patch('cubane.lib.url.reverse')
    def test_should_append_index_if_url_endswith_slash(self, reverse):
        reverse.return_value = 'foo/'
        self.assertEqual('foo/index.html', get_filepath_from_url('foo'))


    @patch('cubane.lib.url.reverse')
    def test_should_not_append_index_if_url_does_not_endswith_slash(self, reverse):
        reverse.return_value = 'foo.html'
        self.assertEqual('foo.html', get_filepath_from_url('foo'))


    @patch('cubane.lib.url.reverse')
    def test_should_return_relative_path_even_for_absolute_url_path(self, reverse):
        reverse.return_value = '/foo.html'
        self.assertEqual('foo.html', get_filepath_from_url('foo'))


    def test_should_raise_exception_if_reverse_name_is_not_found(self):
        with self.assertRaisesRegexp(NoReverseMatch, 'not found'):
            get_filepath_from_url('does-not-exist')