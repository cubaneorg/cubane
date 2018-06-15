# coding=UTF-8
from __future__ import unicode_literals
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.resources import generate_resource_version_identifier
from cubane.lib.resources import save_resource_version_identifier
from cubane.svgicons import (
    get_svg_name_from_file,
    get_svg_content,
    get_combined_svg_for_resources,
    get_svgicons_filename
)


# further tests
from cubane.svgicons.tests.templatetags import *
from cubane.svgicons.tests.create_svgicons import *
from cubane.svgicons.tests.views import *


class SvgIconsGetSvgNameFromFileTestCase(CubaneTestCase):
    """
    cubane.svgicons.get_svg_name_from_file()
    """
    def test_should_ignore_path(self):
        self.assertEqual('test', get_svg_name_from_file('/home/svgicons/test.svg'))


    def test_should_make_lowercase(self):
        self.assertEqual('test', get_svg_name_from_file('/home/svgicons/Test.svg'))


    def test_should_remove_icon_reference(self):
        self.assertEqual('test-svg', get_svg_name_from_file('/home/svgicons/IconTestIconSvg.svg'))


    def test_get_svg_name_from_file_should_remove_double_spacing(self):
        self.assertEqual('this-is-an', get_svg_name_from_file('/home/svgicons/This   Is   An   Icon.svg'))


class SvgIconsGetSvgContentTestCase(CubaneTestCase):
    """
    cubane.svgicons.get_svg_content()
    """
    def test_should_return_viewbox_and_content_removing_id_attributes_and_comments_and_xml_declaration(self):
        self.assertEqual(
            ('0 0 64 64', '<g id="my_filename-xNv91c.tif"> <g> <path d="M28.4,0c1.8,0,3.5,0,5.3,0c0.1,0,0.2,0.1,0.4,0.1c8.7,1.3,15.1,5.8,18.9,13.7c2.1,4.2,2.9,8.8,1.9,13.5 c-0.7,3.4-2.2,6.5-3.9,9.6c-4.2,7.7-9.4,14.7-15,21.5c-1.5,1.9-3.1,3.7-4.7,5.6c-0.1,0-0.2,0-0.3,0C24.8,57,19,49.7,14,41.7 c-3.1-4.9-5.9-10-7-15.8c0-1.5,0-3,0-4.5c0-0.2,0.1-0.4,0.1-0.6c1.5-9.1,6.4-15.4,14.8-19.1C24,0.8,26.2,0.4,28.4,0z"/> </g> </g>'),
            get_svg_content('my_filename',
                """
                <?xml version="1.0" encoding="utf-8"?>
                <!-- Generator: Adobe Illustrator 19.1.0, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
                <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"
                	 width="64px" height="64px" viewBox="0 0 64 64" style="enable-background:new 0 0 64 64;" xml:space="preserve">
                <g id="xNv91c.tif">
                	<g>
                		<path fill="red" stroke="blue" d="M28.4,0c1.8,0,3.5,0,5.3,0c0.1,0,0.2,0.1,0.4,0.1c8.7,1.3,15.1,5.8,18.9,13.7c2.1,4.2,2.9,8.8,1.9,13.5
                			c-0.7,3.4-2.2,6.5-3.9,9.6c-4.2,7.7-9.4,14.7-15,21.5c-1.5,1.9-3.1,3.7-4.7,5.6c-0.1,0-0.2,0-0.3,0C24.8,57,19,49.7,14,41.7
                			c-3.1-4.9-5.9-10-7-15.8c0-1.5,0-3,0-4.5c0-0.2,0.1-0.4,0.1-0.6c1.5-9.1,6.4-15.4,14.8-19.1C24,0.8,26.2,0.4,28.4,0z"/>
                	</g>
                </g>
                </svg>
                """
            )
        )


    def test_should_remove_style_by_default(self):
        self.assertEqual(
            ('0 0 64 64', '<g> <path d="M28.4,0c1.8,0,3.5,0,5.3,0"/> </g>'),
            get_svg_content(
                'my_filename',
                """
                <svg viewBox="0 0 64 64">
                <style type="text/css">
                    .st0{fill:#980D1F; stroke: black; stroke-width:10;}
                    .st1{fill:red;}
                </style>
            	<g>
                    <path class="st0 st1" d="M28.4,0c1.8,0,3.5,0,5.3,0"/>
                </g>
                </svg>
                """
            )
        )


    def test_should_retain_fill_none_even_with_style_removed(self):
        self.assertEqual(
            ('0 0 64 64', '<g> <path d="M28.4,0c1.8,0,3.5,0,5.3,0" style="fill:none;"/> </g>'),
            get_svg_content(
                'my_filename',
                """
                <svg viewBox="0 0 64 64">
                <style type="text/css">
                    .st0{fill:none;}
                </style>
            	<g>
                    <path class="st0" d="M28.4,0c1.8,0,3.5,0,5.3,0"/>
                </g>
                </svg>
                """
            )
        )


    def test_should_inline_style_if_specified(self):
        self.assertEqual(
            ('0 0 64 64', '<g> <path d="M28.4,0c1.8,0,3.5,0,5.3,0" style="fill:#980D1F; stroke: black; stroke-width:10; fill:red;"/> </g>'),
            get_svg_content(
                'my_filename',
                """
                <svg viewBox="0 0 64 64">
                <style type="text/css">
                    .st0{fill:#980D1F; stroke: black; stroke-width:10;}
                    .st1{fill:red;}
                </style>
            	<g>
                    <path class="st0 st1" d="M28.4,0c1.8,0,3.5,0,5.3,0"/>
                </g>
                </svg>
                """, with_style=True
            )
        )


    def test_should_ignore_classes_without_style(self):
        self.assertEqual(
            ('0 0 64 64', '<g> <path d="M28.4,0c1.8,0,3.5,0,5.3,0"/> </g>'),
            get_svg_content(
                'my_filename',
                """
                <svg viewBox="0 0 64 64">
                <style type="text/css">
                    .st1{fill:red;}
                </style>
            	<g>
                    <path class="st0" d="M28.4,0c1.8,0,3.5,0,5.3,0"/>
                </g>
                </svg>
                """, with_style=True
            )
        )


class SvgIconsGetCombinedSvgForResourcesTestCase(CubaneTestCase):
    """
    cubane.svgicons.get_combined_svg_for_resources()
    """
    def test_should_raise_error_if_resource_file_does_not_exist(self):
        with self.assertRaisesRegexp(ValueError, 'Unable to read svg icon file'):
            get_combined_svg_for_resources(['does-not-exist.svg'])


class SvgIconsGetSvgiconsFilenameTestCase(CubaneTestCase):
    """
    cubane.svgicons.get_svgicons_filename()
    """
    @override_settings(TRACK_REVISION=False)
    def test_should_contain_target_name(self):
        self.assertEqual('cubane.svgicons.frontend.svg', get_svgicons_filename('frontend'))


    @override_settings(TRACK_REVISION=False)
    def test_should_ignore_identifier_if_revisions_are_not_tracked(self):
        identifier = generate_resource_version_identifier()
        self.assertEqual('cubane.svgicons.frontend.svg', get_svgicons_filename('frontend', identifier='foo'))


    @override_settings(TRACK_REVISION=True)
    def test_should_contain_revision_number_if_configured(self):
        identifier = generate_resource_version_identifier()
        self.assertEqual('cubane.svgicons.frontend.%s.svg' % identifier, get_svgicons_filename('frontend', identifier))
