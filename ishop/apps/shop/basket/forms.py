# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from cubane.forms import BaseForm
from cubane.lib.libjson import to_json
from cubane.ishop.apps.forms import VarietyField
from cubane.ishop.models import Variety, VarietyAssignment, ProductSKU
from cubane.ishop import get_product_model
from collections import OrderedDict
import sys


class AddToBasketForm(BaseForm):
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        product = kwargs.pop('product')
        prefix = kwargs.pop('prefix', None)
        with_varieties = kwargs.pop('with_varieties', True)
        self._price_calculation = kwargs.pop('price_calculation', False)

        super(AddToBasketForm, self).__init__(*args, **kwargs)

        self._configure_for_product(request, product, prefix, with_varieties)


    quantity = forms.ChoiceField(required=True, initial=1, widget=forms.Select(attrs={'class': 'input-mini'}))
    product_id = forms.IntegerField(required=True, widget=forms.HiddenInput())
    prefix = forms.CharField(required=False, max_length=32, widget=forms.HiddenInput())


    @property
    def can_be_added_to_basket(self):
        """
        Return True, if this product can be added to the basket.
        """
        return self._product.can_be_added_to_basket(self._request)


    @property
    def fieldnames(self):
        """
        Return list of all form fields, excluding hidden fields but including
        varieties text label fields.
        """
        fields = []
        for field in self.fields:
            if field in ['quantity', 'product_id', 'prefix']: continue
            fields.append(field)
        return ','.join(fields)


    @property
    def product_price(self):
        """
        Return the initial product price based on the initial state of this
        form.
        """
        if self._has_skus and self._combination and self._combination.get('sku') and self._combination.get('sku').price:
            # SKU based
            return self._combination.get('sku').price
        else:
            # Varieties (first variety option for each variety)
            price = self._product.price
            for variety in self._varieties:
                price += variety._assignments[0].price
            return price


    @property
    def variety_option_ids(self):
        """
        Return a list of all possible variety combinations that is used by
        javascript on the front-end in order to determine valid combinations
        while choosing variety options.
        """
        from cubane.ishop.templatetags.shop_tags import get_shop_price
        result = []

        for combination in self._combinations:
            price = combination.get('sku').price
            if not price:
                price = self._product.price

            result.append({
                'ids': combination.get('ids'),
                'price': {
                    'value': price,
                    'display': get_shop_price(price)
                }
            })

        return to_json(result)


    def _get_product_variety_combinations(self, product):
        """
        Return a list of all possible combinations for variety options for the
        given product based on SKU records.
        """
        skus = product.product_sku.filter(enabled=True).prefetch_related('variety_options')

        # build list of varity options
        combinations = []
        option_ids = []
        for sku in skus:
            combination = [option.pk for option in sku.variety_options.all()]
            for _id in combination:
                if _id not in option_ids:
                    option_ids.append(_id)
            combinations.append({
                'sku': sku,
                'ids': combination
            })

        return combinations


    def get_variety_options(self):
        """
        Return a list of variety options that have been chosen for the given
        product assuming this form has already been validated.
        """
        # get option ids from cleaned data
        ids = []
        for k, v in self.cleaned_data.items():
            if k in ['quantity', 'product_id', 'prefix']: continue
            if k.endswith('--label'): continue
            ids.append(int(v))

        # fetch options from database
        assignments = list(VarietyAssignment.objects.select_related('variety_option', 'variety_option__variety').filter(variety_option__id__in=ids, product=self._product).order_by('variety_option__variety__title'))
        return [assignment.variety_option for assignment in assignments]


    def get_variety_option_labels(self, variety_options):
        """
        Return a dict of labels assigning additional custom label text for
        individual variety options that have been chosen. We assume that the
        form has already been validated.
        """
        labels = {}
        for k, v in self.cleaned_data.items():
            if not k.endswith('--label'): continue
            variety_slug = k[:-len('--label')]
            for option in variety_options:
                if option.variety.slug == variety_slug:
                    labels[unicode(option.pk)] = v
        return labels


    def get_quantity(self):
        """
        Return the quantity assuming this form has already been validated.
        """
        return int(self.cleaned_data.get('quantity'))


    def get_max_quantity(self, request):
        """
        Return maximum quantity that is left for this product or settings max quantity.
        """
        return request.settings.max_quantity


    def _get_initial_product_combination(self, combinations, varieties):
        """
        Return the best (closest) variety combination that is valid for this
        product based on the given list of all valid combinations. The closest
        match is determined by calculating a distance d, which is the distance
        between the variety sequence index 'seq' of the variety option.
        """
        lowest_d = sys.maxint
        best = None
        for combination in combinations:
            d = 0
            for option_id in combination.get('ids'):
                for variety in varieties:
                    for option in variety._variety_options:
                        if option.id == option_id:
                            d += option.seq

            if d < lowest_d:
                lowest_d = d
                best = combination

        return best


    def _get_matching_variety_by_option_id(self, option_id, varieties):
        """
        Return the matching variety that the variety with the given assignment
        id belongs to based on the given list of all varieties.
        """
        for variety in varieties:
            for option in variety._variety_options:
                if option.id == option_id:
                    return variety
        return None


    def _filter_assignments_by_skus(self, assignments, has_skus, combinations):
        """
        Return a new list of assignments that only contains assignments that
        actually appear within the list of valid SKU combinations, if we
        actually use SKUs.
        """
        # SKUs are not used
        if not has_skus:
            return assignments

        result = []
        for assignment in assignments:
            # keep options that are not taking part ion SKU numbers...
            if not assignment.variety_option.variety.sku:
                result.append(assignment)
                continue

            # try to find matching combination
            found = False
            for combination in combinations:
                if assignment.variety_option.pk in combination.get('ids'):
                    result.append(assignment)
                    break

        return result


    def _configure_for_product(self, request, product, prefix, with_varieties=True):
        """
        Configure form based on given product.
        """
        self._request = request
        self._product = product
        self._prefix = prefix
        self._variety_label_info = []

        self.fields['prefix'].initial = prefix

        # determine all possible combinations of varieties for this product
        if with_varieties:
            self._has_skus = self._product.sku_enabled and self._product.product_sku.all().count() > 0
            if self._has_skus:
                self._combinations = self._get_product_variety_combinations(
                    self._product
                )
            else:
                self._combinations = []
        else:
            self._has_skus = False
            self._combinations = []

        # load all assigned varieties
        if with_varieties:
            assignments = list(VarietyAssignment.objects.select_related(
                'variety_option',
                'variety_option__image',
                'variety_option__variety',
                'variety_option__variety__parent',
                'variety_option__variety__parent__parent',
                'variety_option__variety__parent__parent__parent',
                'product'
            ).filter(
                product=product,
                variety_option__enabled=True,
                variety_option__variety__enabled=True
            ).exclude(
                variety_option__variety__style=Variety.STYLE_ATTRIBUTE
            ).order_by(
                'variety_option__seq',
                'variety_option__id'   # older versions may not have a valid seq.
            ))
        else:
            assignments = []

        # eliminate assigned varieties that do not appear in any SKU, if
        # the product is managed by SKU combinations. Some varieties are not
        # taking part in SKUs directly and will appear regardless...
        if with_varieties:
            assignments = self._filter_assignments_by_skus(
                assignments,
                self._has_skus,
                self._combinations
            )

        # isolate varieties based on assignments (keep order)
        self._varieties = []
        if with_varieties:
            for assignment in assignments:
                if assignment.variety_option.variety not in self._varieties:
                    self._varieties.append(assignment.variety_option.variety)

        # split options per variety
        if with_varieties:
            for variety in self._varieties:
                variety._variety_options = []
                variety._assignments = []
                for assignment in assignments:
                    if assignment.variety_option.variety.id == variety.id:
                        variety._variety_options.append(assignment.variety_option)
                        variety._assignments.append(assignment)

        # sort varieties by seq. number, so that they appear in the order
        # as defined in the backend, but always present SKU-relevant varieties
        # first...
        if with_varieties:
            def _sort(v):
                sorting = [not v.sku]
                if v.parent is not None:
                    sorting.append(v.parent.seq)
                    if v.parent.parent is not None:
                        sorting.append(v.parent.parent.seq)
                        if v.parent.parent.parent is not None:
                            sorting.append(v.parent.parent.parent.seq)
                sorting.append(v.seq)
                return sorting
            self._varieties.sort(key=_sort)

        # rebuild list of varieties, so that varieties where the customer cannot
        # choose from (because there is only one option available) are presented
        # first. Other than that, the defined seq. order is not changed.
        if with_varieties:
            single_option_varieties = []
            multiple_options_varieties = []
            for v in self._varieties:
                if len(v._variety_options) == 1:
                    single_option_varieties.append(v)
                else:
                    multiple_options_varieties.append(v)
            self._varieties = single_option_varieties + multiple_options_varieties

        # determine the total number of possible combinations
        combinations = 1
        if with_varieties:
            for variety in self._varieties:
                if variety.sku:
                    combinations *= len(variety._variety_options)

        # determine if we need to change the style from default drop down
        # to list automatically. Whenever we have at least one possible
        # combination not available we cannot present this as a drop down,
        # because individual options in a drop down control cannot be
        # rendered as being unavailable by default...
        if with_varieties:
            should_be_list = len(self._combinations) != combinations and self._has_skus
        else:
            should_be_list = False

        # generate variety form fields
        self.varieties_fields = OrderedDict()
        if with_varieties:
            for variety in self._varieties:
                # determine if we need to change the style from default drop down
                # to list automatically. Whenever we have at least one possible
                # combination not available we cannot present this as a drop down,
                # because individual options in a drop down control cannot be
                # rendered as being unavailable by default...
                if variety.sku and variety.style == Variety.STYLE_SELECT and should_be_list:
                    variety.style = Variety.STYLE_LIST

                # create variety select field
                self.varieties_fields.update({
                    variety.slug: VarietyField(
                        request,
                        variety,
                        variety._assignments,
                        has_skus=self._has_skus,
                        label=variety.display_title)
                })

                # insert name label if any option of the variety supports
                # a custom name label
                variety_option_with_label_ids = map(lambda option: unicode(option.pk), filter(lambda option: option.text_label, variety._variety_options))
                if variety_option_with_label_ids:
                    label_fieldname = '%s--label' % variety.slug
                    self.varieties_fields.update({
                        label_fieldname: forms.CharField(
                            label='',
                            required=False,
                            max_length=10000,
                            widget=forms.Textarea(attrs={
                                'placeholder': 'Label Text...',
                                'class': 'variety-text-label',
                                'data-variety-name': variety.slug,
                                'data-varity-option-ids': ','.join(variety_option_with_label_ids),
                            })
                        )
                    })
                    self.varieties_fields[label_fieldname].group_class = 'variety-label-text'

                    # add information in order to clean data
                    self._variety_label_info.append({
                        'variety_fieldname': variety.slug,
                        'option_ids': variety_option_with_label_ids,
                        'label_fieldname': label_fieldname
                    })

        # inject product id
        self.fields['product_id'].initial = product.id

        # setup choices for quantity...
        self.fields['quantity'].choices = [
            (i, unicode(i)) for i in range(1, self.get_max_quantity(request) + 1)
        ]

        # apply form fields
        self.fields = OrderedDict(list(self.varieties_fields.items()) + list(self.fields.items()))

        # determine the start configuration of all varieties based on selecting
        # a valid start combination that is as close as possible to the first
        # option for every variety.
        initial = self._get_default_initial()

        # update initials with query arguments
        for k in initial.keys():
            if k in request.GET:
                initial[k] = request.GET.get(k)

        # apply initial values
        for k, v in initial.items():
            self.fields[k].initial = v


    def clean(self, *args, **kwargs):
        d = super(AddToBasketForm, self).clean(*args, **kwargs)

        # clean label (text required)
        if not self._price_calculation:
            for label_info in self._variety_label_info:
                variety_fieldname = label_info.get('variety_fieldname')
                option_ids = label_info.get('option_ids')
                label_fieldname = label_info.get('label_fieldname')
                variety_option_id = d.get(variety_fieldname)
                if variety_option_id and unicode(variety_option_id) in option_ids:
                    # label selected, make sure that a label has actually been
                    # provided; otherwise generate form error...
                    label_value = d.get(label_fieldname)
                    if not label_value:
                        self.field_error(label_fieldname, 'Label text is required.')

        return d


    def _get_default_initial(self):
        """
        Return the default initial value set for all varieties, which is usually
        the first option for each variety.
        """
        initial = {}
        if self._has_skus:
            self._combination = self._get_initial_product_combination(self._combinations, self._varieties)
            if self._combination:
                for option_id in self._combination.get('ids'):
                    variety = self._get_matching_variety_by_option_id(option_id, self._varieties)
                    if variety:
                        initial[variety.slug] = option_id
        else:
            # set the initial variety option to the first option available
            for variety in self._varieties:
                initial[variety.slug] = variety._variety_options[0].pk

        return initial
