# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.media.models import Media
from cubane.cms.cache import Cache, CacheContext
from cubane.testapp.models import CustomPage, TestModel, Settings
from cubane.lib.deploy import save_deploy_timestamp
from cubane.lib.deploy import delete_deploy_timestamp
from cubane.lib.file import file_put_contents
from cubane.lib.file import file_get_contents
from cubane.lib.file import file_set_mtime
from datetime import datetime
from freezegun import freeze_time
import os
import tempfile
import stat
import time
import mock


class CMSCacheContextTestCase(CubaneTestCase):
    def test_should_create_empty_cache(self):
        context = CacheContext()
        self.assertEqual({}, context._cache)


    def test_should_cache_argument(self):
        context = CacheContext()

        # first time f is called to produce the value for 'foo'
        f = mock.Mock(return_value='bar')
        self.assertEqual('bar', context.cached('foo', f))
        self.assertTrue(f.called)

        # second time we receive the value from cache
        f = mock.Mock(return_value='bar')
        self.assertEqual('bar', context.cached('foo', f))
        self.assertFalse(f.called)


class CMSCacheInvalidateTestCase(CubaneTestCase):
    def setUp(self):
        self.cache = Cache()
        self.cache.clear()
        delete_deploy_timestamp()


    def test_context_should_return_cache_context_cached(self):
        context = self.cache.context
        self.assertIsInstance(context, CacheContext)

        # subsequent call should return same instance
        self.assertEqual(context, self.cache.context)


    def test_index_filename_should_return_full_path_to_index_file(self):
        path = os.path.join(settings.CACHE_ROOT, self.cache.INDEX_FILENAME)
        self.assertEqual(path, self.cache.index_filename)


    def test_size_should_return_size_of_cache_in_bytes(self):
        self.assertEqual(0, self.cache.size)
        self.cache.add('test1.html', None, None, '<h1>Hello Foo</h1>', minify_html=False)
        self.cache.add('test2.html', None, None, '<h1>Hello Bar</h1>', minify_html=False)
        self.assertEqual(36, self.cache.size)


    def test_items_should_return_count_of_cached_files(self):
        self.assertEqual(0, self.cache.items)
        self.cache.add('test1.html', None, None, '<h1>Hello Foo</h1>', minify_html=False)
        self.cache.add('test2.html', None, None, '<h1>Hello Bar</h1>', minify_html=False)
        self.assertEqual(2, self.cache.items)


    def test_cache_should_generate_cache_index_file_sorted_by_path_length(self):
        self.assertFalse(os.path.isfile(self.cache.index_filename))
        self.cache.add('test1.html', None, None, '<h1>Hello Foo</h1>', minify_html=False)
        self.cache.add('foo/test2.html', None, None, '<h1>Hello Bar</h1>', minify_html=False)
        self.cache.write()
        self.assertTrue(os.path.isfile(self.cache.index_filename))
        self.assertEqual(['foo/test2.html', 'test1.html'], self.cache.get_index())
        self.cache.clear_index()


    def test_clear_index_should_ignore_if_index_does_not_exist(self):
        self.cache.clear_index()
        self.assertTrue(self.cache.publish_required())


    def test_clear_index_should_remove_index_file(self):
        self.cache.add('test1.html', None, None, '<h1>Hello Foo</h1>', minify_html=False)
        self.cache.add('foo/test2.html', None, None, '<h1>Hello Bar</h1>', minify_html=False)
        self.cache.write()
        self.assertTrue(os.path.isfile(self.cache.index_filename))
        self.cache.clear_index()
        self.assertFalse(os.path.isfile(self.cache.index_filename))


    def test_get_mtime_should_return_last_mod_time_of_file(self):
        base = tempfile.gettempdir()
        filename = os.path.join(base, 'foo')
        file_put_contents(filename, 'test')
        try:
            ts = datetime(2016, 11, 18)
            file_set_mtime(filename, ts)
            self.assertEqual(ts, self.cache.get_mtime(filename))
        finally:
            if os.path.isfile(filename):
                os.remove(filename)


    def test_get_mtime_should_return_last_mod_time_of_invalidated_file(self):
        base = tempfile.gettempdir()
        filename = os.path.join(base, 'foo')
        invalidated_filename = os.path.join(base, '.foo')
        file_put_contents(invalidated_filename, 'test')
        try:
            self.assertFalse(os.path.isfile(filename))

            ts = datetime(2016, 11, 18)
            file_set_mtime(invalidated_filename, ts)
            self.assertEqual(ts, self.cache.get_mtime(filename))
        finally:
            if os.path.isfile(invalidated_filename):
                os.remove(invalidated_filename)


    def test_add_file_to_cache_should_write_file_to_cache_folder_while_clear_cache_should_remove_cached_files(self):
        # build cache
        self.cache.add('index.html', None, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.add('bar/index.html', None, None, '<h1>Bar</h1>', minify_html=False)
        self.cache.add('foo/bar/index.html', None, None, '<h1>Foo Bar</h1>', minify_html=False)
        self.cache.write()
        self.assertFileContent(os.path.join(settings.CACHE_ROOT, 'index.html'), '<h1>Foo</h1>')
        self.assertFileContent(os.path.join(settings.CACHE_ROOT, 'bar', 'index.html'), '<h1>Bar</h1>')
        self.assertFileContent(os.path.join(settings.CACHE_ROOT, 'foo', 'bar', 'index.html'), '<h1>Foo Bar</h1>')
        self.assertFalse(self.cache.publish_required())

        # clear
        self.cache.clear()

        # files removed
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'index.html')))
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'bar', 'index.html')))
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'foo', 'bar', 'index.html')))

        # intermediate directories removed
        self.assertFalse(os.path.isdir(os.path.join(settings.CACHE_ROOT, 'foo', 'bar')))
        self.assertFalse(os.path.isdir(os.path.join(settings.CACHE_ROOT, 'bar')))

        # index file removed
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, self.cache.index_filename)))


    def test_invalidate_should_rename_cached_files_and_clear_cache(self):
        # build cache
        self.cache.add('foo.html', None, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.add('bar.html', None, None, '<h1>Bar</h1>', minify_html=False)
        self.cache.add('test/index.html', None, None, '<h1>Test</h1>', minify_html=False)
        self.cache.write()

        # invalidate
        self.cache.invalidate()

        # original files are gone
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'foo.html')))
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'bar.html')))
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'test', 'index.html')))

        # files renamed (. prefix)
        self.assertEqual('<h1>Foo</h1>', file_get_contents(os.path.join(settings.CACHE_ROOT, '.foo.html')))
        self.assertEqual('<h1>Bar</h1>', file_get_contents(os.path.join(settings.CACHE_ROOT, '.bar.html')))
        self.assertEqual('<h1>Test</h1>', file_get_contents(os.path.join(settings.CACHE_ROOT, 'test', '.index.html')))

        # index file removed
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, self.cache.index_filename)))


    def test_add_file_to_cache_should_set_last_modification_timestamp(self):
        # build cache
        lastmod = datetime(2016, 6, 18, 16, 55, 23)
        self.cache.add('index.html', lastmod, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.write()

        # validate last-mod timestamp
        self.assertEqual(
            lastmod,
            self._get_cache_mtime('index.html')
        )


    def test_add_file_to_cache_should_remove_invalidated_content_version_if_exists(self):
        # build cache
        lastmod = datetime(2016, 6, 18, 16, 55, 23)
        self.cache.add('index.html', lastmod, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.write()

        # invalidate
        self.cache.invalidate()
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'index.html')))
        self.assertEqual('<h1>Foo</h1>', file_get_contents(os.path.join(settings.CACHE_ROOT, '.index.html')))

        # add updated content with a newer timestamp again (changed)
        new_lastmod = datetime(2016, 6, 18, 17, 55, 23)
        self.cache = Cache()
        self.cache.add('index.html', new_lastmod, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.write()

        # invalidated version should have been removed
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, '.index.html')))
        self.assertEqual('<h1>Foo</h1>', file_get_contents(os.path.join(settings.CACHE_ROOT, 'index.html')))
        self.assertEqual(new_lastmod, self._get_cache_mtime('index.html'))


    def test_add_file_to_cache_should_rename_invalidated_content_if_not_changed(self):
        # build cache
        lastmod = datetime(2016, 6, 18, 16, 55, 23)
        self.cache.add('index.html', lastmod, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.write()

        # invalidate
        self.cache.invalidate()
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'index.html')))
        self.assertEqual('<h1>Foo</h1>', file_get_contents(os.path.join(settings.CACHE_ROOT, '.index.html')))

        # add same content with the same timestamp again (not changed)
        self.cache = Cache()
        self.cache.add('index.html', lastmod, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.write()

        # invalidated version should have been renamed
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, '.index.html')))
        self.assertEqual('<h1>Foo</h1>', file_get_contents(os.path.join(settings.CACHE_ROOT, 'index.html')))
        self.assertEqual(lastmod, self._get_cache_mtime('index.html'))


    @freeze_time('2016-11-18')
    def test_add_file_to_cache_should_assume_current_timestamp_if_no_lastmod_given(self):
        self.cache.add('index.html', None, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.write()
        self.assertEqual(datetime(2016, 11, 18), self._get_cache_mtime('index.html'))


    def test_set_index_should_ignore_file_access_errors(self):
        self.cache.clear_index()

        os.mkdir(self.cache.index_filename)
        self.cache.set_index(['index.html'])

        self.assertTrue(os.path.isdir(os.path.join(settings.CACHE_ROOT, self.cache.index_filename)))
        os.rmdir(self.cache.index_filename)


    def test_save_cms_model_should_invalidate_cache(self):
        cache = Cache()

        for model in [CustomPage, TestModel, Media, Settings]:
            cache.set_index([])
            self.assertFalse(self.cache.publish_required())

            x = model()
            x.save()
            self.assertTrue(self.cache.publish_required())


    def test_delete_cms_model_should_invalidate_cache(self):
        cache = Cache()

        for model in [CustomPage, TestModel, Media, Settings]:
            x = model()
            x.save()

            cache.set_index([])
            self.assertFalse(self.cache.publish_required())

            x.delete()
            self.assertTrue(self.cache.publish_required(), 'Deleting instance of %s did not invalidate cache.' % model)


    def test_should_minify_html_content(self):
        self.cache.add('index.html', None, None, '<h1>Foo</h1>    <p>Test</p>', minify_html=True)
        self.cache.write()
        self.assertFileContent(
            os.path.join(settings.CACHE_ROOT, 'index.html'),
            '<html><head></head><body><h1>Foo</h1><p>Test</p></body></html>'
        )


    def test_should_not_add_end_tag_to_source_or_self_closing_for_minify_html_content(self):
        self.cache.add('index.html', None, None, '<source src="https://video.m4v" type="video/m4v">', minify_html=True)
        self.cache.write()
        self.assertFileContent(
            os.path.join(settings.CACHE_ROOT, 'index.html'),
            '<html><head></head><body><source src="https://video.m4v" type="video/m4v"></body></html>',
            '<html><head></head><body><source src="https://video.m4v" type="video/m4v"/></body></html>'
        )


    @mock.patch('cubane.cms.cache.html_minify')
    def test_should_ignore_error_minifying_content(self, html_minify):
        html_minify.side_effect = Exception('Boom!')
        self.cache.add('index.html', None, None, '<h1>Foo</h1>    <p>Test</p>', minify_html=True)
        self.cache.write()
        self.assertFileContent(
            os.path.join(settings.CACHE_ROOT, 'index.html'),
            '<h1>Foo</h1>    <p>Test</p>'
        )


    def test_cleanup_should_remove_all_files_and_folders_that_are_not_within_the_cache(self):
        # create cache
        self.cache.add('index.html', None, None, '<h1>Foo</h1>', minify_html=False)
        self.cache.write()

        # create content the cache system is not aware of
        file_put_contents(os.path.join(settings.CACHE_ROOT, 'foo.html'), 'Foo')
        os.mkdir(os.path.join(settings.CACHE_ROOT, 'test'))
        os.mkdir(os.path.join(settings.CACHE_ROOT, 'test', 'foo'))
        file_put_contents(os.path.join(settings.CACHE_ROOT, 'test', 'bar.html'), 'Bar')

        # cleanup cache content
        self.cache.cleanup()

        # except for the cache content, everything else should be gone
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'foo.html')))
        self.assertFalse(os.path.isfile(os.path.join(settings.CACHE_ROOT, 'test', 'bar.html')))
        self.assertFalse(os.path.isdir(os.path.join(settings.CACHE_ROOT, 'test')))
        self.assertFalse(os.path.isdir(os.path.join(settings.CACHE_ROOT, 'test', 'foo')))


    def _get_cache_mtime(self, filename):
        """
        Return the last modification timestamp for the given cache file as
        datetime.
        """
        return datetime.fromtimestamp(
            os.path.getmtime(os.path.join(settings.CACHE_ROOT, filename))
        )
