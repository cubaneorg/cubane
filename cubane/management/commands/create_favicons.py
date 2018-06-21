# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.staticfiles.finders import find
from wand.image import Image as wandimage
from cubane.lib.file import ensure_dir
from cubane.lib.verbose import out
from cubane.lib.image import *
import os


class Command(BaseCommand):
    """
    Generate all favicons from png.
    """
    args = ''
    help = 'Generate all favicons from png'


    def handle(self, *args, **options):
        """
        Run command.
        """
        rel_path = os.path.join(settings.FAVICON_PATH, settings.FAVICON_FILENAME)
        self.original_img_path = find(rel_path)

        if not self.original_img_path or not os.path.isfile(self.original_img_path):
            out('favicon file doesn\'t exist please ensure there is a file here: %s' % rel_path)
        else:
            out('Processing favicons...Please Wait...')

            for i, image in enumerate(settings.FAVICON_PNG_SIZES, start=1):
                self.generate_image(image)
                out('%-70s   [%d%%]' % (
                    image['filename'],
                    int(float(i) / float(len(settings.FAVICON_PNG_SIZES)) * 100.0)
                ))
            out('%d of %d favicons processed.' % (i, len(settings.FAVICON_PNG_SIZES)))

            self.generate_ico_file()

            out('Complete.')


    def generate_image(self, img):
        path = self.get_image_path(img['size'], 'png')
        ensure_dir(path)
        w = int(img['size'].split('x')[0])
        h = int(img['size'].split('x')[1])

        resize_image(self.original_img_path, path, w, h, 'scale')


    def generate_ico_file(self):
        filename = self.get_image_path(settings.FAVICON_ICO_SIZES[-1]['size'], 'png')
        with wandimage(filename=filename) as ico:
            for img in settings.FAVICON_ICO_SIZES[:-1]:
                image = wandimage(filename=self.get_image_path(img['size'], 'png'))
                ico.sequence.append(image)

            ico_filename = os.path.join(settings.PUBLIC_HTML_ROOT, 'favicon.ico')
            ensure_dir(ico_filename)
            ico.save(filename=ico_filename)


    def get_image_path(self, size, ext):
        filename = 'favicon-' + size + '.' + ext
        return os.path.join(settings.MEDIA_ROOT, 'favicons', filename)
