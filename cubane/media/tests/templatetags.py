# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.media.models import Media
from cubane.media.templatetags.media_tags import *


class MediaTemplateTagsRenderSVGImageTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(MediaTemplateTagsRenderSVGImageTestCase, cls).setUpClass()
        cls.image = Media(id=1, is_image=True, is_svg=True, caption='foo')


    def test_should_render_as_lazyload_markup(self):
        self.assertEqual(
            '<span class="lazy-load"><span class="lazy-load-shape-original" style="padding-bottom:100.0%;"><noscript data-shape="original" data-path="/0/1/" data-blank="0" data-sizes="xx-small" data-alt="foo" data-title="foo" data-svg="1" data-inline="0"><img src="http://www.testapp.cubane.innershed.com/media/shapes/original/xx-small/0/1/" alt="foo" title="foo"></noscript></span></span>',
            render_image(self.image)
        )


    def test_should_render_as_lazyload_inline_markup(self):
        self.assertEqual(
            '<span class="lazy-load"><span class="lazy-load-shape-original" style="padding-bottom:100.0%;"><noscript data-shape="original" data-path="/0/1/" data-blank="0" data-sizes="xx-small" data-alt="foo" data-title="foo" data-svg="1" data-inline="1"><img src="http://www.testapp.cubane.innershed.com/media/shapes/original/xx-small/0/1/" alt="foo" title="foo"></noscript></span></span>',
            render_image(self.image, inline=True)
        )


    def test_should_render_given_shape_as_plain_img_tag(self):
        self.assertEqual(
            '<span class="lazy-load"><span class="lazy-load-shape-header"><noscript data-shape="header" data-path="/0/1/" data-blank="0" data-sizes="xx-small" data-alt="foo" data-title="foo" data-svg="1" data-inline="0"><img src="http://www.testapp.cubane.innershed.com/media/shapes/original/xx-small/0/1/" alt="foo" title="foo"></noscript></span></span>',
            render_image(self.image, 'header')
        )


class MediaTemplateTagsRenderImageSizesTestCase(CubaneTestCase):
    @classmethod
    def setUpClass(cls):
        super(MediaTemplateTagsRenderImageSizesTestCase, cls).setUpClass()
        cls.image_sizes = sorted(
            settings.IMAGE_SIZES.items(),
            key=lambda x: x[1]
        )


    def test_should_render_lazyload_markup_containing_size_references_up_to_the_supported_size(self):
        sizes = []
        for size, width in self.image_sizes:
            self._assert_image_size(width - 1, sizes)
            sizes.append(size)
            self._assert_image_size(width, sizes)
            self._assert_image_size(width + 1, sizes)


    def _assert_image_size(self, width, sizes):
        if len(sizes) == 0:
            sizes = ['xx-small']

        image = Media(id=1, is_image=True, width=width, height=width, caption='foo')
        html = render_image(image)
        for size in sizes:
            self.assertIn(size, html)