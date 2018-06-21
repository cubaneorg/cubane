# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.file import folder_is_empty
from cubane.fonts.fontcache import FontCache
from cubane.fonts.declaration import FontDeclaration
from cubane.fonts.backends import GoogleFontsBackend
from mock import MagicMock
import cubane.testapp as testapp
import os


class FontCacheGetUniqueFontNameTestCase(CubaneTestCase):
    """
    cubane.fonts.fontcache.FontCache.get_unique_font_name()
    """
    def test_should_return_slugified_font_name(self):
        self.assertEqual('open-sans', FontCache.get_unique_font_name('Open Sans'))


class FontCacheGetFontCSSUrlTestCase(CubaneTestCase):
    """
    cubane.fonts.fontcache.FontCache.get_font_css_url()
    """
    def test_should_return_media_url_path_to_font_declaration_css_file(self):
        self.assertEqual(
            '/media/fonts/open-sans/open-sans.css',
            FontCache.get_font_css_url('Open Sans')
        )


class FontCacheGetFontDeclarationTestCase(CubaneTestCase):
    """
    cubane.fonts.fontcache.FontCache.get_font_declaration()
    """
    def test_should_patrse_font_declaration(self):
        d = FontCache.get_font_declaration('Open Sans:300,300i')
        self.assertIsInstance(d, FontDeclaration)
        self.assertEqual('Open Sans', d.font_name)
        self.assertEqual(['300', '300i'], d.variants_display)


class FontCacheTestCaseBase(CubaneTestCase):
    def setUp(self):
        self.fontcache = FontCache()


@CubaneTestCase.complex()
class FontCacheClearTestCase(FontCacheTestCaseBase):
    """
    cubane.fonts.fontcache.FontCache.clear()
    """
    def test_should_remove_font_cache_folder_content_if_not_empty(self):
        path = os.path.join(settings.CUBANE_FONT_ROOT, 'test')
        os.mkdir(path)
        try:
            self.fontcache.clear()
            self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))
        finally:
            if os.path.isdir(path):
                os.rmdir(path)


    def test_should_leave_font_cache_folder_empty_if_already_empty(self):
        self.fontcache.clear()
        self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))
        self.fontcache.clear()
        self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))


@CubaneTestCase.complex()
class FontCacheUpdateTestCase(FontCacheTestCaseBase):
    """
    cubane.fonts.fontcache.FontCache.update()
    """
    def test_should_download_fonts(self):
        resources = testapp.RESOURCES
        try:
            # 100 does not exist, the font system should ignore it
            testapp.RESOURCES = [
                'font|Open Sans:100,300,300i,400,400i'
            ]

            # clear cache first
            self.fontcache.clear()
            self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))

            # remove main font cache folder, the system should automatically
            # re-create such folder when updating the font cache
            if os.path.isdir(settings.CUBANE_FONT_ROOT):
                os.rmdir(settings.CUBANE_FONT_ROOT)

            # update cache system
            self.fontcache.update()

            # folder should contain data
            self.assertFalse(folder_is_empty(settings.CUBANE_FONT_ROOT))

            # folder should contain fonts used, but only those that actually
            # exist
            fontbase = os.path.join(settings.CUBANE_FONT_ROOT, 'open-sans')
            version = 'v15'
            self.assertTrue(os.path.isdir(fontbase))
            for weight in ['300', '400']:
                for style in ['normal', 'italic']:
                    for typ in ['woff2', 'woff']:
                        filename = 'open-sans-%s-%s-%s.%s' % (
                            version,
                            weight,
                            style,
                            typ
                        )
                        path = os.path.join(fontbase, filename)
                        self.assertTrue(os.path.isfile(path), 'expected font file: %s. File does not exist.' % filename)
        finally:
            testapp.RESOURCES = resources


    def test_should_ignore_empty_list_for_font_declarations(self):
        self.fontcache.clear()
        self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))

        def empty_font_declarations():
            return []
        self.fontcache.get_used_font_declarations = empty_font_declarations

        self.fontcache.update()
        self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))


    @override_settings(CUBANE_FONT_BACKENDS=None)
    def test_should_raise_exception_if_no_backends_are_available(self):
        with self.assertRaisesRegexp(ValueError, 'Unable to update fonts because no font backend is available'):
            self.fontcache.update()


    @override_settings(DEBUG=True)
    def test_should_raise_exception_if_font_is_not_found_in_debug(self):
        def mocked_font_declarations():
            return [FontDeclaration.parse('Foo:300')]
        self.fontcache.get_used_font_declarations = mocked_font_declarations

        with self.assertRaisesRegexp(ValueError, 'The font \'Foo\' could not be found'):
            self.fontcache.update()


    def test_should_not_download_cached_font(self):
        # mock font download handler
        self.fontcache._cache_font = MagicMock()

        # mock font declarations
        def mocked_font_declarations():
            return [FontDeclaration.parse('Foo:300')]
        self.fontcache.get_used_font_declarations = mocked_font_declarations

        # create font folder to cause the font to be already cached
        path = os.path.join(settings.CUBANE_FONT_ROOT, 'foo')
        os.mkdir(path)
        try:
            # after updating the font cache, the font has not been processed
            self.fontcache.update()
            self.assertFalse(self.fontcache._cache_font.called)
        finally:
            os.rmdir(path)


    def test_should_not_create_font_folder_if_download_failed(self):
        resources = testapp.RESOURCES
        try:
            # 100 does not exist
            testapp.RESOURCES = [
                'font|Open Sans:100'
            ]

            # clear cache first
            self.fontcache.clear()
            self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))

            # update cache system
            self.fontcache.update()

            # folder should still be empty, since we could not download
            # any assets...
            self.assertTrue(folder_is_empty(settings.CUBANE_FONT_ROOT))
        finally:
            testapp.RESOURCES = resources


class FontCacheGetUsedFontDeclarationsTestCase(FontCacheTestCaseBase):
    """
    cubane.fonts.fontcache.FontCache.get_used_font_declarations()
    """
    def test_should_return_unique_list_of_declared_font_names_sorted_by_name(self):
        resources = testapp.RESOURCES
        try:
            testapp.RESOURCES = [
                'font|Ubuntu',
                'font|Open Sans',
                'font|Abel',
                'font|Abel',
            ]
            declarations = self.fontcache.get_used_font_declarations()
            names = [d.font_name for d in declarations]
            self.assertEqual(['Abel', 'Open Sans', 'Ubuntu'], names)
        finally:
            testapp.RESOURCES = resources


class FontCacheIsFontCachedTestCase(FontCacheTestCaseBase):
    """
    cubane.fonts.fontcache.FontCache.is_font_cached()
    """
    def test_should_return_true_if_font_cache_folder_exists(self):
        path = os.path.join(settings.CUBANE_FONT_ROOT, 'foo')
        os.mkdir(path)
        try:
            self.assertTrue(self.fontcache.is_font_cached('Foo'))
        finally:
            os.rmdir(path)


    def test_should_return_false_if_font_cache_folder_does_not_exist(self):
        path = os.path.join(settings.CUBANE_FONT_ROOT, 'foo')
        if os.path.isdir(path):
            os.rmdir(path)

        self.assertFalse(self.fontcache.is_font_cached('Foo'))


class FontCacheGetBackendsTestCase(CubaneTestCase):
    """
    cubane.fonts.fontcache.FontCache.get_backends()
    """
    def test_should_return_list_of_installed_backends(self):
        fontcache = FontCache()
        self.assertIn(GoogleFontsBackend, [backend.__class__ for backend in fontcache.get_backends()])


    @override_settings(CUBANE_FONT_BACKENDS=None)
    def test_should_ignore_not_a_list(self):
        fontcache = FontCache()
        self.assertEqual([], fontcache.get_backends())