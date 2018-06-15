# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from cubane.lib.file import sizeof_fmt
from cubane.lib.verbose import out


class Command(BaseCommand):
    """
    Generate redirect rules based on legacy urls in the system.
    """
    args = ''
    help = 'Generate redirect rules based on legacy urls in the system.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        from cubane.cms.views import get_cms
        cms = get_cms()

        out('Generating redirect urls...Please Wait...')

        sitemap = cms.get_sitemaps()
        redirects = {}
        for k, sitemap in sitemap.items():
            print k
            for item in sitemap.items():
                if hasattr(item, 'legacy_url'):
                    legacy_url = item.legacy_url
                    if legacy_url:
                        redirects[legacy_url] = item.get_absolute_url()
                elif hasattr(item, 'get_legacy_urls'):
                    legacy_urls = item.get_legacy_urls()
                    for legacy_url in legacy_urls:
                        redirects[legacy_url] = item.get_absolute_url()

        if not settings.TEST:
            print redirects