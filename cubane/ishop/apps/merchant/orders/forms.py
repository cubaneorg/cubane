# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from django.forms.utils import ErrorList
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from cubane.forms import BaseModelForm, BaseForm, SectionField, FilterFormMixin
from cubane.ishop import get_order_model
from cubane.ishop.forms import *
from cubane.ishop.apps.merchant.customers.forms import BrowseCustomerField
from cubane.ishop.models import OrderBase
from cubane.models import Country
from cubane.ishop.basket import Basket
from cubane.postcode.forms import PostcodeLookupField
import datetime


class BasketWidget(forms.Widget):
    """
    Form widget for rendering order summary information.
    """
    def __init__(self, *args, **kwargs):
        super(BasketWidget, self).__init__(*args, **kwargs)
        self.order = None
        self.basket = None


    def render(self, name, value, attrs=None, renderer=None):
        return render_to_string('cubane/ishop/elements/order/basket/basket_frame.html', context={
            'order': self.order,
            'basket': self.basket,
            'request': self.basket.request
        })


class BasketField(forms.Field):
    """
    Form field for presenting and editing order line items.
    """
    widget = BasketWidget


    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', False)
        super(BasketField, self).__init__(*args, **kwargs)


    def widget_attrs(self, widget):
        attrs = super(BasketField, self).widget_attrs(widget)
        attrs['class'] = 'no-label'
        return attrs


class OrderFilterForm(BaseModelForm, FilterFormMixin):
    class Meta:
        model = get_order_model()
        fields = '__all__'


    def __init__(self, *args, **kwargs):
        super(OrderFilterForm, self).__init__(*args, **kwargs)
        self.add_filter_by_created_on()


class OrderForm(BaseModelForm):
    ADDRESS_NAMES = [
        'company',
        'address1',
        'address2',
        'address3',
        'city',
        'county',
        'postcode',
        'country'
    ]


    class Meta:
        model = get_order_model()
        fields = [
            # status
            'status',

            # tracking
            'tracking_provider',
            'tracking_code',

            # customer
            'customer',
            'email',
            'telephone',

            # details
            'special_requirements',

            # billing
            'billing_postcode_lookup',
            'full_name',
            'billing_company',
            'billing_address1',
            'billing_address2',
            'billing_address3',
            'billing_city',
            'billing_county',
            'billing_postcode',
            'billing_country',

            # delivery
            'delivery_postcode_lookup',
            'delivery_name',
            'delivery_company',
            'delivery_address1',
            'delivery_address2',
            'delivery_address3',
            'delivery_city',
            'delivery_county',
            'delivery_postcode',
            'delivery_country'
        ]
        tabs = [
            {
                'title': 'Line Items',
                'fields': [
                    '_basket'
                ]
            }, {
                'title': 'Status and Tracking',
                'fields': [
                    # status
                    'status',

                    # tracking
                    'tracking_provider',
                    'tracking_code'
                ]
            }, {
                'title': 'Details',
                'fields': [
                    # customer
                    'customer',
                    'email',
                    'telephone',

                    # details
                    'special_requirements',

                    # billing
                    'billing_postcode_lookup',
                    'full_name',
                    'billing_company',
                    'billing_address1',
                    'billing_address2',
                    'billing_address3',
                    'billing_city',
                    'billing_county',
                    'billing_postcode',
                    'billing_country',

                    # delivery
                    'delivery_postcode_lookup',
                    'delivery_name',
                    'delivery_company',
                    'delivery_address1',
                    'delivery_address2',
                    'delivery_address3',
                    'delivery_city',
                    'delivery_county',
                    'delivery_postcode',
                    'delivery_country'
                ]
            }
        ]
        sections = {
            'status': 'Order Status',
            'tracking_provider': 'Order Delivery Tracking',
            'customer': 'Customer Information',
            'special_requirements': 'Customer Details',
            'billing_postcode_lookup': 'Billing Address',
            'delivery_postcode_lookup': 'Delivery Address',
        }


    _basket = BasketField()

    customer = BrowseCustomerField(
        required=False,
        help_text='The registered customer of this order; otherwise this order is a Guest Checkout.'
    )

    tracking_provider = forms.ChoiceField(
        label='Tracking Provider',
        choices=[],
        required=False,
        help_text='Choose the tracking provider that is tracking the delivery of this order.'
    )

    billing_postcode_lookup = PostcodeLookupField(
        label='Find Address',
        address1='id_billing_address1',
        address2='id_billing_address2',
        address3='id_billing_address3',
        address4=None,
        locality=None,
        city='id_billing_city',
        county='id_billing_county',
        postcode='id_billing_postcode'
    )


    delivery_postcode_lookup = PostcodeLookupField(
        label='Find Address',
        address1='id_delivery_address1',
        address2='id_delivery_address2',
        address3='id_delivery_address3',
        address4=None,
        locality=None,
        city='id_delivery_city',
        county='id_delivery_county',
        postcode='id_delivery_postcode'
    )


    def get_available_status_choices(self, instance):
        """
        Return list of available status choices that are applicable for the given order.
        """
        choices = OrderBase.BACKEND_STATUS_CHOICES_FILTER

        new_choices = []
        if instance.click_and_collect:
            for choice in choices:
                if not choice[0] == OrderBase.STATUS_PARTIALLY_SHIPPED and not choice[0] == OrderBase.STATUS_SHIPPED:
                    new_choices.append(choice)
        else:
            for choice in choices:
                if not choice[0] == OrderBase.STATUS_READY_TO_COLLECT:
                    new_choices.append(choice)

        if instance.customer_not_present:
            # created via backend (customer not present)
            new_choices = filter(lambda c: c[0] in OrderBase.CUSTOMER_NOT_PRESENT_STATUS, new_choices)
        elif instance.is_invoice:
            # pay by invoice orders do not have any payment-related states
            new_choices = filter(lambda c: c[0] in OrderBase.INVOICE_STATUS, new_choices)
        elif instance.is_zero_amount_checkout:
            # zero amount checkout do not have payment-related status
            new_choices = filter(lambda c: c[0] in OrderBase.ZERO_AMOUNT_CHECKOUT_STATUS, new_choices)
        else:
            # regular non-invoice orders do not have invoice-related status
            new_choices = filter(lambda c: c[0] in OrderBase.PAYMENT_STATUS, new_choices)

        return new_choices


    def clean(self):
        d = super(OrderForm, self).clean()
        click_and_collect = self.basket.click_and_collect

        # clean billing address
        clean_company(self, d, 'billing_company')
        clean_address_line(self, d, 'billing_address1')
        clean_address_line(self, d, 'billing_address2')
        clean_address_line(self, d, 'billing_address3')
        clean_city(self, d, 'billing_city')
        clean_county(self, d, 'billing_county', 'billing_country')
        clean_postcode(self, d, 'billing_postcode', 'billing_country')

        # clean delivery address
        if not click_and_collect:
            # setup default values for delivery address based on billing address
            for fieldname in self.ADDRESS_NAMES:
                delivery_fieldname = 'delivery_%s' % fieldname
                if not d.get(delivery_fieldname):
                    self.cleaned_data[delivery_fieldname] = d[delivery_fieldname] = d.get('billing_%s' % fieldname)

            # clean delivery address
            clean_company(self, d, 'delivery_company')
            clean_address_line(self, d, 'delivery_address1')
            clean_address_line(self, d, 'delivery_address2')
            clean_address_line(self, d, 'delivery_address3')
            clean_city(self, d, 'delivery_city')
            clean_county(self, d, 'delivery_county', 'delivery_country')
            clean_postcode(self, d, 'delivery_postcode', 'delivery_country')

        # make delivery address fields required if not click and collect
        if not click_and_collect:
            address1 = d.get('delivery_address1')
            city = d.get('delivery_city')
            postcode = d.get('delivery_postcode')
            country = d.get('delivery_country')

            if not address1: self.field_error('delivery_address1', self.ERROR_REQUIRED)
            if not city: self.field_error('delivery_city', self.ERROR_REQUIRED)
            if not postcode: self.field_error('delivery_postcode', self.ERROR_REQUIRED)
            if not country: self.field_error('delivery_country', self.ERROR_REQUIRED)

        # verify that we do not end up with an empty basket
        basket = Basket(self._request, prefix=self._instance.backend_basket_prefix)
        if basket.is_empty():
            from cubane.lib.mail import trigger_exception_email
            trigger_exception_email(self._request, 'Cannot save empty order.', data={
                'form': self,
                'formdata': d,
                'basket:': basket.save_to_dict(use_session=False)
            })
            raise forms.ValidationError('Cannot save empty order.')

        return d


    def configure(self, request, instance=None, edit=True):
        super(OrderForm, self).configure(request, instance, edit)

        if 'cubane.postcode' not in settings.INSTALLED_APPS:
            self.remove_field('delivery_postcode_lookup')
            self.remove_field('billing_postcode_lookup')
            self.Meta.sections['full_name'] = 'Billing Address'
            self.Meta.sections['delivery_name'] = 'Delivery Address'
            self.update_sections()

        # creating a new order should always have customer not present flag set
        if not edit:
            instance.customer_not_present = True
            instance.status = OrderBase.STATUS_NEW_ORDER

        # basket
        if request.method == 'POST':
            self.basket = Basket(request, prefix=instance.backend_basket_prefix)
        else:
            self.basket = Basket.restore_from_order(instance, request=request, prefix=instance.backend_basket_prefix, persistent=True)
        self.basket.save()
        self.fields['_basket'].widget.order = instance
        self.fields['_basket'].widget.basket = self.basket

        # status
        self.fields['status'].choices = self.get_available_status_choices(instance)

        # customer
        self.fields['customer'].queryset = User.objects.filter(is_staff=False, is_superuser=False, is_active=True)
        self.fields['customer'].label_from_instance = lambda user: user.full_name_email

        # tracking provider
        if len(settings.TRACKING_PROVIDERS) > 0:
            self.fields['tracking_provider'].choices = [('', '-------')] + [(name, name) for name, _ in settings.TRACKING_PROVIDERS]
        else:
            self.remove_field('tracking_provider')
            self.remove_field('tracking_code')
            self.update_sections()

        # initial countries for billing/delivery
        try:
            default_country = Country.objects.get(iso=settings.SHOP_DEFAULT_DELIVERY_COUNTRY_ISO)
            self.fields['billing_country'].initial = default_country
            self.fields['delivery_country'].initial = default_country
        except Country.DoesNotExist:
            pass


class ChangeOrderStatusForm(forms.Form):
    _status = SectionField(label='Status')

    status = forms.ChoiceField(choices=OrderBase.BACKEND_STATUS_CHOICES_FILTER)
    tracking_provider = forms.ChoiceField(choices=[], required=False)
    tracking_code = forms.CharField(max_length=255, required=False)
    delivery_type = forms.ChoiceField(
        label='Delivery Type',
        required=True,
        choices=OrderBase.BACKEND_DELIVERY_TYPE_CHOICES,
        help_text='Click and Collect or Delivery'
    )

    special_requirements = forms.CharField(
        label='Special Requirements',
        widget=forms.Textarea,
        required=False
    )

    _delivery = SectionField(label='Delivery')

    delivery_name = forms.CharField(
        label='Name',
        max_length='255',
        required=False
    )

    delivery_company = forms.CharField(
        label='Company',
        max_length=255,
        required=False
    )

    delivery_address1 = forms.CharField(
        label='Address1',
        max_length=255,
        required=False
    )

    delivery_address2 = forms.CharField(
        label='Address2',
        max_length=255,
        required=False
    )

    delivery_address3 = forms.CharField(
        label='Address3',
        max_length=255,
        required=False
    )

    delivery_city = forms.CharField(
        label='City',
        max_length=255,
        required=False
    )

    delivery_county = forms.CharField(
        label='County',
        max_length=255,
        required=False
    )

    delivery_postcode = forms.CharField(
        label='Postcode',
        max_length=255,
        required=False
    )

    delivery_country = forms.ModelChoiceField(
        label='Country',
        queryset=None,
        required=False
    )


    def configure(self, request, instance=None, edit=True):
        # determine available choices for status
        choices = OrderBase.BACKEND_STATUS_CHOICES_FILTER

        new_choices = []
        if instance.click_and_collect:
            for choice in choices:
                if not choice[0] == OrderBase.STATUS_PARTIALLY_SHIPPED and not choice[0] == OrderBase.STATUS_SHIPPED:
                    new_choices.append(choice)
        else:
            for choice in choices:
                if not choice[0] == OrderBase.STATUS_READY_TO_COLLECT:
                    new_choices.append(choice)

        if instance.customer_not_present:
            # created via backend (customer not present)
            new_choices = filter(lambda c: c[0] in OrderBase.CUSTOMER_NOT_PRESENT_STATUS, new_choices)
        elif instance.is_invoice:
            # pay by invoice orders do not have any payment-related states
            new_choices = filter(lambda c: c[0] in OrderBase.INVOICE_STATUS, new_choices)
        else:
            # regular non-invoice orders do not have invoice-related status
            new_choices = filter(lambda c: c[0] in OrderBase.PAYMENT_STATUS, new_choices)

        self.fields['status'].choices = new_choices

        # customer
        if len(settings.TRACKING_PROVIDERS) > 0:
            self.fields['tracking_provider'].choices = [('', '-------')] + [(name, name) for name, _ in settings.TRACKING_PROVIDERS]
        else:
            del self.fields['tracking_provider']
            del self.fields['tracking_code']

        # country
        self.fields['delivery_country'].queryset = Country.objects.all()


    def clean(self):
        d = self.cleaned_data

        if d:
            provider = d.get('tracking_provider')
            code = d.get('tracking_code')

            # provider is required if a tracking code is present
            if code and not provider:
                self._errors.setdefault('tracking_provider', ErrorList()).append('Tracking provider required for given tracking code.')

            # code is required if a tracking provider has been choosen
            if provider and not code:
                self._errors.setdefault('tracking_code', ErrorList()).append('Tracking code required for chosen tracking provider.')

            # delivery details are required, if this is a delivery order
            delivery_type = int(d.get('delivery_type'))
            if delivery_type == OrderBase.BACKEND_DELIVERY_TYPE_DELIVERY:
                if not d.get('delivery_address1'):
                    self._errors.setdefault('delivery_address1', ErrorList()).append('Address1 is required for delivery orders.')

                if not d.get('delivery_city'):
                    self._errors.setdefault('delivery_city', ErrorList()).append('City is required for delivery orders.')

                if not d.get('delivery_postcode'):
                    self._errors.setdefault('delivery_postcode', ErrorList()).append('Postcode is required for delivery orders.')

                if not d.get('delivery_country'):
                    self._errors.setdefault('delivery_country', ErrorList()).append('Country is required for delivery orders.')

        return d


class ApproveOrderForm(forms.Form):
    pass


class RejectOrderForm(forms.Form):
    reject_msg = forms.CharField(
        label='Reason for rejection',
        max_length=5000,
        required=True,
        help_text='Provide a brief summary on why you rejected the order. This text is presented to the customer.',
        widget=forms.Textarea(attrs={'class': 'full'})
    )


class CancelOrderForm(forms.Form):
    cancel_msg = forms.CharField(
        label='Reason for cancelation',
        max_length=5000,
        required=True,
        help_text='Provide a brief summary on why this order has been cancelled. This text is presented to the customer and might also be submitted to external payment or loan application systems.',
        widget=forms.Textarea(attrs={'class': 'full'})
    )
