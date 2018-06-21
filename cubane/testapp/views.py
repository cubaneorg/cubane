# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db.models import Q
from cubane.cms.views import CMS
from cubane.cms.models import Page
from cubane.lib.libjson import to_json
from cubane.ishop.views import Shop
from cubane.testapp.models import *


class TestAppCMS(CMS):
    def on_template_context(self, request, context, template_context):
        template_context.update({
            'on_template_context': True,
            'objects': TestModel.objects.all()
        })

        return template_context


class TestAppShop(Shop):
    pass


def test_get_absolute_url(request): # pragma: no cover
    pass


def test_non_standard_cms_page(request): # pragma: no cover
    pass