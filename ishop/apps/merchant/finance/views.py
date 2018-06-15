# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.views import ModelView, view_url, view
from cubane.backend.views import BackendSection
from cubane.ishop.models import FinanceOption


class FinanceOptionView(ModelView):
    """
    Editing finance options
    """
    template_path = 'cubane/ishop/merchant/finance/'
    model = FinanceOption


    def _get_objects(self, request):
        return self.model.objects.all()


class FinanceOptionBackendSection(BackendSection):
    title = 'Finance'
    slug = 'finance'
    view = FinanceOptionView()