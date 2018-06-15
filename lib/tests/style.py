# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.style import (
    parse_style,
    parse_inline_style,
    encode_inline_style
)


class LibStyleParseStyleTestCase(CubaneTestCase):
    """
    cubane.svgicons.parse_style()
    """
    def test_should_split_css_code_by_selector(self):
        self.assertEqual(
            {
                '.foo': 'color: red;',
                '.bar': 'border:1px solid red; line-height: 1em;'
            },
            parse_style('.foo { color: red; }\r\n.bar{border:1px solid red; line-height: 1em;}')
        )


    def test_should_combine_selectors(self):
        self.assertEqual(
            {
                '.foo': 'color: red;display: block;',
            },
            parse_style('.foo { color: red; }\r\n.foo{ display: block; }')
        )


class LibStyleParseInlineStyleTestCase(CubaneTestCase):
    """
    cubane.svgicons.parse_inline_style()
    """
    def test_should_return_empty_dict_for_none(self):
        self.assertEqual({}, parse_inline_style(None))


    def test_should_return_empty_dict_for_empty_inline_style(self):
        self.assertEqual({}, parse_inline_style(''))


    def test_should_split_css_inline_style_by_rule(self):
        self.assertEqual(
            {
                'fill': 'red',
                'stroke': '#efefef'
            },
            parse_inline_style('  fill: red;  stroke: #efefef  ')
        )


    def test_should_ignore_empty_rules(self):
        self.assertEqual(
            {'fill': 'red'},
            parse_inline_style('  fill: red;  stroke;;;  ')
        )


class LibStyleEncodeInlineStyleTestCase(CubaneTestCase):
    """
    cubane.svgicons.encode_inline_style()
    """
    def test_should_return_empty_string_for_none(self):
        self.assertEqual('', encode_inline_style(None))


    def test_should_return_empty_string_for_empty_dict(self):
        self.assertEqual('', encode_inline_style({}))


    def test_should_encode_css_inline_style(self):
        self.assertEqual(
            'fill:red;stroke:#efefef',
            encode_inline_style({
                '  fill  ': '  red  ',
                ' stroke ': ' #efefef '
            })
        )