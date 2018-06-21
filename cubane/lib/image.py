# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.file import file_get_contents, file_put_contents
from cubane.lib.file import file_move
from cubane.lib.style import (
    parse_style,
    inline_style,
    parse_inline_style,
    encode_inline_style,
    remove_attr
)
from bs4 import BeautifulSoup, element
import sys
import io
import os
import re
import base64
import hashlib
import tempfile
import subprocess

# wand
from wand.image import Image as WandImage
from wand.color import Color as WandColor
from wand.drawing import Drawing as WandDrawing
from wand import exceptions as wand_exceptions


NOT_AN_IMAGE_WAND_EXCEPTIONS = (
    wand_exceptions.MissingDelegateError,
    wand_exceptions.BlobError,
    wand_exceptions.CorruptImageError,
    wand_exceptions.TypeError,
    wand_exceptions.FileOpenError
)


SUPPORTED_SVG_STYLE_OVERWRITES = [
    'fill',
    'stroke'
]


def open_image(filename):
    """
    Open image with pillow or wand.
    """
    return WandImage(filename=filename)


def is_image(filename):
    """
    Return True, if the given file is an image file.
    """
    ext = get_ext(filename)
    if ext == 'pdf':
        return False

    try:
        with WandImage(filename=filename) as img:
            return True
    except NOT_AN_IMAGE_WAND_EXCEPTIONS:
        return False


def get_ext(filename):
    """
    Return files extension (example: svg, jpg)
    """
    if '.' in filename:
        parts = filename.split('.')
        return parts[-1]
    else:
        return ''


def get_image_size(filename):
    """
    Return (width, height) for given image file in pixels.
    """
    try:
        with WandImage(filename=filename) as img:
            return (img.width, img.height)
    except NOT_AN_IMAGE_WAND_EXCEPTIONS:
        raise IOError()


def remove_image_transparency(img):
    """
    Remove any transparency layer from the given image and return the result.
    """
    if img.alpha_channel:
        bg = WandImage(width=img.width, height=img.height, background=WandColor('white'))
        bg.composite(img, 0, 0)
        img.destroy()
        img = bg

    return img


def get_image_fitting(width, height, target_width, target_height):
    """
    Return the actual image dimensions in order to resize an image with the
    given dimensions by 'fitting' the image into the target box without
    affecting the aspect ratio of the image.
    """
    if height == 0:
        ar = 0.0
    else:
        ar = float(width) / float(height)

    # try to stretch it to the target width
    w = target_width
    h = int(w / ar) if ar != 0.0 else 0

    # if the height is too big, try the other way around
    if h > target_height and ar > 0.0:
        h = target_height
        w = int(h * ar)

    return (w, h)


def prefix_ids(node, prefix):
    """
    Generate a unique identifier for the xml content and version of the
    file and prefix every id and reference within the document.
    """
    def _rewrite_url_ref(node, attr_name, prefix):
        """
        Rewrite url(#id); references within the given attribute of the given
        node.
        """
        try:
            v = node[attr_name]
            def repl_ref(m):
                return 'url(#%s%s)' % (prefix, m.group('ref'))
            node[attr_name] = re.sub(r'url\(#(?P<ref>.*?)\)', repl_ref, v)
        except KeyError:
            pass


    if isinstance(node, element.NavigableString):
        return

    # rewrite id attribute
    try:
        _id = node['id']
        node['id'] = '%s%s' % (prefix, _id)
    except KeyError:
        pass

    # rewrite xlink:href attribute reference
    try:
        href = node['xlink:href']
        if href.startswith('#'):
            node['xlink:href'] = '#%s%s' % (prefix, href[1:])
    except KeyError:
        pass

    # rewrite url(#id); references in inline style attributes
    _rewrite_url_ref(node, 'style', prefix)

    # rewrite url(#id); references in clip-path attributes
    _rewrite_url_ref(node, 'clip-path', prefix)

    # rewrite url(#id); references in clip-path attributes
    _rewrite_url_ref(node, 'mask', prefix)

    # process children
    for child in node.children:
        prefix_ids(child, prefix)


def get_image_crop_area(width, height, target_width, target_height, focal_point=None, valign='center'):
    """
    Return the crop rectangle for an image with given width and height to
    be cropped and fitted into the given target width and height.
    The resulting crop width and height might be smaller (or larger) than the
    given target width and height depending on the input image size; however
    the aspect ratio is the same.
    The crop region is based around the given focal point which describes the
    main focal point of the image which should become the center of the new
    image. If no focal point is given, the image center position is assumed.
    Focal point coordinates are in relative coordinates between 0.0 and 1.0.
    """
    if target_height == 0 or height == 0:
        return (0, 0, round(target_width), 0)

    # focal point
    if focal_point is None:
        fx, fy = 0.5, 0.5
    else:
        fx, fy = focal_point
        if fx is None: fx = 0.5
        if fy is None: fy = 0.5
    # make sure focal point is float
    fx = float(fx)
    fy = float(fy)

    fx = max(0.0, min(1.0, fx))
    fy = max(0.0, min(1.0, fy))

    # aspect ratios
    src_ar = float(width) / float(height)
    target_ar = float(target_width) / float(target_height)
    src_landscape = src_ar > 1
    target_landscape = target_ar > 1

    # focal point in image space
    img_fx = float(width) * fx
    img_fy = float(height) * fy

    # if we are cropping from portrait to landscape we tend to get better
    # results if the focal point will become the center of the new (cropped)
    # image...
    #if not src_landscape and target_landscape:
    #    fx = 0.5
    #    fy = 0.5

    # find largest possible crop region where focal point is relative to
    # where it is in the original image (binary search)...
    top = float(width)
    bottom = 0.0
    target_threshold = target_width * 1.01
    w = top
    i = 0
    while True:
        h = w / target_ar
        x = img_fx - (fx * w)
        y = img_fy - (fy * h)

        if w < target_threshold:
            if x < 0: x = 0
            if y < 0: y = 0
            if x + w > width: x = width - w
            if y + h > height: y = height - h

        valid = x >= 0 and y >= 0 and x + w <= width and y + h <= height
        if valid:
            # valid -> increase
            bottom = w
        else:
            # not valid -> decrease
            top = w

        w = bottom + ((top - bottom) / 2.0)

        # good enough?
        if valid and top - bottom < 1.0:
            break

        i += 1
        if i > 20: break

    # vertical alignment, in particular used for generating images from
    # PDF docuemnts, where we want to start from the top of the page...
    if valign == 'top':
        y = 0
    elif valign == 'bottom':
        y = height - h

    # return crop region (integers)
    x = round(x)
    y = round(y)
    w = round(w)
    h = round(h)
    if x < 0: x = 0
    if y < 0: y = 0
    return (x, y, w, h)


def get_image_crop_area_normalised(width, height, target_width, target_height, focal_point=None, valign='center'):
    """
    Return the crop rectangle for an image with given width and height to
    be cropped and fitted into the given target width and height as a
    resolution-independent and normalised figure, so that is can be applied
    independently of the actual size.
    """
    if target_height == 0 or height == 0:
        return (0.0, 0.0, 1.0, 0)

    (x, y, cropw, croph) = get_image_crop_area(width, height, target_width, target_height, focal_point, valign)

    dx = float(width)
    dy = float(height)

    return (x / dx, y / dy, cropw / dx, croph / dy)


def get_exif_image_rotation(img):
    """
    Return the orientation of the given image according to the embedded
    EXIF meta data tag for orientation (if any). The orientation is given
    in degrees in the direction the image would need to be rotated in order
    to counter-balance the 'miss' - orientation (counter-clockwise).
    """
    exif = img.metadata
    orientation_key = 'exif:Orientation'

    if exif:
        if orientation_key in exif:
            orientation = exif[orientation_key]
            rotate_values = {
                3: 180,
                6: 270,
                8: 90
            }

            if orientation in rotate_values:
                return rotate_values[orientation]

    return 0


def exif_auto_rotate_image(img):
    """
    Automatically rotate the given image if the EXIF meta data tag
    for orientation indicates that the image is taken with a specific
    orientation. Usually this tag is generated by the digital camera.
    """
    orientation = get_exif_image_rotation(img)
    if orientation != 0:
        img.rotate(orientation)

    return img


def is_png_without_transparency(filename):
    """
    Return True, if the given file is a PNG image file without any transparency
    layer. Usually this means that we could replace the PNG file with a JPG
    file in order to save storage and bandwidth.
    """
    try:
        with WandImage(filename=filename) as img:
            if is_png_image_object(img):
                return not img.alpha_channel
    except NOT_AN_IMAGE_WAND_EXCEPTIONS:
        pass

    return False


def convert_image(src_filename, dst_filename, quality=settings.IMAGE_COMPRESSION_QUALITY):
    """
    Convert the given source image and re-encode it as the given dest. file,
    where the dest. file may be a different image file type. The original image
    is removed. The image is not scaled.
    """
    # convert image
    try:
        with WandImage(filename=src_filename) as img:
            if is_jpeg_image_object(img):
                img.compression_quality = min(img.compression_quality, quality)

            img.strip()
            img.save(filename=dst_filename)

            # remove source if dest. file exists and source and
            # dest. are not the same
            if src_filename != dst_filename and os.path.isfile(dst_filename):
                os.unlink(src_filename)

            return True
    except NOT_AN_IMAGE_WAND_EXCEPTIONS:
        return False


def open_image_for_resize(filename):
    """
    Pre-process the given image for the purpose of generating multiple versions
    based on the given image.
    """
    # open image file
    img = WandImage(filename=filename)

    # auto-rotate image based on EXIF data embedded in the image
    img = exif_auto_rotate_image(img)

    return img


def generate_preview_image(filename, dest_filename):
    """
    Generate preview image from given document file (PDF).
    """
    # build external command
    command = settings.IMAGE_PDF_PREVIEW_COMMAND % {
        'source': filename,
        'dest': dest_filename
    }

    # execute
    p = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    (output, err_output) = p.communicate()
    p.wait()

    # raise exception on error
    if p.returncode != 0:
        # in DEBUG mode, print warning message but silently ignore in
        # any case (in particular in production mode), since if we cannot
        # generate a preview image than we can still use the document in the
        # system, we just don't have a preview image.
        if settings.DEBUG and not settings.TEST:
            sys.stderr.write('Error generating preview image: %s: %s\n' % (filename, err_output))
        return False

    return True


def resize_image_object(
    img,
    dst_filename,
    width,
    height,
    mode='crop',
    valign='center',
    auto_fit=False,
    focal_point=None,
    quality=settings.IMAGE_COMPRESSION_QUALITY,
    optimize=settings.IMAGE_OPTIMIZE
):
    """
    Resize given image object in the same was as resize_image() would; however
    we use the existing input image to perform the resize operation in order
    to avoid loading the same images over and over again.
    """
    # create a new copy of the image, we do not want to modify the original
    # image object we were given...
    img = img.clone()
    try:
        # if the resulting file is a jpg, remove transparency from the image,
        # since this might be a png source with transparency on it...
        _, ext = os.path.splitext(dst_filename)
        if ext not in ['.png', '.gif']:
            img = remove_image_transparency(img)

        # auto fitting:
        if auto_fit:
            img = auto_fit_image_object(img, width, height, settings.IMAGE_FITTING_COLOR)

        # process image based on given mode
        if mode == 'scale':
            # do not upscale!
            w, h = img.size
            if width > w or height > h:
                width = w
                height = h

            # force width and height to be bigger than zero, if scale result of
            # the one dimension is zero (i.e 8000x10 image)
            if width < 1:
                width = 1

            if height < 1:
                height = 1

            # calc. new width and height by fitting it into the
            # desired boundaries
            w, h = get_image_fitting(w, h, width, height)
            img.resize(w, h)
        elif mode == 'crop':
            x, y, w, h = get_image_crop_area(img.width, img.height, width, height, focal_point, valign)
            x = int(x)
            y = int(y)
            w = int(w)
            h = int(h)
            img.crop(x, y, width=w, height=h)
            if width != w or height != h:
                img.resize(width, height)

        # determine image quality. Do not use a higher image quality
        # as the input image. Smaller images may use a lower quality level.
        if is_jpeg_image_object(img):
            img.compression_quality = min(img.compression_quality, quality)

        # save image back to target format
        img.strip()
        img.save(filename=dst_filename)
    finally:
        img.destroy()

    # optimize image
    if optimize:
        optimize_image(dst_filename)


def auto_fit_image_object(img, width, height, bg_color):
    """
    Automatically fit the given input image into a canvas with the given
    background color that satisfies the aspect ratio of the target width
    and height but is just big enough to 'fit' the input image in.
    """
    # invalid target size?
    if width == 0 or height == 0:
        return img

    # colorspace we cannot work with
    if img.colorspace == 'cmyk':
        return img

    # get input image size
    img_w, img_h = img.size

    # aspect ratio of the target size and image size
    ar = float(width) / float(height)
    img_ar = float(img_w) / float(img_h)

    # aspect ratio is already almost perfect?
    if abs(ar - img_ar) < 0.05:
        return img

    # try image width
    w = img_w
    h = int(w / ar)
    x = 0
    y = int( (float(h) - float(img_h)) / 2.0 )

    # if the height is too short, then the other way around must fit...
    if h < img_h:
        h = img_h
        w = int(h * ar)
        x = int( (float(w) - float(img_w)) / 2.0 )
        y = 0

    # create a new image of the resolved target size in the given
    # background color
    result_img = WandImage(width=w, height=h, background=WandColor(bg_color))
    result_img.composite(img, x, y)
    img.destroy()

    return result_img


def is_jpeg_image_object(image):
    """
    Return True, if the given image is compressed using the JPEG compression
    standard.
    """
    return image.format == 'JPEG'


def is_jpeg_image(filename):
    """
    Return True, if the given file is a JPEG image file.
    """
    try:
        with WandImage(filename=filename) as img:
            return is_jpeg_image_object(img)
    except:
        pass

    return False


def is_png_image_object(image):
    """
    Return True, if the given image is compressed using the PNG compression
    standard.
    """
    try:
        return image.format == 'PNG'
    except:
        return False


def is_png_image(filename):
    """
    Return True, if the given file is a PNG image file.
    """
    try:
        with WandImage(filename=filename) as img:
            return is_png_image_object(img)
    except:
        pass

    return False


def get_jpg_image_quality(filename):
    """
    Return the jpeg image quality of the given JPEG file.
    """
    try:
        with WandImage(filename=filename) as img:
            return img.compression_quality
    except:
        pass

    return None


def can_optimize_images():
    """
    Return True, if image optimization for JPEG and PNG files is available
    in terms of being able to execute external optimization scripts.
    """
    def test_executable(command_pattern):
        # build command with --help argument
        try:
            command = command_pattern.split(' ')[0] + ' --help'
        except IndexError:
            return False

        # execute command
        p = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        (output, err_output) = p.communicate()
        p.wait()

        # determine of we were able to run the script at all...
        return p.returncode != 127

    # both need to succeed, jpeg and png
    return (
        test_executable(settings.IMAGE_JPEG_OPT_COMMAND) and
        test_executable(settings.IMAGE_PNG_OPT_COMMAND)
    )


def optimize_image(filename, dst_filename=None):
    """
    Execute the given external application for optimizing the given image file.
    """
    # determine image type and corresponding optimization command
    command_pattern = None

    with WandImage(filename=filename) as img:
        if is_jpeg_image_object(img):
            command_pattern = settings.IMAGE_JPEG_OPT_COMMAND
        elif is_png_image_object(img):
            command_pattern = settings.IMAGE_PNG_OPT_COMMAND

    # ignore if no external command is not defined for the given image format
    if command_pattern is None:
        return False

    # build temp filename for output file
    _, ext = os.path.splitext(filename)
    m = hashlib.sha224()
    m.update(filename)
    temp_filename = m.hexdigest() + ext

    # make sure the dest. file does not exist yet
    if os.path.isfile(temp_filename):
        os.remove(temp_filename)

    # build external command
    out_filename = os.path.join(tempfile.gettempdir(), temp_filename)
    command = command_pattern % {
        'source': filename,
        'dest': out_filename
    }

    # execute
    p = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    (output, err_output) = p.communicate()
    p.wait()

    # raise exception on error
    if p.returncode != 0:
        # in DEBUG mode, print warning message but silently ignore in
        # any case (in particular in production mode), since if we cannot
        # optimise an image than we can still perform everything else...
        if settings.DEBUG and not settings.TEST:
            sys.stderr.write('Error optimizing image: %s: %s\n' % (filename, err_output))
        return False

    if dst_filename is None:
        # replace input image with output image
        os.remove(filename)
        file_move(out_filename, filename)
    else:
        # replace output file
        if os.path.isfile(dst_filename):
            os.remove(dst_filename)
        file_move(out_filename, dst_filename)

    return True


def resize_image(
    filename,
    dst_filename,
    width,
    height,
    mode='crop',
    valign='center',
    auto_fit=False,
    focal_point=None,
    quality=settings.IMAGE_COMPRESSION_QUALITY,
    optimize=settings.IMAGE_OPTIMIZE
):
    """
    Resize given image file to given width and height and store it as a new
    image file under the given destination filename.
    If mode is 'scale', the image is scaled (but not upscaled) but nor cropped.
    If mode is 'crop' (default), the image is cropped only.
    """
    # open image file
    with open_image_for_resize(filename) as img:
        resize_image_object(img, dst_filename, width, height, mode, valign, auto_fit, focal_point, quality, optimize)


def resize_image_if_too_wide(filename):
    """
    Resize given image file if the width is larger than IMG_MAX_WIDTH (settings).
    """
    if settings.IMG_MAX_WIDTH is not None:
        try:
            (width, height) = get_image_size(filename)
            if width > settings.IMG_MAX_WIDTH:
                factor = settings.IMG_MAX_WIDTH / float(width)
                new_width = settings.IMG_MAX_WIDTH
                new_height = int(factor * height)

                if (new_width != 0 and new_height != 0):
                    resize_image(
                        filename,
                        filename,
                        new_width,
                        new_height,
                        'scale',
                        quality=99,
                        optimize=False
                    )
                    return True
        except:
            pass

    return False


def resize_svg_image(
    filename,
    dst_filename,
    width,
    height,
    focal_point=None,
    optimize=True,
    crop=True,
    prefix=None
):
    """
    Scale the given vector image (SVG) to the given width and height and save
    the result as a new vector image as the given dest. filename. Vector
    images, such as SVG do not necessarily need to be resized, however they may
    contain bitmap data which we will scale accordingly. Any vector data and
    viewport information is preserved.

    In addition, we will prefix all id attribute values and internal references
    with a short prefix that is unique to the file. We do this in case we inline
    multiple SVG files into the actual websites and we do not want to have any
    identifiers and/or references colliding.

    Finally, we also remove any style from the SVG, since this may then become
    global to the document when we inline an SVG.
    """
    def _scale_image(data, width, height):
        """
        Scale given image data blog to fit the given width and height.
        """
        # open image data
        try:
            img = WandImage(blob=data)
        except NOT_AN_IMAGE_WAND_EXCEPTIONS:
            # not an image! -> ignore and leave as is
            return None

        # do not upscale!
        w, h = img.size
        if width > w or height > h:
            width = w
            height = h

        if width < 1:
            width = 1

        if height < 1:
            height = 1

        # calc. new width and height by fitting it into the
        # desired boundaries
        w, h = get_image_fitting(w, h, width, height)
        img.resize(w, h)

        # return image blob
        blob = io.BytesIO()
        img.strip()
        img.save(file=blob)
        return blob.getvalue()


    def _match_image(m):
        """
        Process SVG <image> tag. Only deal with base64 embedded image data and
        ignore external references.
        """
        # extract attributes
        attr = {}
        for attrname, value in re.findall(r'(?P<attrname>\w+)="(?P<value>.*?)"', m.group('attr')):
            attr[attrname] = value

        # get image data
        data = attr.get('href', '')
        href = re.match(r'^data:image\/(?P<fmt>\w+);base64,(?P<data>.*?)$', data)
        data = None
        fmt = None
        if href:
            fmt = href.group('fmt')
            try:
                data = base64.b64decode(href.group('data'))
            except TypeError:
                # base64 decoding error! -> ignore and leave as is
                pass

        # scale embedded image down to the max. given width, hegiht is
        # determined by aspect ratio of the image...
        if data is not None:
            data = _scale_image(data, width, height)
            if data is not None:
                data = base64.b64encode(data)
                attr['href'] = 'data:image/%s;base64,%s' % (fmt, data)
                return '<image %s/>' % ' '.join(
                    ['%s="%s"' % (name, value) for name, value in attr.items()]
                )

        # fallback -> leave as is
        return m.group(0)


    def _replace_images(svg):
        """
        Find any replace any references to images.
        """
        return re.sub(r'<image (?P<attr>.*?)(?P<tail>(/>)|(></image>))', _match_image, svg)


    def _get_viewbox(xml):
        """
        Return the viewbox coordinates from the viewBox attribute on the svg tag.
        """
        # parse vieewBox attribute
        viewbox = xml.svg.get('viewBox', '')
        components = re.split(r'[\s,]', viewbox, 4)
        x, y, w, h = (0.0, 0.0, 64.0, 64.0)
        if len(components) == 4:
            try:
                x, y, w, h = [float(c) for c in components]
            except:
                pass

        # do not allow an invalid viewbox, default to square
        if h == 0.0:
            h = 1.0

        return x, y, w, h


    def _set_viewbox(xml, x, y, w, h):
        """
        Set the viewBox within the given SVG xml markup to the new dimensions
        as given.
        """
        # set viewBox
        xml.svg['viewBox'] = '%s %s %s %s' % (
            x, y, w, h
        )

        # rewrite enable-background style (not really used by many browsders,
        # but we want to be consistent)
        style = xml.svg.get('style', '')
        style = re.sub(
            r'enable-background:\s*new\s+([-.,\d]+)\s+([-.,\d]+)\s+([-.,\d]+)\s+([-.,\d]+);?',
            'enable-background:new %s %s %s %s;' % (x, y, w, h),
            style
        )
        xml.svg['style'] = style


    def _normalised(x):
        """
        Return integer of x, if x has no fraction component.
        """
        intx = int(x)
        return intx if intx == x else x


    def _scale_viewbox(xml, width, height):
        """
        Scale the viewBox to the new aspect ratio of the given width and height.
        """
        # get viewBox from current SVG
        x, y, w, h = _get_viewbox(xml)

        # make the target width the same with as the SVG. The target height
        # is adjusted based on the target aspect ratio
        if height == 0:
            height = 1
        ar = float(width) / float(height)
        width = w
        height = width / ar

        # determine new cropping area
        cropx, cropy, cropw, croph = get_image_crop_area(w, h, width, height, focal_point)

        # adjust to new (cropped) viewBox
        cropx += x
        cropy += y

        # normalise values to int if we do not have a fraction
        cropx = _normalised(cropx)
        cropy = _normalised(cropy)
        cropw = _normalised(cropw)
        croph = _normalised(croph)

        # apply new viewbox
        _set_viewbox(xml, cropx, cropy, cropw, croph)


    def _inline_style(xml):
        """
        Take embedded style and inline all style information.
        """
        # extract style
        style = ''
        for tag in xml.svg.find_all('style'):
            style += '\n'.join(tag.contents) + '\n'
            tag.decompose()

        # inline all collected style
        inline_style(xml.svg, parse_style(style))
        remove_attr(xml.svg, ['class'])


    def _get_prefix(filename, prefix):
        """
        Return a unique prefix to be used, if the given prefix is None. Since
        the prefix may be used as unique identifiers, they must start with
        a letter and cannot start with a number.
        """
        # generate hash based on filename
        if prefix is None:
            m = hashlib.sha224()
            m.update(filename)
            prefix = m.hexdigest()[:6]

        # if the first character is a number, it becomes a letter
        # between a-f depending on the number.
        if prefix:
            try:
                n = int(prefix[0])
                prefix = ['a', 'b', 'c', 'd', 'e', 'f'][n % 6] + prefix[1:]
            except ValueError:
                pass

        if prefix != '' and not prefix.endswith('_'):
            prefix += '_'

        return prefix


    def _prefix_ids(node, prefix):
        prefix_ids(node, prefix)


    # open svg file as text and replace embedded bitmap data
    markup = file_get_contents(filename)
    markup = _replace_images(markup)

    # load xml
    if optimize or crop:
        xml = BeautifulSoup(markup, 'xml')
    else:
        xml = None

    # is SVG?
    if xml and xml.svg:
        # crop
        if crop:
            _scale_viewbox(xml, width, height)

        if optimize:
            _inline_style(xml)
            _prefix = _get_prefix(dst_filename, prefix)
            _prefix_ids(xml, _prefix)
            if _prefix:
                xml.svg['data-prefix'] = _prefix[:-1]

        # render xml out
        if xml:
            markup = unicode(xml)

    # write output to target filename
    file_put_contents(dst_filename, markup)


def get_colorized_svg_image(filename, layers):
    """
    Open the given svg file and colorise all given layers (by id) to the given
    colour values. The given layers argument represents a dictionary that maps
    any given layer to the new fill colour, which is given as a hex-value,
    like #rrggbb.
    """
    # load xml (svg)
    xml = BeautifulSoup(open(filename), 'xml')

    # determine layer prefix (if any)
    prefix = xml.svg.get('data-prefix', '')
    if prefix != '':
        prefix += '_'

    # find all layers we need to colorise...
    for layer_id, instructions in layers.items():
        el = xml.find(id='%s%s' % (prefix, layer_id))
        if el is None:
            continue

        # assume a list of instructions
        if not isinstance(instructions, list):
            instructions = [instructions]

        style = parse_inline_style(el.get('style', ''))
        for instruction in instructions:
            # split attr:value
            instr = instruction.strip()
            p = instr.split(':')
            if len(p) == 1:
                attr = 'fill'
                value = instr
            elif len(p) == 2:
                attr = p[0]
                value = p[1]
            else:
                attr = None

            # skip instructions that we do not understand
            if attr is None:
                continue

            # skip attributes what we do not support
            if attr not in SUPPORTED_SVG_STYLE_OVERWRITES:
                continue

            # remove attribute if exists, for example 'fill' might be expressed
            # as an attribute or inline style. We will write this as inline
            # style, therefore we remove the corresponding attribute if it
            # exists...
            del el[attr]

            # if the value is hexadecimal, append a # to encode the correct
            # colour information if it is missing.
            if not value.startswith('#') and re.match(r'^[0-9a-fA-F]+$', value):
                value = '#' + value

            # add to style
            style[attr] = value

        # update element's inline style
        el['style'] = encode_inline_style(style)

    # return changed content as xml. We should be safe from any code injection
    # here, since bs4 will re-build and escape all style attributes...
    return unicode(xml)


def get_shapes_from_svg_image(filename, prefix=None):
    """
    Return a list of shapes with an identifier from the given image, which we
    assume is an SVG image.
    """
    if not filename:
        return []

    # parse xml
    xml = BeautifulSoup(open(filename), 'xml')
    if not xml.svg:
        return []

    # determine layer svg prefix (if any)
    svg_prefix = xml.svg.get('data-prefix', '')
    if svg_prefix != '':
        svg_prefix += '_'

    # walk all nodes and extract identifiers
    identifiers = []
    def _walk(node):
        if isinstance(node, element.NavigableString):
            return

        # exact id attribute (remove svg prefix)
        if node.name != 'svg':
            try:
                identifiers.append(node['id'].replace(svg_prefix, ''))
            except KeyError:
                pass

        # process child nodes
        for child in node.children:
            _walk(child)

    # collect all identifiers
    _walk(xml)

    # filter by prefix
    if prefix:
        identifiers = filter(lambda x: x.startswith(prefix), identifiers)

    return identifiers
