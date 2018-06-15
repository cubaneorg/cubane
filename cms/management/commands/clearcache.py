# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from cubane.lib.file import sizeof_fmt
from cubane.lib.verbose import out


class Command(BaseCommand):
    """
    Clear entire CMS cache and remove all cached content files and meta data.
    """
    args = ''
    help = 'Deletes all CMS content from the cache.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        from cubane.cms.views import get_cms
        cms = get_cms()

        out('Deleting cache...Please Wait...')
        out('CACHE: %s' % settings.CACHE_ROOT)

        items = cms.clear_cache(verbose=True)
        out('%d files removed.' % items)