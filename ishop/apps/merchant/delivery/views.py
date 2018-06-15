# coding=UTF-8
from __future__ import unicode_literals
from cubane.views import ModelView, view_url, view
from cubane.backend.views import BackendSection
from cubane.ishop.models import DeliveryOption
from forms import DeliveryOptionForm


class DeliveryView(ModelView):
    """
    Customise delivery options.
    """
    template_path = 'cubane/ishop/merchant/delivery'
    namespace = 'cubane.ishop.delivery'
    model = DeliveryOption
    form = DeliveryOptionForm


    def _get_objects(self, request):
        return self.model.objects.all()


class DeliveryBackendSection(BackendSection):
    title = 'Delivery'
    slug = 'delivery'
    view = DeliveryView()