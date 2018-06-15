# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete, post_delete
from django.db.models.signals import ModelSignal
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from cubane.models import DateTimeBase
from cubane.cms.cache import Cache
from cubane.lib.url import url_join, make_absolute_url
from cubane.lib.file import ensure_dir, get_caption_from_filename
from cubane.lib.file import file_move
from cubane.lib.image import *
from cubane.lib.libjson import to_json, decode_json
from cubane.tasks import TaskRunner
import re
import os
import shutil
import math
import uuid
import hashlib
import random
import string
import requests


MAX_FILENAME_LENGTH = 255


pre_delete_media = ModelSignal(providing_args=['instance'], use_caching=True)


def filter_by_image_size(objects, args):
    """
    Filter for images with a maximum width. This helper function is used as
    part of the media filter form within the backend for filtering media assets
    by width.
    """
    v = args.get('image_size', None)
    if not v: return objects

    p = v.split('-', 2)
    if len(p) != 2:
        return objects

    try:
        low = int(p[0])
        high = int(p[1])
    except ValueError:
        return objects

    return objects.filter(is_image=True, width__gte=low, width__lte=high)


def get_ratio_percent(ratio):
    """
    Return the given ratio as an integer if it is an integer, otherwise
    the value is expressed as a float value. The css compressor has an issue
    with xyz.0%, which is why we force it to xyz% instead...
    """
    r = 100.0 / ratio
    r_int = int(r)
    if r_int == r:
        r = r_int
    return r


def get_art_direction_for_shape(shape_directives, shapes):
    """
    Return a list of art direction directives including min. and max. width
    mapped to image shapes sorted by width based on the given art direction
    settings for a particular art-directed shape.
    """
    art_directions = []
    width = []

    for w, shape in shape_directives.items():
        # determine max. target width (inclusive)
        if w == '*':
            w = 0
        else:
            try:
                w = int(w)
            except ValueError:
                w = -1

        if w >= 0 and w not in width:
            width.append(w)
            art_directions.append( (w, shape) )

    # sort by width
    art_directions = sorted(art_directions, key=lambda x: x[0])

    # place with 0 to the end
    if art_directions and art_directions[0][0] == 0:
        art_directions = art_directions[1:] + [art_directions[0]]

    # inject min-width and max-width components
    result = []
    _minw = -1
    _maxw = -1
    for w, shape in art_directions:
        # maintain min. width
        minw = _minw
        maxw = w
        if maxw == 0:
            maxw = -1

        # lookup shape, which must exist and determine aspect ratio
        if shape in shapes:
            result.append( (minw, maxw, shape, get_ratio_percent(shapes.get(shape)) ) )

        if maxw != -1:
            _minw = maxw + 1


    # the last item in the list should always ignore max-width
    if result:
        result[-1] = (result[-1][0], -1, result[-1][2], result[-1][3])

    return result


class MediaFolder(DateTimeBase):
    """
    CMS media folder.
    """
    class Meta:
        verbose_name        = 'Media Folder'
        verbose_name_plural = 'Media Folders'
        db_table            = 'cubane_mediafolder'
        ordering            = ['title']

    class Listing:
        columns = [
            'title',
            'parent',
            'updated_on|Last Changed'
        ]
        edit_columns = [
            'title',
            'parent'
        ]
        edit_view = True
        filter_by = [
            'title',
            'updated_on'
        ]


    title = models.CharField(
        verbose_name='Folder Name',
        max_length=255,
        db_index=True,
        help_text="The name of the folder."
    )

    parent = models.ForeignKey(
        'self',
        verbose_name='Parent Folder',
        null=True,
        blank=True,
        help_text='The parent folder of this folder or empty.'
    )


    @classmethod
    def get_form(cls):
        from cubane.media.forms import MediaFolderForm
        return MediaFolderForm


    def __unicode__(self):
        return self.title


class Media(DateTimeBase):
    """
    CMS media content such as images and documents.
    """
    can_merge = False


    class Meta:
        ordering            = ['caption']
        db_table            = 'cubane_media'
        verbose_name        = 'Media'
        verbose_name_plural = 'Media'


    class Listing:
        columns = [
            'caption',
            'parent|Folder',
            'size',
            '/auto_fit',
            '/share_enabled|Shared',
            '/quality_display|Quality',
            'updated_on|Last Changed'
        ]
        edit_columns = [
            'caption',
            'auto_fit',
            'jpeg_quality|Quality',
            'parent'
        ]
        edit_view = True
        grid_view = True
        default_view = 'grid'
        filter_by = [
            ':Caption',
            'caption',
            'filename',

            ':Size and Fit',
            'image_size',
            'auto_fit',

            ':Last Modification',
            'updated_on',

            ':Shared',
            'share_enabled',
            'share_filename'
        ]


    BACKEND_IMAGE_RATIO           = 1.3333333
    BACKEND_LISTING_IMAGE_RATIO   = 1.6
    BUCKET_SIZE                   = 1000
    BACKEND_IMAGE_RATIO_THRESHOLD = 0.25


    def save(self, *args, **kwargs):
        if self.uid is None:
            self.uid = '%s' % uuid.uuid4()
        if self.hashid is None:
            r = random.SystemRandom()
            self.hashid = hashlib.sha224('%s-%s' % (
                uuid.uuid4(),
                ''.join([r.choice(string.printable) for i in range(0, 1024)])
            )).hexdigest()
        if self.pk is not None:
            self.update_filename()
        if self.pk == None and self._being_duplicated:
            super(Media, self).save(*args, **kwargs)
            self.duplicate_file()
        super(Media, self).save(*args, **kwargs)


    def on_duplicated(self):
        self._prior_pk = self.pk
        self._being_duplicated = True
        self.uid = None
        self.hashid = None


    def on_changelog(self, action):
        """
        Archive original file so that it can be restored.
        """
        if action == 'delete' and os.path.isfile(self.original_path):
            ensure_dir(self.archived_path)
            shutil.copyfile(self.original_path, self.archived_path)


    def on_changelog_restored(self, action):
        """
        Restore original file and re-generate all thumbnail versions.
        """
        if action == 'delete' and os.path.isfile(self.archived_path):
            ensure_dir(self.original_path)
            file_move(self.archived_path, self.original_path)
            self.generate_images()


    uid = models.CharField(
        verbose_name='Unique ID',
        max_length=64,
        db_index=True,
        unique=True,
        null=True,
        editable=False
    )

    hashid = models.CharField(
        verbose_name='Unique ID (Hashed)',
        max_length=64,
        db_index=True,
        unique=True,
        null=True,
        editable=False
    )

    parent = models.ForeignKey(
        MediaFolder,
        verbose_name='Folder',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='The folder this media asset is stored.'
    )

    share_enabled = models.BooleanField(
        verbose_name='Share Enabled',
        default=False,
        db_index=True,
        help_text='Enable file sharing for this media asset.'
    )

    share_filename = models.CharField(
        verbose_name='Public Filename',
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text='Public filename under which the system will make this document or image publicly available for download.'
    )

    caption = models.CharField(max_length=255, db_index=True)
    credits = models.CharField(max_length=255, null=True, blank=True)
    filename = models.CharField(max_length=255)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    is_image = models.BooleanField(default=True, db_index=True)
    has_preview = models.BooleanField(default=False, db_index=True)
    is_member_image = models.BooleanField(default=False)
    is_blank = models.BooleanField(default=False, db_index=True)
    member_id = models.IntegerField(null=True, blank=True)
    extra_image_title = models.CharField(max_length=4000, null=True, blank=True)
    is_svg = models.BooleanField(default=False)
    auto_fit = models.BooleanField(default=False)
    external_url = models.CharField(max_length=255, null=True, db_index=True, unique=True)
    version = models.IntegerField(null=True, blank=True, editable=False)
    org_quality = models.PositiveSmallIntegerField(null=True, blank=True)
    jpeg_quality = models.PositiveSmallIntegerField(null=True, blank=True)
    focal_x = models.FloatField(null=True, blank=True)
    focal_y = models.FloatField(null=True, blank=True)


    @classmethod
    def get_json_fieldnames(cls):
        return ['id', 'caption', 'filename', 'width', 'height', 'is_image', 'url']


    @classmethod
    def get_form(cls):
        from cubane.media.forms import MediaForm
        return MediaForm


    @classmethod
    def get_filter_form(cls):
        from cubane.media.forms import MediaFilterForm
        return MediaFilterForm


    @classmethod
    def filter_by(cls, objects, args):
        return filter_by_image_size(objects, args)


    @classmethod
    def get_shape_list(cls):
        """
        Return a list of all shapes and aspect ratio.
        """
        return [{
            'name': shape,
            'ratio': ratio,
            'ratio_percent': get_ratio_percent(ratio)
        } for shape, ratio in Media.get_shapes().items()]


    @classmethod
    def get_shape_labels(cls):
        """
        Return a list of all available shapes in aspect ratio order with a
        human-readable title/description of the usage of the shape alongside its
        aspect ratio. Shapes are ordered by aspect ratio (smallest first)
        """
        if not hasattr(cls, '_shapes_in_order'):
            shapes = cls.get_shapes().items()

            # resolve title
            shapes_with_title = []
            for shape, ar in shapes:
                title = shape.title()
                if settings.IMAGE_SHAPE_NAMES:
                    title = settings.IMAGE_SHAPE_NAMES.get(shape, title)
                shapes_with_title.append((shape, title, ar))

            cls._shapes_in_order = sorted(shapes_with_title, key=lambda x: x[2])

        return cls._shapes_in_order


    @classmethod
    def get_shapes(cls):
        """
        Return a list of all available shapes and the corresponding aspect ratio.
        """
        if not hasattr(cls, '_shapes'):
            def _parse_number(s, shape, ratio, label):
                try:
                    return float(s)
                except ValueError:
                    raise ValueError('Incorrect shape declaration \'%s\' for shape \'%s\': Component %s \'%s\' is not a number.' % (
                        ratio,
                        shape,
                        label,
                        s
                    ))

            cls._shapes = {}
            for shape, ratio in settings.IMAGE_SHAPES.items():
                if shape == 'original':
                    continue

                # shapes are defined as aspect ratios and we require the
                # specific format <width>:<height>. We raise an error if
                # we encounter an invalid shape definition.
                m = re.match(r'^\s*(?P<width>\d+)\s*:\s*(?P<height>\d+)\s*$', ratio)
                if not m:
                    raise ValueError('Incorrect shape declaration \'%s\' for shape \'%s\': Expected format: <width> : <height>' % (
                        ratio,
                        shape
                    ))

                # parse width and height as numbers
                width = float(m.group('width'))
                height = float(m.group('height'))

                # width cannot be zero
                if width == 0.0:
                    raise ValueError('Incorrect shape declaration \'%s\' for shape \'%s\': Width cannot be zero.' % (
                        ratio,
                        shape
                    ))

                # height cannot be 0
                if height == 0.0:
                    raise ValueError('Incorrect shape declaration \'%s\' for shape \'%s\': Height cannot be zero.' % (
                        ratio,
                        shape
                    ))

                # cache valid shape definition
                cls._shapes[shape] = width / height

        return cls._shapes


    @classmethod
    def get_shape_names(cls):
        """
        Return a list of all valid image shape names.
        """
        return cls.get_shapes().keys()


    @classmethod
    def get_shape_base_path(cls):
        """
        Return the base path where all image data is stored for all shapes.
        """
        return os.path.join(
            settings.MEDIA_ROOT,
            'shapes'
        )


    @classmethod
    def get_shape_path(cls, shape):
        """
        Return the path where images are stored for the given shape.
        """
        return os.path.join(
            Media.get_shape_base_path(),
            unicode(shape)
        )


    @classmethod
    def get_art_direction(cls):
        """
        Return list of art direction directives in the format
        (min-width, max-width, shape name). -1 indicates that the corresponding
        components is ignored.
        """
        if not hasattr(cls, '_art_direction'):
            cls._art_direction = {}
            shapes = cls.get_shapes()
            for shape, shape_directives in settings.IMAGE_ART_DIRECTION.items():
                cls._art_direction[shape] = get_art_direction_for_shape(
                    shape_directives,
                    shapes
                )
        return cls._art_direction


    def __init__(self, *args, **kwargs):
        super(Media, self).__init__(*args, **kwargs)
        self._sizes = None
        self._prior_pk = None
        self._being_duplicated = False


    @property
    def is_jpeg_image(self):
        """
        Return True, if this image is a JPEG image.
        """
        return is_jpeg_image(self.original_path)


    @property
    def is_png_image(self):
        """
        Return True, if this image is a PNG image.
        """
        return is_png_image(self.original_path)


    @property
    def quality(self):
        """
        Return the quality level of this image.
        """
        if self.jpeg_quality is None:
            return settings.IMAGE_COMPRESSION_QUALITY
        else:
            return self.jpeg_quality


    @property
    def quality_display(self):
        """
        Return the jpeg quality and the original quality for display purposes.
        """
        if self.jpeg_quality:
            if self.org_quality:
                return '%d / %d' % (self.jpeg_quality, self.org_quality)
            else:
                return '%d' % self.jpeg_quality
        elif self.org_quality:
            return '%d' % self.org_quality
        else:
            return '-'


    @property
    def focal_point(self):
        """
        Return the focal point of this image as a tuple of (x, y) in relative
        coordinate space according to the original image dimensions between
        0.0 and 1.0. If no focal point has been defined for this media asset,
        then the default focal point is the centre of the image (0.5, 0.5).
        """
        x = self.focal_x
        y = self.focal_y
        if x is None: x = 0.5
        if y is None: y = 0.5
        return (x, y)


    @property
    def has_generated_images(self):
        """
        Return True, if this media asset should have generated image versions,
        which is the case if the media asset is an image or a PDF document for
        example.
        """
        return self.is_image or self.has_dimensions or get_ext(self.filename) == 'pdf'


    @property
    def orientation(self):
        """
        Return the orientation of the image, landscape or portrait.
        """
        return 'landscape' if self.aspect_ratio >= 1 else 'portrait'


    @property
    def backend_orientation(self):
        """
        Return the orientation of the image, landscape or portrait based on the
        image presentation within the backend (gallery).
        """
        return 'landscape' if self.aspect_ratio >= self.BACKEND_IMAGE_RATIO else 'portrait'


    @property
    def backend_listing_orientation(self):
        """
        Return the orientation of the image, landscape or portrait based on the
        image presentation within the backend (listing).
        """
        return 'landscape' if self.aspect_ratio >= self.BACKEND_LISTING_IMAGE_RATIO else 'portrait'


    @property
    def backend_orientation_mismatch(self):
        """
        Return True, if the aspect ratio of this image is off by a certain
        factor compared to the aspect ratio of the backend.
        """
        return abs(1.0 - (self.aspect_ratio / self.BACKEND_IMAGE_RATIO)) > self.BACKEND_IMAGE_RATIO_THRESHOLD


    @property
    def bucket_id(self):
        """
        Return a folder id that groups media assets in buttons of 1000 elements.
        """
        return int(math.floor(float(self.pk) / float(self.BUCKET_SIZE)) * self.BUCKET_SIZE)


    @property
    def unique_id(self):
        """
        Return the unique identifier of the media asset, which is usually the
        primary key of the media record but might be a hash if
        CUBANE_HASHED_MEDIA_URLS is True.
        """
        if settings.CUBANE_HASHED_MEDIA_URLS and self.hashid is not None:
            return self.hashid
        else:
            return self.pk


    def get_filename_with_version(self, filename, version=-1):
        """
        Return the filename of the media asset combined with the version
        number of the asset. If we re-upload the asset, the version number
        increases and the asset becomes a new file that has not been seen
        by any upstream cache before.
        """
        version = version if version != -1 else self.version

        if version:
            return '%d-%s' % (version, filename)
        else:
            return filename


    @property
    def filename_with_version(self):
        """
        Return the filename of the media asset combined with the version
        number of the asset. If we re-upload the asset, the version number
        increases and the asset becomes a new file that has not been seen
        by any upstream cache before.
        """
        return self.get_filename_with_version(self.filename)


    @property
    def original_path(self):
        """
        Return the full path to the original media asset.
        """
        return os.path.join(
            settings.MEDIA_ROOT,
            'originals',
            unicode(self.bucket_id),
            unicode(self.unique_id),
            self.filename_with_version
        )


    @property
    def archived_path(self):
        """
        Return the full path to the archived media asset.
        """
        return os.path.join(
            settings.MEDIA_ROOT,
            '.archive',
            unicode(self.bucket_id),
            unicode(self.unique_id),
            self.filename_with_version
        )


    @property
    def original_exists(self):
        """
        Return True, if the original image exists on the local file system.
        """
        return os.path.isfile(self.original_path)


    def get_original_url(self, attr_url=None):
        """
        Return the original url to this image. Optionally a media api url
        is returned with the given image customisation attributes applied.
        """
        return self._make_media_url(
            [
                'originals',
                unicode(self.bucket_id),
                unicode(self.unique_id),
                self.filename_with_version
            ],
            attr_url
        )


    @property
    def original_url(self):
        """
        Return the full url to the original media asset.
        """
        return self.get_original_url()


    @property
    def original_or_preview_url(self):
        """
        Return the full url to the original media asset. In case of a document
        that has a preview image, the url to the highest-resolution preview image
        is returned instead.
        """
        if not self.is_image and self.has_preview:
            return self.get_image_url(self.get_default_image_size_name(), 'original')
        else:
            return self.get_original_url()


    @property
    def is_image_or_preview(self):
        """
        Return True, if this media asset is an image or is a document but has a
        preview image, like a PDF document.
        """
        return self.is_image or self.has_preview


    @property
    def has_dimensions(self):
        """
        Return True, if this media asset has image dimensions, e.g.
        width and height. A document may have image dimensions, if a
        preview image could be generated from the document, for example a PDF
        file.
        """
        return self.width != 0 and self.height != 0


    @property
    def aspect_ratio(self):
        """
        Return the aspect ratio of the original image that was uploaded.
        """
        if self.height != 0:
            return float(self.width) / float(self.height)
        else:
            return 1


    @property
    def aspect_ratio_percent(self):
        """
        Return the aspect ratio for this image in percentage, so that this
        value can be directly used as padding-bottom effectively giving the
        element the correct height based on its width according to the aspect
        ratio of the image.
        """
        return 100.0 / self.aspect_ratio


    def get_aspect_ratio(self, shape):
        """
        Return the aspect ratio for the given shape.
        """
        shapes = Media.get_shapes()
        if not shape in shapes or shape == settings.DEFAULT_IMAGE_SHAPE:
            return self.aspect_ratio
        else:
            return shapes.get(shape)


    def get_aspect_ratio_percent(self, shape):
        """
        Return the aspect ratio for the given shape in percentage.
        """
        return 100.0 / self.get_aspect_ratio(shape)


    def get_available_image_sizes(self):
        """
        Return a list of all image sizes that are available for this media
        asset. Some sizes may be too big for this media assets. We will not
        upscale images. However, we guarantee that we have at least one
        image size at all. Further, we will always include the image version
        that was too big, so that we do not upscale too much there...
        """
        if not hasattr(self, '_available_image_sizes'):
            image_sizes = sorted(
                settings.IMAGE_SIZES.items(),
                key=lambda x: x[1]
            )
            sizes = {}
            done = False

            for size, width in image_sizes:
                if done:
                    break

                if self.width < width:
                    done = True

                sizes[size] = width
            self._available_image_sizes = sizes
        return self._available_image_sizes


    def get_sizes(self, shape):
        """
        Return a list of all available image sizes for the given shape with the
        name and url for this media asset in the corresponding quality/size.
        Please note that certain sizes may be not available to all media assets
        depending on the size of the media asset.
        """
        if not self._sizes:
            self._sizes = {}

        if not shape in self._sizes:
            self._sizes[shape] = [{
                'name': size,
                'url': self.get_image_url(size, shape)
            } for size in self.get_available_image_sizes()]

        return self._sizes.get(shape)


    def get_default_image_size_name(self):
        """
        Return the name of the default image size.
        """
        return self.get_image_size_or_smaller('original', settings.DEFAULT_IMAGE_SIZE)


    def get_default_image_size(self):
        """
        Return the default size of the image in pixels as a
        pair of width and height.
        """
        size = self.get_default_image_size_name()
        return (
            self.get_width(size, 'original'),
            self.get_height(size, 'original')
        )


    def get_smaller_size(self, size):
        """
        Return the next smaller image size based on the given size without
        testing if the current image supports it.
        """
        if size == 'xxx-large':
            return 'xx-large'
        elif size == 'xx-large':
            return 'x-large'
        elif size == 'x-large':
            return 'large'
        elif size == 'large':
            return 'medium'
        elif size == 'medium':
            return 'small'
        elif size == 'small':
            return 'x-small'
        elif size == 'x-small':
            return 'xx-small'
        elif size == 'xx-small':
            return 'xxx-small'
        else:
            # nothing matched, return largest size we know
            return 'xxx-large'


    def get_image_size_or_smaller(self, shape, size):
        """
        Return the given image size for the given shape if the given
        image size is supported. If not, return the next smaller image size
        instead.
        """
        sizes = self.get_sizes(shape)
        names = [s.get('name') for s in sizes]
        if size in names:
            return size
        else:
            smaller_size = self.get_smaller_size(size)
            return self.get_image_size_or_smaller(shape, smaller_size)


    @property
    def size(self):
        """
        Return width and height.
        """
        if self.width == 0 and self.height == 0:
            return 'Unknown Size'
        else:
            return '%s x %s' % (intcomma(self.width), intcomma(self.height))


    @property
    def default_url(self):
        """
        Return the default image url (mainly used in the case that the
        client cannot execute javascript).
        """
        size = self.get_image_size_or_smaller('original', settings.DEFAULT_IMAGE_SIZE)
        return self.get_image_url(size)


    @property
    def xxsmall_url(self):
        return self.get_image_url(
            self.get_image_size_or_smaller('original', 'xx-small')
        )


    @property
    def xsmall_url(self):
        return self.get_image_url(
            self.get_image_size_or_smaller('original', 'x-small')
        )


    @property
    def small_url(self):
        return self.get_image_url(
            self.get_image_size_or_smaller('original', 'small')
        )


    @property
    def medium_url(self):
        return self.get_image_url(
            self.get_image_size_or_smaller('original', 'medium')
        )


    @property
    def large_url(self):
        return self.get_image_url(
            self.get_image_size_or_smaller('original', 'large')
        )


    @property
    def xlarge_url(self):
        return self.get_image_url(
            self.get_image_size_or_smaller('original', 'x-large')
        )


    @property
    def xxlarge_url(self):
        return self.get_image_url(
            self.get_image_size_or_smaller('original', 'xx-large')
        )


    @property
    def xxxlarge_url(self):
        return self.get_image_url(
            self.get_image_size_or_smaller('original', 'xxx-large')
        )


    @property
    def url(self):
        """
        Return the url to the original file.
        """
        if self.is_image and not self.is_svg:
            return self.default_url
        else:
            return self.original_url


    @property
    def has_original_image(self):
        """
        Return True, if we actually have an original image available. For non-
        blank images, we simply assume that this is the case, since we want to
        avoid asking the file system too often. However, for blank images with
        an external url, we would need to actually test.
        """
        if self.is_blank and self.external_url:
            return os.path.isfile(self.original_path)
        else:
            # assume that we have an original image to avoid asking
            # the file system.
            return True

    def resize_if_too_wide(self):
        """
        Resize the image
        """
        resized = False
        # determine media asset type (image, document) and image size
        self.is_image = is_image(self.original_path)
        if self.is_image:
            resized = resize_image_if_too_wide(self.original_path)
            (self.width, self.height) = get_image_size(self.original_path)
        else:
            self.width = 0
            self.height = 0

        # save the new heights and widths
        self.save()
        return resized


    def delete(self, *args, **kwargs):
        """
        Deleting database instance should also delete files on disk.
        """
        # pre media deletion signal
        pre_delete_media.send(Media, instance=self)

        self.delete_generated_images()
        self.delete_original()
        super(Media, self).delete(*args, **kwargs)


    def get_preview_ext(self, filename, ext):
        """
        Replace the extension of the given filename with the given one.
        """
        fn, _ = os.path.splitext(filename)
        return '%s%s' % (fn, ext)


    def get_image_path(self, size, shape=settings.DEFAULT_IMAGE_SHAPE, filename=None, version=-1):
        """
        Return the full path to the media asset file
        based on the given size.
        """
        filename = filename if filename is not None else self.filename
        version = version if version != -1 else self.version

        if not self.is_image and self.has_preview:
            filename = self.get_preview_ext(filename, settings.CUBANE_DEFAULT_MEDIA_PREVIEW_EXT)

        return os.path.join(
            settings.MEDIA_ROOT,
            'shapes',
            unicode(shape),
            unicode(size),
            unicode(self.bucket_id),
            unicode(self.unique_id),
            self.get_filename_with_version(filename, version)
        )


    def get_image_url(self, size, shape=settings.DEFAULT_IMAGE_SHAPE, attr_url=None):
        """
        Return the full url path to the media asset file based on the given
        size. Optionally, a full path to the media api is returned if there are
        any image customisations provided.
        """
        if self.is_blank:
            return self.get_original_url(attr_url)
        else:
            filename = self.filename

            if not self.is_image and self.has_preview:
                filename = self.get_preview_ext(filename, settings.CUBANE_DEFAULT_MEDIA_PREVIEW_EXT)

            return self._make_media_url(
                [
                    'shapes',
                    unicode(shape),
                    unicode(size),
                    unicode(self.bucket_id),
                    unicode(self.unique_id),
                    self.get_filename_with_version(filename)
                ],
                attr_url
            )


    def get_image_url_component(self):
        """
        Return the main image url components that is not dependent on image
        size or shape.
        """
        filename = self.filename

        if not self.is_image and self.has_preview:
            filename = self.get_preview_ext(filename, settings.CUBANE_DEFAULT_MEDIA_PREVIEW_EXT)

        return url_join(
            unicode(self.bucket_id),
            unicode(self.unique_id),
            self.get_filename_with_version(filename)
        )


    def get_image_url_or_smaller(self, size, shape=settings.DEFAULT_IMAGE_SHAPE):
        """
        Return the image url for this image based on the given shape and size or the next smaller
        image size that is available.
        """
        available_size = self.get_image_size_or_smaller(shape, size)
        return self.get_image_url(available_size, shape)


    def get_width(self, size, shape):
        """
        Return the width of the image depending on the given size and shape.
        """
        return int(settings.IMAGE_SIZES[size])


    def get_height(self, size, shape):
        """
        Return the height of the image depending on the given size and shape.
        """
        return int(self.get_width(size, shape) / self.get_aspect_ratio(shape))


    def generate_images_for_shape(self, img, size, shape, valign='center', auto_fit=False):
        """
        Generate multiple versions of the original media assets depending on
        global image size configuration for the given image shape.
        """
        path = self.get_image_path(size, shape)
        ensure_dir(path)

        w = self.get_width(size, shape)
        h = self.get_height(size, shape)

        if shape == settings.DEFAULT_IMAGE_SHAPE:
            mode = 'scale'
        else:
            mode = 'crop'

        resize_image_object(img, path, w, h, mode, valign, auto_fit, self.focal_point, self.quality)


    def generate_svg_images_for_shape(self, filename, size, shape):
        """
        Generate multiple versions of the original vector image depending on
        global image size configuration for the given image shape. A vector
        image does not usually need to be resized, but an SVG image may host
        bitmap data, which we will scale down accordingly. The result will be a
        valid SVG image with all vector information preserved.
        """
        path = self.get_image_path(size, shape)
        ensure_dir(path)

        w = self.get_width(size, shape)
        h = self.get_height(size, shape)

        resize_svg_image(filename, path, w, h, self.focal_point)


    def generate_bitmap_images(self, request, shape=None):
        """
        Generate different image versions for a bitmap-based image (non-vector).
        """
        from cubane.backend.views import Progress

        # open image for resize
        with open_image_for_resize(self.original_path) as img:
            # generate versions for all shapes
            sizes = self.get_available_image_sizes().keys()
            shapes = Media.get_shape_names()
            total = len(sizes) * len(shapes)
            i = 0
            for size in sizes:
                # original shape
                if shape is None:
                    self.generate_images_for_shape(
                        img,
                        size,
                        settings.DEFAULT_IMAGE_SHAPE
                    )

                # all configured shapes
                for _shape in shapes:
                    if shape is None or shape == _shape:
                        auto_fit = (
                            self.auto_fit and
                            settings.IMAGE_FITTING_ENABLED and
                            _shape in settings.IMAGE_FITTING_SHAPES
                        )
                        self.generate_images_for_shape(img, size, _shape, auto_fit=auto_fit)

                    i += 1
                    Progress.set_sub_progress(request, i, total)


    def generate_svg_images(self, request, shape=None):
        """
        Generate different image versions for vector (svg) images. SVG images
        may contain bitmap data which we need to generate different versions
        depending on the image size.
        """
        from cubane.backend.views import Progress

        sizes = self.get_available_image_sizes().keys()
        shapes = Media.get_shape_names()
        total = len(sizes) * len(shapes)
        i = 0
        for size in sizes:
            # original shape
            if shape is None:
                self.generate_svg_images_for_shape(
                    self.original_path,
                    size,
                    settings.DEFAULT_IMAGE_SHAPE
                )

            # all configured shapes
            for _shape in shapes:
                if shape is None or shape == _shape:
                    self.generate_svg_images_for_shape(
                        self.original_path,
                        size,
                        _shape
                    )

                i += 1
                Progress.set_sub_progress(request, i, total)


    def generate_document_preview_images(self, request, shape=None):
        """
        Return preview images representing an image representation of a
        document.
        """
        from cubane.backend.views import Progress

        # generate original image (tmp)
        _, tmp_path = tempfile.mkstemp(suffix='.jpg')
        if generate_preview_image(self.original_path, tmp_path):
            img = open_image_for_resize(tmp_path)

            # store size
            self.width, self.height = img.size
            self.save()

            try:
                # generate thumbnail images
                sizes = self.get_available_image_sizes().keys()
                shapes = Media.get_shape_names()
                total = len(sizes) * len(shapes)
                i = 0
                for size in sizes:
                    # original shape
                    if shape is None:
                        self.generate_images_for_shape(
                            img,
                            size,
                            settings.DEFAULT_IMAGE_SHAPE,
                            valign='top'
                        )

                    # all configured shapes
                    for _shape in shapes:
                        if shape is None or shape == _shape:
                            self.generate_images_for_shape(img, size, _shape, valign='top')

                        i += 1
                        Progress.set_sub_progress(request, i, total)
            finally:
                try:
                    os.remove(tmp_path)
                except:
                    pass


    def generate_images(self, request=None, shape=None):
        """
        Generate multiple versions of the original media assets depending on
        global image size configuration and shapes.
        """
        is_pdf = get_ext(self.filename) == 'pdf'

        if self.is_image:
            # generate image versions
            if self.is_svg:
                self.generate_svg_images(request, shape)
            else:
                self.generate_bitmap_images(request, shape)
        elif self.has_dimensions or is_pdf:
            # generate document preview images
            self.generate_document_preview_images(request, shape)

        # clear cache
        self._sizes = None


    def duplicate_file(self):
        """
        Generate a duplicate and let self point to the new image.
        """
        old_filepath = os.path.join(
            settings.MEDIA_ROOT,
            'originals',
            unicode(self.bucket_id),
            unicode(self._prior_pk),
            self.filename_with_version
        )
        new_filepath = self.original_path
        ensure_dir(new_filepath)
        try:
            shutil.copyfile(old_filepath, new_filepath)
        except:
            self.delete()
            raise

        self.generate_images()
        self.update_filename()
        self._being_duplicated = False


    def delete_generated_image(self, size, shape):
        """
        Delete all generated media versions for the given shape.
        """
        path = self.get_image_path(size, shape)

        # remove image file and parent folder if empty
        if os.path.exists(path) and os.path.isfile(path):
            os.unlink(path)

            folder = os.path.dirname(path)
            try:
                os.rmdir(folder)
            except OSError:
                pass


    def delete_generated_images(self):
        """
        Delete all generated media versions.
        """
        if self.is_image or self.has_preview:
            for size in settings.IMAGE_SIZES.keys():
                self.delete_generated_image(size, settings.DEFAULT_IMAGE_SHAPE)

                for shape in Media.get_shape_names():
                    self.delete_generated_image(size, shape)


    def delete_original(self):
        """
        Delete original media file.
        """
        if self.pk and self.filename:
            # remove folder
            if os.path.exists(self.original_path):
                os.remove(self.original_path)

            # remove parent folder
            folder = os.path.dirname(self.original_path)
            if os.path.exists(folder):
                try:
                    os.rmdir(folder)
                except:
                    pass


    def set_filename(self, filename):
        """
        Construct and set filename based on the extension of the given original
        filename and the caption.
        """
        _name, ext = os.path.splitext(filename)

        if not self.caption:
            self.caption = get_caption_from_filename(filename)

        fn = slugify(self.caption)
        ext = ext.lower()
        if len(fn) + len(ext) > MAX_FILENAME_LENGTH:
            fn = fn[:(len(fn) - (len(fn) + len(ext) - MAX_FILENAME_LENGTH))]

        self.filename = fn + ext


    def update_filename(self):
        """
        Updates the filename on the disk if the caption has changed. This will
        also rename files in case we change the version of the media asset.
        """
        try:
            orig = Media.objects.get(pk=self.pk)
        except Media.DoesNotExist:
            return

        old_filename = orig.get_filename_with_version(orig.filename)

        # determine new filename based on caption
        new_name = slugify(self.caption).strip()

        # make sure that we do not end up with an empty filename
        if new_name == '':
            new_name = 'unnamed'

        # was using old_filename to get new ext, now using self.filename
        _, ext = os.path.splitext(self.filename)
        sought_filename = self.get_filename_with_version(slugify(new_name) + ext.lower())

        if (self.filename_with_version != old_filename or sought_filename != old_filename):
            # caption changed
            old_path = orig.original_path
            new_path = old_path.replace(old_filename, sought_filename)

            # rename the file
            try:
                file_move(old_path, new_path)
            except:
                return

            # if succeeded rename the current filename
            self.filename = slugify(new_name) + ext.lower()

            # rename the thumbnail images as well, but ignore if errors
            # occur here can be genenerated with create_thumbnails
            # if anything goes wrong
            self.update_generated_images(orig.filename, orig.version)


    def update_generated_image(self, size, shape, old_filename, old_version):
        """
        Rename all generated media versions for the given shape.
        """
        path = self.get_image_path(size, shape, old_filename, old_version)
        new_path = self.get_image_path(size, shape)

        try:
            file_move(path, new_path)
        except:
            pass


    def update_generated_images(self, old_filename, old_version):
        """
        Rename all generated media versions.
        """
        if self.has_generated_images:
            for size in settings.IMAGE_SIZES.keys():
                self.update_generated_image(size, settings.DEFAULT_IMAGE_SHAPE, old_filename, old_version)

                for shape in Media.get_shape_names():
                    self.update_generated_image(size, shape, old_filename, old_version)


    def upload_from_source(self, writer, filename=None, generate_images=True, request=None):
        """
        Upload given media assets and generate different image sizes by
        executing the given data writer, which copies the data to the file
        system of the server.
        """
        # remove previous file (if exists)
        if self.id:
            self.delete_generated_images()
            self.delete_original()

        # setup filename based on caption and original filename
        self.set_filename(filename)

        # copy image data to disk by using the given writer
        path = self.original_path
        ensure_dir(path)
        dest = open(path, 'wb+')
        writer(dest)
        dest.close()

        if settings.IMAGE_CONVERT_PNG_TO_JPG:
            # if we uploaded a PNG file without transparency, then replace it
            # with a JPG version, simply pretending that the JPG file was
            # uploaded to begin with
            if is_png_without_transparency(self.original_path):
                # keep path to original
                original = self.original_path

                # change filename
                _name, ext = os.path.splitext(original)
                self.set_filename(_name + '.jpg')

                # convert PNG file into JPG (deleting original image)
                convert_image(original, self.original_path, self.quality)

        # handle post-upload (process original image)
        self.upload(generate_images, request=request)


    def upload_from_stream(self, stream, request=None):
        """
        Upload given media assets and generate different image sizes
        based on given image stream.
        """
        def writer(dest):
            for c in stream.chunks():
                dest.write(c)

        self.upload_from_source(writer, stream.name, request=request)


    def upload_save_from_stream(self, stream, request=None):
        """
        Upload given media assets and generate different image sizes
        based on given image stream.
        """
        def writer(dest):
            for c in stream.chunks():
                dest.write(c)

        # get filename from stream and generate caption
        self.filename = stream.name
        self.caption = get_caption_from_filename(self.filename)

        self.upload_from_source(writer, stream.name, request=request)


    def upload_from_content(self, content, filename=None, generate_images=True, request=None):
        """
        Upload given media assets and generate different image size based
        on given image data.
        """
        def writer(dest):
            dest.write(content)

        self.upload_from_source(writer, filename, generate_images=generate_images, request=request)


    def upload(self, generate_images=True, request=None, shape=None):
        """
        Process uploaded media asset and store some meta information.
        """
        # determine media asset type (image, document) and image size
        is_pdf = get_ext(self.filename) == 'pdf'
        self.is_svg = get_ext(self.filename) == 'svg'
        self.is_image = is_image(self.original_path)

        if self.is_image:
            # scale original image down if it is too big
            if not self.is_svg:
                resize_image_if_too_wide(self.original_path)

        # determine image/preview dimensions (for PDF we are not using
        # ImageMagic, which would be too slow...)
        self.width = 0
        self.height = 0
        if not is_pdf:
            try:
                self.width, self.height = get_image_size(self.original_path)
            except IOError:
                pass

        # determine jpeg image quality
        if self.is_image:
            self.org_quality = get_jpg_image_quality(self.original_path)

        # a document with dimensions would yield preview images
        if self.is_image or self.has_dimensions or is_pdf:
            self.has_preview = True

        # create a blank image if the task runner is installed (images only)
        self.is_blank = TaskRunner.is_available() and self.has_preview

        # update properties
        self.save()

        # generate image versions (unless this is a blank image, in which case
        # the task runner will take of generating image versions).
        if not self.is_blank and generate_images:
            # generate image versions
            self.generate_images(request, shape)


    def increase_version(self):
        """
        Increase version number of the media asset and rename physical files
        on disk.
        """
        if settings.CUBANE_MEDIA_VERSIONS:
            if self.version:
                self.version += 1
            else:
                self.version = 2

        self.save()


    def download_from_external_source(self):
        """
        Download the original image version for an external source if available.
        """
        if not self.external_url:
            return False

        # download content from url
        content = requests.get(self.external_url, timeout=1000)
        if content == None: return False
        if content.status_code != 200: return False

        # save changes and put original file in place
        self.upload_from_content(content.content, self.filename)


    def to_dict(self):
        """
        Return a short dictionary representation of this model instance.
        """
        return {
            'id': self.pk,
            'hashid': self.hashid,
            'caption': self.caption,
            'url': self.url,
            'original_url': self.original_url,
            'shapes': dict([
                (shape, dict([(item.get('name'), item.get('url')) for item in self.get_sizes(shape)]))
            for shape in self.get_shapes().keys() + ['original']]),
            'is_svg': self.is_svg,
            'lastmod': self.updated_on
        }


    def to_compact_dict(self):
        """
        Return a dictionary representation of this model that is required to
        reconstruct a lazy-load container in javascript at runtime.
        """
        return {
            'path': self.get_image_url_component(),
            'def_url': self.default_url,
            'caption': self.caption,
            'is_blank': self.is_blank,
            'sizes': self.get_available_image_sizes().keys(),
            'ar': self.get_aspect_ratio_percent('original')
        }


    def _make_media_url(self, components, attr_url=None):
        """
        Return the full url to this media components based on the given url
        components. Optionally a media api url is returned with the given image
        customisation attributes applied.
        """
        # media or media-api?
        if attr_url:
            components.insert(0, settings.MEDIA_API_URL)
        else:
            components.insert(0, settings.MEDIA_URL)

        # construct absolute url from components
        url = make_absolute_url(url_join(*components))

        # append image customisation attributes
        if attr_url:
            url += '?' + attr_url

        return url


    def __unicode__(self):
        return '%s' % self.caption


class MediaGallery(models.Model):
    """
    Captures assignment of media assets to other things, such as (but not
    limited to) pages and childs pages.
    """
    class Meta:
        ordering            = ['seq']
        db_table            = 'cubane_media_gallery'
        verbose_name        = 'Media Gallery'
        verbose_name_plural = 'Media Galleries'


    media = models.ForeignKey(
        Media,
        verbose_name='Media',
        help_text='The media assets that is part of a gallery.'
    )

    seq = models.IntegerField(
        verbose_name='Sequence',
        db_index=True,
        default=0,
        editable=False,
        help_text='The sequence number determines the order in which media ' +
                  'assets are presented, for example within a list of ' +
                  'gallery items or a carousel.'
    )

    content_type = models.ForeignKey(ContentType)
    target_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'target_id')


    def __unicode__(self):
        return '%s' % self.media_id


#
# Any CMS entity deleted should reflect this within the settings as a seperate
# timestamp in order to detect content changes due to content deletion.
#
@receiver(post_delete)
def update_entity_deleted_on(sender, **kwargs):
    if 'cubane.cms' in settings.INSTALLED_APPS:
        from cubane.cms.views import get_cms
        cms = get_cms()
        cms.notify_content_changed(sender, Media, delete=True)


#
# Invalidate cache when saving or deleting media content
#
@receiver(post_save)
def invalidate_cache_on_content_changed(sender, **kwargs):
    if 'cubane.cms' in settings.INSTALLED_APPS:
        from cubane.cms.views import get_cms
        cms = get_cms()
        cms.notify_content_changed(sender, Media)