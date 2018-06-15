# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db.models import Prefetch, Count
from cubane.views import ModelView, view_url, view
from cubane.backend.views import BackendSection
from cubane.lib.libjson import to_json_response
from cubane.lib.parse import parse_int
from cubane.ishop import get_product_model
from cubane.ishop.apps.merchant.varieties.forms import (
    VarietyForm,
    VarietyFormset,
    VarietyAttributeFormset,
    VarietyOptionImportForm
)
from cubane.ishop.models import (
    Variety,
    VarietyOption,
    VarietyAssignment,
    ProductCategory
)


class VarietyView(ModelView):
    """
    Editing varieties.
    """
    template_path = 'cubane/ishop/merchant/varieties/'
    namespace = 'cubane.ishop.varieties'
    folder_model = Variety
    model = Variety
    form = VarietyForm


    patterns = [
        view_url(r'options/', 'options', name='options'),
        view_url(r'products/', 'products', name='products'),
        view_url(r'update\-seq/(?P<variety_id>\d+)/', 'update_seq', name='update_seq'),
    ]

    listing_actions = [
        ('[Options]', 'options', 'single'),
        ('[Products]', 'products', 'single'),
    ]

    shortcut_actions = [
        'options',
        'products'
    ]


    def _get_objects(self, request):
        return self.model.objects.prefetch_related(
            Prefetch('options', queryset=VarietyOption.objects.order_by('seq'))
        ).annotate(
            num_products=Count('options__assignments__product', distinct=True)
        )


    def _get_objects_for_seq(self, request):
        return self.model.objects.all()


    def _get_folders(self, request, parent):
        folders = self.folder_model.objects.all()

        if parent:
            folders = folders.filter(parent=parent)

        return folders


    def options(self, request):
        # load variety
        variety_id = request.GET.get('pk')
        variety = get_object_or_404(Variety, pk=variety_id)

        # load import variety
        import_variety_id = request.GET.get('import_variety')
        import_variety = None
        if import_variety_id:
            try:
                import_variety = Variety.objects.get(pk=import_variety_id)
            except variety.DoesNotExist:
                pass

        # get current list of options, or if we are importing from the
        # given source
        if import_variety:
            options = list(import_variety.options.order_by('seq'))
            for option in options:
                option.id = None
                option.variety = None
        else:
            options = list(variety.options.order_by('seq', 'id'))

        initial = [{
            'title': option.title,
            'enabled': option.enabled,
            'image': option.image,
            'color': option.color,
            'offset_type': option.default_offset_type,
            'offset_value': option.default_offset_value,
            'text_label': option.text_label,
            'seq': seq,
            '_id': option.id
        } for seq, option in enumerate(options, start=1)]

        # determine form (attribute or variety)
        if variety.is_attribute:
            form_class = VarietyAttributeFormset
        else:
            form_class = VarietyFormset

        # create main form
        if request.method == 'POST':
            formset = form_class(request.POST, initial=initial)
        else:
            formset = form_class(initial=initial)

        # form validation
        if request.method == 'POST':
            if request.POST.get('cubane_form_cancel', '0') == '1':
                return self._redirect(request, 'index')

            if formset.is_valid():
                seq = 0
                for form in formset.forms:
                    d = form.cleaned_data

                    try:
                        option = filter(lambda o: o.id == d.get('_id'), options)[0]
                    except IndexError:
                        option = VarietyOption()

                    if d.get('DELETE') == False and d.get('title'):
                        option.title = d.get('title')
                        option.enabled = d.get('enabled')
                        option.image = d.get('image')
                        option.color = d.get('color')
                        option.seq   = d.get('seq')
                        option.text_label = d.get('text_label')
                        option.variety = variety

                        if option.seq is None:
                            option.seq = seq + 1
                            seq += 1

                        if option.seq > seq:
                            seq = option.seq

                        if not variety.is_attribute:
                            option.default_offset_type = d.get('offset_type')
                            option.default_offset_value = d.get('offset_value')

                        # get previous state
                        if option.pk is not None:
                            previous_instance = request.changelog.get_changes(option)
                        else:
                            previous_instance = None

                        # save option
                        option.save()

                        # generate changelog
                        if previous_instance:
                            request.changelog.edit(option, previous_instance)
                        else:
                            request.changelog.create(option)

                    elif d.get('DELETE') == True and option.id != None:
                        # delete option
                        request.changelog.delete(option)
                        option.delete()

                request.changelog.commit(
                    'Variety Options for <em>%s</em> updated.' % variety.title,
                    variety,
                    flash=True
                )
                return self.redirect_to_index_or(request, 'options', variety)

        # create import form
        if request.method == 'GET':
            import_form = VarietyOptionImportForm()
            import_form.configure(request, variety)
        else:
            import_form = None

        return {
            'variety': variety,
            'form': formset,
            'import_form': import_form,
            'kit_builder': settings.SHOP_ENABLE_KIT_BUILDER
        }


    def products(self, request):
        variety_id = request.GET.get('pk')
        variety = get_object_or_404(Variety, pk=variety_id)

        assignments = VarietyAssignment.objects.filter(variety_option__variety=variety).values('product_id').distinct()
        product_ids = [a.get('product_id') for a in assignments]

        # get products
        if settings.SHOP_MULTIPLE_CATEGORIES:
            products = get_product_model().objects.prefetch_related(
                Prefetch('categories', queryset=ProductCategory.objects.select_related('category').order_by('seq'))
            ).distinct()
        else:
            products = get_product_model().objects.select_related('category')
        products = products.filter(pk__in=product_ids).order_by('title')

        if request.method == 'POST':
            return self._redirect(request, 'index')

        return {
            'variety': variety,
            'products': products
        }


    def combine(self, request):
        variety_ids = request.GET.getlist('pks[]')

        # get target
        if len(variety_ids) > 0:
            target = Variety.objects.get(pk=variety_ids[0])
        else:
            target = None

        # get sources
        sources = []
        if len(variety_ids) > 1:
            varieties = Variety.objects.in_bulk(variety_ids[1:])
            for vid in variety_ids[1:]:
                sources.append(varieties.get(int(vid)))

        # get combines options
        options = list(target.options.all())
        for s in sources:
            options.extend(list(s.options.all()))

        if request.method == 'POST':
            if request.POST.get('cubane_form_cancel', '0') != '1':
                # build index for target
                labels = {}
                for option in target.options.all():
                    labels[option.title] = option

                # process all sources
                obsolete_options = []
                for variety in sources:
                    for option in variety.options.all().order_by('seq'):
                        if option.title in labels:
                            # already exists. Now we have to change all assignments over to point to the new one in target
                            for assignment in VarietyAssignment.objects.filter(variety_option=option):
                                assignment.variety_option = labels.get(option.title)
                                assignment.save()
                            obsolete_options.append(option)
                        else:
                            # does not exist yet, simply change the option over to point to the target variety
                            option.variety = target
                            option.save()
                            labels[option.title] = option

                # remove obsolete options
                [option.delete() for option in obsolete_options]

                # remove source varieties, since they all have been combined into target.
                [variety.delete() for variety in sources]

                messages.add_message(request, messages.SUCCESS, 'Varieties Combined successfully into <em>%s</em>.' % target.title)

            return self._redirect(request, 'index')

        return {
            'target': target,
            'sources': sources,
            'options': options
        }


    @view(require_POST)
    def update_seq(self, request, variety_id=None):
        variety = get_object_or_404(Variety, pk=variety_id)

        option_ids = [parse_int(x, 0) for x in request.POST.getlist('option[]')]
        if any(map(lambda x: x == 0, option_ids)):
            raise Http404('Unable to parse option id list.')

        options = list(variety.options.order_by('seq', 'id'))
        for i, oid in enumerate(option_ids, start = 1):
            o = [o for o in options if o.id == oid][0]
            o.seq = i
            o.save()

        return to_json_response({'success': True})


class VarietyOptionView(ModelView):
    """
    Editing variety options.
    """
    template_path = 'cubane/ishop/merchant/variety_options/'
    namespace = 'cubane.ishop.variety_options'
    folder_model = Variety
    model = VarietyOption


    def _get_objects(self, request):
        return self.model.objects.all()


    def _get_folders(self, request, parent):
        folders = self.folder_model.objects.all()

        if parent:
            folders = folders.filter(parent=parent)

        return folders


    def _get_folder_assignment_name(self):
        """
        Return the name of the field that is used to assign a folder to
        (variety).
        """
        return 'variety'


class VarietyBackendSection(BackendSection):
    title = 'Varieties'
    slug = 'varieties'
    view = VarietyView()


class VarietyOptionBackendSection(BackendSection):
    title = 'Variety Options'
    slug = 'variety-options'
    view = VarietyOptionView()