# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db.models import Q
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.media.models import Media
from cubane.lib.image import get_ext
import os
import shutil


class Command(BaseCommand):
    """
    Re-Generate all image thumbnail versions.
    """
    args = ''
    help = 'Re-Generate image thumbnails'


    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--pk',
            metavar=('primary-key of an individual image to update'),
            help='Re-generate thumbnail versions of the image with given primary key.'
        )

        parser.add_argument(
            '--images',
            action='store_true',
            help='Re-generate thumbnail versions of all images only.'
        )

        parser.add_argument(
            '--documents',
            action='store_true',
            help='Re-generate thumbnail versions of all documents only.'
        )

        parser.add_argument(
            '--continue',
            metavar=('primary-key of an individual image from where the process is continued.'),
            help='Continue re-generation of thumbnail versions from a specific filename.'
        )

        parser.add_argument(
            '--shape',
            metavar=('Name of a shape for which thumbnail versions are generated.'),
            help='Generates all thumbnail versions for a specific shape only.'
        )


    def handle(self, *args, **options):
        """
        Run command.
        """
        # determine images to work with
        process_documents = False
        if options.get('documents'):
            # documents only
            images = Media.objects.filter(
                is_image=False,
                has_preview=True
            )
            process_documents = True
        elif options.get('images'):
            # images only
            images = Media.objects.filter(
                is_image=True
            )
        else:
            # images and docuements
            images = Media.objects.filter(
                Q(is_image=True) |
                Q(has_preview=True)
            )
            process_documents = True

        # specific pk?
        if options.get('pk'):
            images = images.filter(pk=options.get('pk'))

        # continuation
        if options.get('continue'):
            continue_filename = options.get('continue')
        else:
            continue_filename = None

        # specific shape?
        shape = options.get('shape')
        if shape:
            shapes = Media.get_shapes().keys()
            if shape not in shapes:
                print 'ERROR: Invalid shape name \'%s\'. Available shapes: %s.' % (
                    shape,
                    ', '.join(['\'%s\'' % s for s in shapes])
                )
                return

        # re-evaluate PDF files
        for media in Media.objects.filter(is_image=False, has_preview=False):
            if get_ext(media.filename) == 'pdf':
                media.has_preview = True
                media.save()

        # delete deprecated image shapes and sizes
        self.delete_deprecated_image_sizes()
        self.delete_deprecated_image_shapes()

        # determine count of images to process...
        n = images.count()

        # process images
        print 'Processing images...Please Wait...'
        process_item = continue_filename is None
        for i, image in enumerate(images, start=1):
            # continuation?
            if continue_filename:
                if image.filename == continue_filename:
                    process_item = True

            # generate image versions and re-generate meta data
            if process_item:
                image.upload(shape=shape)

            # verbose output
            print '%-70s   [%d%%]' % (
                image.filename,
                int(float(i) / float(n) * 100.0)
            )
        print '%d images processed.' % n


    def delete_deprecated_image_sizes(self):
        """
        Delete any image sizes that are no longer defined.
        """
        sizes = settings.IMAGE_SIZES.keys()
        deprecated_sizes = []
        for shape in Media.get_shape_names():
            base_path = Media.get_shape_path(shape)
            try:
                folders = os.listdir(base_path)
            except OSError:
                folders = []

            for folder in folders:
                if not folder.startswith('.') and folder not in sizes:
                    path = os.path.join(base_path, folder)
                    if os.path.isdir(path):
                        shutil.rmtree(path)

                        if folder not in deprecated_sizes:
                            deprecated_sizes.append(folder)

        if len(deprecated_sizes) > 0:
            print '%d deprecated image size(s) deleted (%s).' % (
                len(deprecated_sizes),
                ', '.join(deprecated_sizes)
            )


    def delete_deprecated_image_shapes(self):
        """
        Delete any image shapes that are no longer defined.
        """
        shapes = Media.get_shape_names()
        deprecated_shapes = []
        base_path = Media.get_shape_base_path()
        try:
            folders = os.listdir(base_path)
        except OSError:
            folders = []

        for folder in folders:
            if not folder.startswith('.') and folder != 'original' and folder not in shapes:
                path = os.path.join(base_path, folder)
                if os.path.isdir(path):
                    shutil.rmtree(path)

                    if folder not in deprecated_shapes:
                        deprecated_shapes.append(folder)

        if len(deprecated_shapes) > 0:
            print '%d deprecated image shape(s) deleted (%s).' % (
                len(deprecated_shapes),
                ', '.join(deprecated_shapes)
            )