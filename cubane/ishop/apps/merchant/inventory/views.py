# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.db import transaction
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_GET, require_POST
from django.template.defaultfilters import slugify
from django.db.models import Prefetch
from django.shortcuts import render
from cubane.lib.url import get_absolute_url
from cubane.lib.text import pluralize
from cubane.lib.module import get_class_from_string
from cubane.lib.libjson import to_json
from cubane.backend.views import BackendSection
from cubane.views import ModelView, view_url, view
from cubane.cms.views import get_cms_settings
from cubane.ishop.apps.merchant.inventory.forms import ShopInventoryImportForm, ShopInventoryExportForm
from cubane.ishop.apps.merchant.inventory.importer import ShopInventoryImporter
from cubane.ishop.apps.merchant.inventory.exporter import ShopInventoryExporter
from cubane.ishop.models import ProductSKU, VarietyOption, VarietyAssignment
import os
import datetime


class InventoryView(ModelView):
    model = ProductSKU
    namespace = 'cubane.ishop.inventory'
    template_path = 'cubane/ishop/merchant/inventory/'

    patterns = [
        view_url(r'inventory-import/', 'inventory_import', name='inventory_import'),
        view_url(r'inventory-export/', 'inventory_export', name='inventory_export'),
    ]

    listing_actions = [
        ('Import / Export', 'inventory_import', 'any')
    ]


    def _get_objects(self, request):
        return ProductSKU.objects.prefetch_related(
            Prefetch('variety_options', queryset=VarietyOption.objects.order_by('seq'))
        )


    def before_save(self, request, cleaned_data, instance, edit):
        """
        Save barcode as SKU number
        """
        if request.settings.sku_is_barcode:
            instance.sku = cleaned_data.get('barcode')


    def after_save(self, request, cleaned_data, instance, edit):
        """
        Maintain variety assignments
        """
        for variety_option in instance.variety_options.all():
            try:
                assignment = VarietyAssignment.objects.get(product=instance.product, variety_option=variety_option)
            except VarietyAssignment.DoesNotExist:
                VarietyAssignment.objects.create(
                    product=instance.product,
                    variety_option=variety_option
                )


    def before_delete(self, request, instance):
        """
        Delete variety assignments
        """
        for variety_option in instance.variety_options.select_related('variety').all():
            if variety_option.variety.sku:
                try:
                    assignment = VarietyAssignment.objects.get(product=instance.product, variety_option=variety_option)
                    assignment.delete()
                except VarietyAssignment.DoesNotExist:
                    pass


    def inventory_import(self, request):
        """
        Shop Inventory Import (CSV).
        """
        # default encoding
        initial = {
            'encoding': get_cms_settings().default_encoding
        }

        if request.method == 'POST':
            form = ShopInventoryImportForm(request.POST, request.FILES)
        else:
            form = ShopInventoryImportForm(initial=initial)
            form.configure(request)

            export_form = ShopInventoryExportForm(initial=initial)
            export_form.configure(request)

        if request.method == 'POST' and form.is_valid():
            d = form.cleaned_data

            # create importer and import date
            importer = ShopInventoryImporter()
            importer.import_from_stream(
                request,
                request.FILES['csvfile'],
                encoding=d.get('encoding')
            )

            # present information what happend during import
            if importer.has_errors:
                transaction.rollback()

                errors = importer.get_formatted_errors()
                messages.add_message(
                    request,
                    messages.ERROR, (
                        'Import failed due to %s. No data ' +
                        'has been imported. Please correct all issues ' +
                        'and try again.'
                    ) % pluralize(len(errors), 'error', tag='em')
                )

                for message in errors:
                    messages.add_message(request, messages.ERROR, message)

                # redirect to itself if we have errors
                return HttpResponseRedirect(get_absolute_url('cubane.ishop.inventory.inventory_import'))
            else:
                # success message, render image processing page
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    pluralize(
                        importer.num_records_processed,
                        'record',
                        'processed successfully',
                        tag='em'
                    )
                )

                # redirect to itself if we have errors
                return HttpResponseRedirect(get_absolute_url('cubane.ishop.inventory.inventory_import'))

        return {
            'form': form,
            'export_form': export_form,
            'export_form_action': reverse('cubane.ishop.inventory.inventory_export')
        }


    def inventory_export(self, request):
        """
        Shop Inventory Export (CSV).
        """
        # create exporter and export inventory data
        exporter = ShopInventoryExporter()
        f = exporter.export_to_temp_file(encoding=request.GET.get('encoding'))

        # generate filename based on today's date
        cms_settings = get_cms_settings()
        today = datetime.date.today()
        filename = '{0}__{1:02d}_{2:02d}_{3:04d}.csv'.format(
            slugify(cms_settings.name).replace('-', '_'),
            today.day,
            today.month,
            today.year
        )

        # serve file
        response = FileResponse(f)
        response['Content-Type'] = 'text/csv'
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


    def old_data_importer(self, request):
        """
        Import Form.
        """
        if request.method == 'POST':
            form = ShopDataImportForm(request.POST, request.FILES)
        else:
            form = ShopDataImportForm()
            form.configure(request)

            export_form = ShopInventoryExportForm()
            export_form.configure(request)

        if request.method == 'POST' and form.is_valid():
            d = form.cleaned_data

            # load data importer
            import_classname = settings.CUBANE_SHOP_IMPORT.get('importer', 'cubane.ishop.apps.merchant.dataimport.importer.ShopDataImporter')
            import_class = get_class_from_string(import_classname)

            # create importer and start importing...
            importer = import_class(
                import_images=d.get('import_images')
            )
            importer.import_from_stream(
                request,
                request.FILES['csvfile'],
                encoding=d.get('encoding')
            )

            # present information what happend during import
            if importer.has_errors:
                transaction.rollback()

                errors = importer.get_formatted_errors()
                messages.add_message(
                    request,
                    messages.ERROR, (
                        'Import failed due to %s. No data ' +
                        'has been imported. Please correct all issues ' +
                        'and try again.'
                    ) % pluralize(len(errors), 'error', tag='em')
                )

                for message in errors:
                    messages.add_message(request, messages.ERROR, message)

                # redirect to itself if we have errors
                return HttpResponseRedirect(get_absolute_url('cubane.ishop.dataimport.index'))
            else:
                # success message, render image processing page
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    pluralize(
                        importer.num_records_processed,
                        'record',
                        'processed successfully',
                        tag='em'
                    )
                )

                # redirect to itself if we have errors
                return HttpResponseRedirect(get_absolute_url('cubane.ishop.dataimport.index'))

        return {
            'form': form,
            'export_form': export_form
        }


class InventoryBackendSection(BackendSection):
    title = 'Inventory'
    slug = 'inventory'
    view = InventoryView()