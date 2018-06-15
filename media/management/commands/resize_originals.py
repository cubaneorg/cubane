# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.media.models import Media
import os


class Command(BaseCommand):
    """
    Re-Generate all image thumbnail versions.
    """
    args = ''
    help = 'Resize original images'


    def handle(self, *args, **options):
        """
        Run command.
        """
        images = Media.objects.filter(is_image=True)
        n = images.count()

        print 'Processing images...Please Wait...'

        for i, image in enumerate(images, start=1):
            if image.resize_if_too_wide():
                print '%-70s   [%d%%]' % (
                    image.filename,
                    int(float(i) / float(n) * 100.0)
                )
        print '%d of %d images processed.' % (i, n)
