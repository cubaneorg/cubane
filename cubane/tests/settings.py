# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.settings import (
    SettingsValidationError,
    SettingWrapper,
    validate_settings,
    get_default_templates,
    default_env
)
import os


class SettingsMock(object):
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class SettingsValidateSettingsTestCase(CubaneTestCase):
    """
    cubane.settings.validate_settings()
    """
    def test_should_pass_if_staticfiles_is_not_used(self):
        validate_settings(SettingsMock(INSTALLED_APPS=['cubane']))


    def test_should_pass_if_staticfiles_is_used_without_cubane(self):
        validate_settings(SettingsMock(INSTALLED_APPS=['django.contrib.staticfiles']))


    def test_should_pass_if_staticfiles_is_installed_after_cubane(self):
        validate_settings(SettingsMock(INSTALLED_APPS=['cubane', 'django.contrib.staticfiles']))


    def test_should_fail_if_staticfiles_is_installed_before_cubane(self):
        with self.assertRaisesRegexp(SettingsValidationError, 'The app \'django.contrib.staticfiles\' should appear AFTER \'cubane\''):
            validate_settings(SettingsMock(INSTALLED_APPS=['django.contrib.staticfiles', 'cubane']))


class SettingsGetDefaultTemplatesTestCase(CubaneTestCase):
    """
    cubane.settings.get_default_templates()
    """
    def test_should_construct_template_path_from_base_path(self):
        self.assertIn(
            '/foo/templates',
            get_default_templates('/foo/', debug=False)[0].get('DIRS')
        )


    def test_should_load_default_template_loaders_in_debug_without_caching(self):
        self.assertEqual(
            (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader'
            ),
            get_default_templates('/', debug=True)[0].get('OPTIONS').get('loaders')
        )


    def test_should_load_template_cache_in_production(self):
        self.assertEqual(
            (
                (
                    'django.template.loaders.cached.Loader', (
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader'
                    )
                ),
            ),
            get_default_templates('/', debug=False)[0].get('OPTIONS').get('loaders')
        )


class SettingsSettingWrapperAddTemplateContextProcessorsTestCase(CubaneTestCase):
    """
    cubane.settings.SettingWrapper.add_template_context_processors()
    """
    def setUp(self):
        self.env = SettingWrapper(SettingsMock(TEMPLATES=[
            {
                'OPTIONS': {
                    'context_processors': [
                        'foo',
                    ]
                }
            }
        ]))


    def test_should_add_single_context_processor(self):
        self.env.add_template_context_processors('bar')
        self.assertEqual(
            ['foo', 'bar'],
            self.env.settings.TEMPLATES[0].get('OPTIONS').get('context_processors')
        )


    def test_should_add_multiple_context_processors(self):
        self.env.add_template_context_processors(['bar', 'test'])
        self.assertEqual(
            ['foo', 'bar', 'test'],
            self.env.settings.TEMPLATES[0].get('OPTIONS').get('context_processors')
        )


    def test_should_construct_structure_if_not_present(self):
        self.env = SettingWrapper(SettingsMock(BASE_PATH='/', DEBUG=True))
        self.env.add_template_context_processors('foo')
        self.assertIn('foo', self.env.settings.TEMPLATES[0].get('OPTIONS').get('context_processors'))


    def test_should_create_templates_options_if_not_present(self):
        self.env = SettingWrapper(SettingsMock(TEMPLATES=[{}]))
        self.env.add_template_context_processors('foo')
        self.assertIn('foo', self.env.settings.TEMPLATES[0].get('OPTIONS').get('context_processors'))


    def test_should_create_templates_options_context_processors_if_not_present(self):
        self.env = SettingWrapper(SettingsMock(TEMPLATES=[{'OPTIONS': {}}]))
        self.env.add_template_context_processors('foo')
        self.assertIn('foo', self.env.settings.TEMPLATES[0].get('OPTIONS').get('context_processors'))


class SettingsSettingWrapperAddAppsTestCase(CubaneTestCase):
    """
    cubane.settings.SettingWrapper.add_apps()
    """
    def setUp(self):
        self.env = SettingWrapper(SettingsMock(INSTALLED_APPS=['foo']))


    def test_should_add_single_app(self):
        self.env.add_apps('bar')
        self.assertEqual(['foo', 'bar'], self.env.settings.INSTALLED_APPS)


    def test_should_add_multiple_apps(self):
        self.env.add_apps(['app1', 'app2'])
        self.assertEqual(['foo', 'app1', 'app2'], self.env.settings.INSTALLED_APPS)


    def test_should_add_given_apps_to_settings_without_duplicates(self):
        self.env.add_apps(['foo', 'bar'])
        self.assertEqual(['foo', 'bar'], self.env.settings.INSTALLED_APPS)


    def test_should_add_staticfiles_without_dependencies_cubane(self):
        self.env.add_apps(['django.contrib.staticfiles'])
        self.assertEqual(['foo', 'django.contrib.staticfiles'], self.env.settings.INSTALLED_APPS)


    def test_should_add_cubane_without_staticfiles(self):
        self.env.add_apps(['cubane'])
        self.assertEqual(['foo', 'cubane'], self.env.settings.INSTALLED_APPS)


    def test_should_add_staticfiles_after_cubane(self):
        self.env.add_apps(['cubane', 'django.contrib.staticfiles'])
        self.assertEqual(
            ['foo', 'cubane', 'django.contrib.staticfiles'],
            self.env.settings.INSTALLED_APPS
        )


    def test_should_enforce_staticfiles_loaded_after_cubane(self):
        self.env.add_apps(['django.contrib.staticfiles', 'cubane'])
        self.assertEqual(
            ['foo', 'cubane', 'django.contrib.staticfiles'],
            self.env.settings.INSTALLED_APPS
        )


    def test_should_enfore_staticfiles_loaded_after_cubane_within_existing_list(self):
        self.env = SettingWrapper(SettingsMock(INSTALLED_APPS=['django.contrib.staticfiles', 'cubane']))
        self.env.add_apps()
        self.assertEqual(
            ['cubane', 'django.contrib.staticfiles'],
            self.env.settings.INSTALLED_APPS
        )


class SettingsDefaultEnvTestCase(CubaneTestCase):
    """
    cubane.settings.default_env()
    """
    #
    # DATABASE_NAME
    #
    def test_should_derive_database_name_from_domain_name_automatically(self):
        env = default_env(__name__, 'foo.com', 'root@localhost')
        self.assertEqual('foo_com', env.settings.DATABASE_NAME)


    def test_should_apply_specific_database_name_if_given(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', db_name='bar')
        self.assertEqual('bar', env.settings.DATABASE_NAME)


    #
    # ADMIN
    #
    def test_should_setup_site_admin_with_email(self):
        env = default_env(__name__, 'foo.com', 'root@localhost')
        self.assertEqual(
            (
                ('admin', 'root@localhost'),
            ),
            env.settings.ADMINS
        )


    #
    # MINIFY_CMD_JS
    #
    def test_should_use_older_but_fater_yui_compressor_in_test(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', test=True)
        self.assertIn('yuicompressor', env.settings.MINIFY_CMD_JS)


    def test_should_use_google_closure_compiler_in_production(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', test=False)
        self.assertIn('closure-compiler', env.settings.MINIFY_CMD_JS)


    #
    # MEDIA_ROOT
    #
    def test_should_use_media_folder_in_debug(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', debug=True, test=False)
        base = os.path.abspath(env.settings.BASE_PATH)
        self.assertEqual(
            '/media',
            env.settings.MEDIA_ROOT.replace(base, '')
        )


    def test_should_use_public_html_folder_in_production(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', debug=False, test=False)
        base = os.path.abspath(os.path.join(env.settings.BASE_PATH, '..', '..'))
        self.assertEqual(
            '/public_html/media',
            env.settings.MEDIA_ROOT.replace(base, '')
        )


    #
    # IMAGE_SIZES, DEFAULT_IMAGE_SIZE
    #
    def test_should_use_default_image_sizes(self):
        env = default_env(__name__, 'foo.com', 'root@localhost')
        self.assertEqual(
            {
                'xx-small':  50,
                'x-small':  160,
                'small':    320,
                'medium':   640,
                'large':    900,
                'x-large': 1200
            },
            env.settings.IMAGE_SIZES
        )
        self.assertEqual('x-large', env.settings.DEFAULT_IMAGE_SIZE)


    def test_should_use_extra_large_image_sizes_if_argument_is_given(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', high_res_images=True)
        self.assertEqual(
            {
                'xx-small':    50,
                'x-small':    160,
                'small':      320,
                'medium':     640,
                'large':      900,
                'x-large':   1200,
                'xx-large':  1600,
                'xxx-large': 2400,
            },
            env.settings.IMAGE_SIZES
        )
        self.assertEqual('xxx-large', env.settings.DEFAULT_IMAGE_SIZE)


    #
    # SSL
    #
    def test_should_not_load_ssl_by_default(self):
        env = default_env(__name__, 'foo.com', 'root@localhost')
        self.assertNotIn(
            'cubane.middleware.SSLResponseRedirectMiddleware',
            env.settings.MIDDLEWARE_CLASSES
        )


    def test_should_load_ssl_if_argument_is_given(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', ssl=True)
        self.assertIn(
            'cubane.middleware.SSLResponseRedirectMiddleware',
            env.settings.MIDDLEWARE_CLASSES
        )


    #
    # Debug toolbar
    #
    def test_should_not_load_debug_toolbar_by_default(self):
        env = default_env(__name__, 'foo.com', 'root@localhost')
        self.assertNotIn(
            'debug_toolbar.middleware.DebugToolbarMiddleware',
            env.settings.MIDDLEWARE_CLASSES
        )


    def test_should_not_load_debug_toolbar_if_not_in_debug_mode(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', debug=False, debug_toolbar=True)
        self.assertNotIn(
            'debug_toolbar.middleware.DebugToolbarMiddleware',
            env.settings.MIDDLEWARE_CLASSES
        )


    def test_should_load_debug_toolbar_if_argument_is_given_in_debug_mode(self):
        env = default_env(__name__, 'foo.com', 'root@localhost', debug=True, debug_toolbar=True)
        self.assertIn(
            'debug_toolbar.middleware.DebugToolbarMiddleware',
            env.settings.MIDDLEWARE_CLASSES
        )