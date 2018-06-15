# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.libjson import to_json


RESOURCES = [
    'css/cubane.medialoader.css',
    'all|css/cubane.medialoader.shapes.templating.css',
    'js/cubane.medialoader.templating.js'
]


def get_deploy_context():
    from cubane.media.models import Media

    image_sizes = {}

    image_sizes['xxx_large'] = 2400
    image_sizes['xx_large'] = 1600

    for image in settings.IMAGE_SIZES:
        name = image.replace('-', '_')
        image_sizes[name] = settings.IMAGE_SIZES[image]

    disable_device_ratio = 'true' if settings.DISABLE_DEVICE_RATIO else 'false'

    shapes = Media.get_shape_list()
    image_art_direction = Media.get_art_direction()

    # generate list of choke-points
    image_size_list = [
        image_sizes.get('xxx_large'),
        image_sizes.get('xx_large'),
        image_sizes.get('x_large'),
        image_sizes.get('large'),
        image_sizes.get('medium'),
        image_sizes.get('small'),
        image_sizes.get('x_small'),
        image_sizes.get('xx_small'),
        image_sizes.get('xxx_small')
    ]

    # names of image shapes
    image_size_names = [
        'xxx-large',
        'xx-large',
        'x-large',
        'large',
        'medium',
        'small',
        'x-small',
        'xx-small',
        'xxx-small'
    ]

    # list of aspect ratios poer shape
    aspect_ratio_by_shape = dict([(shape.get('name'), shape.get('ratio_percent')) for shape in shapes])

    return {
        'image_sizes': image_sizes,
        'disable_device_ratio': disable_device_ratio,
        'shapes': shapes,
        'MEDIA_URL': settings.MEDIA_URL,
        'MEDIA_API_URL': settings.MEDIA_API_URL,
        'image_art_direction': image_art_direction,
        'image_art_direction_json': to_json(image_art_direction),
        'image_size_list_json': to_json(image_size_list),
        'image_size_names_json': to_json(image_size_names),
        'aspect_ratio_by_shape': to_json(aspect_ratio_by_shape)
    }