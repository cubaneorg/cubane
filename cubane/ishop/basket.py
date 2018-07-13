# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from django.db.models import Q, F, Prefetch
from django.core.exceptions import FieldDoesNotExist
from django.template import Template, Context
from cubane.forms import BaseForm
from cubane.models import Country
from cubane.ishop import get_product_model, get_category_model
from cubane.ishop.models import VarietyAssignment, Voucher
from cubane.ishop.models import DeliveryOption, ProductDeliveryOption
from cubane.ishop.models import ProductSKU, FinanceOption, ProductCategory
from cubane.ishop.apps.shop.basket.forms import AddToBasketForm
from cubane.media.models import Media
from cubane.lib.libjson import decode_json, to_json_response
from cubane.lib.args import list_of, clean_dict
from cubane.lib.template import get_template
import hashlib
import decimal
import datetime


class DeliveryOptionsFrom(BaseForm):
    delivery_option = forms.ChoiceField(
        label='Delivery Method',
        required=True,
        choices=()
    )

    click_and_collect = forms.BooleanField(
        label='Click and Collect',
        required=False,
        help_text='Tick, if this order is a \'Click and Collect\' order.'
    )


    def configure(self, request, choices, option, click_and_collect):
        self._request = request
        self.fields['delivery_option'].choices = choices

        if option:
            self.fields['delivery_option'].initial = option.id

        self.fields['click_and_collect'].initial = click_and_collect


def save_decimal(d):
    """
    Because Decimal is not JSON-serialisable by default, we convert
    currency values from Decimal to integers (pence).
    """
    if d is None:
        return None

    return int(d * 100)


def load_decimal(pence):
    """
    Because Decimal is not JSON-serialisable by default, we convert
    currency values from Decimal to integers (pence) and back.
    """
    if pence is None:
        return None

    return decimal.Decimal(pence / decimal.Decimal('100.0'))


def get_hash(product, variety_options=None, custom=None, labels=None):
    """
    Return a unique hash for the given combination of product,
    variety options, custom properties and custom text labels.
    """
    if custom == None:
        custom = {}

    # sort variety options by key
    variety_options = sorted(list_of(variety_options), key=lambda x: x.id)

    # sort custom properties by key
    if custom is not None:
        sorted_custom_pairs = sorted(custom.items(), key=lambda x: x[0])
    else:
        sorted_custom_pairs = []

    # sort custom labels by key
    if labels is not None:
        sorted_labels_pairs = sorted(labels.items(), key=lambda x: x[0])
    else:
        sorted_labels_pairs = []

    s = unicode(product.id) + \
        '-'.join([unicode(option.id) for option in variety_options]) + \
        '-'.join(['%s=%s' % (k, v) for k, v in sorted_custom_pairs])

    if sorted_labels_pairs:
        s += '-'.join(['%s=%s' % (k, v) for k, v in sorted_labels_pairs])

    return hashlib.sha224(s.encode('utf-8')).hexdigest()


def get_legacy_hash(product_id, variety_option_ids=None, custom=None, labels=None):
    """
    Return a unique hash for the given combination of product,
    variety options, custom properties and custom text labels where
    the actual entity objects are not necessarily available.
    """
    if custom == None:
        custom = {}

    # sort variety options by key
    variety_option_ids = sorted(list_of(variety_option_ids))

    # sort custom properties by key
    if custom is not None:
        sorted_custom_pairs = sorted(custom.items(), key=lambda x: x[0])
    else:
        sorted_custom_pairs = []

    # sort custom labels by key
    if labels is not None:
        sorted_labels_pairs = sorted(labels.items(), key=lambda x: x[0])
    else:
        sorted_labels_pairs = []

    s = unicode(product_id) + \
        '-'.join([unicode(option_id) for option_id in variety_option_ids]) + \
        '-'.join(['%s=%s' % (k, v) for k, v in sorted_custom_pairs])

    if sorted_labels_pairs:
        s += '-'.join(['%s=%s' % (k, v) for k, v in sorted_labels_pairs])

    return hashlib.sha224(s.encode('utf-8')).hexdigest()


def get_add_to_basket_price_html(request, product):
    """
    Return the basket price (html).
    """
    template = get_template('cubane/ishop/elements/basket/basket_price.html')
    context = {
        'product': product
    }
    return template.render(context, request)


def get_basket_variety_update(request, product):
    """
    Update add to basket form to reflect the price and variety options.
    """
    html = ''
    errors = False
    item = None

    # create form
    form = AddToBasketForm(
        request.POST,
        request=request,
        product=product,
        price_calculation=True
    )

    # validate
    if form.is_valid():
        d = form.cleaned_data

        # create basket item
        item = BasketItem(
            product,
            form.get_variety_options(),
            quantity=1
        )
    else:
        errors = form.errors

    # generate new add to basket form markup
    if item:
        html = get_add_to_basket_price_html(request, item.total_product)

    # return result (json)
    return to_json_response({
        'success': not errors,
        'html': html,
        'errors': errors
    })


class BasketItem(object):
    """
    Individual item of the basket (product, variety options and quantity)
    """
    def __init__(self, product, variety_options=None, quantity=1, custom=None, labels=None):
        variety_options = list_of(variety_options)

        # placeholder (in case the underlying database data is gone)
        self.placeholder = {}

        # product
        self._is_frozen = False
        self.product = product
        self.product_id = None
        self.processed = False

        if product:
            self.product_id = product.pk

        # properties
        self._sku = None
        self.sku_id = None
        self.sku_code = None
        self.sku_barcode = None
        self.sku_price = None
        self.variety_options = variety_options
        self._variety_assignments = VarietyAssignment.objects.filter(
            product=self.product, variety_option__in=self.variety_options
        )
        self.custom = custom
        self.quantity = quantity
        self.variety_option_ids = [option.id for option in variety_options]
        self.labels = labels

        # hash
        if product is not None:
            self.hash = get_hash(product, variety_options, custom, labels)
        else:
            self.hash = ''

        # load matching sku record for this product
        if self.product is not None:
            self.load_sku(self.product, self.variety_options)

        # construct label values
        BasketItem.load_label_values(self.variety_options, self._variety_assignments, self.labels)


    def save_to_dict(self, use_session=True):
        """
        Save this basket item to be serialised into the session (JSON).
        """
        d = {
            'product_id': self.product_id,
            'processed': self.processed,
            'sku_id': self.sku_id,
            'sku_code': self.sku_code,
            'sku_barcode': self.sku_barcode,
            'custom': self.custom,
            'labels': self.labels,
            'quantity': self.quantity,
            'hash': self.hash,
            'variety_option_ids': self.variety_option_ids,
            'placeholder': self.placeholder
        }

        if (not use_session or self.is_frozen) and not d.get('placeholder'):
            d['placeholder'] = {
                'title':                            self.title,
                'excerpt':                          self.excerpt,
                'image_id':                         self.product.image_id if self.product else self.placeholder.get('image_id'),
                'variety_data':                     self.variety_data,
                'product_price':                    self.product_price.quantize(decimal.Decimal('.01')),
                'total_product':                    self.total_product.quantize(decimal.Decimal('.01')),
                'total_varieties':                  self.total_varieties.quantize(decimal.Decimal('.01')),
                'total_product_without_deposit':    self.total_product_without_deposit.quantize(decimal.Decimal('.01')),
                'total':                            self.total.quantize(decimal.Decimal('.01')),
                'total_without_deposit':            self.total_without_deposit.quantize(decimal.Decimal('.01')),
                'total_discountable':               self.total_discountable.quantize(decimal.Decimal('.01')),
                'quantity':                         self.quantity,
                'deposit_only':                     self.deposit_only,
                'deposit':                          self.deposit,
                'barcode':                          self.barcode,
                'is_pre_order':                     self.is_pre_order,
                'is_loan_exempt':                   self.is_loan_exempt,
                'is_exempt_from_free_delivery':     self.is_exempt_from_free_delivery,
                'is_exempt_from_discount':          self.is_exempt_from_discount,
                'is_non_returnable':                self.is_non_returnable,
                'is_collection_only':               self.is_collection_only,
                'part_number':                      self.part_number,
                'icon_url':                         self.icon_url,
                'url':                              self.get_absolute_url(),
                'get_absolute_url':                 self.get_absolute_url(),
                'get_absolute_url_with_varieties':  self.get_absolute_url_with_varieties(),
                'product_id':                       self.product_id,
                'variety_option_ids':               self.variety_option_ids,
                'varieties': [{
                    'variety_option': {
                        'variety': {
                            'title': assignment.variety_option.variety.title,
                            'display_title': assignment.variety_option.variety.display_title
                        },
                        'title': assignment.variety_option.title,
                        'text_label': assignment.variety_option.text_label,
                        'text_label_value': assignment.variety_option.text_label_value if hasattr(assignment.variety_option, 'text_label_value') else None,
                        'price': assignment.price
                    }
                } for assignment in self._variety_assignments],
                'sku': {
                    'id': self.sku_id,
                    'code': self.sku_code,
                    'barcode': self.sku_barcode,
                    'price': self.sku_price
                },
                'custom_properties': self.custom_properties,
                'labels': self.labels,
                'image_attribute_url': self.image_attribute_url
            }

        return d


    @classmethod
    def from_dict(self, d):
        """
        Return a new basket item that has been restored from the given dict d.
        """
        item = BasketItem(None)
        item.product_id = d.get('product_id')
        item.processed = d.get('processed', False)
        item.sku_id = d.get('sku_id')
        item.sku_code = d.get('sku_code')
        item.sku_barcode = d.get('sku_barcode')
        item.custom = d.get('custom')
        item.labels = d.get('labels')
        item.quantity = d.get('quantity')
        item.hash = d.get('hash')
        item.variety_option_ids = d.get('variety_option_ids', [])
        item.placeholder = d.get('placeholder', {})

        # patch placeholder data
        for assignment in item.placeholder.get('varieties', []):
            if not assignment.get('price'):
                assignment['price'] = assignment.get('variety_option', {}).get('price')

        return item


    @classmethod
    def load_label_values(cls, variety_options, variety_assignments, labels):
        """
        Load label values and inject them into variety options.
        """
        if labels:
            # options
            for option in variety_options:
                pk = unicode(option.pk)
                if pk in labels:
                    option.text_label_value = labels.get(pk)

            # assignment options
            for assignment in variety_assignments:
                pk = unicode(assignment.variety_option.pk)
                if pk in labels:
                    assignment.variety_option.text_label_value = labels.get(pk)


    def restore(self, products, variety_options, is_frozen=False):
        """
        Restore product and variety assignment objects based on internal
        product id and variety assignment id list (both from session) and
        the given list of products and variety assignments (both from database).
        Return True, if the product could be restored successfully, otherwise
        return False.
        """
        # frozen state
        self._is_frozen = is_frozen
        result = False

        # restore product
        found = False
        for p in products:
            if p.id == self.product_id:
                self.product = p
                found = True
                break

        # ensure variety ids is an array and not None
        if self.variety_option_ids is None:
            self.variety_option_ids = []

        # restore variety options
        self.variety_options = []
        if found:
            # restore variety options, remove missing options
            matched = []
            for _id in self.variety_option_ids:
                for option in variety_options:
                    if _id == option.id:
                        if _id not in matched:
                            matched.append(_id)

                        if option not in self.variety_options:
                            self.variety_options.append(option)

            missing = [_id for _id in self.variety_option_ids if _id not in matched]
            for _id in missing:
                self.variety_option_ids.remove(_id)

            # load SKU
            self.load_sku(self.product, self.variety_options)

            # load variety assignments
            self._variety_assignments = VarietyAssignment.objects.filter(
                product=self.product,
                variety_option__in=self.variety_options
            )

            # assign variety option labels
            BasketItem.load_label_values(self.variety_options, self._variety_assignments, self.labels)
            result = len(missing) == 0

        return result


    def load_sku(self, product, variety_options):
        """
        Load product SKU record based on given set of variety options.
        """
        sku = ProductSKU.objects.get_by_variety_options(product, variety_options)
        if sku is not None:
            self._sku = sku
            self.sku_id = sku.pk
            self.sku_code = sku.sku
            self.sku_barcode = sku.barcode
            self.sku_price = sku.price


    def freeze(self):
        """
        Freeze this basket item.
        """
        self._is_frozen = True


    @property
    def is_frozen(self):
        """
        Return True, if this basket item is frozen and should maintain it's
        original pricing information based on the time it was serialised.
        """
        return self._is_frozen


    @property
    def product(self):
        """
        Return the product that is associated with this basket item.
        """
        return self._product


    @product.setter
    def product(self, product):
        """
        Set the product for this basket item and maintain some internal state
        about the associated product.
        """
        self._product = product

        if product:
            self.product_id = product.id
            self._image = product.image


    @property
    def image(self):
        """
        Return the primary product image or None.
        """
        if not hasattr(self, '_image'):
            if self.is_frozen:
                self._image = None
                media_pk = self.placeholder.get('image_id')
                if media_pk:
                    try:
                        self._image = Media.objects.get(pk=media_pk, is_image=True)
                    except Media.DoesNotExist:
                        pass
            else:
                self._image = self.product.image

        return self._image


    @property
    def icon_url(self):
        """
        Return the url to the image of the product.
        """
        if self.product and self.product.image:
            return self.product.image.url
        elif self.image:
            return self.image.url
        else:
            return self.placeholder.get('icon_url')


    @property
    def image_attributes(self):
        """
        Return image customisation overwrite attributes (Kit Builder).
        """
        if not hasattr(self, '_image_attributes'):
            attr = {}
            if self.variety_options:
                for option in self.variety_options:
                    variety = option.variety
                    if variety.layer:
                        attr[variety.layer] = option.url_safe_color

            if attr:
                self._image_attributes = attr
            else:
                self._image_attributes = None
        return self._image_attributes


    @property
    def image_attribute_url(self):
        """
        Return image customisation attributes in url-encoded format.
        """
        attributes = self.image_attributes
        if attributes:
            return '&'.join(['%s=%s' % (attr, value) for attr, value in attributes.items()])
        else:
            return None


    @property
    def title(self):
        """
        Return the product title.
        """
        if self.is_frozen:
            return self.placeholder.get('title')
        else:
            return self.product.title


    @property
    def description(self):
        """
        Return the product description.
        """
        return self.product.description


    @property
    def excerpt(self):
        """
        Return a shortened version of the product dexcription (excerpt).
        """
        if self.is_frozen:
            return self.placeholder.get('excerpt')
        else:
            return self.product.get_excerpt()


    @property
    def custom_properties(self):
        """
        Return a list of custom variety properties sorted by label.
        """
        if self.is_frozen:
            return self.placeholder.get('custom_properties')
        else:
            if self.custom == None:
                return []

            sorted_pairs = sorted(self.custom.items(), key=lambda x: x[0])
            properties = settings.SHOP_CUSTOM_PROPERTIES

            return [{
                'name': k,
                'value': v,
                'label': properties.get(k, (k.title(), ))[0],
                'unit': properties.get(k, ('', ''))[1]
            } for k, v in sorted_pairs]


    @property
    def variety_data(self):
        """
        Return the exact variety data for this basket item.
        """
        if self.is_frozen:
            return self.placeholder.get('variety_data', {})
        else:
            d = {}
            for option in self.variety_options:
                if option.variety.slug:
                    d[option.variety.slug] = option.pk
            return d


    @property
    def variety_assignments(self):
        """
        Return a list of variety assignments that have been selected for this
        basket item.
        """
        if self.is_frozen:
            return self.placeholder.get('varieties', [])
        else:
            return self._variety_assignments


    @property
    def product_price(self):
        """
        Return the base price for this product (without any additional
        costs for varieties).
        """
        if self.is_frozen:
            return self.placeholder.get('product_price', decimal.Decimal('0.00'))
        elif self.product is not None and self.product.price is not None:
            return self.product.price
        else:
            return decimal.Decimal('0.00')


    @property
    def total_varieties(self):
        """
        Return the total amount for all variety options for this product
        (for one product only). The result only describes the additional price
        for varieties and does not include the base price of the product. Further
        the returned price is for one product (quanity=1) only and only contains
        varieties that are independent of SKU numbers.
        """
        if self.is_frozen:
            return self.placeholder.get('total_varieties', decimal.Decimal('0.00'))
        elif len(self.variety_options) > 0:
            v = sum([assignment.price for assignment in self._variety_assignments if not assignment.variety_option.variety.sku])
            return decimal.Decimal('0.00') if v == 0 else v
        else:
            return decimal.Decimal('0.00')


    @property
    def total_product(self):
        """
        Return the total amount for this product and variety options
        (for one product only, quantity=1).
        Or return deposit price if product has been chose to pay deposit only.
        """
        if self.is_frozen:
            return self.placeholder.get('total_product', decimal.Decimal('0.00'))
        elif self.deposit_only:
            return self.deposit
        else:
            return self.total_product_without_deposit


    @property
    def total_product_without_deposit(self):
        """
        Return the total amount without considering deposit.
        """
        # find SKU record for the current set of assigned varieties and
        # determine the new total base price for it through the SKU record
        # (if price is given and sku record is available).
        if self.is_frozen:
            return self.placeholder.get('total_product_without_deposit', decimal.Decimal('0.00'))
        elif self.sku_price is not None:
            return self.sku_price + self.total_varieties
        else:
            # default is product base price
            return self.product_price + self.total_varieties


    @property
    def total(self):
        """
        Return the total amount for this basket item
        (quantity times total product net).
        """
        if self.is_frozen:
            return self.placeholder.get('total', decimal.Decimal('0.00'))
        else:
            return self.quantity * self.total_product


    @property
    def total_without_deposit(self):
        """
        Return the total amount for this basket item (quantity times total product net) without considering deposit.
        """
        if self.is_frozen:
            return self.placeholder.get('total_without_deposit', self.total)
        else:
            return self.quantity * self.total_product_without_deposit


    def get_total_discountable(self, discounted_category_ids=None):
        """
        Return the total amount of this basket item that is discountable. Some
        products may be excluded from discounts. Further a discount is only
        given if the product matches any of the given categories.
        """
        if self.is_frozen:
            return self.placeholder.get('total_discountable', decimal.Decimal('0.00'))
        else:
            # deposit is excluded from discount
            if self.deposit_only:
                return decimal.Decimal('0.00')

            # excluded from discount?
            if self.product.exempt_from_discount:
                return decimal.Decimal('0.00')

            if discounted_category_ids and len(discounted_category_ids) > 0:
                # matches any of discounted categories?
                if self.product.category_id in discounted_category_ids:
                    return self.total
                else:
                    return decimal.Decimal('0.00')
            else:
                # no categories given, so every category is discounted...
                return self.total
    total_discountable = property(get_total_discountable)


    @property
    def is_pre_order(self):
        """
        Return True, if this basket item is a pre-order item.
        """
        if self.is_frozen:
            return self.placeholder.get('is_pre_order', False)
        else:
            return self.product.pre_order


    @property
    def is_loan_exempt(self):
        """
        Return True, if this basket item is exempt from loan applications.
        """
        if self.is_frozen:
            return self.placeholder.get('is_loan_exempt', False)
        else:
            return self.product.loan_exempt


    @property
    def is_exempt_from_free_delivery(self):
        """
        Return True, if this basket item is exempt from free deliveries.
        """
        if self.is_frozen:
            return self.placeholder.get('is_exempt_from_free_delivery', False)
        else:
            return self.product.exempt_from_free_delivery


    @property
    def is_exempt_from_discount(self):
        """
        Return True, if this basket item is exempt from discounts.
        """
        if self.is_frozen:
            return self.placeholder.get('is_exempt_from_discount', False)
        else:
            return self.product.exempt_from_discount


    @property
    def deposit_only(self):
        """
        Return True, if this product requires a deposit.
        """
        if self.is_frozen:
            return self.placeholder.get('deposit_only', False)
        else:
            return self.product.deposit_only


    @property
    def is_non_returnable(self):
        """
        Return True, if this product cannot be returned.
        """
        if self.is_frozen:
            return self.placeholder.get('is_non_returnable', False)
        else:
            return self.product.non_returnable


    @property
    def is_collection_only(self):
        """
        Return True, if this product is for collection only.
        """
        if self.is_frozen:
            return self.placeholder.get('is_collection_only', False)
        else:
            return self.product.collection_only


    @property
    def barcode(self):
        """
        Return the barcode of this basket item.
        """
        if self.is_frozen:
            return self.placeholder.get('barcode', None)
        else:
            return self.product.barcode


    @property
    def deposit(self):
        """
        Return the amount of deposit for this basket item.
        """
        if self.is_frozen:
            return self.placeholder.get('deposit', decimal.Decimal('0.00'))
        else:
            return self.product.deposit


    @property
    def sku(self):
        """
        Return the SKU for this basket item.
        """
        if self.is_frozen:
            _sku = self.placeholder.get('sku')
            if _sku and _sku.get('id'):
                return ProductSKU(
                    id=_sku.get('id'),
                    sku=_sku.get('code'),
                    barcode=_sku.get('barcode'),
                    price=_sku.get('price'),
                    enabled=True
                )
        else:
            return self._sku


    @property
    def part_number(self):
        """
        Return the part number of this basket item.
        """
        if self.is_frozen:
            return self.placeholder.get('part_number')
        else:
            return self.product.part_number


    def matches_hash(self, _hash):
        """
        Return True, if the given basket item matches the given hash value,
        which uniquly identifies a certain combination of product and variety options.
        """
        return self.hash == _hash


    def increase_quantity_by(self, quantity):
        """
        Increase the quantity of this basket item by given (positive) amount.
        """
        if quantity > 0:
            self.quantity += quantity


    def get_absolute_url(self):
        """
        Return the absolute url for the corresponding product details page.
        """
        if self.is_frozen:
            return self.placeholder.get('get_absolute_url')
        else:
            return self.product.get_absolute_url()


    def get_absolute_url_with_varieties(self):
        """
        Return the absolute url for the corresponding product details page that
        reflects the exact state of the basket item including all its varieties.
        """
        if self.is_frozen:
            return self.placeholder.get('get_absolute_url_with_varieties')
        else:
            data = self.variety_data
            if data:
                return '%s?%s' % (
                    self.get_absolute_url(),
                    '&'.join(['%s=%s' % (k, v) for k, v in data.items()])
                )
            else:
                return self.get_absolute_url()


    @property
    def url(self):
        if self.is_frozen:
            return self.placeholder.get('url')
        else:
            return self.get_absolute_url()


    def as_legacy_dict(self):
        """
        Return a key/value pair representation of this basket item for the
        purpose of representing it as JSON.
        """
        return {
            'title':                            self.title,
            'excerpt':                          self.excerpt,
            'product_price':                    self.product_price.quantize(decimal.Decimal('.01')),
            'total_product':                    self.total_product.quantize(decimal.Decimal('.01')),
            'total_product_without_deposit':    self.total_product_without_deposit.quantize(decimal.Decimal('.01')),
            'total':                            self.total.quantize(decimal.Decimal('.01')),
            'total_without_deposit':            self.total_without_deposit.quantize(decimal.Decimal('.01')),
            'quantity':                         self.quantity,
            'deposit_only':                     self.deposit_only,
            'icon_url':                         None if self.product.image == None else self.product.image.url,
            'url':                              self.get_absolute_url(),
            'get_absolute_url':                 self.get_absolute_url(),
            'get_absolute_url_with_varieties':  self.get_absolute_url_with_varieties(),
            'product_id':                       self.product_id,
            'variety_option_ids':               self.variety_option_ids,
            'varieties': [{
                'variety_option': {
                    'variety': {
                        'title': assignment.variety_option.variety.title,
                        'display_title': assignment.variety_option.variety.display_title
                    },
                    'title': assignment.variety_option.title,
                    'text_label': assignment.variety_option.text_label,
                    'text_label_value': assignment.variety_option.text_label_value if hasattr(assignment.variety_option, 'text_label_value') else None,
                    'price': assignment.price
                }
            } for assignment in self._variety_assignments],
            'sku': {
                'id': self.sku_id,
                'code': self.sku_code,
                'barcode': self.sku_barcode,
                'price': self.sku_price
            },
            'custom_properties': self.custom_properties,
            'labels': self.labels,
            'image_attribute_url': self.image_attribute_url
        }


    def to_ga_dict(self, extras=None):
        """
        Return a key/value poair representation of this basket item that
        contains relevant information for google analytics for eCommerce
        integrations.
        """
        if self.product:
            d = self.product.to_ga_dict(extras)
            d['variant'] = ', '.join([option.title for option in self.variety_options])
            d['quantity'] = self.quantity
            d['price'] = self.total_product
            return d
        else:
            return {}


    def __str__(self):
        return self.__unicode__()


    def __repr__(self):
        return self.__unicode__()


    def __unicode__(self):
        return '%s x %d (%s)' % (self.title, self.quantity, self.product_price)


class Basket(object):
    """
    Customer's Basket (Session based)
    """
    EU_COUNTRY_CODES = [
        'AT', 'BE', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU',
        'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI',
        'ES', 'SE'
    ]


    MESSAGE_PRE_ORDER = (
        'Due to an item in the basket being Pre-order only, the delivery may take longer than expected.',
        'Due to an item in the basket being Pre-order only, the delivery may take longer than expected.'
    )

    MESSAGE_FINANCE_OPTION = (
        'Thank you for considering our <strong>Finance Option</strong> for this purchase.',
        '<strong>Finance</strong> order.'
    )

    MESSAGE_FINANCE_AVAILABLE = (
        'There is a <strong>Finance Option</strong> available for this basket. Choose <strong>Finance</strong> during checkout.',
        '<strong>Finance Option</strong> available.'
    )

    MESSAGE_EXEMPT_FROM_LOAN = (
        'Unfortunatly we are currently unable to provide a Finance Option for the product <strong>{{ basket.loan_excempt_product }}</strong>.',
        '<strong>Finance Option</strong> not available for product <strong>{{ basket.loan_excempt_product }}</strong>.'
    )

    MESSAGE_TOO_LOW_FOR_LOAN = (
        'There is a <strong>Finance Option</strong> available for this basket, if you spend <strong>{% shop_price basket.loan_threshold %}</strong> or more. You would need to increase your basket value by <strong>{% shop_price basket.remaining_loan_total %}</strong> to qualify for a loan.',
        '<strong>Finance Option</strong> available for <strong>{% shop_price basket.loan_threshold %}</strong> or more (+<strong>{% shop_price basket.remaining_loan_total %}</strong> to qualify).'
    )

    MESSAGE_UNABLE_TO_RESTORE = 'This basket cannot be changed because some aspects of the basket could not be restored (for example a product may no longer exist).'

    MESSAGE_FROZEN_BASKET = 'This basket cannot be changed anymore (payment transaction started or completed).'


    def __init__(self, request=None, prefix=None, persistent=True):
        """
        Create a new basket instance based on the user's current session
        (if available). Otherwise an empty basket is created.
        """
        if prefix is None:
            prefix = settings.SHOP_BASKET_SESSION_VAR

        self.request = request
        self.prefix = prefix
        self.persistent = persistent
        self.placeholder = {}
        self._is_frozen = False
        self._unable_to_restore = False

        self.clear(save_basket=False)

        # load initial basket
        if persistent and self.is_stored_in_session():
            self.load()


    @classmethod
    def _restore_finance_option(self, finance_option_id):
        """
        Load the finance option with the given finance option id.
        """
        finance_option = None

        if finance_option_id is not None:
            try:
                finance_option = FinanceOption.objects.get(pk=finance_option_id)
            except FinanceOption.DoesNotExist:
                finance_option_id = None
        return (finance_option, finance_option_id)


    @classmethod
    def restore_from_order(cls, order, request=None, prefix=None, persistent=False):
        """
        Restore full basket from given order. Items where the underlying product
        no longer exist are restored partially.
        """
        basket = Basket(request, prefix=prefix, persistent=persistent)
        basket.load_from_order(order)
        return basket


    @classmethod
    def restore_from_legacy_dict(cls, d):
        """
        Restore parts of the basket based on the given dictionary by loading
        certain model instances from the database, which are injected back into
        the resulting dictionary. This will not reconstruct an entire basket
        instance but will allow to render the basket content on the screen.
        The resulting structure looks like a basket.
        """
        # load products and inject propper model instances
        d['items'] = d.pop('products', [])
        d['can_deliver'] = True
        d['has_pre_order_item'] = False
        product_ids = [i.get('product_id') for i in d.get('items', [])]

        # load product data
        if product_ids:
            if settings.SHOP_MULTIPLE_CATEGORIES:
                products = list(
                    get_product_model().objects.select_related('image').filter(pk__in=product_ids).prefetch_related(
                        Prefetch('categories', queryset=ProductCategory.objects.select_related('category').order_by('seq'))
                    ).distinct()
                )
            else:
                products = list(get_product_model().objects.select_related('category', 'image').filter(pk__in=product_ids))
        else:
            products = []

        # inject additional information about each product
        for p in products:
            for i in d.get('items', []):
                if i.get('product_id') == p.id:
                    i['product'] = p
                    i['image'] = p.image
                    if p.pre_order:
                        d['has_pre_order_item'] = True
                    if p.collection_only:
                        d['is_click_and_collect'] = True

        # totals
        for item in d.get('totals', []):
            d[item] = d.get('totals')[item]

        # restore variety options and assignments (mocks)
        for item in d.get('items', []):
            # fill in missing data
            for v in item.get('varieties'):
                variety = v.get('variety_option').get('variety')
                if not variety.get('display_title'):
                    variety['display_title'] = variety.get('title')

            # generate variety options and assignment mocks
            item['variety_options'] = [v.get('variety_option') for v in item.get('varieties')]
            item['variety_assignments'] = [{
                'variety_option': v.get('variety_option'),
                'price': v.get('variety_option').get('price')
            } for v in item.get('varieties')]

        # restore finance option
        finance_option, finance_option_id = Basket._restore_finance_option(d.get('finance_option_id'))
        d['finance_option_id'] = finance_option_id
        d['finance_option'] = finance_option

        return d


    def unable_to_restore(self):
        """
        Indicate that this basket could not be restored; perhaps due to a
        product that is non longer available. The basket is also frozen.
        """
        self._unable_to_restore = True
        self.freeze()


    def freeze(self):
        """
        Freeze this basket and all its items.
        """
        self._is_frozen = True
        for item in self.items:
            item.freeze()


    @property
    def was_unable_to_restore(self):
        """
        Return True, if this basket could not be restored entirely; perhaps
        because a product was no longer available. A basket in this state is
        also frozen.
        """
        return self._unable_to_restore


    @property
    def is_frozen(self):
        """
        Return True, if this basket is frozen and cannot be changed. A frozen
        basket will also reflect product information accurately based on the
        data that was in place when the basket was serialised and not
        necessarily contain up-to-date information as it would be if this basket
        would be editable.
        """
        return self._is_frozen


    @property
    def has_voucher(self):
        return self.voucher != None


    @property
    def can_deliver(self):
        """
        Return True, if we can deliver this basket according to the chosen
        delivery option and destination country.
        """
        return self._can_deliver(self.delivery_option)


    @property
    def is_quote_only(self):
        """
        Return True, if we can only quote for individual deliveries according to
        the chosen delivery option and destination country.
        """
        return self._is_quote_only(self.delivery_option)


    @property
    def items_with_barcode(self):
        """
        Return a list of basket items that have a barcode.
        """
        return filter(lambda item: item.barcode, self.items)


    def is_stored_in_session(self):
        """
        Return True, if a basket representation is stored in the given session.
        """
        return (
            self.request is not None and
            self.prefix is not None and
            (
                self.prefix in self.request.session or
                ('%s_BASKET' % self.prefix) in self.request.session
            )
        )


    def save(self):
        """
        Save current basket state within user's session.
        """
        if not self.request or not self.persistent: return

        # save to session
        self.request.session['%s_BASKET' % self.prefix] = self.save_to_dict(use_session=True)


    def save_to_dict(self, use_session=True):
        """
        Save this basket as a dictionary representation which can be stored in
        the user's session and/or order in JSON format.
        """
        d = {
            'ITEMS': [item.save_to_dict(use_session) for item in self.items],
            'VOUCHER': self.voucher.code if self.voucher else None,
            'BILLING_ADDRESS': self.save_address(self.billing_address),
            'DELIVERY_ADDRESS': self.save_address(self.delivery_address),
            'FINANCE_OPTION_ID': self.finance_option_id,
            'LOAN_DEPOSIT': self.loan_deposit,
            'NEWSLETTER': self.newsletter,
            'SPECIAL_REQ': self.special_req,
            'SURVEY': self.survey,
            'SIGNUP': self.signup,
            'UPDATE_PROFILE': self.update_profile,
            'DELIVERY_OPTION': self.delivery_option.id if self.delivery_option else None,
            'TERMS': self.terms,
            'CLICK_AND_COLLECT': self.click_and_collect,
            'FREE_DELIVERY_TO': self.free_delivery_to,
            'INVOICE': self.invoice,
            'INVOICE_NUMBER': self.invoice_number,
            'DEFAULT_DELIVERY': self.default_delivery,
            'CAN_EDIT_BILLING_ADDRESS': self.can_edit_billing_address,
            'CAN_EDIT_DELIVERY_ADDRESS': self.can_edit_delivery_address,
            'CUSTOM_TOTAL': save_decimal(self.custom_total)
        }

        if use_session:
            d['IS_FROZEN'] = self._is_frozen
            d['UNABLE_TO_RESTORE'] = self._unable_to_restore

        if (not use_session or self._is_frozen) and not d.get('PLACEHOLDER'):
            d['PLACEHOLDER'] = {
                'totals': self.get_totals()
            }

        return d


    def save_address(self, address):
        """
        Save billing or delivery address information to basket session (JSON)
        """
        if not address:
            address = {}

        country = address.get('country')
        name = address.get('name')
        title = address.get('title')
        first_name = address.get('first_name')
        last_name = address.get('last_name')
        telephone = address.get('telephone')
        email = address.get('email')
        state = address.get('state')

        d = {
            'company': address.get('company'),
            'address1': address.get('address1'),
            'address2': address.get('address2'),
            'address3': address.get('address3'),
            'city': address.get('city'),
            'county': address.get('county'),
            'postcode': address.get('postcode'),
            'country-iso': country.iso if country else address.get('country-iso')
        }

        if title: d['title'] = title
        if name: d['name'] = name
        if first_name: d['first_name'] = first_name
        if last_name: d['last_name'] = last_name
        if telephone: d['telephone'] = telephone
        if email: d['email'] = email
        if state: d['state'] = state

        return d


    def load(self):
        """
        Load and restore basket, all basket items and voucher from session. Previous versions of the shop
        system serialised basket data differently. We detect based on the session which version is used.
        """
        if not self.request: return

        key = '%s_BASKET' % self.prefix
        if key in self.request.session:
            d = self.request.session.get(key)
        else:
            d = self.get_dict_from_legacy_session(self.request.session)

        self.load_from_dict(d, restore_from_order=False, is_frozen=False)


    def get_dict_from_legacy_session(self, session):
        """
        Return the dict representation of the basket that was constructed from a legacy
        format stored in the given session.
        """
        return {
            'ITEMS': session.get(self.prefix, []),
            'VOUCHER': session.get('%s_VOUCHER' % self.prefix),
            'BILLING_ADDRESS': session.get('%s_BILLING_ADDRESS' % self.prefix, None),
            'DELIVERY_ADDRESS': session.get('%s_DELIVERY_ADDRESS' % self.prefix, None),
            'FINANCE_OPTION_ID': session.get('%s_FINANCE_OPTION_ID' % self.prefix, None),
            'LOAN_DEPOSIT': session.get('%s_LOAN_DEPOSIT' % self.prefix, None),
            'NEWSLETTER': session.get('%s_NEWSLETTER' % self.prefix, False),
            'SPECIAL_REQ': session.get('%s_SPECIAL_REQ' % self.prefix, None),
            'SURVEY': session.get('%s_SURVEY' % self.prefix, None),
            'SIGNUP': session.get('%s_SIGNUP' % self.prefix, None),
            'UPDATE_PROFILE': session.get('%s_UPDATE_PROFILE' % self.prefix, None),
            'DELIVERY_OPTION': self.delivery_option.id if self.delivery_option else None,
            'TERMS': session.get('%s_TERMS' % self.prefix, None),
            'CLICK_AND_COLLECT': session.get('%s_CLICK_AND_COLLECT' % self.prefix, False),
            'FREE_DELIVERY_TO': session.get('%s_FREE_DELIVERY_TO' % self.prefix, False),
            'INVOICE': session.get('%s_INVOICE' % self.prefix, False),
            'INVOICE_NUMBER': session.get('%s_INVOICE_NUMBER' % self.prefix, None),
            'DEFAULT_DELIVERY': session.get('%s_DEFAULT_DELIVERY' % self.prefix, False),
            'CAN_EDIT_BILLING_ADDRESS': session.get('%s_CAN_EDIT_BILLING_ADDRESS' % self.prefix, True),
            'CAN_EDIT_DELIVERY_ADDRESS': session.get('%s_CAN_EDIT_DELIVERY_ADDRESS' % self.prefix, True)
        }


    def load_from_dict(self, d, restore_from_order=False, is_frozen=False):
        """
        Load and restore basket from given dictionary representatioin
        """
        # frozen state
        self._is_frozen = d.get('IS_FROZEN', False) or is_frozen
        self._unable_to_restore = d.get('UNABLE_TO_RESTORE', False)

        # load basket items
        items_meta = d.get('ITEMS', [])
        self.items = []
        for item_meta in items_meta:
            item = BasketItem.from_dict(item_meta)
            self.items.append(item)

        # restore all basket items by loading product and variety assingments
        # from database (they are not stored within the session).
        product_ids = self.get_product_ids()
        variety_option_ids = self.get_variety_option_ids()
        products = list(
            get_product_model().objects \
                .select_related('category', 'image') \
                .prefetch_related('finance_options') \
                .filter(pk__in=product_ids, draft=False)
        )
        assignments = list(
            VarietyAssignment.objects \
                .select_related('variety_option', 'variety_option__variety') \
                .filter(
                    product_id__in=product_ids,
                    variety_option_id__in=variety_option_ids,
                    variety_option__variety__enabled=True
                )
        )
        variety_options = [assignment.variety_option for assignment in assignments]

        # restore all basket items and collect broken items that can no longer
        # be restored...
        broken_items = []
        for item in self.items:
            if not item.restore(products, variety_options, self._is_frozen):
                broken_items.append(item)

        # missing product?
        if broken_items:
            if not restore_from_order and not self._is_frozen:
                # restoring from session for a basket that is not frozen
                # -> simply remove broken item
                for item in broken_items:
                    self.items.remove(item)
            else:
                # restoring from order -> freeze
                self.unable_to_restore()

        # restore all basket meta data, like billing and delivery addresses
        # and other information...
        self.billing_address = self.load_address(d.get('BILLING_ADDRESS'))
        self.delivery_address = self.load_address(d.get('DELIVERY_ADDRESS'))
        self.loan_deposit = d.get('LOAN_DEPOSIT')
        self.newsletter = d.get('NEWSLETTER', False)
        self.special_req = d.get('SPECIAL_REQ')
        self.survey = d.get('SURVEY')
        self.signup = d.get('SIGNUP')
        self.update_profile = d.get('UPDATE_PROFILE')
        self.terms = d.get('TERMS')
        self.click_and_collect = d.get('CLICK_AND_COLLECT', False)
        self.free_delivery_to = d.get('FREE_DELIVERY_TO', False)
        self.invoice = d.get('INVOICE', False)
        self.invoice_number = d.get('INVOICE_NUMBER')
        self.default_delivery = d.get('DEFAULT_DELIVERY', False)
        self.can_edit_billing_address = d.get('CAN_EDIT_BILLING_ADDRESS', True)
        self.can_edit_delivery_address = d.get('CAN_EDIT_DELIVERY_ADDRESS', True)
        self.custom_total = load_decimal(d.get('CUSTOM_TOTAL'))
        self.placeholder = d.get('PLACEHOLDER', {})

        # load delivery option
        self.delivery_option = None
        delivery_option_id = d.get('DELIVERY_OPTION')
        if delivery_option_id:
            try:
                # load delivery option from database
                self.delivery_option = DeliveryOption.objects.get(pk=delivery_option_id, enabled=True)
            except DeliveryOption.DoesNotExist:
                # freeze if we cannot restore delivery option from order
                if restore_from_order:
                    self.unable_to_restore()

        # load voucher
        self.voucher = None
        voucher_code = d.get('VOUCHER')
        if voucher_code:
            if not self.set_voucher(voucher_code, restore_from_order or self._is_frozen):
                if restore_from_order:
                    # restore from order -> freeze
                    self.unable_to_restore()

        # load finance option
        finance_option_id = d.get('FINANCE_OPTION_ID')
        if finance_option_id:
            self.finance_option, self.finance_option_id = Basket._restore_finance_option(finance_option_id)
            if not self.supports_finance_option(self.finance_option):
                self.finance_option_id = None
                self.finance_option = None

                # restore from order -> freeze
                if restore_from_order:
                    self.unable_to_restore()


    def load_address(self, d):
        """
        Load address information from the given de-serialised JSON representation.
        """
        if d is None:
            d = {}

        # load country
        country_iso = d.get('country-iso')
        try:
            country = Country.objects.get(pk=country_iso)
        except Country.DoesNotExist:
            country = None

        title = d.get('title')
        first_name = d.get('first_name')
        last_name = d.get('last_name')
        telephone = d.get('telephone')
        email = d.get('email')
        state = d.get('state')
        name = d.get('name')

        address = {
            'company': d.get('company'),
            'address1': d.get('address1'),
            'address2': d.get('address2'),
            'address3': d.get('address3'),
            'city': d.get('city'),
            'county': d.get('county'),
            'postcode': d.get('postcode'),
            'country-iso': country_iso,
            'country': country
        }

        if name: address['name'] = name
        if title: address['title'] = title
        if first_name: address['first_name'] = first_name
        if last_name: address['last_name'] = last_name
        if telephone: address['telephone'] = telephone
        if email: address['email'] = email
        if state: address['state'] = state

        return clean_dict(address)


    def load_from_order(self, order):
        """
        Load basket data from given order.
        """
        if order.basket_json_v2 is not None:
            json = decode_json(order.basket_json_v2)
        else:
            json = decode_json(order.basket_json)

        if 'products' in json:
            # convert legacy JSON format into new format
            json = self.get_json_from_legacy_format(json, order)

        # load from json, keep broken items
        self.load_from_dict(json, restore_from_order=True, is_frozen=order.is_frozen)

        # patch placeholder if the basket is frozen and the placeholder is
        # not available (e.g. legacy basket encoding)
        if self.is_frozen and not self.placeholder.get('totals'):
            self.placeholder['totals'] = {
                'sub_total': order.sub_total,
                'delivery': order.delivery,
                'total': order.total,
                'quantity': order.basket_size
            }


    def get_json_from_legacy_format(self, d, order):
        """
        Return new JSON format representation of a basket based on the old
        format that was stored alongside legacy orders. Missing fields:
        - SIGNUP
        - UPDATE_PROFILE
        - TERMS
        - DEFAULT_DELIVERY
        - CAN_EDIT_BILLING_ADDRESS
        - CAN_EDIT_DELIVERY_ADDRESS
        """
        def get_json_from_legacy_item(item):
            sku = item.get('sku', {})
            item_d = {
                'product_id': item.get('product_id'),
                'deposit_only': item.get('deposit_only'),
                'sku_id': sku.get('id'),
                'sku_code': sku.get('code'),
                'sku_barcode': sku.get('barcode'),
                'sku_price': sku.get('price'),
                'labels': item.get('labels'),
                'quantity': item.get('quantity'),
                'variety_option_ids': item.get('variety_option_ids'),
                'placeholder': item
            }
            item_d['hash'] = get_legacy_hash(
                item_d.get('product_id'),
                item_d.get('variety_option_ids'),
                item_d.get('custom_properties'),
                item_d.get('labels')
            )
            return item_d

        # voucher
        voucher = d.get('voucher')
        if voucher is None: voucher = {}

        return {
            'ITEMS': [get_json_from_legacy_item(item) for item in d.get('products', [])],
            'VOUCHER': voucher.get('code'),
            'BILLING_ADDRESS': order.billing_address,
            'DELIVERY_ADDRESS': order.delivery_address,
            'FINANCE_OPTION_ID': d.get('finance_option_id'),
            'LOAN_DEPOSIT': d.get('loan_deposit'),
            'NEWSLETTER': order.customer.user.newsletter if order.customer else False,
            'SPECIAL_REQ': order.special_requirements,
            'SURVEY': order.survey,
            'DELIVERY_OPTION': order.delivery_option.pk if order.delivery_option else None,
            'CLICK_AND_COLLECT': order.click_and_collect,
            'FREE_DELIVERY_TO': order.free_delivery_to,
            'INVOICE': order.is_invoice,
            'INVOICE_NUMBER': order.invoice_number
        }


    def is_empty(self):
        """
        Return True, if this basket is empty, e.g. the count of basket item it
        contains is zero.
        """
        return len(self.items) == 0


    def is_deposit_only(self):
        """
        Return True, if all basket items are deposit only products.
        """
        for item in self.items:
            if item.deposit_only == False:
                return False
        return True


    def get_finance_options(self, consider_minimum_basket=True, consider_exempt=True):
        """
        Return a list of all finance options that qualify for this basket.
        """
        # empty basket
        if len(self.items) == 0:
            return []

        # loan disabled globally?
        if not settings.SHOP_LOAN_ENABLED:
            return []

        # if any product is except from loan, the entire
        # basket does NOT qualify
        if consider_exempt and self.is_exempt_from_loan():
            return []

        # frozen?
        if self.is_frozen:
            return []

        # collect all finance options that are applicable with min. basket value
        rates = FinanceOption.objects.filter(enabled=True).order_by('seq')
        if consider_minimum_basket:
            rates = rates.filter(min_basket_value__lte=self.total)
        rates = list(rates)

        # collect all per-product finance option assignments
        per_product_finance_option_ids = []
        for item in self.items:
            for finance_option in item.product.finance_options.all():
                per_product_finance_option_ids.append(finance_option.pk)

        # exclude rates where it only qualifies for specific products,
        # yet that product is not in the basket
        finance_options = []
        for rate in rates:
            if rate.per_product:
                if rate.pk not in per_product_finance_option_ids:
                    continue
            finance_options.append(rate)

        return finance_options


    def get_finance_options_queryset(self):
        """
        Return a queryset that describes the possible finance option a customer
        may choose from.
        """
        ids = [option.pk for option in self.get_finance_options()]
        return FinanceOption.objects.filter(pk__in=ids).order_by('seq')


    def supports_finance_option(self, finance_option):
        """
        Return True, if the given finance option qualifies for this basket.
        """
        if finance_option is None:
            return False

        ids = [option.pk for option in self.get_finance_options()]
        return finance_option.pk in ids


    def is_exempt_from_loan(self):
        """
        Return True, if at least one product in the basket is exempt from
        finance option/loan.
        """
        return self.loan_excempt_product() is not None


    def loan_excempt_product(self):
        """
        Return the first product within the basket that is exempt from
        finance options/loan.
        """
        for item in self.items:
            if item.is_loan_exempt or (item.is_pre_order and item.deposit):
                return item.product


    def is_available_for_loan(self):
        """
        Return True, if this basket can be purchases as a loan application.
        All basket items need to qualify for a loan application in order
        to finance this basket. Also the total basket value must be above a
        certain minimum threshold to qualify.
        """
        return len(self.get_finance_options()) > 0


    def is_available_for_loan_in_principal(self):
        """
        Return True, if this basket can be purchases as a loan application in
        principal. All basket items need to qualify for a loan application in
        order to finance this basket. The total basket may be below the
        threshold required.
        """
        return len(self.get_finance_options(
            consider_minimum_basket=False,
            consider_exempt=False
        )) > 0


    @property
    def loan_threshold(self):
        """
        Return the minimum amount of basket value that qualifies for a loan
        application based on the lowest threshold in the system for all
        finance options available in general.
        """
        thresholds = [r.min_basket_value for r in self.get_finance_options(consider_minimum_basket=False)]
        return min(thresholds)


    @property
    def remaining_loan_total(self):
        """
        Return the remaining total value that a customer would need to spend
        in addition to the current basket's total value in order to qualify
        for a loan application.
        """
        if self.is_available_for_loan_in_principal() and self.total < self.loan_threshold:
            return self.loan_threshold - self.total
        else:
            return decimal.Decimal('0.00')


    def get_difference_between_deposit_and_full_amount(self):
        """
        Return the difference between the full amount of the basket
        and the full amount for deposit only.
        """
        total = decimal.Decimal('0.00')
        for item in self.items:
            total += item.total_without_deposit - item.total
        return total


    def get_size(self):
        """
        Return the amount of items in the basket, which is the sum over the quantity for all
        products in the basket.
        """
        items = self.get_items()
        if len(items) > 0:
            return sum([item.quantity for item in items])
        else:
            return 0


    def get_special_requirements(self):
        """
        Return special requirements text.
        """
        return self.special_req
    special_requirements = property(get_special_requirements)


    def set_special_requirements(self, special_req):
        """
        Set special requirement text for the basket.
        """
        self.special_req = special_req


    def get_items(self):
        """
        Return a list of basket items.
        """
        return self.items


    def get_click_and_collect_items(self):
        """
        Return a list of basket items that are click and collect only products.
        """
        collection_only_items = []
        for item in self.items:
            if item.is_collection_only:
                collection_only_items.append(item)
        return collection_only_items
    click_and_collect_items = property(get_click_and_collect_items)


    def get_ga_items(self):
        """
        Return google analytics for eCommerce information for all basket items.
        """
        return [item.to_ga_dict() for item in self.items if item.product]
    ga_items = property(get_ga_items)


    def get_product_ids(self):
        """
        Return a list of all product ids across all basket items without dublicates.
        """
        return list(set([item.product_id for item in self.items]))


    def get_variety_option_ids(self):
        """
        Return a list of all variety option identifiers across all basket items
        without duplicates.
        """
        ids = set()
        for item in self.items:
            if item.variety_option_ids:
                ids = ids.union(item.variety_option_ids)
        return list(ids)


    def clear(self, save_basket=True):
        """
        Clear basket by removing all items.
        """
        self.items = []
        self.voucher = None
        self.billing_address = None
        self.delivery_address = None
        self.finance_option_id = None
        self.finance_option = None
        self.loan_deposit = None
        self.newsletter = False
        self.special_req = None
        self.survey = None
        self.signup = None
        self.update_profile = False
        self.delivery_option = None
        self.terms = False
        self.click_and_collect = False
        self.free_delivery_to = False
        self.invoice = False
        self.invoice_number = None
        self.default_delivery = False
        self.can_edit_billing_address = True
        self.can_edit_delivery_address = True
        self.custom_total = None

        if save_basket:
            self.save()


    def get_item_by_hash(self, _hash):
        """
        Return the basket item with the given hash value which uniquly identifies
        a certain combination of a product and variety options. If such a product
        is not within the basket, None is returned.
        """
        for item in self.items:
            if item.matches_hash(_hash):
                return item
        return None


    def get_item_by_product(self, product, variety_options=None, custom=None, labels=None):
        """
        Return the basket item with the given combination of product and variety
        options. If the basket does not contain such a combination, None is returned.
        """
        return self.get_item_by_hash(get_hash(product, variety_options, custom, labels))


    def add_item(self, product, variety_options=None, quantity=1, custom=None, labels=None):
        """
        Add given product with given variety options and quantity to the basket.
        If the qty is not a defined positive integer larger than 1, qyt is considered
        to be 0 and no product is added to the basket. The given set of variety options
        may be empty.

        Each item may have an arbitrary number of custom properties, such as
        measurements etc.

        In additional, any variety option may have a custom label text attached.
        """
        if self.is_frozen:
            return None

        if not product.can_be_added_to_basket(self.request):
            return None

        try:
            quantity = int(quantity)
        except ValueError:
            quantity = 0

        if quantity <= 0:
            return None

        item = self.get_item_by_product(product, variety_options, custom, labels)
        if item != None:
            # just update quantity. Product already inside the basket.
            item.increase_quantity_by(quantity)
        else:
            item = BasketItem(
                product,
                variety_options,
                quantity,
                custom,
                labels
            )
            self.items.append(item)

        return item


    def _match_voucher_time_interval(self, date_ref):
        """
        Return queryset filter arguments for filtering vouchers to match
        the given date reference (which is usually today's date).
        """
        return (
            (Q(valid_from__isnull=True) | Q(valid_from__lte=date_ref)) &
            (Q(valid_until__isnull=True) | Q(valid_until__gte=date_ref))
        )


    def set_voucher(self, voucher_code, restore_from_order_or_frozen=False):
        """
        Set the given voucher code for this basket. Returns True, if the voucher
        code is valid and has been applied to this basket successfully.
        """
        today = datetime.date.today()

        try:
            # find matching voucher, enabled and within valid time interval
            if restore_from_order_or_frozen:
                voucher = Voucher.objects.get(
                    enabled=True,
                    code__iexact=voucher_code
                )
            else:
                voucher = Voucher.objects.get(
                    self._match_voucher_time_interval(today),
                    enabled=True,
                    code__iexact=voucher_code
                )

            # test if voucher is available (usage)
            if restore_from_order_or_frozen or voucher.is_available():
                self.voucher = voucher
                return True
        except Voucher.DoesNotExist:
            pass

        return False


    def remove_voucher(self):
        """
        Remove voucher code and discount from basket.
        """
        self.voucher = None


    def get_voucher_code(self):
        """
        Return the current voucher code or None.
        """
        return self.voucher.code.upper() if self.voucher else None
    voucher_code = property(get_voucher_code)


    def get_voucher_title(self):
        """
        Return the title text for the voucher or None.
        """
        return self.voucher.title if self.voucher else None
    voucher_title = property(get_voucher_title)


    def set_click_and_collect(self, click_and_collect):
        self.click_and_collect = click_and_collect


    def set_free_delivery_to(self, free_delivery_to):
        self.free_delivery_to = free_delivery_to


    def is_click_and_collect(self):
        return self.click_and_collect


    def is_free_delivery_to(self):
        return self.free_delivery_to


    def set_invoice(self, invoice, invoice_number=None):
        """
        Make this basket order an invoice order depending on the given invoice
        argument. Optionally with the given customer invoice number.
        """
        self.invoice = invoice

        if self.invoice:
            if invoice_number is not None:
                self.invoice_number = invoice_number
        else:
            self.invoice_number = None


    def is_invoice(self):
        """
        Return True, if this basket represents an invoice order.
        """
        return self.invoice


    def set_default_delivery(self, default_delivery):
        """
        Make the order automatically select the default delivery option
        that is available without asking the customer to choose one.
        """
        self.default_delivery = default_delivery


    def is_default_delivery(self):
        """
        Return True, if this basket is configured with the default delivery
        option automatically.
        """
        return self.default_delivery


    def set_can_edit_billing_address(self, can_edit_billing_address):
        """
        Turns edit-ability of the billing address on/off.
        """
        self.can_edit_billing_address = can_edit_billing_address


    def set_can_edit_delivery_address(self, can_edit_delivery_address):
        """
        Turns edit-ability of the delivery address on/off.
        """
        self.can_edit_delivery_address = can_edit_delivery_address


    def remove_item_by_hash(self, _hash):
        """
        Remove the basket item with the given hash from the basket.
        The removed basket item is returned.
        """
        if not self.is_frozen:
            item = self.get_item_by_hash(_hash)
            if item != None:
                self.items.remove(item)
                return item
        return None


    def update_quantity_by_hash(self, _hash, quantity):
        """
        Update quantity for all basket items that do match the given hash.
        If the quantity is not an integer or less than zero, the new quantity
        is considered to be 0. If the given quantity is 0, the corresponding
        basket items are removed from the basket. This function returns False
        once the quanity has been updated. If the item got removed, True is
        returned.
        """
        if not self.is_frozen:
            try:
                quantity = int(quantity)
            except ValueError:
                quantity = 0
            if quantity < 0: quantity = 0
            if quantity > 9999: quantity = 9999
            item = self.get_item_by_hash(_hash)
            if item != None:
                if quantity > 0:
                    item.quantity = quantity
                else:
                    self.items.remove(item)
                    return True
        return False


    def update_processed_by_hash(self, _hash, processed):
        """
        Update processed flag for a line item with the given hash to the
        given (boolean) value.
        """
        item = self.get_item_by_hash(_hash)
        if item != None:
            item.processed = processed
            return True
        return False


    def _check_us_address(self, country, address):
        """
        Set the address state based on the address county for the US.
        """
        if country and country.iso == 'US':
            address['state'] = address.get('county')
            address['county'] = None


    def has_billing_address(self):
        """
        Return True, if the basket has a billing address.
        """
        return self.billing_address != None


    def set_finance_option(self, finance_option):
        """
        Enable/Disable finance option for this basket.
        """
        if self.supports_finance_option(finance_option):
            self.finance_option_id = finance_option.pk
            self.finance_option = finance_option
        else:
            self.finance_option_id = None
            self.finance_option = None


    def set_loan_deposit(self, loan_deposit):
        """
        Add/Delete loan deposit for this basket.
        """
        if loan_deposit:
            self.loan_deposit = loan_deposit
        else:
            self.loan_deposit = None


    @property
    def billing_address_fields(self):
        """
        Return an array of address fields that are defined for the billing
        address for this basket, excluding title and name of the person.
        """
        return filter(lambda a: a, [
            self.billing_address.get('company'),
            self.billing_address.get('address1'),
            self.billing_address.get('address2'),
            self.billing_address.get('address3'),
            self.billing_address.get('city'),
            self.billing_address.get('county'),
            self.billing_address.get('postcode'),
            self.billing_address.get('country')
        ])


    def set_billing_address(self, title, first_name, last_name, email, telephone, company, address1, address2, address3, city, country, county, postcode):
        """
        Set the billing address to the given properties.
        """
        self.billing_address = clean_dict({
            'title': title,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'telephone': telephone,
            'company': company,
            'address1': address1,
            'address2': address2,
            'address3': address3,
            'city': city,
            'country': country,
            'country-iso': country.iso,
            'county': county,
            'postcode': postcode
        })
        self._check_us_address(country, self.billing_address)


    def has_delivery_address(self):
        """
        Return True, if the basket has a delivery address.
        """
        return self.delivery_address != None


    def set_delivery_address(self, name, company, address1, address2, address3, city, country, county, postcode):
        """
        Set the delivery address to the given properties.
        """
        self.delivery_address = clean_dict({
            'name': name,
            'company': company,
            'address1': address1,
            'address2': address2,
            'address3': address3,
            'city': city,
            'country': country,
            'country-iso': country.iso,
            'county': county,
            'postcode': postcode
        })
        self._check_us_address(country, self.delivery_address)


    def set_delivery_country(self, country):
        """
        Set the delivery country, which is critical for delivery calculation.
        """
        if not self.delivery_address:
            self.delivery_address = {};

        self.delivery_address['country'] = country;
        self.delivery_address['country-iso'] = country.iso;


    def get_delivery_country(self):
        """
        Return the delivery country for this basket.
        """
        if self.delivery_address:
            return self.delivery_address.get('country')
        else:
            return None


    def _get_address_component(self, address, name, default=None):
        """
        Return the address components of the given address with the given name.
        """
        if address:
            return address.get(name, default)
        else:
            return default


    def get_billing_address_components(self):
        """
        Return all components of the billing address, even if no billing address is available.
        """
        return {
            'title': self._get_address_component(self.billing_address, 'title'),
            'first_name': self._get_address_component(self.billing_address, 'first_name'),
            'last_name': self._get_address_component(self.billing_address, 'last_name'),
            'email': self._get_address_component(self.billing_address, 'email'),
            'telephone': self._get_address_component(self.billing_address, 'telephone'),
            'company': self._get_address_component(self.billing_address, 'company'),
            'address1': self._get_address_component(self.billing_address, 'address1'),
            'address2': self._get_address_component(self.billing_address, 'address2'),
            'address3': self._get_address_component(self.billing_address, 'address3'),
            'city': self._get_address_component(self.billing_address, 'city'),
            'country': self._get_address_component(self.billing_address, 'country'),
            'country-iso': self._get_address_component(self.billing_address, 'country-iso'),
            'county': self._get_address_component(self.billing_address, 'county'),
            'state': self._get_address_component(self.billing_address, 'state'),
            'postcode': self._get_address_component(self.billing_address, 'postcode')
        }
    billing_address_components = property(get_billing_address_components)


    def get_delivery_address_components(self):
        """
        Return all components of the delivery address, even if no billing address is available.
        """
        return {
            'name': self._get_address_component(self.delivery_address, 'name'),
            'company': self._get_address_component(self.delivery_address, 'company'),
            'address1': self._get_address_component(self.delivery_address, 'address1'),
            'address2': self._get_address_component(self.delivery_address, 'address2'),
            'address3': self._get_address_component(self.delivery_address, 'address3'),
            'city': self._get_address_component(self.delivery_address, 'city'),
            'country': self._get_address_component(self.delivery_address, 'country'),
            'country-iso': self._get_address_component(self.delivery_address, 'country-iso'),
            'county': self._get_address_component(self.delivery_address, 'county'),
            'state': self._get_address_component(self.delivery_address, 'state'),
            'postcode': self._get_address_component(self.delivery_address, 'postcode')
        }
    delivery_address_components = property(get_delivery_address_components)


    def set_signup(self, email, first_name, last_name, password):
        """
        Set signup account details.
        """
        self.signup = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'password': password
        }


    def is_collection_only(self):
        """
        Return True, if at least one product is collection only.
        """
        for item in self.items:
            if item.is_collection_only:
                return True
        return False


    def has_pre_order_item(self):
        """
        Check if any product is pre-order.
        """
        for item in self.items:
            if item.is_pre_order:
                return True
        return False


    def get_delivery_options(self):
        """
        Return a list of valid delivery options for customers to choose from
        that can be applied to this basket primarily based on the current
        delivery country set for the basket and the (enabled) delivery options
        available in the system.
        """
        # get list of delivery options (cached)
        if not hasattr(self, '_delivery_options'):
            self._delivery_options = list(DeliveryOption.objects.filter(enabled=True))
        options = self._delivery_options

        # filter by current delivery country, assume UK if delivery
        # address is not available
        this = self
        def filter_by_country(option):
            if this.delivery_to_uk() and not option.deliver_uk and not option.quote_uk:
                return False
            if not this.delivery_to_uk() and this.delivery_to_eu() and not option.deliver_eu and not option.quote_eu:
                return False
            if not this.delivery_to_uk() and not this.delivery_to_eu() and not option.deliver_world and not option.quote_world:
                return False

            return True

        return filter(filter_by_country, options)


    def get_delivery_choices(self):
        """
        Return a list of delivery choices for this basket.
        """
        options = self.get_delivery_options()
        return [(x.pk, x.title) for x in options]


    def set_delivery_option(self, delivery_option):
        """
        Set delivery option.
        """
        self.delivery_option = delivery_option


    def delivery_to(self, country_code):
        """
        Return True, if the delivery country is the one given via the country
        code or list of country codes. If no delivery address has been specified
        for the basket, the default country as specified in settings is assumed.
        """
        try:
            iso = self.delivery_address['country'].iso
        except:
            iso = settings.SHOP_DEFAULT_DELIVERY_COUNTRY_ISO

        if isinstance(country_code, list):
            return iso in country_code
        else:
            return iso == country_code


    def delivery_to_uk(self):
        """
        Return True, if the delivery country is the UK.
        """
        return self.delivery_to('GB')


    def delivery_to_eu(self):
        """
        Return True, if the delivery country is a member state of the EU.
        """
        return self.delivery_to(self.EU_COUNTRY_CODES)


    def delivery_to_world(self):
        """
        Return True, if the delivery country is NOT UK and NOT EU.
        """
        return not self.delivery_to_uk() and not self.delivery_to_eu()


    def get_delivery_option(self):
        """
        Return the delivery option that is used for the basket.
        """
        return self.delivery_option


    def get_delivery_option_or_default(self):
        """
        Return current delivery option or default delivery option, which is the
        first delivery option or None if no delivery options are available.
        """
        if self.delivery_option:
            return self.delivery_option
        else:
            return self.get_default_delivery_option()
    delivery_option_or_default = property(get_delivery_option_or_default)


    def get_default_delivery_option(self):
        """
        Return the default delivery option, which is the first delivery option
        in the system or None if no delivery option is available.
        """
        delivery_options = self.get_delivery_options()
        if len(delivery_options) > 0:
            return delivery_options[0]
        else:
            return None


    def get_delivery_details(self, option):
        """
        Return delivery description and total delivery price for this basket
        based on the given global delivery option.
        """
        if not hasattr(self, '_delivery_details_cache'):
            self._delivery_details_cache = {}

        if option.pk not in self._delivery_details_cache:
            # determine base items to work with
            description = option.description
            defaults = option.get_defaults()
            items = self.items

            # calc. max. of delivery costs for all products
            zero = decimal.Decimal('0.00')
            uk, eu, world = (zero, zero, zero)
            for item in items:
                _uk = zero
                _eu = zero
                _world = zero
                try:
                    # per product override (or default)
                    product_option = ProductDeliveryOption.objects.get(product=item.product, delivery_option=option)
                    if product_option.uk != None:
                        _uk = product_option.uk
                    else:
                        if option.uk_def != None: _uk = option.uk_def

                    if product_option.eu != None:
                        _eu = product_option.eu
                    else:
                        if option.eu_def != None: _eu = option.eu_def

                    if product_option.world != None:
                        _world = product_option.world
                    else:
                        if option.world_def != None: _world = option.world_def
                except ProductDeliveryOption.DoesNotExist:
                    # defaults
                    if option.uk_def != None: _uk = option.uk_def
                    if option.eu_def != None: _eu = option.eu_def
                    if option.world_def != None: _world = option.world_def

                # determine max.
                if _uk > uk: uk = _uk
                if _eu > eu: eu = _eu
                if _world > world: world = _world

            # determine final total based on region
            if self.delivery_to_uk():
                total = uk
            elif self.delivery_to_eu():
                total = eu
            else:
                total = world

            # quote only total is always zero
            is_quote_only = self._is_quote_only(option)
            if is_quote_only:
                total = zero

            # calculate total before delivery (including discounts). Now if we apply
            # a free delivery discount we cannot include it here, otherwise we
            # would end up within an infinite loop
            total_before_delivery = self.get_total_before_delivery(exclude_free_delivery=True)

            # free delivery for UK delivery only if free delivery is enabled
            # and the total basket value exceeds free delivery threshold
            # and no products are exempt from free delivery
            free_delivery = False
            free_delivery_threshold = zero
            if self.delivery_to_uk() and \
               option.free_delivery and \
               option.free_delivery_threshold != None and \
               total_before_delivery >= option.free_delivery_threshold and \
               not self.contains_items_exempt_from_free_delivery():
                total = zero
                free_delivery = True
                free_delivery_threshold = option.free_delivery_threshold

            # deposit only products are with free delivery
            if self.is_deposit_only():
                total = zero

            # free delivery address
            if self.is_free_delivery_to():
                total = zero

            # construct result
            self._delivery_details_cache[option.pk] = {
                'description': description,
                'free_delivery': free_delivery,
                'free_delivery_threshold': free_delivery_threshold,
                'free_delivery_threshold_display': '%s%s' % (settings.CURRENCY, free_delivery_threshold),
                'total': total,
                'total_display': '%s%s' % (settings.CURRENCY, total),
                'can_deliver': self._can_deliver(option),
                'is_quote_only': is_quote_only
            }

        return self._delivery_details_cache[option.pk]


    def _can_deliver(self, option):
        """
        Return True, if delivery can be made by using the given delivery option.
        """
        if not option:
            option = self.get_default_delivery_option()

        if not option:
            return False

        return \
            (self.delivery_to_uk() and (option.deliver_uk or option.quote_uk)) or \
            (self.delivery_to_eu() and (option.deliver_eu or option.quote_eu)) or \
            (self.delivery_to_world() and (option.deliver_world or option.quote_world))


    def _is_quote_only(self, option):
        """
        Return True, if we can only quote for the given delivery option.
        """
        if option is None:
            option = self.get_default_delivery_option()

        if option is None:
            return False

        return \
            (self.delivery_to_uk() and option.quote_uk) or \
            (self.delivery_to_eu() and option.quote_eu) or \
            (self.delivery_to_world() and option.quote_world)


    def _get_discounted_category_ids(self):
        """
        Return a list of category identifiers, for which a discount is given
        based on the current attached voucher.
        """
        if self.voucher:
            return [c.get('id') for c in self.voucher.categories.all().values('id')]
        else:
            return []


    def can_present_voucher(self):
        """
        Return True, if there is any potential voucher available in the system
        that can potentially be applied to this basket. This will take all
        enabled vouchers into consideration which match by valid time interval
        and category restrictions. If no categories are restricted then all
        products may qualify for any valid voucher. If there are category
        restrictions, only products matching those categories qualify for a
        voucher. The basket must then contain at least one product that
        qualifies for a voucher in order to allow customers to see the voucher
        input field.
        """
        # all enabled vouchers
        vouchers = Voucher.objects.filter(enabled=True)

        # must match time interval
        today = datetime.date.today()
        vouchers = vouchers.filter(self._match_voucher_time_interval(today))

        # at least one product within the basket must match categories or
        # the voucher has no restriction to begin with
        q = Q(categories=None)
        if self.items:
            for item in self.items:
                if item.product:
                    q |= Q(categories=item.product.category)
        vouchers = vouchers.filter(q)

        # voucher must be available (usage) or usage restriction is turned off
        for v in vouchers:
            if v.is_available():
                return True
        return False


    def can_have_free_delivery_to(self):
        """
        Return True if Category model has free_delivery and delivery_code fields and
        there is at least one product in basket which belongs to this category/location.
        """
        # invoice order cannot have free delivery
        if self.invoice:
            return False

        if self.get_free_delivery_to():
            return True
        return False


    def get_free_delivery_to(self):
        """
        Return Category name if product can be freely shipped to this category/location.
        """
        if hasattr(self, 'free_delivery_to_category'):
            return self.free_delivery_to_category

        category_model = get_category_model()

        try:
            category_model._meta.get_field('free_delivery')
            category_model._meta.get_field('delivery_code')
            # check if it has got at least postcode, address1 and city, Country default to UK if not available
            category_model._meta.get_field('address1')
            category_model._meta.get_field('city')
            category_model._meta.get_field('postcode')
        except FieldDoesNotExist:
            return False

        categories = category_model.objects.filter(free_delivery=True)

        if self.items:
            for item in self.items:
                if item.product:
                    for category in categories:
                        if item.product.category_id == category.pk and category.delivery_code != None and category.delivery_code != '':
                            self.free_delivery_to_category = category
                            return category
        return None


    def get_normalized_free_delivery_to_address(self):
        """
        Return normalized address for basket based on free delivery to.
        """
        address = self.get_free_delivery_to()

        normalized_address = {}
        normalized_address['title'] = address.title
        normalized_address['address1'] = address.address1
        normalized_address['city'] = address.city
        normalized_address['postcode'] = address.postcode

        for field in ['address2', 'address3', 'county', 'country']:
            try:
                address._meta.get_field(field)
                normalized_address[field] = getattr(address, field)
            except FieldDoesNotExist:
                if field == 'country':
                    normalized_address['country'] = Country.objects.get(iso='GB')
                else:
                    normalized_address[field] = ''
        return normalized_address


    def clear_signup(self):
        """
        Remove signup data from basket.
        """
        self.signup = None


    def get_sub_total(self):
        """
        Return the sub-total value of the entire basket which is the sum
        over the sub-totals over all basket items (including times quantity).
        """
        if self.is_frozen:
            v = self.placeholder.get('totals', {}).get('sub_total')
            if v is not None: return v

        items = self.get_items()
        if len(items) > 0:
            x = sum([item.total for item in items])
        else:
            x = decimal.Decimal('0.00')
        return x
    sub_total = property(get_sub_total)


    def get_sub_total_discountable(self):
        """
        Return the sub-total value of the entire basket which is discountable.
        Excluded are products that do not qualify for discounts and all products
        that do not match the voucher discount rule.
        """
        items = self.get_items()

        discounted_category_ids = self._get_discounted_category_ids()

        if len(items) > 0:
            x = sum([item.get_total_discountable(discounted_category_ids) for item in items])
        else:
            x = decimal.Decimal('0.00')

        return x
    sub_total_discountable = property(get_sub_total_discountable)


    def get_delivery(self):
        """
        Return the amount of delivery costs that applies for this basket.
        """
        if self.is_frozen:
            v = self.placeholder.get('totals', {}).get('delivery')
            if v is not None: return v

        # exclude delivery costs if there is only one product with deposit
        if self.is_deposit_only():
            return decimal.Decimal('0.00')

        # click and collect does not have a delivery charge
        if self.is_click_and_collect():
            return decimal.Decimal('0.00')

        # invoice order does not have a delivery charge
        if self.invoice:
            return decimal.Decimal('0.00')

        # if we have no delivery option, assume default or zero delivery charge
        delivery_option = self.get_delivery_option_or_default()
        if not delivery_option:
            return decimal.Decimal('0.00')

        delivery_details = self.get_delivery_details(delivery_option)
        return delivery_details.get('total')
    delivery = property(get_delivery)


    def get_discount_value(self, exclude_free_delivery=False):
        """
        Return the amount of value this basket has been discounted by, based
        for example on a voucher code.
        """
        if self.is_frozen:
            v = self.placeholder.get('totals', {}).get('discount')
            if v is not None: return v

        if self.voucher:
            total_discountable = self.get_sub_total_discountable()
            if self.voucher.discount_type == Voucher.DISCOUNT_PERCENTAGE:
                # percentage
                response = (total_discountable / 100) * self.voucher.discount_value
                return response.quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_UP)
            elif self.voucher.discount_type == Voucher.DISCOUNT_PRICE:
                # fixed reduction (also handle overflow)
                discounted = total_discountable - self.voucher.discount_value
                if discounted < 0:
                    return total_discountable
                else:
                    return self.voucher.discount_value
            elif self.voucher.discount_type == Voucher.DISCOUNT_FREE_DELIVERY:
                # free delivery excluded when calculating the discountable
                # total, otherwise we would end up within an inifinite loop
                if not exclude_free_delivery:
                    # make sure that the delivery country applies. If we do not
                    # have a delivery country yet, we ignore this bit for now
                    delivery_country = self.get_delivery_country()
                    if delivery_country is None or self.voucher.matches_delivery_country(delivery_country):
                        # reduce the amount of delivery (if any)
                        return self.delivery

        # default: no discount.
        return decimal.Decimal('0.00')
    discount_value = property(get_discount_value)


    def clear_custom_total(self):
        """
        Remove custom total value of this basket (backend orders only).
        """
        self.custom_total = None


    def set_custom_total(self, custom_total):
        """
        Set the custom total of this basket.
        """
        self.custom_total = custom_total


    def some_products_exempt_from_discount(self):
        """
        Return True, if a discount does not apply for at least one product.
        Perhabs the product is exempt from discounts or does not match
        the category.
        """
        return self.get_sub_total_discountable() != self.get_sub_total()


    def some_products_exempt_from_free_delivery(self):
        """
        Return True, if a free delivery does not apply because there
        is at least one product that is exempt from free delivery.
        """
        delivery_option = self.get_delivery_option_or_default()
        if delivery_option:
            return \
                delivery_option.free_delivery and \
                any([item.is_exempt_from_free_delivery for item in self.get_items()])
        else:
            return False


    def contains_items_exempt_from_free_delivery(self):
        """
        Return True, if the basket contains at least one item that is exempt from
        free delivery.
        """
        return any([item.is_exempt_from_free_delivery for item in self.get_items()])


    def get_total_before_delivery(self, exclude_free_delivery=False):
        """
        Return the total value of the basket excluding delivery.
        """
        return self.get_sub_total() - self.get_discount_value(exclude_free_delivery)
    total_before_delivery = property(get_total_before_delivery)


    def get_calculated_total(self):
        """
        Return the actual total of the basket (including delivery), even if
        the basket total has been overwritten by a custom total
        (backend orders only).
        """
        if self.is_frozen:
            v = self.placeholder.get('totals', {}).get('total')
            if v is not None: return v

        return self.get_total_before_delivery() + self.get_delivery()
    calculated_total = property(get_calculated_total)


    def get_total(self):
        """
        Return the total value of the basket (including delivery). The total
        value might be overridden by a custom total (backend orders only).
        """
        if self.custom_total is not None:
            return self.custom_total
        else:
            return self.get_calculated_total()
    total = property(get_total)


    def get_totals(self):
        """
        Return a dict representation of all total values for this basket.
        """
        return {
            'sub_total': self.get_sub_total(),
            'delivery': self.get_delivery().quantize(decimal.Decimal('.01')),
            'discount': self.get_discount_value(),
            'total': self.get_total().quantize(decimal.Decimal('.01')),
            'quantity': self.get_quantity(),
            'difference_between_deposit_and_full_amount': self.get_difference_between_deposit_and_full_amount()
        }
    totals = property(get_totals)


    def get_quantity(self):
        """
        Return the total number of products in the basket.
        """
        items = self.get_items()
        if len(items) > 0:
            return sum([item.quantity for item in items])
        else:
            return 0
    quantity = property(get_quantity)


    def get_messages(self, backend=False):
        """
        Return a list of customer-facing and backend-facing messages related to
        the content of this basket.
        """
        result = []

        # no messages for empty baskets
        if not self.items:
            return result

        if not self.is_frozen:
            index = 1 if backend else 0

            if self.has_pre_order_item():
                result.append(self.MESSAGE_PRE_ORDER[index])

            if self.is_available_for_loan():
                if self.finance_option:
                    result.append(self.MESSAGE_FINANCE_OPTION[index])
                else:
                    result.append(self.MESSAGE_FINANCE_AVAILABLE[index])
            elif self.is_available_for_loan_in_principal():
                if self.is_exempt_from_loan():
                    result.append(self.MESSAGE_EXEMPT_FROM_LOAN[index])
                else:
                    result.append(self.MESSAGE_TOO_LOW_FOR_LOAN[index])
        elif backend:
            # frozen basket for backend
            if self.was_unable_to_restore:
                result.append(self.MESSAGE_UNABLE_TO_RESTORE)
            else:
                result.append(self.MESSAGE_FROZEN_BASKET)

        # process each message via the template system
        messages = []
        context = Context({ 'basket': self })
        for text in result:
            t = Template('{% load shop_tags %}' + text)
            messages.append(t.render(context))
        return messages


    def get_customer_messages(self):
        """
        Return a list of customer-facing messages related to the content
        of this basket.
        """
        return self.get_messages(backend=False)
    customer_messages = property(get_customer_messages)


    def get_backend_messages(self):
        """
        Return a list of backend-facing messages related to the content
        of this basket.
        """
        return self.get_messages(backend=True)
    backend_messages = property(get_backend_messages)


    @property
    def delivery_option_form(self):
        """
        Return an instance of a delivery option form, pre-configured with
        a list of available delivery option and the current delivery option
        selected.
        """
        delivery_option_choices = self.get_delivery_choices()
        delivery_option = self.get_delivery_option()
        delivery_option_form = DeliveryOptionsFrom()
        delivery_option_form.configure(
            self.request,
            delivery_option_choices,
            delivery_option,
            self.click_and_collect
        )
        return delivery_option_form


    def as_legacy_dict(self):
        """
        Return the entire basket content as a dict.
        structure that can be used for AJAX responses or can be serialised.
        """
        products = [i.as_legacy_dict() for i in self.get_items()]

        if len(products) > 0:
            quantity = sum([p['quantity'] for p in products])
        else:
            quantity = 0

        sub_total = self.get_sub_total()
        if sub_total == 0:
            sub_total = decimal.Decimal('0.00')

        return {
            'products': products,
            'is_quote_only': self.is_quote_only,
            'totals': {
                'sub_total': sub_total,
                'delivery': self.get_delivery().quantize(decimal.Decimal('.01')),
                'total': self.get_total().quantize(decimal.Decimal('.01')),
                'quantity': quantity,
                'difference_between_deposit_and_full_amount': self.get_difference_between_deposit_and_full_amount(),
            },
            'voucher': {
                'title': self.voucher.title,
                'code': self.voucher.code
            } if self.voucher else None,
            'discount_value': self.discount_value,
            'finance_option_id': self.finance_option_id,
            'loan_deposit': self.loan_deposit,
            'is_available_for_loan': self.finance_option is not None,
            'is_invoice': self.invoice,
            'invoice_number': self.invoice_number
        }
