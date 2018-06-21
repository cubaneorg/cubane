# coding=UTF-8
from __future__ import unicode_literals
from cubane.views import ModelView
from cubane.backend.views import BackendSection
from cubane.ishop.models import Voucher
from cubane.ishop.apps.merchant.vouchers.forms import VoucherForm


class VoucherView(ModelView):
    """
    Editing vouchers.
    """
    template_path = 'cubane/ishop/merchant/vouchers/'
    namespace = 'cubane.ishop.vouchers'
    model = Voucher
    form = VoucherForm


    def _get_objects(self, request):
        return self.model.objects.all()


class VoucherBackendSection(BackendSection):
    title = 'Vouchers'
    slug = 'vouchers'
    view = VoucherView()