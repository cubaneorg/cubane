# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.utils.text import slugify
from cubane.views import ApiView, view_url
from cubane.lib.acl import Acl
from cubane.lib.model import model_to_dict
from cubane.lib.module import get_class_from_string


class LinkBuilder(object):
    """
    Helper class for customer-facing code to add additional object links.
    """
    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.links = []


    def add(self, model, links, title=None, slug=None):
        """
        Add the given list of links based on the given model.
        """
        if title is None:
            title = model._meta.verbose_name_plural.title()

        if slug is None:
            slug = slugify(title)

        links = Acl.of(links.model).filter(self.request, links)

        self.links.append({
            'title': title,
            'type': model.__name__,
            'slug': slug,
            'links': [{
                'id': x.pk,
                'title': '%s' % x
            } for x in links]
        })


class BackendApiView(ApiView):
    """
    Backend api (XHR only).
    """
    namespace = 'cubane.backend.api'
    slug = 'api'
    patterns = [
        ('links/$',  'links',  {}, 'links'),
        ('images/$', 'images', {}, 'images'),
        ('db/(?P<model_name>[-_\w\d\.]+)/$', 'db_get_all', {}, 'db.getall'),
        ('db/(?P<model_name>[-_\w\d\.]+)/(?P<pk>[-_\w\d\.]+)/$', 'db_get', {}, 'db.get')
    ]


    def links(self, request):
        """
        Return a list of links (e.g. pages, documents etc).
        """
        items = []

        if 'cubane.cms' in settings.INSTALLED_APPS:
            from cubane.cms import get_page_model
            from cubane.cms.views import get_cms

            # pages
            page_model = get_page_model()
            pages = page_model.objects.filter(disabled=False)
            pages = Acl.of(page_model).filter(request, pages)
            items.append({
                'title': page_model._meta.verbose_name_plural.title(),
                'type': page_model.__name__,
                'slug': slugify(page_model._meta.verbose_name_plural),
                'links': [{
                    'id': x.id,
                    'title': x.title
                } for x in pages]
            })

            # child pages
            cms = get_cms()
            for model in cms.get_child_page_models():
                child_pages = model.objects.filter(disabled=False)
                child_pages = Acl.of(model).filter(request, child_pages)
                items.append({
                    'title': model._meta.verbose_name_plural.title(),
                    'type': model.__name__,
                    'slug': slugify(model._meta.verbose_name_plural),
                    'links': [{
                        'id': x.id,
                        'title': x.title
                    } for x in child_pages]
                })

            # call back into CMS class to receive more links
            link_builder = LinkBuilder(request)
            cms.on_object_links(link_builder)
            items.extend(link_builder.links)


        if 'cubane.media' in settings.INSTALLED_APPS:
            from cubane.media.models import Media
            media = Media.objects.filter(is_image=False)
            media = Acl.of(Media).filter(request, media)
            items.append({
                'title': 'Documents',
                'type': 'Media',
                'slug': 'documents',
                'links': [{
                    'id': x.id,
                    'title': x.caption
                } for x in media]
            })

        return {
            'items': items,
            'links': None
        }


    def images(self, request):
        """
        Return a list of images.
        """
        if 'cubane.media' in settings.INSTALLED_APPS:
            from cubane.media.models import Media
            images = Media.objects.filter(is_image=True)
            images = Acl.of(Media).filter(request, images)
        else:
            images = []

        return images


    def db_get_all(self, request, model_name):
        """
        As part of the REST API, return a list of all model instances.
        """
        # get model
        try:
            model = get_class_from_string(model_name)
        except:
            return self._db_error('Unknown model.')

        # get list
        qs = model.objects.all()
        instances = Acl.of(model).filter(request, qs)
        result = [model_to_dict(instance, exclude_many_to_many=True, json=True) for instance in instances]

        # result
        return {
            'success': True,
            'message': 'OK',
            'result': result
        }


    def db_get(self, request, model_name, pk):
        """
        As part of the REST API, return a specific instance of the given model
        with the given pk.
        """
        # get model
        try:
            model = get_class_from_string(model_name)
        except:
            return self._db_error('Unknown model.')

        # get instance
        try:
            qs = model.objects.filter(pk=pk)
            instance = Acl.of(model).filter(request, qs)[0]
        except:
            return self._db_error('Unknown pk.')

        # result
        return {
            'success': True,
            'message': 'OK',
            'result': model_to_dict(instance, exclude_many_to_many=True, json=True)
        }


    def _db_error(self, msg):
        """
        REST API error response.
        """
        return {
            'success': False,
            'message': msg
        }