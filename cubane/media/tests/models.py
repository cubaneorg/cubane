# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.media.models import get_art_direction_for_shape
from cubane.media.models import Media, MediaFolder
from cubane.media.models import MAX_FILENAME_LENGTH
from cubane.media.forms import MediaForm, MediaFilterForm, MediaFolderForm
from cubane.cms.views import get_cms
from cubane.lib.image import (
    open_image,
    is_jpeg_image_object,
    is_png_image_object
)
import os.path


class CMSMediaModelsGetArtDirectionForShapeTestCase(CubaneTestCase):
    """
    cubane.media.get_art_direction_for_shape()
    """
    def test_empty_art_direction_should_yield_empty_list_of_directives(self):
        self.assertEqual(
            [],
            get_art_direction_for_shape({}, {})
        )


    def test_single_directive_should_yield_rule_without_min_and_max_width(self):
        self.assertEqual(
            [(-1, -1, 'phone', 100.0)],
            get_art_direction_for_shape({
                '767': 'phone'
            }, {
                'phone': 1.0
            })
        )


    def test_first_directive_should_ignore_min_width(self):
        self.assertEqual(
            [
                (-1, 767, 'phone', 100.0),
                (768, -1, 'tablet', 50.0)
            ],
            get_art_direction_for_shape({
                '767': 'phone',
                '979': 'tablet',
            }, {
                'phone': 1.0,
                'tablet': 2.0
            })
        )


    def test_catch_all_directive_should_be_last_and_should_ignore_max_width(self):
        self.assertEqual(
            [
                (-1, 767, 'phone', 100.0),
                (768, -1, 'desktop', 50.0)
            ],
            get_art_direction_for_shape({
                '*':   'desktop',
                '767': 'phone'
            }, {
                'phone': 1.0,
                'desktop': 2.0
            })
        )


    def test_should_ignore_shapes_that_are_not_defined(self):
        self.assertEqual(
            [
                (-1, -1, 'phone', 100.0)
            ],
            get_art_direction_for_shape({
                '*':   'desktop',
                '767': 'phone'
            }, {
                'phone': 1.0
            })
        )


@CubaneTestCase.complex()
class CMSMediaModelsMediaFolderTestCase(CubaneTestCase):
    def test_get_form_should_return_default_form(self):
        m = MediaFolder()
        self.assertTrue(issubclass(m.get_form(), MediaFolderForm))


@CubaneTestCase.complex()
class CMSMediaModelsMediaTestCase(CubaneTestCase):
    def setUp(self):
        self.m = Media()


    def tearDown(self):
        if self.m.pk:
            self.m.delete()


    def test_save_should_generate_uid_if_not_present(self):
        self.m.save()
        self.assertIsNotNone(self.m.uid)


    def test_save_should_ignore_uid_if_present(self):
        self.m.uid = 'uuid'
        self.m.save()
        self.assertEqual('uuid', self.m.uid)


    def test_save_should_rename_filename_on_disk_if_caption_changed(self):
        cms = get_cms()
        self.m = cms.create_media_from_file(self.get_test_image_path('test.jpg'), 'Test')
        self.assertEqual(self.m.caption, 'Test')
        self.assertEqual(self.m.filename, 'test.jpg')
        self.assertEqual('test.jpg', os.path.basename(self.m.original_path))
        self.assertTrue(os.path.isfile(self.m.original_path))

        self.m.caption = 'Hello World'
        self.m.save()

        self.assertEqual('Hello World', self.m.caption)
        self.assertEqual('hello-world.jpg', self.m.filename)
        self.assertEqual('hello-world.jpg', os.path.basename(self.m.original_path))
        self.assertTrue(os.path.isfile(self.m.original_path))


    def test_save_should_rename_filename_to_unnamed_on_disk_if_caption_changed_to_empty_string(self):
        cms = get_cms()
        self.m = cms.create_media_from_file(self.get_test_image_path('test.jpg'), 'Test')
        self.assertEqual(self.m.caption, 'Test')
        self.assertEqual(self.m.filename, 'test.jpg')

        self.m.caption = ''
        self.m.save()

        self.assertEqual('', self.m.caption)
        self.assertEqual('unnamed.jpg', self.m.filename)
        self.assertEqual('unnamed.jpg', os.path.basename(self.m.original_path))
        self.assertTrue(os.path.isfile(self.m.original_path))


    def test_save_should_duplicate_file_if_asset_was_duplicated(self):
        cms = get_cms()
        self.m = cms.create_media_from_file(self.get_test_image_path('test.jpg'), 'Test')

        # prepare for duplication
        org = Media.objects.get(pk=self.m.pk)
        self.m.on_duplicated()
        self.assertEqual(self.m.pk, self.m._prior_pk)
        self.assertTrue(self.m._being_duplicated)
        self.assertIsNone(self.m.uid)
        self.m.pk = None

        # save() should create duplicate
        self.m.caption = 'Hello World'
        self.m.save()
        self.assertNotEqual(self.m.pk, org.pk)
        self.assertNotEqual(self.m.uid, org.uid)
        self.assertNotEqual(self.m.original_path, org.original_path)
        self.assertTrue(os.path.isfile(self.m.original_path))
        self.assertTrue(os.path.isfile(org.original_path))

        # was also renamed due to caption change
        self.assertEqual('Hello World', self.m.caption)
        self.assertEqual('hello-world.jpg', self.m.filename)
        self.assertEqual('hello-world.jpg', os.path.basename(self.m.original_path))

        org.delete()


    def test_get_json_fieldnames_should_return_fieldnames_for_json_encoding(self):
        self.assertEqual([
            'id',
            'caption',
            'filename',
            'width',
            'height',
            'is_image',
            'url'
        ], self.m.get_json_fieldnames())


    def test_get_form_should_return_default_form(self):
        self.assertTrue(issubclass(self.m.get_form(), MediaForm))


    def test_get_filter_form_should_return_default_form(self):
        self.assertTrue(issubclass(self.m.get_filter_form(), MediaFilterForm))


    def test_filter_by_should_understand_filtering_by_image_size(self):
        self._assert_media_filter([256, 512, 1024], {'image_size': '200-600'}, [256, 512])


    def test_filter_by_image_size_should_ignore_missing_arg(self):
        self._assert_media_filter([256, 512, 1024], {}, [256, 512, 1024])


    def test_filter_by_image_size_should_ignore_incorrect_arg_format(self):
        self._assert_media_filter([256, 512, 1024], {'image_size': '200'}, [256, 512, 1024])


    def test_filter_by_image_size_should_ignore_parsing_error_min_value(self):
        self._assert_media_filter([256, 512, 1024], {'image_size': 'xxx-200'}, [256, 512, 1024])


    def test_filter_by_image_size_should_ignore_parsing_error_max_value(self):
        self._assert_media_filter([256, 512, 1024], {'image_size': '200-xxx'}, [256, 512, 1024])


    @override_settings(IMAGE_SHAPES={'test': '200:200', 'original': '300:200'})
    def test_get_shapes_should_ignore_reserved_name_original(self):
        self._assert_get_shapes({'test': 1.0})


    @override_settings(IMAGE_SHAPES={'test': '200:200', 'error': '300'})
    def test_get_shapes_should_raise_exception_on_formatting_errors(self):
        with self.assertRaisesRegexp(ValueError, 'Incorrect shape declaration'):
            self._assert_get_shapes({'test': 1.0})


    @override_settings(IMAGE_SHAPES={'test': '200:200', 'error': '0:300'})
    def test_get_shapes_should_raise_exception_on_zero_width(self):
        with self.assertRaisesRegexp(ValueError, 'Incorrect shape declaration'):
            self._assert_get_shapes({'test': 1.0})


    @override_settings(IMAGE_SHAPES={'test': '200:200', 'error': '300:0'})
    def test_get_shapes_should_raise_exception_on_zero_height(self):
        with self.assertRaisesRegexp(ValueError, 'Incorrect shape declaration'):
            self._assert_get_shapes({'test': 1.0})


    def test_orientation_should_return_landscape_for_landscape_images(self):
        self._assert_orientation(1024, 512, 'orientation', 'landscape')


    def test_orientation_should_return_landscape_for_squared_images(self):
        self._assert_orientation(512, 512, 'orientation', 'landscape')


    def test_orientation_should_return_portrait_for_portrait_images(self):
        self._assert_orientation(512, 1024, 'orientation', 'portrait')


    def test_backend_orientation_should_return_landscape_for_wider_images(self):
        self._assert_orientation(1024, 512, 'backend_orientation', 'landscape')


    def test_backend_orientation_should_return_landscape_for_exact_images(self):
        self._assert_orientation(1024, 1024.0 / Media.BACKEND_IMAGE_RATIO, 'backend_orientation', 'landscape')


    def test_backend_orientation_should_return_landscape_for_thinner_images(self):
        self._assert_orientation(512, 1024, 'backend_orientation', 'portrait')


    def test_backend_listing_orientation_should_return_landscape_for_wider_images(self):
        self._assert_orientation(1024, 512, 'backend_listing_orientation', 'landscape')


    def test_backend_listing_orientation_should_return_landscape_for_exact_images(self):
        self._assert_orientation(1024, 1024.0 / Media.BACKEND_LISTING_IMAGE_RATIO, 'backend_listing_orientation', 'landscape')


    def test_backend_listing_orientation_should_return_landscape_for_thinner_images(self):
        self._assert_orientation(512, 1024, 'backend_listing_orientation', 'portrait')


    def test_bucket_id_should_spread_pk_within_buckets_of_defined_size(self):
        buckets = {}
        for i in range(0, 3 * Media.BUCKET_SIZE):
            self.m.id = i
            bucket_id = self.m.bucket_id
            if bucket_id not in buckets:
                buckets[bucket_id] = 0
            buckets[bucket_id] += 1

        for bucket_id, n in buckets.items():
            self.assertEqual(Media.BUCKET_SIZE, n)


    def test_original_path_should_combine_base_path_with_bucket_id_pk_and_filename(self):
        self.m.pk = 433
        self.m.filename = 'test.jpg'
        self.assertTrue(self.m.original_path.endswith('/originals/0/433/test.jpg'))


    def test_original_url_should_combine_bucket_id_pk_and_filename_matching_physical_path(self):
        self.m.pk = 433
        self.m.filename = 'test.jpg'
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/media/originals/0/433/test.jpg',
            self.m.original_url
        )


    def test_aspect_ratio_should_return_wdith_over_height(self):
        self.m.width = 1024
        self.m.height = 512
        self.assertEqual(2, self.m.aspect_ratio)


    def test_aspect_ratio_should_return_1_if_height_is_zero(self):
        self.m.width = 1024
        self.m.height = 0
        self.assertEqual(1, self.m.aspect_ratio)


    def test_aspect_ratio_percent_should_represent_aspect_ratio_in_percent(self):
        self.m.width = 1024
        self.m.height = 512
        self.assertEqual(50, self.m.aspect_ratio_percent)


    def test_aspect_ratio_percent_should_return_100_percent_if_height_zero(self):
        self.m.width = 1024
        self.m.height = 0
        self.assertEqual(100, self.m.aspect_ratio_percent)


    def test_get_default_image_size(self):
        self.m.id = 1
        self.m.width = 1000
        self.m.height = 500
        self.assertEqual((1280, 640), self.m.get_default_image_size())


    def test_size_property_should_return_size_display_value(self):
        self.m.width = 1024
        self.m.height = 1250
        self.assertEqual('1,024 x 1,250', self.m.size)


    def test_xxsmall_url(self):
        self._assert_size_url('xxsmall', 'xx-small')


    def test_xsmall_url(self):
        self._assert_size_url('xsmall', 'x-small')


    def test_small_url(self):
        self._assert_size_url('small', 'small')


    def test_medium_url(self):
        self._assert_size_url('medium', 'medium')


    def test_large_url(self):
        self._assert_size_url('large', 'large')


    def test_xlarge_url(self):
        self._assert_size_url('xlarge', 'x-large')


    @override_settings(IMAGE_SIZES={'xx-large': 1600})
    def test_xxlarge_url_url(self):
        self._assert_size_url('xxlarge', 'xx-large')


    @override_settings(IMAGE_SIZES={'xxx-large': 2400})
    def test_xxxlarge_url(self):
        self._assert_size_url('xxxlarge', 'xxx-large')


    def test_url_property_should_return_default_url_for_regular_images(self):
        self.m.id = 1
        self.m.width = 1000
        self.m.height = 500
        self.assertEqual(self.m.default_url, self.m.url)


    def test_url_property_should_return_original_url_for_svg_images(self):
        self.m.id = 1
        self.m.width = 1000
        self.m.height = 500
        self.m.is_svg = True
        self.assertEqual(self.m.original_url, self.m.url)


    @override_settings(IMG_MAX_WIDTH=600)
    def test_resize_if_too_wide(self):
        cms = get_cms()
        self.m = cms.create_media_from_file(self.get_test_image_path('test.jpg'), 'Hobbiton')
        self.assertEqual(512, self.m.width)
        self.assertEqual(512, self.m.height)

        max_width = settings.IMG_MAX_WIDTH
        settings.IMG_MAX_WIDTH = 400
        self.m.resize_if_too_wide()
        settings.IMG_MAX_WIDTH = max_width

        self.assertEqual(400, self.m.width)
        self.assertEqual(400, self.m.height)


    def test_resize_if_too_wide_should_ignore_non_image_file(self):
        cms = get_cms()
        self.m = cms.create_media_from_file(self.get_test_image_path('test.txt'), 'Test')
        self.m.resize_if_too_wide()
        self.assertEqual(0, self.m.width)
        self.assertEqual(0, self.m.height)
        self.assertFalse(self.m.is_image)


    def test_upload_png_image_without_transparency_should_store_image_as_jpg(self):
        cms = get_cms()
        self.m = cms.create_media_from_file(self.get_test_image_path('test.png'), 'Test')

        # verify it's a JPEG file
        img = open_image(self.m.original_path)
        self.assertEqual('test.jpg', self.m.filename)
        self.assertTrue(is_jpeg_image_object(img))


    def test_upload_png_with_transparency_should_not_convert_image_to_jpg(self):
        cms = get_cms()
        self.m = cms.create_media_from_file(self.get_test_image_path('test_with_transparency.png'), 'Test')

        # verify it's still a PNG file with transparency layer
        img = open_image(self.m.original_path)
        self.assertEqual('test.png', self.m.filename)
        self.assertTrue(is_png_image_object(img))


    def test_delete_media_asset_should_remove_physical_files(self):
        cms = get_cms()
        self.m = cms.create_media_from_file(self.get_test_image_path('test.jpg'), 'Test')

        files = [
            self.m.original_path,
        ]
        for size in self.m.get_available_image_sizes():
            files.append(self.m.get_image_path(size, settings.DEFAULT_IMAGE_SHAPE))
            for shape in Media.get_shape_names():
                files.append(self.m.get_image_path(size, shape))

        for f in files:
            self.assertTrue(os.path.isfile(f), f)

        self.m.delete()

        for f in files:
            self.assertFalse(os.path.isfile(f), f)


    def test_get_available_image_sizes_should_return_available_image_sizes(self):
        self.m.width = 512
        self.m.height = 512
        self.assertEqual({
            'small': 254,
            'large': 738,
            'xx-small': 75,
            'medium': 336,
            'x-small': 149
        }, self.m.get_available_image_sizes())


    def test_get_image_url_or_smaller(self):
        self.m.id = 1
        self.m.width = 600
        self.m.height = 600
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/media/shapes/original/large/0/1/',
            self.m.get_image_url_or_smaller('x-large')
        )


    @override_settings(IMAGE_SHAPES={'landscape': '400:200'})
    def test_get_width(self):
        delattr(Media, '_shapes')
        self.m.width = 600
        self.assertEqual(1280, self.m.get_width('x-large', 'landscape'))


    @override_settings(IMAGE_SHAPES={'landscape': '400:200'})
    def test_get_height(self):
        delattr(Media, '_shapes')
        self.m.width = 600
        self.assertEqual(640, self.m.get_height('x-large', 'landscape'))


    def test_set_filename_should_set_caption_if_not_set(self):
        self.m.set_filename('hello_world.jpg')
        self.assertEqual('hello-world.jpg', self.m.filename)
        self.assertEqual('Hello World', self.m.caption)


    def test_set_filename_should_not_exceed_os_max_filename_length(self):
        fn = 'x' * MAX_FILENAME_LENGTH + '.jpg'
        self.m.set_filename(fn)
        self.assertEqual('x' * (MAX_FILENAME_LENGTH - 4) + '.jpg', self.m.filename)
        self.assertTrue(len(self.m.filename) <= MAX_FILENAME_LENGTH)


    @override_settings(IMAGE_SHAPES={'landscape': '400:200'})
    def test_to_dict(self):
        delattr(Media, '_shapes')
        self.m.id = 1
        self.m.width = 600
        self.m.height = 600
        self.m.filename = 'test.jpg'
        self.m.caption = 'Test'
        self.m.is_image = True
        self.assertEqual({
            'url': 'http://www.testapp.cubane.innershed.com/media/shapes/original/large/0/1/test.jpg',
            'original_url': u'http://www.testapp.cubane.innershed.com/media/originals/0/1/test.jpg',
            'caption': 'Test',
            'shapes': {
                'original': {
                    'small': 'http://www.testapp.cubane.innershed.com/media/shapes/original/small/0/1/test.jpg',
                    'large': 'http://www.testapp.cubane.innershed.com/media/shapes/original/large/0/1/test.jpg',
                    'xx-small': 'http://www.testapp.cubane.innershed.com/media/shapes/original/xx-small/0/1/test.jpg',
                    'medium': 'http://www.testapp.cubane.innershed.com/media/shapes/original/medium/0/1/test.jpg',
                    'x-small': 'http://www.testapp.cubane.innershed.com/media/shapes/original/x-small/0/1/test.jpg'
                },
                'landscape': {
                    'small': 'http://www.testapp.cubane.innershed.com/media/shapes/landscape/small/0/1/test.jpg',
                    'large': 'http://www.testapp.cubane.innershed.com/media/shapes/landscape/large/0/1/test.jpg',
                    'xx-small': 'http://www.testapp.cubane.innershed.com/media/shapes/landscape/xx-small/0/1/test.jpg',
                    'medium': 'http://www.testapp.cubane.innershed.com/media/shapes/landscape/medium/0/1/test.jpg',
                    'x-small': 'http://www.testapp.cubane.innershed.com/media/shapes/landscape/x-small/0/1/test.jpg'
                }
            },
            'id': 1,
            'hashid': None,
            'is_svg': False,
            'lastmod': None
        }, self.m.to_dict())


    def _assert_media_filter(self, widths, image_size, expected_widths):
        media = []
        for w in widths:
            m = Media(width=w)
            m.save()
            media.append(m)

        self.assertEqual(expected_widths, [m.width for m in Media.filter_by(Media.objects.all(), image_size)])

        for m in media:
            m.delete()


    def _assert_get_shapes(self, expected_shapes):
        delattr(Media, '_shapes')
        shapes = Media.get_shapes()
        self.assertEqual(expected_shapes, shapes)


    def _assert_orientation(self, width, height, attr, expected_orientation):
        self.m.width = width
        self.m.height = height
        self.assertEqual(expected_orientation, getattr(self.m, attr))


    def _assert_size_url(self, size, url_size):
        self.m.id = 1
        self.m.width = 2400
        self.m.height = 2400
        self.assertEqual(
            'http://www.testapp.cubane.innershed.com/media/shapes/original/%s/0/1/' % url_size,
            getattr(self.m, '%s_url' % size)
        )