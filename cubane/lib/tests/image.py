# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.test.utils import override_settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.file import is_same_file, file_get_contents
from cubane.lib.image import (
    open_image,
    is_image,
    get_ext,
    get_image_size,
    remove_image_transparency,
    get_image_fitting,
    get_image_crop_area,
    get_image_crop_area_normalised,
    resize_image,
    resize_image_if_too_wide,
    is_jpeg_image_object,
    is_png_image_object,
    can_optimize_images,
    optimize_image,
    get_exif_image_rotation,
    exif_auto_rotate_image,
    is_png_without_transparency,
    convert_image,
    resize_svg_image,
    get_colorized_svg_image,
    get_shapes_from_svg_image
)
from bs4 import BeautifulSoup
from wand.image import Image as WandImage
import tempfile
import os
import shutil


class TestImage(object):
    def __init__(self, filename, width, height):
        self.filename = filename
        self.width = width
        self.height = height


TEST_IMAGES = [
    TestImage('test.jpg', 512, 512),
    TestImage('test.png', 512, 512),
    TestImage('test-transparent.png', 589, 150),
    TestImage('test.tiff', 512, 512),
    TestImage('test.gif', 512, 512),
    TestImage('test.bmp', 512, 512),
    TestImage('test.svg', None, None)
]


TEST_IMAGES_NO_SVG = [f for f in TEST_IMAGES if get_ext(f.filename) != 'svg']


class LibImageGetImageFittingTestCase(CubaneTestCase):
    """
    cubane.lib.image.get_image_fitting()
    """
    def test_landscape_fit(self):
        self.assertEqual((450, 300), get_image_fitting(600, 400, 1024, 300))


    def test_portrait_fit(self):
        self.assertEqual((300, 200), get_image_fitting(600, 400, 300, 1024))


    def test_zero_height_landscape_fit(self):
        self.assertEqual((1024, 0), get_image_fitting(600, 0, 1024, 300))


class LibImageGetImageCropAreaTestCase(CubaneTestCase):
    """
    cubane.lib.image.get_image_crop_area()
    """
    def test_with_zero_image_height_should_return_area_with_zero_height(self):
        self.assert_image_crop(500, 0, 500, 500, 0, 0, 500, 0)


    def test_with_zero_target_height_should_return_area_with_zero_height(self):
        self.assert_image_crop(500, 500, 500, 0, 0, 0, 500, 0)


    def test_landscape_to_smaller_square_should_center_crop_area_horizontally(self):
        self.assert_image_crop(1000, 800, 500, 500, 100, 0, 800, 800)


    def test_landscape_to_bigger_square_should_center_crop_area_horizontally(self):
        self.assert_image_crop(1000, 300, 500, 500, 350, 0, 300, 300)


    def test_portrait_to_smaller_square_should_center_crop_area_vertically(self):
        self.assert_image_crop(800, 1000, 500, 500, 0, 100, 800, 800)


    def test_portrait_to_bigger_square_should_center_crop_area_vertically(self):
        self.assert_image_crop(300, 1000, 500, 500, 0, 350, 300, 300)


    def test_landscape_to_portrait(self):
        self.assert_image_crop(1000, 300, 300, 1000, 455, 0, 90, 300)


    def test_portrait_to_landscape(self):
        self.assert_image_crop(300, 1000, 1000, 300, 0, 455, 300, 90)


    def test_landscape_to_landscape_does_not_fit_by_height_should_then_be_based_on_width_instead(self):
        self.assert_image_crop(1200, 1200, 640, 421, 0, 205, 1200, 789)


    def test_landscape_to_portrait_does_not_fit_by_width_should_then_be_based_on_height_instead(self):
        self.assert_image_crop(1200, 1200, 421, 640, 205, 0, 790, 1200)


    def test_portrait_to_landscape_does_not_fit_by_height_should_then_be_based_on_width_instead(self):
        self.assert_image_crop(800, 1200, 640, 421, 0, 337, 800, 526)


    def test_portrait_to_portrait_does_not_fit_by_width_should_then_be_based_on_height_instead(self):
        self.assert_image_crop(800, 1200, 421, 640, 5, 0, 789, 1200)


    def assert_image_crop(self, width, height, target_width, target_height, x, y, w, h):
        (area_x, area_y, area_w, area_h) = get_image_crop_area(width, height, target_width, target_height)
        area_x = int(area_x)
        area_y = int(area_y)
        area_w = int(area_w)
        area_h = int(area_h)

        self.assertEqual(area_x, x, 'crop area x: should be %f but was %f' % (x, area_x))
        self.assertEqual(area_y, y, 'crop area y: should be %f but was %f' % (y, area_y))
        self.assertEqual(area_w, w, 'crop area w: should be %f but was %f' % (w, area_w))
        self.assertEqual(area_h, h, 'crop area h: should be %f but was %f' % (h, area_h))


class LibImageGetImageCropAreaNormalisedTestCase(CubaneTestCase):
    """
    cubane.lib.image.get_image_crop_area_normalised()
    """
    def test_with_zero_image_height_should_return_area_with_zero_height(self):
        self.assert_image_crop(500, 0, 500, 500, 0, 0, 1.0, 0)


    def test_with_zero_target_height_should_return_area_with_zero_height(self):
        self.assert_image_crop(500, 500, 500, 0, 0, 0, 1.0, 0)


    def test_landscape_to_smaller_square_should_center_crop_area_horizontally(self):
        self.assert_image_crop(1000, 800, 500, 500, 0.1, 0, 0.8, 1.0)


    def test_landscape_to_bigger_square_should_center_crop_area_horizontally(self):
        self.assert_image_crop(1000, 300, 500, 500, 0.350, 0, 0.3, 1.0)


    def test_portrait_to_smaller_square_should_center_crop_area_vertically(self):
        self.assert_image_crop(800, 1000, 500, 500, 0, 0.1, 1.0, 0.8)


    def test_portrait_to_bigger_square_should_center_crop_area_vertically(self):
        self.assert_image_crop(300, 1000, 500, 500, 0, 0.350, 1.0, 0.3)


    def test_landscape_to_portrait(self):
        self.assert_image_crop(1000, 300, 300, 1000, 0.455, 0, 0.09, 1.0)


    def test_portrait_to_landscape(self):
        self.assert_image_crop(300, 1000, 1000, 300, 0, 0.455, 1.0, 0.09)


    def assert_image_crop(self, width, height, target_width, target_height, x, y, w, h):
        (area_x, area_y, area_w, area_h) = get_image_crop_area_normalised(width, height, target_width, target_height)
        self.assertEqual(area_x, x, 'normalised crop area x: should be %f but was %f' % (x, area_x))
        self.assertEqual(area_y, y, 'normalised crop area y: should be %f but was %f' % (y, area_y))
        self.assertEqual(area_w, w, 'normalised crop area w: should be %f but was %f' % (w, area_w))
        self.assertEqual(area_h, h, 'normalised crop area h: should be %f but was %f' % (h, area_h))


class LibImageIsImageTestCase(CubaneTestCase):
    """
    cubane.lib.image.is_image()
    """
    def test_should_return_true_for_images(self):
        for image in TEST_IMAGES:
            self.assertTrue(is_image(self.get_test_image_path(image.filename)))


    def test_should_return_false_if_extension_is_pdf(self):
        self.assertFalse(is_image(self.get_test_image_path('test.pdf')))


    def test_should_return_false_for_non_images(self):
        self.assertFalse(is_image(self.get_test_image_path('test.txt')))


class LibImageGetExtTestCase(CubaneTestCase):
    """
    cubane.lib.image.get_ext()
    """
    def test_should_return_last_extension_part_without_dot(self):
        self.assertEqual(get_ext('/home/cubane/test.backup.txt'), 'txt')


    def test_should_return_empty_extension_if_no_extension_is_present(self):
        self.assertEqual(get_ext('/home/cubane/'), '')


class LibImageGetImageSizeTestCase(CubaneTestCase):
    """
    cubane.lib.image.get_image_size()
    """
    def test_should_return_image_size_in_pixels(self):
        for image in TEST_IMAGES:
            filename = self.get_test_image_path(image.filename)
            if get_ext(filename) != 'svg':
                image_size = get_image_size(filename)
                self.assertEqual(image_size[0], image.width, '%s: width should be %d but was %d' % (image.filename, image.width, image_size[0]))
                self.assertEqual(image_size[1], image.height, '%s: height should be %d but was %d' % (image.filename, image.height, image_size[1]))


    def test_should_return_image_size_in_pixels_for_svg_image(self):
        image_size = get_image_size(self.get_test_image_path('test.svg'))
        self.assertEqual(164, image_size[0])
        self.assertEqual(84, image_size[1])


    def test_should_raise_ioerror_if_not_an_image(self):
        with self.assertRaises(IOError):
            get_image_size(self.get_test_image_path('test.txt'))


class LibImageRemoveImageTransparencyTestCase(CubaneTestCase):
    """
    cubane.lib.image.remove_image_transparency()
    """
    def test_should_remove_transparent_layer(self):
        img = open_image(self.get_test_image_path('test-transparent.png'))
        self.assertTrue(self.has_transparency_layer(img))
        img = remove_image_transparency(img)
        self.assertFalse(self.has_transparency_layer(img))


    def test_should_ignore_if_no_transparency_layer_present(self):
        img = open_image(self.get_test_image_path('test.jpg'))
        self.assertFalse(self.has_transparency_layer(img))
        img = remove_image_transparency(img)
        self.assertFalse(self.has_transparency_layer(img))


    def has_transparency_layer(self, img):
        return img.alpha_channel


class LibImageResizeImageTestCase(CubaneTestCase):
    """
    cubane.lib.image.resize_image()
    """
    def test_should_crop_image(self):
        for image in TEST_IMAGES:
            self.assert_resize_image(image.filename, 350, 120, 'crop')


    def test_should_scale_image(self):
        self.assert_resize_image('test.jpg', 350, 120, 'scale', 120, 120)
        self.assert_resize_image('test.png', 350, 120, 'scale', 120, 120)
        self.assert_resize_image('test-transparent.png', 350, 120, 'scale', 350, 89)
        self.assert_resize_image('test.tiff', 350, 120, 'scale', 120, 120)
        self.assert_resize_image('test.svg', 164, 84, 'scale')


    def test_should_not_upscale_when_scaling(self):
        self.assert_resize_image('test.jpg', 1024, 1024, 'scale', 512, 512)


    def assert_resize_image(self, filename, width, height, mode, expected_width=None, expected_height=None):
        if expected_width == None: expected_width = width
        if expected_height == None: expected_height = height

        filename = self.get_test_image_path(filename)
        ext = get_ext(filename)
        dst_filename = os.path.join(tempfile.gettempdir(), 'resized_image.%s' % ext)

        resize_image(filename, dst_filename, width, height, mode)

        self.assertTrue(os.path.isfile(dst_filename), 'file exists')
        self.assertTrue(is_image(dst_filename), 'is image file')

        # check image size
        size = get_image_size(dst_filename)
        self.assertEqual(size[0], expected_width, 'expected image width of %d, but was %d.' % (expected_width, size[0]))
        self.assertEqual(size[1], expected_height, 'expected image height of %d, but was %d.' % (expected_height, size[1]))


class LibResizeImageIfTooWideTestCase(CubaneTestCase):
    """
    cubane.lib.image.resize_image_if_too_wide()
    """
    @override_settings(IMG_MAX_WIDTH=256)
    def test_should_resize_if_too_wide(self):
        self.assert_resized('test.jpg', 256, 256)
        self.assert_resized('test.png', 256, 256)
        self.assert_resized('test-transparent.png', 256, 65)
        self.assert_resized('test.tiff', 256, 256)


    @override_settings(IMG_MAX_WIDTH=1024)
    def test_should_not_resize_if_not_too_wide(self):
        for image in TEST_IMAGES_NO_SVG:
            self.assert_not_resized(image)


    @override_settings(IMG_MAX_WIDTH=None)
    def test_should_not_resize_if_none(self):
        for image in TEST_IMAGES_NO_SVG:
            self.assert_not_resized(image)


    def test_should_not_resize_if_error(self):
        resized = resize_image_if_too_wide('does-not-exist.jpg')
        self.assertFalse(resized)


    def assert_resized(self, filename, width, height):
        filename = self.get_test_image_path(filename)
        resized, new_width, new_height = self.resize_image_copy_if_too_wide(filename)
        self.assertTrue(resized)
        self.assertEqual(new_width, width, 'expected image width of %d, but was %d.' % (width, new_width))
        self.assertEqual(new_height, height, 'expected image height of %d, but was %d.' % (height,new_height))


    def assert_not_resized(self, image):
        filename = self.get_test_image_path(image.filename)
        resized, width, height = self.resize_image_copy_if_too_wide(filename)
        self.assertFalse(resized)
        self.assertEqual(width, image.width, 'expected image width of %d, but was %d.' % (image.width, width))
        self.assertEqual(height, image.height, 'expected image height of %d, but was %d.' % (image.height, height))


    def resize_image_copy_if_too_wide(self, filename):
        filename = self.get_test_image_path(filename)
        ext = get_ext(filename)
        dst_filename = os.path.join(tempfile.gettempdir(), 'resized_image_copy.%s' % ext)
        shutil.copyfile(filename, dst_filename)

        resized = resize_image_if_too_wide(dst_filename)

        width, height = get_image_size(dst_filename)
        os.remove(dst_filename)
        return (resized, width, height)


    def test_resize_image_with_exif_tag_should_auto_rotate(self):
        filename = self.get_test_image_path('EXIF_orientation_samples/right.jpg')

        img = open_image(filename)
        img = exif_auto_rotate_image(img)
        (width, height) = img.size

        # the input image size is actually 480x640, but since the system is
        # rotating the image by 90 degrees because of the EXIF orientation tag,
        # we would expect to find the image domensions 640x480
        self.assertEqual(width, 640)
        self.assertEqual(height, 480)


class LibImageIsPngWithoutTransparencyTestCase(CubaneTestCase):
    """
    cubane.lib.image.is_png_without_transparency()
    """
    def test_should_return_false_if_image_is_not_an_image_to_begin_with(self):
        self.assertFalse(is_png_without_transparency(self.get_test_image_path('test.txt')))


    def test_should_return_false_if_image_is_not_png(self):
        self.assertFalse(is_png_without_transparency(self.get_test_image_path('test.jpg')))


    def test_should_return_false_if_image_is_png_with_transparency(self):
        self.assertFalse(is_png_without_transparency(self.get_test_image_path('test_with_transparency.png')))


    def test_should_return_true_if_image_is_png_but_without_transparency(self):
        self.assertTrue(is_png_without_transparency(self.get_test_image_path('test.png')))


class LibImageConvertImageTestCase(CubaneTestCase):
    """
    cubane.lib.image.convert_image()
    """
    def setUp(self):
        self.dst_filename = os.path.join(tempfile.gettempdir(), 'converted_image.jpg')


    def tearDown(self):
        if os.path.isfile(self.dst_filename):
            os.unlink(self.dst_filename)


    def should_return_false_if_not_an_image(self):
        filename = self.get_test_image_path('test.txt')
        self.assertFalse(convert_image(filename, self.dst_filename))
        self.assertFalse(os.path.isfile(self.dst_filename))


    def should_return_true_after_converting_image(self):
        filename = self.get_test_image_path('test.png')
        self.assertTrue(convert_image(filename, self.dst_filename))
        self.assertTrue(os.path.isfile(self.dst_filename))


    def should_return_true_after_converting_and_replacing_image(self):
        filename = self.get_test_image_path('test.jpg')
        shutil.copyfile(filename, self.dst_filename)
        self.assertTrue(convert_image(self.dst_filename, self.dst_filename))
        self.assertTrue(os.path.isfile(self.dst_filename))


class LibImageIsJpegImageTestCase(CubaneTestCase):
    """
    cubane.lib.image.is_jpeg_image_object()
    cubane.lib.image.is_png_image_object()
    """
    def test_is_jpeg_image_object_should_return_true_for_jpeg_image(self):
        self._assert_image_format('test.jpg', 'JPEG', True)


    def test_is_jpeg_image_object_should_return_false_for_none_jpg_image(self):
        for ext in ['png', 'gif', 'tiff', 'bmp', 'svg', 'pdf']:
            self._assert_image_format('test.%s' % ext, 'JPEG', False)


    def test_is_png_image_object_should_return_true_for_png_image(self):
        self._assert_image_format('test.png', 'PNG', True)


    def test_is_png_image_object_should_return_false_for_none_png_image(self):
        for ext in ['jpg', 'gif', 'tiff', 'bmp', 'svg', 'pdf']:
            self._assert_image_format('test.%s' % ext, 'PNG', False)


    def _assert_image_format(self, filename, test_format, expected_result):
        with WandImage(filename=self.get_test_image_path(filename)) as img:
            if expected_result:
                msg = 'Image was expected to be %s, but it was not: %s'
            else:
                msg = 'Image was expected to be non-%s, but it was: %s'

            self.assertEqual(
                expected_result,
                is_jpeg_image_object(img) if test_format == 'JPEG' else is_png_image_object(img),
                msg % (test_format, filename)
            )


class LibImageCanOptimizeImagesTestCase(CubaneTestCase):
    """
    cubane.lib.image.can_optimize_images()
    """
    @override_settings(IMAGE_JPEG_OPT_COMMAND='does_not_exist', IMAGE_PNG_OPT_COMMAND='does_not_exist')
    def test_should_return_false_if_both_executables_fail(self):
        self.assertFalse(can_optimize_images())


    @override_settings(IMAGE_JPEG_OPT_COMMAND='does_not_exist')
    def test_should_return_false_if_jpeg_executables_fail(self):
        self.assertFalse(can_optimize_images())


    @override_settings(IMAGE_PNG_OPT_COMMAND='does_not_exist')
    def test_should_return_false_if_png_executables_fail(self):
        self.assertFalse(can_optimize_images())


    def test_should_return_true_if_both_executables_succeed(self):
        self.assertTrue(can_optimize_images())


class LibImageOptimizeImageTestCase(CubaneTestCase):
    """
    cubane.lib.image.optimize_image()
    """
    def test_optimized_image_should_be_smaller(self):
        for ext in ['jpg', 'gif', 'tiff', 'bmp', 'svg', 'pdf']:
            filename = self.get_test_image_path('test.%s' % ext)
            dst_filename = os.path.join(tempfile.gettempdir(), 'optimized_image.%s' % ext)

            result = optimize_image(filename, dst_filename)

            size = os.path.getsize(filename)

            if ext in ['jpg', 'png']:
                self.assertTrue(result)
                self.assertTrue(
                    os.path.isfile(dst_filename),
                    'Output file should exist: %s' % dst_filename
                )

                optimized_size = os.path.getsize(dst_filename)

                self.assertTrue(
                    optimized_size < size,
                    'Optimized image is NOT smaller than original image: %s' % filename
                )
            else:
                self.assertFalse(result)
                self.assertFalse(
                    os.path.isfile(dst_filename),
                    'Output file should NOT exist: %s' % dst_filename
                )


    @override_settings(DEBUG=True, IMAGE_JPEG_OPT_COMMAND='does_not_exist %(source)s %(dest)s')
    def test_should_silently_fail_in_debug_mode(self):
        filename = self.get_test_image_path('test.jpg')
        dst_filename = os.path.join(tempfile.gettempdir(), 'optimized.jpg')
        self.assertFalse(optimize_image(filename, dst_filename))


    @override_settings(DEBUG=False, IMAGE_JPEG_OPT_COMMAND='does_not_exist %(source)s %(dest)s')
    def test_should_silently_fail_in_production_mode(self):
        filename = self.get_test_image_path('test.jpg')
        dst_filename = os.path.join(tempfile.gettempdir(), 'optimized.jpg')
        self.assertFalse(optimize_image(filename, dst_filename))


class LibImageResizeSVGImageTestCase(CubaneTestCase):
    """
    cubane.lib.image.resize_svg_image()
    """
    def test_should_not_change_pure_vector_image(self):
        src = self.get_test_image_path('test.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 0, 0, crop=False, optimize=False)

            # svg file without any bitmap data embedded should be the same
            # image after resize (without optimizations)...
            self.assertTrue(is_same_file(src, dst))
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_downsampling_embedded_png_image_within_svg_container(self):
        self._assert_downsampling('test_svg_with_png.svg')


    def test_should_downsampling_embedded_jpg_image_within_svg_container(self):
        self._assert_downsampling('test_svg_with_jpg.svg')


    def test_should_ignore_embedded_bitmap_if_image_cannot_be_b64_decoded(self):
        src = self.get_test_image_path('test_svg_with_broken_b64_encoding.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 0, 0, crop=False, optimize=False)

            # svg file with broken bitmap data (base64 decoding error) should
            # contain the same embedded bitmap data as the original
            self.assertTrue(is_same_file(src, dst))
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_ignore_embedded_bitmap_if_image_data_cannot_be_read_or_processed(self):
        src = self.get_test_image_path('test_svg_with_broken_png.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 0, 0, crop=False, optimize=False)

            # svg file with broken bitmap data should be the same as the
            # original without optimizations (ignored)...
            self.assertTrue(is_same_file(src, dst))
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_inline_style(self):
        src = self.get_test_image_path('test_svg_with_style.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 164.4, 83.7, optimize=True, prefix='')
            svg = file_get_contents(dst)
            self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n' + \
                '<svg id="Layer_1" style="enable-background:new 0 0 164 84;" version="1.1" viewBox="0 0 164 84" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n' + \
                '\n' + \
                '<polygon points="36.3,83.7 0.1,62.7 0,20.8 36.1,0 72.2,21.1 72.4,62.9 " style="fill:#E8318A;"/>\n' + \
                '<polygon points="36.4,62.9 54.5,73 54.5,52.4 " style="fill:#BF2174;"/>\n' + \
                '<polygon points="36.4,62.9 36.7,42.1 54.5,52.4 " style="opacity:0.56;fill:#EA53A2;"/>\n' + \
                '</svg>',
                svg
            )
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_prefix_identifiers_and_references(self):
        src = self.get_test_image_path('test_svg_with_ids.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 0, 0, crop=False, optimize=True, prefix='foo')
            svg = file_get_contents(dst)
            self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n' + \
                '<svg data-prefix="foo" id="foo_Layer_1" style="enable-background:new 0 0 164.4 83.7;" version="1.1" viewBox="0 0 164.4 83.7" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n' + \
                '<polygon id="foo_base" points="36.3,83.7 0.1,62.7 0,20.8 36.1,0 72.2,21.1 72.4,62.9 "/>\n' + \
                '<polygon id="foo_cuffs" points="36.4,62.9 54.5,73 54.5,52.4 "/>\n' + \
                '<g id="foo_test" transform="matrix(0.250391,0,0,0.250391,36.1,46.1023)">\n' + \
                '<use height="512px" width="512px" x="0" xlink:href="#foo_Image1" y="0"/>\n' + \
                '</g>\n' + \
                '<defs>\n' + \
                '<image height="512px" id="foo_Image1" width="512px" xlink:href="data:image/png;base64,broken image"/>\n' + \
                '</defs>\n' + \
                '</svg>',
                svg
            )
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_enforce_prefix_always_starting_with_letter(self):
        src = self.get_test_image_path('test_svg_with_ids.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 0, 0, crop=False, optimize=True, prefix='foo')
            svg = file_get_contents(dst)
            self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n' + \
                '<svg data-prefix="foo" id="foo_Layer_1" style="enable-background:new 0 0 164.4 83.7;" version="1.1" viewBox="0 0 164.4 83.7" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n' + \
                '<polygon id="foo_base" points="36.3,83.7 0.1,62.7 0,20.8 36.1,0 72.2,21.1 72.4,62.9 "/>\n' + \
                '<polygon id="foo_cuffs" points="36.4,62.9 54.5,73 54.5,52.4 "/>\n' + \
                '<g id="foo_test" transform="matrix(0.250391,0,0,0.250391,36.1,46.1023)">\n' + \
                '<use height="512px" width="512px" x="0" xlink:href="#foo_Image1" y="0"/>\n' + \
                '</g>\n' + \
                '<defs>\n' + \
                '<image height="512px" id="foo_Image1" width="512px" xlink:href="data:image/png;base64,broken image"/>\n' + \
                '</defs>\n' + \
                '</svg>',
                svg
            )
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_prefix_style_url_references(self):
        src = self.get_test_image_path('test_svg_with_style_url_ref.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 0, 0, crop=False, optimize=True, prefix='123')
            svg = file_get_contents(dst)
            self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n' +
                '<svg data-prefix="b23" id="b23_Layer_1" style="enable-background:new 0 0 64 64;" version="1.1" viewBox="0 0 64 64" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n\n' +
                '<linearGradient gradientUnits="userSpaceOnUse" id="b23_SVGID_1_" x1="0" x2="64" y1="32.3013" y2="32.3013">\n' +
                '<stop offset="0" style="stop-color:#B90404"/>\n' +
                '<stop offset="1" style="stop-color:#8E0000"/>\n' +
                '</linearGradient>\n' +
                '<path d="36.3,83.7 0.1,62.7 0,20.8 36.1,0 72.2,21.1 72.4,62.9" style="fill:url(#b23_SVGID_1_);"/>\n' +
                '</svg>',
                svg
            )
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_prefix_clip_path_url_references(self):
        src = self.get_test_image_path('test_svg_with_clippath_url_ref.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 0, 0, crop=False, optimize=True, prefix='123')
            svg = file_get_contents(dst)
            self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n' +
                '<svg data-prefix="b23" id="b23_Layer_1" style="enable-background:new 0 0 64 64;" version="1.1" viewBox="0 0 64 64" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n' +
                '<clipPath id="b23_clip"><path d="M441.105,324.213l44.837,10.308l13.761,-59.851l-44.837,-10.309l-13.761,59.852l0,0Z"/></clipPath>\n' +
                '<g clip-path="url(#b23_clip)">\n' +
                '<path d="36.3,83.7 0.1,62.7 0,20.8 36.1,0 72.2,21.1 72.4,62.9"/>\n' +
                '</g>\n' +
                '</svg>',
                svg
            )
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_crop_to_new_aspect_ratio_based_on_center_position_for_shape(self):
        src = self.get_test_image_path('test_svg_crop.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 600, 300, prefix='')
            svg = file_get_contents(dst)
            self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n' + \
                '<svg id="Layer_1" style="enable-background:new 0 1 164 82;" version="1.1" viewBox="0 1 164 82" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n' + \
                '<polygon fill="red" points="36.3,83.7 0.1,62.7 0,20.8 36.1,0 72.2,21.1 72.4,62.9 "/>\n' + \
                '</svg>',
                svg
            )
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_crop_to_new_aspect_ratio_based_on_center_position_for_landscape(self):
        src = self.get_test_image_path('test_svg_crop_landscape.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 400, 400, prefix='')
            svg = file_get_contents(dst)
            self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n' + \
                '<svg id="Layer_1" style="enable-background:new 40 0 80 80;" version="1.1" viewBox="40 0 80 80" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n' + \
                '<polygon fill="red" points="36.3,83.7 0.1,62.7 0,20.8 36.1,0 72.2,21.1 72.4,62.9 "/>\n' + \
                '</svg>',
                svg
            )
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def test_should_crop_to_new_aspect_ratio_based_on_center_position_for_portrait(self):
        src = self.get_test_image_path('test_svg_crop_portrait.svg')
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 400, 400, prefix='')
            svg = file_get_contents(dst)
            self.assertEqual(
                '<?xml version="1.0" encoding="utf-8"?>\n' + \
                '<svg id="Layer_1" style="enable-background:new 0 40 80 80;" version="1.1" viewBox="0 40 80 80" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px">\n' + \
                '<polygon fill="red" points="36.3,83.7 0.1,62.7 0,20.8 36.1,0 72.2,21.1 72.4,62.9 "/>\n' + \
                '</svg>',
                svg
            )
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


    def _assert_downsampling(self, filename):
        src = self.get_test_image_path(filename)
        dst = os.path.join(tempfile.gettempdir(), 'resized_svg_image.svg')
        try:
            resize_svg_image(src, dst, 50, 50)

            # svg file with bitmap data embedded should NOT be the same
            # image after resize...
            self.assertFalse(is_same_file(src, dst))

            # image size should be less
            self.assertTrue(os.path.getsize(dst) < os.path.getsize(src))

            # the resulting image should still be an svg image with path
            # information in it
            content = file_get_contents(dst)
            self.assertIn('<svg', content)
            self.assertIn('<path', content)
        finally:
            if os.path.isfile(dst):
                os.unlink(dst)


class LibImageGetColorizedSvgImageTestCase(CubaneTestCase):
    """
    cubane.lib.image.get_colorized_svg_image()
    """
    def test_should_colorise_given_layers(self):
        src = self.get_test_image_path('test_layers.svg')
        svg = get_colorized_svg_image(src, {
            'polygon': 'fill:black',
            'path': 'stroke:#efefef'
        })
        xml = BeautifulSoup(svg, 'xml')
        self.assertEqual('fill:black', xml.find(id='polygon')['style'])
        self.assertEqual('stroke:#efefef', xml.find(id='path')['style'])


    def test_should_ignore_unknown_layers(self):
        src = self.get_test_image_path('test_layers.svg')
        svg = get_colorized_svg_image(src, {
            'does_not_exist': 'fill:black',
            'path': 'fill:#efefef'
        })
        xml = BeautifulSoup(svg, 'xml')
        self.assertIsNone(xml.find(id='does_not_exist'))
        self.assertEqual('fill:#efefef', xml.find(id='path')['style'])


    def test_should_remove_style_attribute_if_present(self):
        src = self.get_test_image_path('test_layers.svg')
        svg = get_colorized_svg_image(src, {
            'polygon': 'fill:black',
        })
        xml = BeautifulSoup(svg, 'xml')
        el = xml.find(id='polygon')
        self.assertEqual('fill:black', el['style'])
        self.assertIsNone(el.get('fill')) # fill=red should have been removed


    def test_should_assume_fill_if_no_action_is_given(self):
        src = self.get_test_image_path('test_layers.svg')
        svg = get_colorized_svg_image(src, {
            'polygon': 'black'
        })
        xml = BeautifulSoup(svg, 'xml')
        self.assertEqual('fill:black', xml.find(id='polygon')['style'])


    def test_should_accept_list_of_instructions(self):
        src = self.get_test_image_path('test_layers.svg')
        svg = get_colorized_svg_image(src, {
            'polygon': ['fill:black', 'stroke:red']
        })
        xml = BeautifulSoup(svg, 'xml')
        el = xml.find(id='polygon')
        self.assertIn('fill:black', el['style'])
        self.assertIn('stroke:red', el['style'])


    def test_should_ignore_unsupported_attributes(self):
        src = self.get_test_image_path('test_layers.svg')
        svg = get_colorized_svg_image(src, {
            'polygon': ['stroke-with:2']
        })
        xml = BeautifulSoup(svg, 'xml')
        self.assertEqual('', xml.find(id='polygon')['style'])


class LibImageGetShapesFromSvgImageTestCase(CubaneTestCase):
    """
    cubane.lib.image.get_shapes_from_svg_image()
    """
    def test_should_return_empty_list_for_none(self):
        self.assertEqual([], get_shapes_from_svg_image(None))


    def test_should_return_empty_list_for_non_svg_file(self):
        filename = self.get_test_image_path('test.jpg')
        self.assertEqual([], get_shapes_from_svg_image(filename))


    def test_should_return_list_of_identifiers_from_svg_file(self):
        filename = self.get_test_image_path('test_identifiers.svg')
        self.assertEqual(
            ['shape1', 'shape2', 'shape3'],
            get_shapes_from_svg_image(filename)
        )


    def test_should_return_list_of_identifiers_from_svg_file_with_prefix(self):
        filename = self.get_test_image_path('test_identifiers_with_prefix.svg')
        self.assertEqual(
            ['shape1', 'shape2', 'shape3'],
            get_shapes_from_svg_image(filename)
        )


    def test_should_return_list_of_identifiers_from_svg_file_filter_by_custom_prefix(self):
        filename = self.get_test_image_path('test_identifiers2.svg')
        self.assertEqual(
            ['foo_shape1', 'foo_shape3'],
            get_shapes_from_svg_image(filename, prefix='foo')
        )