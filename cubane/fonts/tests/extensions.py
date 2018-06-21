# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.resources import ResourceManager
from cubane.fonts.extensions import ResourceManagerExtension


class FontsResourceManagerExtensionTestCase(CubaneTestCase):
    """
    cubane.fonts.extensions.ResourceManagerExtension()
    """
    def setUp(self):
        Manager = ResourceManager.register_extension(ResourceManagerExtension)
        self.manager = Manager()

    def test_process_resource_entry_should_rewrite_font_declaration_for_css_targets(self):
        prefix, resource = self.manager.process_resource_entry('target', '.css', 'screen', 'font', 'Open Sans')
        self.assertEqual('screen', prefix)
        self.assertEqual('/media/fonts/open-sans/open-sans.css', resource)


    def test_process_resource_entry_should_not_rewrite_css_reference(self):
        prefix, resource = self.manager.process_resource_entry('target', '.css', 'screen', None, 'style.css')
        self.assertIsNone(prefix)
        self.assertEqual('style.css', resource)


    def test_process_resource_entry_should_not_rewrite_js_reference(self):
        prefix, resource = self.manager.process_resource_entry('target', '.css', 'screen', None, 'main.js')
        self.assertIsNone(prefix)
        self.assertEqual('main.js', resource)


    def test_process_resource_entry_should_not_rewrite_font_declaration_for_js_targets(self):
        prefix, resource = self.manager.process_resource_entry('target', '.js', None, 'font', 'Open Sans')
        self.assertEqual('font', prefix)
        self.assertEqual('Open Sans', resource)