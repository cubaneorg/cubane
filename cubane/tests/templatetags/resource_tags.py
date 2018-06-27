# coding=UTF-8
from __future__ import unicode_literals
from django import template
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.templatetags.resource_tags import *
from mock.mock import Mock, patch
import re


class ResourceTagsJavascriptURLsTestCase(CubaneTestCase):
    """
    cubane.templatetags.resource_tags.javascript_urls()
    """
    def setUp(self):
        self.parser = Mock()
        self.token = Mock(methods=['split_contents'])


    def test_should_return_javascript_urls_node(self):
        self.token.split_contents.return_value = ['javascript_urls']
        self.assertIsInstance(javascript_urls(self.parser, self.token), JavascriptUrlsNode)


    def test_should_raise_exception(self):
        self.token.split_contents.return_value = ['javascript_urls', 'test']
        self.assertRaises(template.TemplateSyntaxError, javascript_urls, self.parser, self.token)


class ResourceTagsInlineResourcesTestCase(CubaneTestCase):
    """
    cubane.templatetags.resource_tags.inline_resources()
    """
    def setUp(self):
        self.parser = Mock()
        self.token = Mock(methods=['split_contents'])


    def test_not_four_args_should_raise_exception(self):
        self.token.split_contents.return_value = ['inline_resources']
        self.assertRaises(template.TemplateSyntaxError, inline_resources, self.parser, self.token)


    def test_wrong_extension_should_raise_exception(self):
        self.token.split_contents.return_value = ['inline_resources', 'target', '"php"']
        self.assertRaises(template.TemplateSyntaxError, inline_resources, self.parser, self.token)


    def test_should_return_resource_node(self):
        self.token.split_contents.return_value = ['inline_resources', 'target', '"js"']
        self.assertIsInstance(inline_resources(self.parser, self.token), ResourcesNode)


    @override_settings(DEBUG=True)
    def test_should_not_inline_in_debug(self):
        self.token.split_contents.return_value = ['inline_resources', 'target', '"js"']
        node = inline_resources(self.parser, self.token)
        self.assertFalse(node.inline)


    def test_should_setup_resources_node(self):
        self.token.split_contents.return_value = ['inline_resources', 'target', '"js"']
        resources_node = inline_resources(self.parser, self.token)

        self.assertEqual(resources_node.target, 'target')
        self.assertEqual(resources_node.ext, 'js')
        self.assertEqual(resources_node.inline, True)


class ResourceTagsResourcesNodeIncludeTestCase(CubaneTestCase):
    """
    cubane.templatetags.resource_tags.ResourcesNode.include()
    """
    def test_should_include_css_with_media_print(self):
        resources_node = ResourcesNode("'target'", 'css', 'print')
        included = resources_node.include('test.css', 'print')
        self.assertEqual(included.strip(), '<link href="/static/test.css" rel="stylesheet" media="print"/>')


    def test_should_include_css_with_media_screen(self):
        resources_node = ResourcesNode("'target'", 'css')
        included = resources_node.include('test.css')
        self.assertEqual(included.strip(), '<link href="/static/test.css" rel="stylesheet" media="screen"/>')


    def test_should_include_js(self):
        resources_node = ResourcesNode("'target'", 'js')
        included = resources_node.include('test.js')
        self.assertEqual(included.strip(), '<script src="/static/test.js"></script>')


    @override_settings(MINIFY_RESOURCES=True)
    def test_should_include_async_css(self):
        resources_node = ResourcesNode("'target'", 'css')
        included = resources_node.include('test.css', css_media=True, is_async=True)
        self.assertTrue('stylesheet.href = "/static/test.css"' in included)
        self.assertTrue('href="/static/test.css"' in included)


class ResourceTagsResourcesNodeInlineIncludeTestCase(CubaneTestCase):
    """
    cubane.templatags.resource_tags.ResourcesNode.inline_include()
    """
    def test_should_generate_inlined_css_with_screen_media_by_default(self):
        resources_node = ResourcesNode("'target'", 'css')
        style = resources_node.inline_include('test')
        self.assertEqual(style.strip(), '<style media="screen">test</style>')


    def test_should_generate_inlined_js(self):
        resources_node = ResourcesNode("'target'", 'js')
        js = resources_node.inline_include('test')
        self.assertEqual(js.strip(), '<script>test</script>')


class ResourceTagsResourcesNodeRenderTestCase(CubaneTestCase):
    """
    cubane.templatetags.resources_tags.ResourcesNode.render()
    """
    def test_should_not_render_when_target_is_not_in_settings(self):
        resources_node = ResourcesNode("'target'", 'css')
        self.assertEqual(resources_node.render({}), '')


    def test_should_raise_exception_if_css_media_not_in_settings(self):
        resources_node = ResourcesNode("'target'", 'css', "'css_media'")
        self.assertRaises(template.TemplateSyntaxError, resources_node.render, {})


    @override_settings(DEBUG=True, MINIFY_RESOURCES=False)
    def test_should_render_inlined_content(self):
        resources_node = ResourcesNode("'inline'", 'css', "'screen'", inline=True)
        self.assertTrue(True if '.lazy-load' in resources_node.render({}) else False)


    @override_settings(DEBUG=True, MINIFY_RESOURCES=False)
    def test_should_render_not_inlined_content(self):
        resources_node = ResourcesNode("'frontend'", 'css', "'screen'")
        self.assertTrue(True if 'static/cubane/default_frontend/css/default_frontend.css' in resources_node.render({}) else False)


    @override_settings(MINIFY_RESOURCES=True)
    @patch('cubane.templatetags.resource_tags.get_resource')
    @patch('cubane.templatetags.resource_tags.load_resource_version_identifier')
    def test_should_render_inlined_content_using_minified_path(self, load_resource_version_identifier, get_resource):
        load_resource_version_identifier.return_value = None
        resources_node = ResourcesNode("'inline'", 'css', "'screen'", inline=True)
        resources_node.render({})
        get_resource.assert_called_with('cubane.inline.screen.min.css')


    @override_settings(MINIFY_RESOURCES=True)
    @patch('cubane.templatetags.resource_tags.get_resource')
    @patch('cubane.templatetags.resource_tags.load_resource_version_identifier')
    def test_should_render_inlined_content_using_minified_path_including_revision_identifier(self, load_resource_version_identifier, get_resource):
        load_resource_version_identifier.return_value = 'foo'
        resources_node = ResourcesNode("'inline'", 'css', "'screen'", inline=True)
        resources_node.render({})
        get_resource.assert_called_with('cubane.inline.screen.foo.min.css')


    @override_settings(MINIFY_RESOURCES=True)
    @patch('cubane.templatetags.resource_tags.load_resource_version_identifier')
    def test_should_render_not_inlined_content_using_minified_path(self, load_resource_version_identifier):
        load_resource_version_identifier.return_value = None
        resources_node = ResourcesNode("'frontend'", 'css', "'screen'")
        self.assertTrue(True if 'static/cubane.frontend.screen.min.css' in resources_node.render({}) else False)


    @override_settings(MINIFY_RESOURCES=True)
    @patch('cubane.templatetags.resource_tags.load_resource_version_identifier')
    def test_should_render_not_inlined_content_using_minified_path_including_revision_identifier(self, load_resource_version_identifier):
        load_resource_version_identifier.return_value = 'foo'
        resources_node = ResourcesNode("'frontend'", 'css', "'screen'")
        self.assertTrue(True if 'static/cubane.frontend.screen.foo.min.css' in resources_node.render({}) else False)


class ResourceTagsJavascriptUrlsNodeTestCase(CubaneTestCase):
    """
    cubane.templatetags.resource_tags.JavascriptUrlsNode.render()
    """
    def test_should_render_js_node(self):
        node = JavascriptUrlsNode()
        self.assertTrue(re.match('<script>(.*)</script>', node.render({})))


class ResourceTagsResourcesTestCase(CubaneTestCase):
    """
    cubane.templatetags.resources()
    """
    def setUp(self):
        self.parser = Mock()
        self.token = Mock(methods=['split_contents'])

    def test_should_return_resource_node(self):
        self.token.split_contents.return_value = ['resources', 'target', '"css"']
        self.assertIsInstance(resources(self.parser, self.token), ResourcesNode)


    def test_should_raise_exception_for_more_arguments_than_five(self):
        self.token.split_contents.return_value = ['resources', 'target', '"css"', 'css_media', 'async', 'test']
        self.assertRaises(template.TemplateSyntaxError, resources, self.parser, self.token)


    def test_should_raise_exception_for_not_css_or_js(self):
        self.token.split_contents.return_value = ['resources', 'target', '"php"']
        self.assertRaises(template.TemplateSyntaxError, resources, self.parser, self.token)


    def test_should_add_css_media_to_resource_node(self):
        self.token.split_contents.return_value = ['resources', 'target', '"css"', 'media']
        resources_node = resources(self.parser, self.token)
        self.assertEqual(resources_node.css_media, 'media')


    def test_should_not_add_css_media_to_resource_node(self):
        self.token.split_contents.return_value = ['resources', 'target', '"css"']
        resources_node = resources(self.parser, self.token)
        self.assertEqual(resources_node.css_media, None)


    def test_should_setup_resources_node(self):
        self.token.split_contents.return_value = ['resources', 'target', '"js"', 'True']
        resources_node = resources(self.parser, self.token)
        self.assertEqual(resources_node.target, 'target')
        self.assertEqual(resources_node.ext, 'js')
        self.assertEqual(resources_node.is_async, 'True')


class ResourceTagsFaviconsTagTestCase(CubaneTestCase):
    def test_should_return_html(self):
        self.assertEqual(
            '<link rel="shortcut icon" href="/favicon.ico" /><link rel="apple-touch-icon-precomposed" sizes="57x57" href="/media/favicons/favicon-57x57.png" /><link rel="apple-touch-icon-precomposed" sizes="60x60" href="/media/favicons/favicon-60x60.png" /><link rel="apple-touch-icon-precomposed" sizes="72x72" href="/media/favicons/favicon-72x72.png" /><link rel="apple-touch-icon-precomposed" sizes="76x76" href="/media/favicons/favicon-76x76.png" /><link rel="apple-touch-icon-precomposed" sizes="114x114" href="/media/favicons/favicon-114x114.png" /><link rel="apple-touch-icon-precomposed" sizes="120x120" href="/media/favicons/favicon-120x120.png" /><link rel="apple-touch-icon-precomposed" sizes="144x144" href="/media/favicons/favicon-144x144.png" /><link rel="apple-touch-icon-precomposed" sizes="152x152" href="/media/favicons/favicon-152x152.png" /><link rel="icon" type="image/png" href="/media/favicons/favicon-16x16.png" sizes="16x16" /><link rel="icon" type="image/png" href="/media/favicons/favicon-32x32.png" sizes="32x32" /><link rel="icon" type="image/png" href="/media/favicons/favicon-96x96.png" sizes="96x96" /><link rel="icon" type="image/png" href="/media/favicons/favicon-128x128.png" sizes="128x128" /><link rel="icon" type="image/png" href="/media/favicons/favicon-196x196.png" sizes="196x196" /><meta name="msapplication-TileColor" content="#FFFFFF" /><meta name="msapplication-TileImage" content="/media/favicon-144x144.png" /><meta name="msapplication-square70x70logo" content="/media/favicons/favicon-70x70.png" /><meta name="msapplication-square150x150logo" content="/media/favicons/favicon-150x150.png" /><meta name="msapplication-wide310x150logo" content="/media/favicons/favicon-310x150.png" /><meta name="msapplication-square310x310logo" content="/media/favicons/favicon-310x310.png" />',
            favicons()
        )
