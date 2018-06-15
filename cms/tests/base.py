# coding=UTF-8
from __future__ import unicode_literals
from django.template.defaultfilters import slugify
from cubane.tests.base import CubaneTestCase
from cubane.cms.models import Page
from cubane.cms.views import get_cms_settings
from cubane.blog.models import BlogPost


class CMSTestBase(CubaneTestCase):
    @classmethod
    def create_page(cls, title, template='testapp/page.html', nav='header', entity_type=None, seq=0, legacy_url=None, identifier=None, parent=None, is_homepage=False, disabled=False):
        p = Page(
            title=title,
            slug=slugify(title),
            template=template,
            _nav=nav,
            entity_type=entity_type,
            seq=seq,
            legacy_url=legacy_url,
            identifier=identifier,
            parent=parent,
            is_homepage=is_homepage,
            disabled=disabled
        )
        p.save()
        return p


    @classmethod
    def create_child_page_for_page(cls, page, title, seq):
        c = BlogPost(
            title=title,
            slug=slugify(title),
            template='testapp/page.html',
            page=page,
            seq=seq
        )
        c.save()


    def set_settings_vars(self, settings_dict):
        settings = get_cms_settings()
        for item in settings_dict:
            setattr(settings, item, settings_dict[item])
        settings.save()
        return settings