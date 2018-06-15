# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from cubane.lib.file import sizeof_fmt
from cubane.lib.verbose import out


class Command(BaseCommand):
    """
    Invalidate CMS cache and remove all cached content files.
    """
    args = ''
    help = 'Invalidates all CMS content from the cache.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        from cubane.cms.views import get_cms
        cms = get_cms()

        out('Invalidating cache...Please Wait...')
        out('CACHE: %s' % settings.CACHE_ROOT)

        items = cms.invalidate(verbose=True)
        out('%d files removed.' % items)