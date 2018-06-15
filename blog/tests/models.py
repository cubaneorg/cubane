# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.blog.models import BlogPost
from cubane.blog.forms import BlogPostForm


class CMSBlogModelsBlogPostTestCase(CubaneTestCase):
    def test_get_form_should_return_default_form_for_blog_post(self):
        p = BlogPost()
        self.assertTrue(issubclass(p.get_form(), BlogPostForm))