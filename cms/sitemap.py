# coding=UTF-8
from __future__ import unicode_literals
from django.http import Http404
from cubane.views import TemplateView, view_url, view
from cubane.backend.views import BackendSection
from cubane.cms import get_page_model
from cubane.lib.app import get_models
from cubane.lib.libjson import to_json_response


class SitemapView(TemplateView):
    """
    Edit cms content by navigating the main sitemap structure of the website.
    """
    template_path = 'cubane/cms/sitemap/'
    namespace = 'cubane.cms.sitemap'


    patterns = [
        view_url(r'^$',      'index', name='index'),
        view_url(r'^node/$', 'node',  name='node'),
    ]


    def __init__(self, *args, **kwargs):
        super(SitemapView, self).__init__(*args, **kwargs)


    def index(self, request):
        return {}


    def node(self, request):
        # get cms
        from cubane.cms.views import get_cms
        cms = get_cms()

        # root level (pages and directory categories)
        if 'pk' not in request.GET and 'type' not in request.GET:
            return to_json_response({
                'success': True,
                'items': [cms.get_sitemap_item(request, page) for page in cms.get_sitemap_root_pages()]
            })

        # get pk argument
        if 'pk' not in request.GET:
            raise Http404('Missing argument: pk.')
        try:
            pk = int(request.GET.get('pk'))
        except ValueError:
            raise Http404('Invalid pk argument: Not a number.')

        # get type argument
        if 'type' not in request.GET:
            raise Http404('Missing argument: type.')
        type_name = request.GET.get('type')

        # resolve type by given name
        model = None
        for m in get_models():
            if m.__name__ == type_name:
                model = m
                break
        if not model:
            raise Http404('Unknown model type name: \'%s\'.' % type_name)

        # get node by given pk
        node = model.objects.get(pk=pk)

        # generate child nodes
        items = []
        children = cms.get_sitemap_children(node)
        if children:
            for child in children:
                item = cms.get_sitemap_item(request, child)
                if item:
                    items.append(item)

        # return response (json)
        return to_json_response({
            'success': True,
            'items': items
        })


class SitemapSection(BackendSection):
    def __init__(self, *args, **kwargs):
        super(SitemapSection, self).__init__(*args, **kwargs)
        self.view = SitemapView()
        self.title = 'Sitemap'
        self.slug = 'sitemap'