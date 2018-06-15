# coding=UTF-8
from __future__ import unicode_literals
from django.http import Http404, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from cubane.views import TemplateView, ModelView, view_url
from cubane.backend.views import BackendSection
from cubane.media.views import load_media_gallery, save_media_gallery
from cubane.lib.libjson import to_json_response
from cubane.ishop import get_category_model
from cubane.ishop.api import IShop
import copy


class CategoryView(ModelView):
    """
    Editing categories (tree)
    """
    template_path = 'cubane/ishop/merchant/categories/'
    namespace = 'cubane.ishop.categories'
    model = get_category_model()
    folder_model = get_category_model()


    def _get_objects(self, request):
        return self.model.objects.select_related('parent').all()


    def _get_folders(self, request, parent):
        folders = self.folder_model.objects.all()

        if parent:
            folders = folders.filter(parent=parent)

        return folders


    def form_initial(self, request, initial, instance, edit):
        """
        Setup gallery images (initial form data)
        """
        initial['_gallery_images'] = load_media_gallery(instance.gallery_images)


    def after_save(self, request, d, instance, edit):
        """
        Save gallery items (in seq.)
        """
        save_media_gallery(request, instance, d.get('_gallery_images'))


class CategoryBackendSection(BackendSection):
    title = 'Categories'
    slug = 'categories'
    view = CategoryView()