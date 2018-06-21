# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.template import Template, Context
from django.contrib.auth.models import User
from cubane.tests.base import CubaneTestCase
from cubane.backend.views import BackendSection
from cubane.views import View
from cubane.backend.templatetags.backend_tags import listing
from cubane.backend.templatetags.backend_tags import is_visible_for


class TestView(View):
    def user_has_permission(self, user, view=None):
        return True


class BackendTemplateTagsTestCase(CubaneTestCase):
    TEMPLATE_LISTING = Template("{% load backend_tags %} {% listing %}")


    def test_listing_tag_should_render_backend_listing(self):
        self.assertIn('class="cubane-listing', self.TEMPLATE_LISTING.render(Context({})))


    def test_is_visible_for_should_raise_if_given_section_is_not_a_backend_section(self):
        with self.assertRaisesRegexp(ValueError, "Expected instance of 'cubane.backend.views.BackendSection"):
            is_visible_for('not a backend section', User())


    def test_is_visible_for_should_raise_if_given_user_is_not_a_user_instance(self):
        with self.assertRaisesRegexp(ValueError, "Expected instance of 'django.contrib.auth.models.User'"):
            is_visible_for(BackendSection(), 'not a user')


    def test_is_visible_for_should_return_false_if_section_is_NOT_visible_for_given_user(self):
        self.assertFalse(is_visible_for(BackendSection(), User()))


    def test_is_visible_for_should_return_true_if_section_is_visibale_for_given_user(self):
        section = BackendSection()
        section.view = TestView()
        self.assertTrue(is_visible_for(section, User()))