# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.urlresolvers import reverse
from wsgiref.util import FileWrapper
from django.core.files.temp import NamedTemporaryFile
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.utils.html import escape, strip_tags
from django.db.models import Prefetch
from cubane.views import ModelView, view_url, view
from cubane.backend.views import BackendSection, RelatedModelCollection
from cubane.lib.libjson import to_json_response
from cubane.lib.text import clean_unicode, text_from_html, unescape
from cubane.lib.libjson import to_json
from cubane.lib.model import dict_to_model, model_to_dict
from cubane.lib.parse import parse_int
from cubane.media.views import load_media_gallery, save_media_gallery
from cubane.media.models import Media
from cubane.cms.views import get_cms_settings
from cubane.ishop import get_product_model, get_category_model
from cubane.ishop.basket import Basket
from cubane.ishop.apps.merchant.products.forms import DeliveryOptionFormset
from cubane.ishop.apps.merchant.products.forms import ProductSKUForm
from cubane.ishop.apps.merchant.varieties.forms import VarietyAssignmentFormset, VarietyAttributeAssignmentFormset
from cubane.ishop.models import ProductCategory
from cubane.ishop.models import ShopSettings, Variety, VarietyAssignment
from cubane.ishop.models import ProductDeliveryOption, DeliveryOption, RelatedProducts
from cubane.ishop.models import VarietyOption, ProductSKU
from xml.etree.cElementTree import Element, SubElement, tostring
from xml.dom import minidom
import decimal
import datetime
import codecs
import os
import re
import cgi


class ProductView(ModelView):
    """
    Editing categories (tree)
    """
    template_path = 'cubane/ishop/merchant/products/'
    model = get_product_model()


    def __init__(self, namespace, with_folders):
        self.namespace = namespace
        self.with_folders = with_folders

        if with_folders:
            self.folder_model = get_category_model()

        self.sortable = self.with_folders

        # multiple categories
        if settings.SHOP_MULTIPLE_CATEGORIES:
            self.exclude_columns = ['category']
            self.multiple_folders = True
        else:
            self.exclude_columns = ['categories_display']
            self.multiple_folders = False

        super(ProductView, self).__init__()


    patterns = [
        view_url(r'varieties/', 'varieties', name='varieties'),
        view_url(r'varieties/(?P<product_id>\d+)/edit/(?P<variety_id>\d+)/', 'varieties_edit', name='varieties.edit'),
        view_url(r'varieties/(?P<product_id>\d+)/delete/(?P<variety_id>\d+)', 'varieties_delete', name='varieties.delete'),
        view_url(r'sku/', 'sku', name='sku'),
        view_url(r'delivery/', 'delivery', name='delivery'),
        view_url(r'google-products-export/', 'google_products', name='google_products'),
    ]

    listing_actions = [
        ('[SKUs]', 'sku', 'single'),
        ('[Varieties]', 'varieties', 'single'),
        ('[Delivery]', 'delivery', 'single'),
        ('Export To Google', 'google_products', 'any')
    ]

    shortcut_actions = [
        'sku',
        'varieties',
        'delivery'
    ]


    def _get_objects(self, request):
        if settings.SHOP_MULTIPLE_CATEGORIES:
            # multiple categories
            return self.model.objects.prefetch_related(
                Prefetch('categories', queryset=ProductCategory.objects.select_related('category').order_by('seq'))
            ).distinct()
        else:
            # single category
            return self.model.objects.select_related('category').all()


    def _get_folders(self, request, parent):
        folders = self.folder_model.objects.all()

        if parent:
            folders = folders.filter(parent=parent)

        return folders


    def _folder_filter(self, request, objects, category_pks):
        """
        Filter given object queryset by the given folder primary key.
        """
        if category_pks:
            q = Q()
            if settings.SHOP_MULTIPLE_CATEGORIES:
                # multiple categories
                for pk in category_pks:
                    q |= Q(categories__id=pk) | \
                         Q(categories__parent_id=pk) | \
                         Q(categories__parent__parent_id=pk) | \
                         Q(categories__parent__parent__parent_id=pk) | \
                         Q(categories__parent__parent__parent__parent_id=pk) | \
                         Q(categories__parent__parent__parent__parent__parent_id=pk)
            else:
                # single category
                for pk in category_pks:
                    q |= Q(category_id=pk) | \
                         Q(category__parent_id=pk) | \
                         Q(category__parent__parent_id=pk) | \
                         Q(category__parent__parent__parent_id=pk) | \
                         Q(category__parent__parent__parent__parent_id=pk) | \
                         Q(category__parent__parent__parent__parent__parent_id=pk)

            # apply filter
            objects = objects.filter(q)
        return objects


    def _get_folder_assignment_name(self):
        """
        Return the name of the field that is used to assign a folder to.
        """
        if settings.SHOP_MULTIPLE_CATEGORIES:
            return 'categories'
        else:
            return 'category'


    def form_initial(self, request, initial, instance, edit):
        """
        Setup gallery images (initial form data)
        """
        initial['_gallery_images'] = load_media_gallery(instance.gallery_images)
        initial['_related_products_collection'] = RelatedModelCollection.load(instance, RelatedProducts)

        if settings.SHOP_MULTIPLE_CATEGORIES:
            initial['categories'] = RelatedModelCollection.load(instance, ProductCategory, sortable=False)


    def bulk_form_initial(self, request, initial, instance, edit):
        if settings.SHOP_MULTIPLE_CATEGORIES:
            initial['categories'] = RelatedModelCollection.load(instance, ProductCategory, sortable=False)


    def before_save(self, request, cleaned_data, instance, edit):
        """
        Maintain SKU based on barcode.
        """
        if request.settings.sku_is_barcode:
            instance.sku = cleaned_data.get('barcode')


    def after_save(self, request, d, instance, edit):
        """
        Save gallery items (in seq.)
        """
        save_media_gallery(request, instance, d.get('_gallery_images'))
        RelatedModelCollection.save(request, instance, d.get('_related_products_collection'), RelatedProducts)

        if settings.SHOP_MULTIPLE_CATEGORIES:
            RelatedModelCollection.save(request, instance, d.get('categories'), ProductCategory, allow_duplicates=False, sortable=False)


    def after_bulk_save(self, request, d, instance, edit):
        if settings.SHOP_MULTIPLE_CATEGORIES:
            RelatedModelCollection.save(request, instance, d.get('categories'), ProductCategory, allow_duplicates=False, sortable=False)


    def varieties(self, request):
        product_id = request.GET.get('pk')
        product = get_object_or_404(get_product_model(), pk=product_id)

        # load variety options
        variety_options = [(a.variety_option.variety, a.variety_option) for a in VarietyAssignment.objects.select_related('variety_option', 'variety_option__variety').filter(product=product)]
        assigned_variety_ids = [variety.pk for variety, _ in variety_options]

        # load all varieties and split them into assigned and unassigned
        varieties = Variety.objects.prefetch_related('options').exclude(options=None).order_by('title')
        if product.sku_enabled:
            varieties = varieties.filter(sku=False)

        # split into assigned and unassigned
        varieties = list(varieties)
        assigned = filter(lambda v: v.id in assigned_variety_ids, varieties)
        unassigned = filter(lambda v: v.id not in assigned_variety_ids, varieties)

        # inject list of assigned variety options for all assigned varieties
        for v in assigned:
            # collect assigned options
            assigned_options = []
            for variety, option in variety_options:
                if v.pk == variety.pk:
                    assigned_options.append(option)

            # sort by title and construct display text
            assigned_options = sorted(assigned_options, key=lambda o: o.title)
            v.assigned_options_display = ', '.join(
                option.title.strip() for option in assigned_options[:5]
            ) + (', ...' if len(assigned_options) > 5 else '')

        return {
            'product': product,
            'assigned': assigned,
            'unassigned': unassigned,
            'ok_url': self._get_url(request, 'index')
        }


    def varieties_edit(self, request, product_id, variety_id):
        product = get_object_or_404(get_product_model(), pk=product_id)
        variety = get_object_or_404(Variety, pk=variety_id)
        options = list(variety.options.order_by('seq', 'id'))
        assignments = VarietyAssignment.objects.select_related('variety_option').filter(product=product, variety_option__variety=variety)
        assignment_list = list(assignments)

        # dataset based on available options
        initial = [{
            'option_id': option.id,
            'title': option.title,
            'enabled': False,
            'offset_type': option.default_offset_type,
            'offset_value': option.default_offset_value,
            'text_label': option.text_label,
            'seq': option.seq,
            'option_enabled': option.enabled
        } for option in options]

        # update base dataset based on available assignments...
        for initial_option in initial:
            for assignment in assignment_list:
                if initial_option['option_id'] == assignment.variety_option.id:
                    initial_option['enabled'] = True
                    initial_option['option_enabled'] = True
                    initial_option['offset_type'] = assignment.offset_type
                    initial_option['offset_value'] = assignment.offset_value

        # remove options that are not currently assigned but disabled...
        initial = filter(lambda option: option.get('option_enabled'), initial)

        # sort by enabled state, then seq if we have a lot of varieties
        if len(initial) > 15:
            initial = sorted(initial, key=lambda x: (-x.get('enabled', x.get('seq'))))

        # determine form class
        if variety.is_attribute:
            form_class = VarietyAttributeAssignmentFormset
        else:
            form_class = VarietyAssignmentFormset

        # create form
        if request.method == 'POST':
            formset = form_class(request.POST)
        else:
            formset = form_class(initial=initial)

        # validation
        if formset.is_valid():
            # delete existing assignments
            for assignment in assignments:
                request.changelog.delete(assignment)
                assignment.delete()

            # create new assignments
            for form in formset.forms:
                d = form.cleaned_data
                if d.get('enabled') == True:
                    for option in options:
                        if option.id == d.get('option_id'):
                            assignment = VarietyAssignment()
                            assignment.variety_option = option
                            assignment.product = product

                            if not variety.is_attribute:
                                assignment.offset_type = d.get('offset_type')
                                assignment.offset_value = d.get('offset_value')

                            assignment.save()
                            request.changelog.create(assignment)
                            break;

            request.changelog.commit(
                'Variety Options for <em>%s</em> for product <em>%s</em> updated.' % (
                    variety.title,
                    product.title
                ),
                product,
                flash=True
            )

            active_tab = request.POST.get('cubane_save_and_continue', '0')
            if not active_tab == '0':
                return self._redirect(request, 'varieties.edit', args=[product.id, variety.id])
            else:
                return self._redirect(request, 'varieties', product)

        return {
            'product': product,
            'variety': variety,
            'form': formset,
        }


    @view(require_POST)
    def varieties_delete(self, request, product_id, variety_id):
        product = get_object_or_404(get_product_model(), pk=product_id)
        variety = get_object_or_404(Variety, pk=variety_id)
        assignments = VarietyAssignment.objects.filter(product=product, variety_option__variety=variety)

        # delete assignments
        for assignment in assignments:
            request.changelog.delete(assignment)
            assignment.delete()

        request.changelog.commit('Variety <em>%s</em> removed.' % variety.title, product)
        return to_json_response({
            'success': True,
        })


    def sku(self, request):
        # get product
        product_id = request.GET.get('pk')
        product = get_object_or_404(get_product_model(), pk=product_id)

        # get varieties
        _varieties = Variety.objects.prefetch_related(
            Prefetch('options', queryset=VarietyOption.objects.order_by('title'))
        ).filter(sku=True).exclude(options=None).exclude(style=Variety.STYLE_ATTRIBUTE).order_by('title').distinct()
        skus = ProductSKU.objects.filter(product=product)
        assigned_option_ids = [a.variety_option.id for a in VarietyAssignment.objects.select_related('variety_option').filter(product=product, variety_option__variety__sku=True)]

        # initial dataset currently present
        initial = {}
        for sku in skus:
            initial[sku.pk] = sku
            initial[sku.pk].errors = []

        # determine barcode system
        cms_settings = get_cms_settings()
        barcode_system = cms_settings.get_barcode_system(product)

        # create template form
        form_template = ProductSKUForm()
        form_template.configure(request, barcode_system)

        def has_var(prefix, name):
            return 'f-%s-%s' % (prefix, name) in request.POST

        def get_var(prefix, name, default=None):
            return request.POST.get('f-%s-%s' % (prefix, name), default)

        def get_int_var(prefix, name, default=None):
            return parse_int(get_var(prefix, name), default)

        # construct list of variety option names
        varieties = []
        variety_index = {}
        for variety in _varieties:
            variety_index[variety.id] = {
                'id': variety.id,
                'title': variety.title,
                'sku': variety.sku,
                'options': {}
            }

            item = {
                'id': variety.id,
                'title': variety.title,
                'sku': variety.sku,
                'options': [],
                'n_assigned_options': 0
            }
            for option in variety.options.all():
                variety_index[variety.id].get('options')[option.id] = {
                    'id': option.id,
                    'title': option.title,
                    'fullTitle': '%s: <em>%s</em>' % (variety.title, option.title)
                }
                item.get('options').append({
                    'id': option.id,
                    'title': option.title,
                    'assigned': option.id in assigned_option_ids
                })
                if option.pk in assigned_option_ids:
                    item['n_assigned_options'] += 1
            varieties.append(item)

        # sort varieties by number of assigned options, so that varieties that
        # have been assigned are at the top of the list. The rest remains sorted
        # alphabetically...
        varieties.sort(key=lambda x: -x.get('n_assigned_options', 0))

        # validation
        is_valid = True
        if request.method == 'POST':
            # process sku records
            prefixes = request.POST.getlist('skus')
            assigned_option_ids = []
            skus_to_save = []
            sku_code_processed = []
            barcodes_processed = []
            for index, prefix in enumerate(prefixes):
                # extract relevant informatioin from post for
                # individual combination
                _id = get_var(prefix, '_id')
                d = {
                    'enabled': get_var(prefix, 'enabled') == 'on',
                    'sku': get_var(prefix, 'sku'),
                    'barcode': get_var(prefix, 'barcode'),
                    'price': get_var(prefix, 'price'),
                    'stocklevel': get_int_var(prefix, 'stocklevel', 0)
                }

                # parse assigned variety options from request data
                n_variety_option = 1
                d['variety_options'] = []
                while len(d['variety_options']) <= 16:
                    _name = 'vo_%d' % n_variety_option
                    if has_var(prefix, _name):
                        d['variety_options'].append(get_int_var(prefix, _name))
                        n_variety_option += 1
                    else:
                        break

                # make sure that sku, barcode and price are None
                # instead of empty
                if _id == '': _id = None
                if d.get('sku') == '': d['sku'] = None
                if d.get('barcode') == '': d['barcode'] = None
                if d.get('price') == '': d['price'] = None

                # construct form based on this data and validate
                form = ProductSKUForm(d)
                form.configure(request, barcode_system)

                # get variety options
                variety_options = VarietyOption.objects.filter(pk__in=d.get('variety_options'))

                # create or edit?
                sku = initial.get(_id, None)
                if sku is None:
                    sku = ProductSKU.objects.get_by_variety_options(product, variety_options)

                    # still not found? -> create new item
                    if sku is None:
                        sku = ProductSKU()
                        sku.product = product

                # remember the sku record to be saved once we processed
                # everything. We will not save anything until everything
                # is considered to be valid.
                skus_to_save.append(sku)

                # mark any assigned variety options as selected, so that they
                # indeed remain selected, even if they have actually not been
                # properly assigned yet because if from errors for example
                for _variety in varieties:
                    _options = _variety.get('options')
                    for _option in _options:
                        for _assigned_option in variety_options:
                            if _option.get('id') == _assigned_option.pk:
                                _option['assigned'] = True
                                break

                # inject error information and keep track of error states
                sku.errors = []
                if form.is_valid():
                    # update data from from
                    d = form.cleaned_data
                else:
                    for field, error in form.errors.items():
                        sku.errors.append({
                            'field': field,
                            'error': error[0]
                        })
                    is_valid = False

                # copy original data or cleaned data
                sku.enabled = d.get('enabled', False)
                sku.sku = d.get('sku')
                sku.barcode = d.get('barcode')
                sku.price = d.get('price')
                sku.stocklevel = d.get('stocklevel', 0)

                # keep track of variety options that should be assigned due to
                # SKU's that are enabled
                if sku.enabled:
                    assigned_option_ids.extend([option.pk for option in variety_options])

                # set variety options (saved later)
                sku._variety_options = variety_options

                # verify uniqueness of the SKU code
                if not self._verify_sku(product, sku, sku_code_processed, initial):
                    is_valid = False

                # verify uniqueness of barcode
                if not self._verify_barcode(product, sku, barcodes_processed, initial):
                    is_valid = False

                # maintain changed data in initial data set, so that all
                # changes make theire way back into the view, even through
                # we might not have saved changes due to errors
                _id = ('idx_%d' % index) if sku.pk is None else sku.pk
                initial[_id] = sku


        # process if everything is valid
        if request.method == 'POST' and is_valid:
            # create missing option assignments
            assigned_option_ids = list(set(filter(lambda x: x is not None, assigned_option_ids)))
            for option_id in assigned_option_ids:
                try:
                    assignment = VarietyAssignment.objects.get(product=product, variety_option__pk=option_id)
                except VarietyAssignment.DoesNotExist:
                    VarietyAssignment.objects.create(
                        product=product,
                        variety_option_id=option_id
                    )

            # remove deprecated option assignments
            deprecated_assignments = VarietyAssignment.objects.select_related('variety_option').filter(product=product, variety_option__variety__sku=True).exclude(variety_option__pk__in=assigned_option_ids)
            for deprecated_assignment in deprecated_assignments:
                deprecated_assignment.delete()

            # save changes to sku records. Null sku, so that we would not
            # collide when making updates
            sku_ids_saved = []
            for sku in skus_to_save:
                # save product sku itself
                sku._sku = sku.sku
                sku.sku = None
                sku.save()
                sku_ids_saved.append(sku.id)

                # assign and save variety options
                sku.variety_options = sku._variety_options

            # remove all previous SKU
            deprecated_skus = ProductSKU.objects.filter(product=product).exclude(pk__in=sku_ids_saved)
            for deprecated_sku in deprecated_skus:
                deprecated_sku.delete()

            # apply new sku names, which is now safe to do
            for sku in skus_to_save:
                if request.settings.sku_is_barcode:
                    sku.sku = sku.barcode
                else:
                    sku.sku = sku._sku
                sku.save()

        # redirect and message
        if request.method == 'POST' and is_valid:
            messages.add_message(request, messages.SUCCESS, 'Product Varieties and SKUs saved for <em>%s</em>.' % product.title)

            if request.POST.get('cubane_save_and_continue') is None:
                return self._redirect(request, 'index')
            else:
                return self._redirect(request, 'sku', product)

        # materialise current initial data
        _initial = {}
        for _id, _sku in initial.items():
            _initial[_id] = model_to_dict(_sku)
            if _sku.pk is None:
                _initial[_id]['variety_options'] = [option.pk for option in _sku._variety_options]
            else:
                _initial[_id]['variety_options'] = [option.pk for option in _sku.variety_options.all()]
            _initial[_id]['errors'] = _sku.errors if hasattr(_sku, 'errors') else []

        # template context
        return {
            'product': product,
            'varieties': varieties,
            'initial': to_json(_initial),
            'variety_index_json': to_json(variety_index),
            'form_template': form_template
        }


    def _verify_sku(self, product, sku, sku_code_processed, initial):
        """
        Verify that the given SKU does not exist twice in the system.
        """
        is_valid = True

        def add_error(errors, error):
            # already exists?
            for err in errors:
                if err.get('field') == error.get('field') and err.get('error') == error.get('error'):
                    return
            errors.append(error)

        # empty SKU?
        if not sku.sku:
            return is_valid

        # make sure that the sku number does not conflict with
        # any other product in the system.
        products = get_product_model().objects.filter(sku=sku)
        if products.count() > 0:
            sku.errors.append({
                'field': 'sku',
                'error': 'SKU number already in use by product \'%s\'.' % products[0].title
            })
            is_valid = False

        # conflicts with any other record we processed so far?
        if sku.sku in sku_code_processed:
            for _, _sku in initial.items():
                if _sku.sku == sku.sku:
                    error = {
                        'field': 'sku',
                        'error': 'SKU number already in use for this product.'
                    }
                    add_error(sku.errors, error)
                    add_error(_sku.errors, error)
            is_valid = False
        sku_code_processed.append(sku.sku)

        # conflict with any other SKU record for any other product?
        product_skus = ProductSKU.objects.exclude(product=product).filter(sku=sku.sku)
        if product_skus.count() > 0:
            sku.errors.append({
                'field': 'sku',
                'error': 'SKU number already in use by product \'%s\'.' % product_skus[0].product.title
            })
            is_valid = False

        return is_valid


    def _verify_barcode(self, product, sku, barcodes_processed, initial):
        """
        Verify that any assigned barcode does not exist twice in the system.
        """
        is_valid = True

        # empty barcode?
        if not sku.barcode:
            return is_valid

        # make sure that the barcode does not conflict with any product
        products = get_product_model().objects.filter(barcode=sku.barcode)
        if products.count() > 0:
            sku.errors.append({
                'field': 'barcode',
                'error': 'Barcode already in use by product \'%s\'.' % products[0].title
            })
            is_valid = False

        # conflicts with any other record we processed so far?
        if sku.barcode in barcodes_processed:
            for _, _sku in initial.items():
                if _sku.barcode == sku.barcode:
                    error = {
                        'field': 'barcode',
                        'error': 'Barcode already in use for this product.'
                    }
                    sku.errors.append(error)
                    _sku.errors.append(error)
            is_valid = False
        barcodes_processed.append(sku.barcode)

        # conflict with any other SKU record for any other product?
        product_skus = ProductSKU.objects.exclude(product=product).filter(barcode=sku.barcode)
        if product_skus.count() > 0:
            sku.errors.append({
                'field': 'barcode',
                'error': 'Barcode already in use by product \'%s\'.' % product_skus[0].product.title
            })
            is_valid = False

        return is_valid


    def delivery(self, request):
        product_id = request.GET.get('pk')
        product = get_object_or_404(get_product_model(), pk=product_id)

        # get general delivery options that are available
        options = DeliveryOption.objects.filter(enabled=True)

        # get available delivery options
        delivery_options = list(ProductDeliveryOption.objects.select_related('delivery_option').filter(product=product))
        delivery_options_ids = [option.delivery_option.id for option in delivery_options]

        # add missing options, so that each is convered
        for option in options:
            if option.id not in delivery_options_ids:
                assignment = ProductDeliveryOption()
                assignment.product = product
                assignment.delivery_option = option
                delivery_options.append(assignment)

        # dataset based on available options
        initial = [{
            'option_id': option.delivery_option.id,
            'deliver_uk': option.delivery_option.deliver_uk,
            'deliver_eu': option.delivery_option.deliver_eu,
            'deliver_world': option.delivery_option.deliver_world,
            'title': option.delivery_option.title,
            'uk': option.uk,
            'eu': option.eu,
            'world': option.world
        } for option in delivery_options]

        if request.method == 'POST':
            formset = DeliveryOptionFormset(request.POST, initial=initial)
        else:
            formset = DeliveryOptionFormset(initial=initial)

        if request.method == 'POST':
            if formset.is_valid():
                # delete all existing assignments
                assignments = ProductDeliveryOption.objects.filter(product=product)
                for assignment in assignments:
                    request.changelog.delete(assignment)
                    assignment.delete()

                # create new assignments
                for form in formset.forms:
                    d = form.cleaned_data
                    for option in options:
                        if option.id == d.get('option_id'):
                            assignment = ProductDeliveryOption()
                            assignment.product = product
                            assignment.delivery_option = option
                            assignment.uk = d.get('uk')
                            assignment.eu = d.get('eu')
                            assignment.world = d.get('world')
                            assignment.save()
                            request.changelog.create(assignment)
                            break;

                # commit, message and redirect
                request.changelog.commit(
                    'Delivery options for product <em>%s</em> updated.' % product.title,
                    product,
                    flash=True
                )
                return self.redirect_to_index_or(request, 'delivery', product)
            else:
                print formset.errors

        return {
            'product': product,
            'delivery_options': delivery_options,
            'form': formset
        }


    def google_products(self, request):
        def prettify_xml(elem):
            """
            Return a pretty-printed XML string for the Element.
            """
            rough_string = tostring(elem)
            reparsed = minidom.parseString(rough_string)
            return reparsed.toprettyxml(indent='\t').encode('utf-8', 'replace')

        products = get_product_model().objects.filter(feed_google=True)
        root = Element('rss')
        root.attrib['xmlns:g'] = 'http://base.google.com/ns/1.0'
        root.attrib['version'] = '2.0'
        channel = SubElement(root, 'channel')
        title = SubElement(channel, 'title')
        title.text = request.settings.name
        link = SubElement(channel, 'link')
        link.text = settings.DOMAIN_NAME
        description = SubElement(channel, 'description')

        for p in products:
            # availability
            if p.is_available and not p.pre_order:
                txt_availability = 'in stock'
            elif p.pre_order:
                txt_availability = 'preorder'
            else:
                txt_availability = 'out of stock'

            # determine delivery charge by placing the product onto the basket
            basket = Basket()
            basket.add_item(p, None, 1)
            delivery_charge = basket.delivery

            # determine feed item attributes
            txt_id = unicode(p.id)
            txt_title = clean_unicode(p.title).strip()
            txt_link = p.get_absolute_url()
            txt_description = text_from_html(p.description, 5000)
            txt_condition = 'new'
            txt_price = '%.2f GBP' % p.price
            txt_google_category = p.category.google_product_category if p.category and p.category.google_product_category else None
            txt_category = p.category.get_taxonomy_path() if p.category else None
            txt_country = 'GB'
            txt_delivery_price = '%s %s' % (delivery_charge, 'GBP')
            txt_barcode = p.barcode.strip() if p.barcode else None
            txt_part_number = p.part_number.strip() if p.part_number else None
            txt_brand = p.get_brand_title()

            # create item
            item = SubElement(channel, 'item')

            # id
            _id = SubElement(item, 'g:id')
            _id.text = txt_id

            # title
            title = SubElement(item, 'title')
            title.text = txt_title

            # link/url
            link = SubElement(item, 'link')
            link.text = txt_link

            # main text
            description = SubElement(item, 'description')
            description.text = txt_description

            # condition
            condition = SubElement(item, 'g:condition')
            condition.text = txt_condition

            # price
            price = SubElement(item, 'g:price')
            price.text = txt_price

            # availability
            availability = SubElement(item, 'g:availability')
            availability.text = txt_availability

            # google shopping category
            if txt_google_category:
                gcategory = SubElement(item, 'g:google_product_category')
                gcategory.text = txt_google_category

            # product type
            if txt_category:
                category = SubElement(item, 'g:product_type')
                category.text = txt_category

            # shipping
            shipping = SubElement(item, 'g:shipping')

            # country
            country = SubElement(shipping, 'g:country')
            country.text = txt_country

            # delivery price
            delivery_price = SubElement(shipping, 'g:price')
            delivery_price.text = txt_delivery_price

            # barcode, must be a valid UPC-A (GTIN-12), EAN/JAN (GTIN-13)
            # or GTIN-14, so we need to have at least 12 characters.
            if txt_barcode:
                gtin = SubElement(item, 'g:gtin')
                gtin.text = txt_barcode

            # part number
            if txt_part_number:
                _mpn = SubElement(item, 'g:mpn')
                _mpn.text = txt_part_number

            # brand
            if txt_brand:
                brand = SubElement(item, 'g:brand')
                brand.text = txt_brand

            # image
            if p.image:
                image = SubElement(item, 'g:image_link')
                image.text = p.image.large_url

            # additional images
            if len(p.gallery) > 0:
                for m in p.gallery[:10]:
                    additional_image_link = SubElement(item, 'g:additional_image_link')
                    additional_image_link.text = m.large_url

        # get temp. filename
        f = NamedTemporaryFile(delete=False)
        tmp_filename = f.name
        f.close()

        # create tmp file (utf-8)
        f = open(tmp_filename, 'w+b')
        f.write(prettify_xml(root))
        f.seek(0)

        # send response
        filename = 'google_products_%s.xml' % datetime.date.today().strftime('%d_%m_%Y')
        response = HttpResponse(FileWrapper(f), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response


class ProductBackendSection(BackendSection):
    title = 'Products'
    slug = 'products'
    view = ProductView('cubane.ishop.products', with_folders=True)