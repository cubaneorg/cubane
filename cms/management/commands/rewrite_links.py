# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.cms.views import get_cms
from cubane.lib.app import get_models
from cubane.lib.html import get_normalised_links
from cubane.lib.url import is_external_url, to_legacy_url
import re


class Command(BaseCommand):
    """
    Rewrites links within all CMS content fields, so that external website
    URLS are NOT opening in a new window; while external links do.
    """
    args = ''
    help = 'Rewrite CMS links'


    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--simulate',
            action='store_true',
            help='Simulate all actions without actually carrying them out.'
        )
        parser.add_argument(
            '--pk',
            metavar=('primary-key of an individual content page to process'),
            help='Only process content pages with the given matching primary key.'
        )


    def handle(self, *args, **options):
        """
        Run command.
        """
        print 'Rewriting CMS links ...Please Wait...'

        # simulation mode?
        simulate = options.get('simulate', False)

        # collect content models
        cms = get_cms()
        cms_models = tuple(cms.get_supported_models())
        links = self.get_page_links()

        # process all models in the system
        models = get_models()
        i = 0
        n = 0
        for m in models:
            if issubclass(m, cms_models):
                _i, _n = self.process_model(m, links, simulate, options.get('pk'))
                i += _i
                n += _n

        print '%d item(s) updated out of %d content page(s) in total.%s' % (
            i,
            n,
            ' (Simulated!)' if simulate else ''
        )


    def get_page_links(self):
        """
        Return a dictionary of all known content pages via their url path.
        """
        result = {}
        cms = get_cms()
        cms_models = tuple(cms.get_supported_models())
        models = get_models()
        for model in models:
            if issubclass(model, cms_models):
                for instance in model.objects.all():
                    if hasattr(instance, 'get_absolute_url'):
                        page_path = to_legacy_url(instance.get_absolute_url())
                        link = '#link[%s:%s]' % (model.__name__, instance.pk)
                        result[page_path] = link
        return result


    def process_model(self, model, links, simulate=False, pk=None):
        """
        Process the given model.
        """
        instances = model.objects.all()
        if pk:
            instances = instances.filter(pk=pk)

        i = 0
        n = 0
        for instance in instances:
            if hasattr(instance, 'get_data'):
                data = instance.get_data()
                changed = False
                if data:
                    for slotname, content in data.items():
                        new_content = get_normalised_links(content, self.get_href_rewrite(links))
                        if content != new_content:
                            print '\t%-20s\t%-60s' % (model._meta.verbose_name, instance)
                            i += 1
                            if not simulate:
                                data[slotname] = new_content
                                changed = True

                if changed and not simulate:
                    instance.set_data(data)
                    instance.save()

            n += 1

        return i, n


    def get_href_rewrite(self, links):
        """
        Rewrites given href url to shortcut link url if the given href
        is an internal url.
        """
        def href_rewrite(href):
            if href and not href.startswith('#') and not is_external_url(href):
                path = to_legacy_url(href)
                link = links.get(path)
                if link:
                    href = link
            return href
        return href_rewrite