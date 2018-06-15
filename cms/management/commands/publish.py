# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from cubane.lib.file import sizeof_fmt


class Command(BaseCommand):
    """
    Publish CMS content and write static content pages to disk, so that
    we do not hit the application server all the time.
    """
    args = ''
    help = 'Publish CMS content.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        from cubane.cms.views import get_cms
        cms = get_cms()

        print 'Publishing content...Please Wait...'
        print 'CACHE: %s' % settings.CACHE_ROOT
        print

        (items, size_bytes, time_sec) = cms.publish(verbose=True)

        print '%d files published. %s. %s sec.' % (
            items,
            sizeof_fmt(size_bytes),
            '{0:.2f}'.format(time_sec)
        )
