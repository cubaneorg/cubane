# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from cubane.cms.forms import SettingsForm, BrowsePagesField
from cubane.media.forms import BrowseImagesField
from cubane.forms import BaseModelForm
from cubane.forms import NumberInput
from cubane.ishop.models import ProductBase
from cubane.usstates import states
import re
import decimal


def clean_first_name(form, d):
    """
    Clean first name.
    """
    first_name = d.get('first_name')
    if first_name:
        form.cleaned_data['first_name'] = first_name.strip().title()


def clean_last_name(form, d):
    """
    Clean last name.
    """
    last_name = d.get('last_name')
    if last_name:
        form.cleaned_data['last_name'] = last_name.strip().title()


def clean_company(form, d, attrname='company'):
    """
    Clean company name.
    """
    company = d.get(attrname)
    if company:
        form.cleaned_data[attrname] = company.strip().title()


def clean_address_line(form, d, attrname):
    """
    Clean the address line with the given name.
    """
    address = d.get(attrname)
    if address:
        form.cleaned_data[attrname] = address.strip().title()


def clean_address_lines(form, d):
    """
    Clean address line 1 to 3.
    """
    clean_address_line(form, d, 'address1')
    clean_address_line(form, d, 'address2')
    clean_address_line(form, d, 'address3')


def clean_city(form, d, attrname='city'):
    """
    Clean city.
    """
    city = d.get(attrname)
    if city:
        form.cleaned_data[attrname] = city.strip().title()


def clean_county(form, d, county_name='county', country_name='country'):
    """
    Clean county or US state.
    """
    country = d.get(country_name)
    if country:
        county = d.get(county_name, '')
        if country.iso == 'US':
            county = county.strip()

            is_state_valid = False
            for state in states.US_STATES:
                # check if someone typed iso code
                if county.upper() == state['iso']:
                    is_state_valid = True
                    county = county.upper()
                    break
                # check if someone typed full name
                if county.lower() == state['title'].lower():
                    is_state_valid = True
                    county = state['iso']
                    break

            if not is_state_valid:
                form.field_error(county_name, 'This state doesnt\'t exist.')
        else:
            county = county.strip().title()

        form.cleaned_data[county_name] = county


def clean_postcode(form, d, postcode_name='postcode', country_name='country'):
    """
    Clean postcode.
    """
    country = d.get(country_name)
    postcode = d.get(postcode_name)

    # make postcode uppercase and remove spaces
    if postcode:
        postcode = postcode.strip().upper()

        # for UK postcodes, remove all spaces and add the correct space
        # where needed.
        if country and country.iso == 'GB':
            postcode = re.sub(r' ', '', postcode)
            m = re.match(r'^([A-Z]{1,2}[0-9R][0-9A-Z])?([0-9][ABD-HJLNP-UW-Z]{2})$', postcode)
            if m:
                postcode = '%s %s' % (m.group(1), m.group(2))
        form.cleaned_data[postcode_name] = postcode


def clean_address(form, d):
    """
    Clean the address information for given form data d of given form.
    """
    clean_first_name(form, d)
    clean_last_name(form, d)
    clean_company(form, d)
    clean_address_lines(form, d)
    clean_city(form, d)
    clean_county(form, d)
    clean_postcode(form, d)
    return d


def clean_price(form, attr_name, d):
    """
    Clean price information
    """
    price = d.get(attr_name)
    if price:
        if price < decimal.Decimal('0.00'):
            form.field_error(attr_name, 'Price cannot be negative.')
    return price


class ShopSettingsForm(SettingsForm):
    """
    Form for editing website-wide settings (including CMS settings and Shop Settings).
    """
    class Meta:
        widgets = {
            'products_per_page': NumberInput(),
            'max_products_per_page': NumberInput(),
            'related_products_to_show': NumberInput(),
            'max_quantity': NumberInput()
        }
        tabs = [
            {
                'title': 'Shop',
                'fields': [
                    'products_per_page',
                    'max_products_per_page',
                    'related_products_to_show',

                    'order_id',
                    'order_id_prefix',
                    'order_id_suffix',

                    'max_quantity',
                    'guest_checkout',
                    'stocklevel',
                    'special_requirements',

                    'terms_page',
                    'image_placeholder',

                    'sku_is_barcode',
                    'barcode_system',

                    'mail_subject_prefix',
                    'mail_notify_address',
                    'mail_from_address',
                    'shop_email_template',

                    'ordering_options',
                    'ordering_default'
                ]
            }
        ]
        sections = {
            'products_per_page': 'Pagination',
            'order_id': 'Order Reference Number',
            'max_quantity': 'Options',
            'terms_page': 'T&C\'s and Image Placeholder',
            'sku_is_barcode': 'SKU and Barcodes',
            'mail_subject_prefix': 'Email Notification',
            'ordering_options': 'Product Ordering'
        }


    terms_page = BrowsePagesField(
        required=False,
        help_text='Page that represents the terms and conditions of the shop.'
    )

    shop_email_template = BrowsePagesField(
        required=False,
        help_text='Select the page that is used to send the shop email ' + \
                  'to customers who are using the shopping system ' + \
                  'on the website.'
    )

    image_placeholder = BrowseImagesField(
        required=False,
        help_text='Choose an image that is presented as a placeholder ' + \
                  'image in case we are unable to present an image, ' + \
                  'for example a missing category or product image.'
    )


    def clean(self):
        d = super(ShopSettingsForm, self).clean()

        # product ordering
        ordering_options = d.get('ordering_options')
        ordering_default = d.get('ordering_default')
        if ordering_options and ordering_default:
            if ordering_default not in ordering_options:
                self.field_error(
                    'ordering_default',
                    'This option is currently not presented to customers. ' + \
                    'Please choose a different option or make this option ' + \
                    'available to customers.'
                )

        # sku and barcodes
        sku_is_barcode = d.get('sku_is_barcode')
        barcode_system = d.get('barcode_system')
        if sku_is_barcode and not barcode_system:
            self.field_error('barcode_system', 'A default barcode is required when using SKU numbers as barcodes.')

        return d


class ShopEntityForm(BaseModelForm):
    """
    Base class for editing shop entities. Derive from this form in order to
    create new shop entity forms for your specific business objects.
    """
    pass
