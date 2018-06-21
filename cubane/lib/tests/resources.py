# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.resources import get_resource_target_definition
from cubane.lib.resources import generate_resource_version_identifier
from cubane.lib.resources import get_resource_version_filename
from cubane.lib.resources import save_resource_version_identifier
from cubane.lib.resources import load_resource_version_identifier
from cubane.lib.resources import get_resource_files_by_identifier
from cubane.lib.resources import get_resource_files_not_matching_identifier
from cubane.lib.resources import get_resource_targets
from cubane.lib.resources import get_apps_for_resource_target
from cubane.lib.resources import get_resources
from cubane.lib.resources import get_resource
from cubane.lib.resources import get_minified_filename
from cubane.lib.file import file_get_contents
from cubane.lib.file import file_put_contents
import cubane.testapp
import copy
import os
import shutil


class GenerateResourceVersionIdentifierTestCase(CubaneTestCase):
    """
    cubane.lib.resources.generate_resource_version_identifier()
    """
    MAX_VERSIONS = 100

    def test_should_generate_unique_version_identifier(self):
        versions = []
        for i in range(0, self.MAX_VERSIONS):
            version = generate_resource_version_identifier()
            if version not in versions:
                versions.append(version)

        self.assertEqual(self.MAX_VERSIONS, len(versions))


class SaveResourceVersionIdentifierTestCase(CubaneTestCase):
    """
    cubane.lib.resources.save_resource_version_identifier()
    """
    def test_should_save_version_to_file(self):
        version = generate_resource_version_identifier()
        save_resource_version_identifier(version)

        filename = get_resource_version_filename()
        self.assertTrue(os.path.isfile(filename))

        content = file_get_contents(filename)
        os.remove(filename)
        self.assertEqual(version, content)


class LoadResourceVersionIdentifierTestCase(CubaneTestCase):
    """
    cubane.lib.resources.load_resource_version_identifier()
    """
    def test_should_load_resource_version_from_file_if_exists(self):
        version = generate_resource_version_identifier()
        save_resource_version_identifier(version)

        filename = get_resource_version_filename()
        self.assertTrue(os.path.isfile(filename))

        loaded_version = load_resource_version_identifier()
        os.remove(filename)
        self.assertEqual(version, loaded_version)


    def test_should_return_none_if_file_does_not_exist(self):
        filename = get_resource_version_filename()
        self.assertFalse(os.path.isfile(filename))
        self.assertIsNone(load_resource_version_identifier())


class ResourcesByIdentifierTestCaseBase(CubaneTestCase):
    def setUp(self):
        self.identifier = generate_resource_version_identifier()
        self.filenames = []


    def tearDown(self):
        for filename in self.filenames:
            try:
                os.remove(filename)
            except IOError:
                pass


    def _generate_files(self):
        for bucket in ['frontend', 'backend']:
            self._generate_file('cubane.%s.screen.%s.min.css' % (bucket, self.identifier))
            self._generate_file('cubane.%s.print.%s.min.css' % (bucket, self.identifier))
            self._generate_file('cubane.%s.%s.min.js' % (bucket, self.identifier))
            self._generate_file('cubane.svgicons.%s.%s.svg' % (bucket, self.identifier))


    def _generate_file(self, filename):
        if not os.path.exists(settings.STATIC_ROOT):
            os.path.makedirs(settings.STATIC_ROOT)

        filename = os.path.join(settings.STATIC_ROOT, filename)
        file_put_contents(filename, ' ')
        self.filenames.append(filename)
        return filename


class GetResourceFilesByIdentifierTestCase(ResourcesByIdentifierTestCaseBase):
    """
    cubane.lib.resources.get_resource_files_by_identifier()
    """
    def test_should_return_all_resource_files_matching_given_version_identifier(self):
        self._generate_files()
        filenames_for_identifier = get_resource_files_by_identifier(self.identifier)
        self.assertEqual(sorted(self.filenames), sorted(filenames_for_identifier))


    def test_should_return_empty_list_if_identifier_is_not_defined(self):
        self.assertEqual([], get_resource_files_by_identifier(None))


class GetResourceFilesNotMatchingIdentifierTestCase(ResourcesByIdentifierTestCaseBase):
    """
    cubane.lib.resources.get_resource_files_not_matching_identifier()
    """
    def test_should_return_all_resource_files_not_matching_given_identifier(self):
        self._generate_files()
        filenames_not_matching = get_resource_files_not_matching_identifier('does-not-match')
        for filename in self.filenames:
            self.assertTrue(filename in filenames_not_matching, filename)


    def test_should_return_empty_list_if_identifier_is_not_defined(self):
        self.assertEqual([], get_resource_files_not_matching_identifier(None))


class GetResourceTargetsTestCase(CubaneTestCase):
    """
    cubane.lib.resources.get_resource_targets()
    """
    EXPECTED_TARGETS = [
        'frontend',
        'inline',
        'backend',
        'backend-inline',
        'testing',
        'recursive',
        'empty'
    ]


    def test_get_resource_targets_should_return_list(self):
        self.assertIsInstance(get_resource_targets(), list)


    def test_get_resource_targets_should_return_list_with_correct_amount_of_resources(self):
        targets = get_resource_targets()
        for target in self.EXPECTED_TARGETS:
            self.assertIn(target, targets)


    def test_get_resource_targets_should_return_list_in_alphabetical_order(self):
        resources = get_resource_targets()
        alphabetical_ordered_resources = sorted(list(resources))
        for a, b in zip(resources, alphabetical_ordered_resources):
            self.assertEqual(a, b)


class GetAppsForResourceTargetTestCase(CubaneTestCase):
    """
    cubane.lib.resources.get_apps_for_resource_target()
    """
    def test_get_apps_for_resource_target_should_return_list(self):
        self.assertIsInstance(get_apps_for_resource_target('testing'), list)


    def test_get_apps_for_resource_target_should_return_list_with_one_item(self):
        self.assertEqual(1, len(get_apps_for_resource_target('testing')))


    def test_get_apps_for_resource_target_should_return_dependent_apps(self):
        # backend not listed directly within settings
        resources = get_resource_target_definition()
        self.assertIn('cubane.media', get_apps_for_resource_target('backend'))


    def test_get_apps_for_resource_target_should_not_recursivly_include_the_same_dependency(self):
        self.assertEqual(['cubane.testapp.recursive'], get_apps_for_resource_target('recursive'))


class GetResourcesTestCase(CubaneTestCase):
    """
    cubane.lib.resources.get_resources()
    """
    EXPECTED_GLOB_RESOURCES = [
        '/cubane/testapp/css/glob/a.css',
        '/cubane/testapp/css/glob/b.css',
        '/cubane/testapp/css/glob/c.css',
    ]

    EXPECTED_SUBAPP_GLOB_RESOURCES = [
        '/cubane/testapp/subapp/svgicons/email.svg',
    ]

    EXPECTED_RESOURCES = [
       'cubane/testapp/css/style.templating.css',
    ] + EXPECTED_GLOB_RESOURCES

    EXPECTED_PRINT_RESOURCES = [
        'cubane/testapp/css/print.css'
    ]


    def test_get_resources_should_return_list(self):
        self.assertIsInstance(get_resources('testing'), list)


    def test_get_resources_should_return_resources_matching_screen_media_without_media_prefix(self):
        resources = get_resources('testing', 'css')
        self._assertExpectedResources(self.EXPECTED_RESOURCES, resources)


    def test_get_resources_should_return_resources_matching_given_media_prefix(self):
        self.assertEqual(1, len(get_resources('testing', css_media='print')))


    @override_settings()
    def test_get_resources_should_ignore_apps_that_do_not_exist(self):
        settings.RESOURCES = {'testing': ['fakeapp']}
        settings.INSTALLED_APPS = ['fakeapp']

        self.assertEqual([], get_resources('testing', 'css'))


    def test_get_resources_should_return_resources_matching_given_ext(self):
        self._assertExpectedResources(
            self.EXPECTED_RESOURCES,
            get_resources('testing', ext='css')
        )

        self._assertExpectedResources(
            self.EXPECTED_PRINT_RESOURCES,
            get_resources('testing', ext='css', css_media='print')
        )


    def test_get_resources_should_apply_glob_sorted_alphabetically(self):
        self._assertExpectedResources(
            self.EXPECTED_GLOB_RESOURCES,
            get_resources('testing', ext='css')
        )


    def test_get_resources_should_apply_glob_for_resources_of_sub_app(self):
        self._assertExpectedResources(
            self.EXPECTED_SUBAPP_GLOB_RESOURCES,
            get_resources('subapp', ext='svg')
        )


    def test_get_resources_should_filter_by_name(self):
        self.assertEqual(
            ['cubane/testapp/css/style.templating.css'],
            get_resources('testing', ext='css', name='style.templating')
        )


    def test_get_resources_should_filter_by_name_after_glob_if_argument_is_given(self):
        self.assertEqual(
            ['/cubane/testapp/css/glob/b.css'],
            get_resources('testing', ext='css', name='b')
        )


    def _assertExpectedResources(self, expected_resources, actual_resources):
        for resource in expected_resources:
            self.assertIn(resource, actual_resources)


class GetResourceTestCase(CubaneTestCase):
    """
    cubane.lib.resources.get_resource()
    """
    def test_should_return_resources_for_debug_mode(self):
        self.assertEqual('html{color:red;}', get_resource('cubane/testapp/css/test_simple.css'))


    @override_settings(MINIFY_RESOURCES=True)
    def test_should_return_resources_for_production_mode(self):
        base_path = self.get_testapp_static_path()
        src_filename = os.path.join(base_path, 'css', 'test_simple.css')
        dst_filename = os.path.join(settings.STATIC_ROOT, 'cubane', 'testapp', 'css', 'test_simple.css')
        dst_path = os.path.dirname(dst_filename)

        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
        shutil.copyfile(src_filename, dst_filename)

        self.assertEqual('html{color:red;}', get_resource('cubane/testapp/css/test_simple.css'))

        os.remove(dst_filename)


    @override_settings(MINIFY_RESOURCES=True)
    def test_should_not_raise_error_if_absolute_path(self):
        base_path = self.get_testapp_static_path()
        src_filename = os.path.join(base_path, 'css', 'test_simple.css')
        dst_filename = os.path.join(settings.STATIC_ROOT, 'cubane', 'testapp', 'css', 'test_simple.css')
        dst_path = os.path.dirname(dst_filename)

        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
        shutil.copyfile(src_filename, dst_filename)

        self.assertEqual('html{color:red;}', get_resource('cubane/testapp/css/test_simple.css'))

        os.remove(dst_filename)


class CubaneLibResourcesGetMinifiedFilenameTestCase(CubaneTestCase):
    """
    cubane.lib.resources.get_minified_filename()
    """
    def test_default_media_for_css_should_be_screen(self):
        self.assertEqual(
            'cubane.testapp.screen.min.css',
            get_minified_filename('testapp', 'css', css_media=None)
        )


    def test_with_media_for_css(self):
        self.assertEqual(
            'cubane.testapp.print.min.css',
            get_minified_filename('testapp', 'css', css_media='print')
        )

    def test_with_media_for_js_should_ignore_media(self):
        self.assertEqual(
            'cubane.testapp.min.js',
            get_minified_filename('testapp', 'js', css_media='print')
        )


    @override_settings(TRACK_REVISION=True)
    def test_should_include_revision_identifier_for_css_resource_filename(self):
        identifier = generate_resource_version_identifier()
        self.assertEqual(
            'cubane.testapp.screen.%s.min.css' % identifier,
            get_minified_filename('testapp', 'css', identifier=identifier)
        )


    @override_settings(TRACK_REVISION=True)
    def test_should_include_revision_identifier_for_js_resource_filename(self):
        identifier = generate_resource_version_identifier()
        self.assertEqual(
            'cubane.testapp.%s.min.js' % identifier,
            get_minified_filename('testapp', 'js', identifier=identifier)
        )