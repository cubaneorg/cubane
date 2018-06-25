# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.forms.widgets import TextInput


class PostcodeLookupWidget(forms.TextInput):
    group_class = 'postcode-lookup-group'


class PostcodeLookupField(forms.CharField):
    """
    Simple Wrapper over InputField
    """
    widget = PostcodeLookupWidget


    def __init__(
        self,
        label='Postcode',
        address1='id_address1',
        address2='id_address2',
        address3='id_address3',
        address4=None,
        locality=None,
        city='id_city',
        county='id_county',
        postcode='id_postcode',
        single_field=None,
        max_length=10,
        size=10,
        custom_css=None,
        placeholder=None,
        prefix=None
    ):
        self.address_line_1   = address1
        self.address_line_2   = address2
        self.address_line_3   = address3
        self.address_line_4   = address4
        self.address_locality = locality
        self.address_city     = city
        self.address_county   = county
        self.address_postcode = postcode
        self.single_field     = single_field
        self.size             = size
        self.custom_css       = custom_css
        self.placeholder      = placeholder
        self.prefix           = prefix

        super(PostcodeLookupField, self).__init__(label=label, required=False, max_length=max_length)


    def widget_attrs(self, widget):
        attrs = super(PostcodeLookupField, self).widget_attrs(widget)
        if isinstance(widget, TextInput):
            attrs['autocomplete'] = 'off'
            attrs['autocorrect'] = 'off'
            attrs['autocapitalize'] = 'off'
            attrs['spellcheck'] = 'off'

            if self.single_field is not None:
                attrs['data-single-field'] = self.ref_name(self.single_field)
            else:
                if self.address_line_1 is not None:
                    attrs['data-address-line-1'] = self.ref_name(self.address_line_1)
                if self.address_line_2 is not None:
                    attrs['data-address-line-2'] = self.ref_name(self.address_line_2)
                if self.address_line_3 is not None:
                    attrs['data-address-line-3'] = self.ref_name(self.address_line_3)
                if self.address_line_4 is not None:
                    attrs['data-address-line-3'] = self.ref_name(self.address_line_4)
                if self.address_locality is not None:
                    attrs['data-address-locality'] = self.ref_name(self.address_locality)
                if self.address_city is not None:
                    attrs['data-address-city'] = self.ref_name(self.address_city)
                if self.address_county is not None:
                    attrs['data-address-county'] = self.ref_name(self.address_county)

            if self.address_postcode is not None:
                attrs['data-address-postcode'] = self.ref_name(self.address_postcode)
            if self.placeholder is not None:
                attrs['placeholder'] = self.placeholder
            else:
                attrs['placeholder'] = 'Postcode ...'

            attrs['data-size'] = self.size

            attrs['class'] = 'postcode-lookup'

            if self.custom_css is not None:
                attrs['class'] = '%s %s' % (attrs['class'], self.custom_css)
        return attrs


    def ref_name(self, name):
        if self.prefix:
            if name.startswith('id_'):
                return 'id_%s_%s' % (self.prefix, name[3:])
            else:
                return 'id_%s%s' % (self.prefix, name)
        else:
            return name