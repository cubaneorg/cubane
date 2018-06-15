# coding=UTF-8
#
# Convert HTML into docx.
# Implementation based on https://github.com/evidenceprime/html-docx-js
# Copyright (c) 2015 Evidence Prime, Inc.
# MIT License
#
from __future__ import unicode_literals
from django.core.files.temp import NamedTemporaryFile
from cubane.media.models import Media
from cubane.lib.image import get_ext, NOT_AN_IMAGE_WAND_EXCEPTIONS
from wand.image import Image as WandImage
import zipfile
import base64
import re
import requests
import urlparse
import os


def twips_to_pixels(twips):
    """
    Return the given amount of twips as pixels.
    """
    return int(float(twips) / 20.0)


def cm_to_twips(cm):
    """
    Return the given amount of cm in twips units.
    """
    return cm * 566.9291338583


def html_to_docx_content(*args, **kwargs):
    """
    Generate docx file content rather than a file handle.
    """
    with html_to_docx(*args, **kwargs) as f:
        return f.read()


def html_to_docx(
    html_content,
    doc_width=11907,
    doc_height=16839,
    m_top=1440,
    m_right=1440,
    m_bottom=1440,
    m_left=1440,
    m_header=720,
    m_footer=720,
    m_gutter=0,
    encoding='utf-8'):
    """
    Returns a file handle to a file that represents a docx file as a result
    of converting the given html document to a docx file. This approach is using
    the altChunk markup as part of the open xml word processing standard.
    """
    f = NamedTemporaryFile()
    zf = zipfile.ZipFile(f, mode='w', compression=zipfile.ZIP_DEFLATED)
    max_image_width = twips_to_pixels(doc_width - m_left - m_right - m_gutter)

    # rewrite all image references
    images = []
    def repl(m):
        img_ref = m.group('img_ref')
        pk = _get_img_arg(img_ref, 'data-media-id')
        src = _get_img_arg(img_ref, 'src', '')
        alt = _get_img_arg(img_ref, 'alt', '')
        width = _get_img_arg(img_ref, 'width')
        height = _get_img_arg(img_ref, 'height')

        if pk:
            media = _get_media_by_pk(pk)
            image = _image_from_media(media, width, height)
        elif src:
            image = _image_from_url(src, width, height)
        else:
            image = None

        if image:
            if image.get('width') > max_image_width:
                ar = float(image.get('width')) / float(image.get('height'))
                image['width'] = max_image_width
                image['height'] = int(image.get('width') / ar)

            images.append(image)
            return '<img width="%s" height="%s" src="%s" alt="%s">' % (
                image.get('width'),
                image.get('height'),
                image.get('content_location'),
                alt if alt else ''
            )
        else:
            return ''
    html_content = re.sub(r'<img(?P<img_ref>.*?)\/?>', repl, html_content)

    def zipwrite(filename, content):
        zf.writestr(filename, content.encode(encoding))

    zipwrite('_rels/.rels', _RELS)
    zipwrite('[Content_Types].xml', _CONTENT_TYPES)
    zipwrite('word/_rels/document.xml.rels', _DOCUMENT_XML_RELS)
    zipwrite('word/document.xml', _DOCUMENT_XML % {
        'doc_width': doc_width,
        'doc_height': doc_height,
        'm_top': m_top,
        'm_right': m_right,
        'm_bottom': m_bottom,
        'm_left': m_left,
        'm_header': m_header,
        'm_footer': m_footer,
        'm_gutter': m_gutter
    })
    zipwrite('word/afchunk.mht', _AFCHUNK_MHT_TEMPLATE % {
        'encoding': encoding,
        'html': re.sub(r'=', '=3D', html_content),
        'content_parts': '\n'.join([
            _CONTENT_PART_TEMPLATE % image
        for image in images])
    })

    # close and reset file
    zf.close()
    f.seek(0)
    return f


def _get_img_arg(img_ref, name, default=None):
    """
    Return the attribute value of the attribute of given name from the given
    image reference (html) or return the given default value instead.
    """
    if img_ref:
        m = re.search('%s="(?P<v>.*?)"' % name, img_ref)
        if m:
            return m.group('v')
    return default


def _get_media_by_pk(pk):
    """
    Return media item by given pk or None.
    """
    try:
        return Media.objects.get(pk=pk)
    except Media.DoesNotExist:
        return None


def _parse_int(x, default=None):
    """
    Parse given integer value x or return given default value.
    """
    if x:
        try:
            return int(x)
        except ValueError:
            pass
    return default


def _image(src, ext, content, img_width, img_height):
    """
    Create image meta data structure.
    """
    img_width = _parse_int(img_width)
    img_height = _parse_int(img_height)

    if not img_width or not img_height:
        try:
            with WandImage(blob=content) as img:
                org_width = img.width
                org_height = img.height
                ar = float(org_width) / float(org_height)

                if not img_width:
                    if img_height:
                        img_width = int(ar * float(img_height))
                    else:
                        img_width = org_width

                if not img_height:
                    if img_width:
                        img_height = int(float(img_width) / ar)
                    else:
                        img_height = org_height
        except NOT_AN_IMAGE_WAND_EXCEPTIONS:
            pass

    return {
        'content_type': 'image/%s' % ext,
        'content_encoding': 'base64',
        'content_location': src,
        'encoded_content': base64.b64encode(content),
        'width': img_width,
        'height': img_height
    }


def _image_from_media(media, width, height):
    """
    Return image meta data from given media object.
    """
    src = 'file:///C:/fake/%s' % media.filename
    ext = get_ext(media.filename)
    with open(media.original_path, 'rb') as f:
        content = f.read()

    return _image(src, ext, content, width, height)


def _image_from_url(url, width, height):
    """
    Return image meta information from given (external) image url.
    """
    # download content from url
    content = requests.get(url, timeout=1000)
    if content == None: return None
    if content.status_code != 200: return None

    # generate filename based on given url
    url_parts = urlparse.urlparse(url)
    path = url_parts.path
    filename = os.path.basename(path)
    ext = get_ext(filename)
    src = 'file:///C:/fake/%s' % filename

    return _image(src, ext, content.content, width, height)


_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship
      Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
      Target="/word/document.xml" Id="R09c83fafc067488e" />
</Relationships>"""

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType=
    "application/vnd.openxmlformats-package.relationships+xml" />
  <Override PartName="/word/document.xml" ContentType=
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/afchunk.mht" ContentType="message/rfc822"/>
</Types>"""

_DOCUMENT_XML_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/aFChunk"
    Target="/word/afchunk.mht" Id="htmlChunk" />
</Relationships>"""

_DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document
  xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:ns6="http://schemas.openxmlformats.org/schemaLibrary/2006/main"
  xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"
  xmlns:ns8="http://schemas.openxmlformats.org/drawingml/2006/chartDrawing"
  xmlns:dgm="http://schemas.openxmlformats.org/drawingml/2006/diagram"
  xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
  xmlns:ns11="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
  xmlns:dsp="http://schemas.microsoft.com/office/drawing/2008/diagram"
  xmlns:ns13="urn:schemas-microsoft-com:office:excel"
  xmlns:o="urn:schemas-microsoft-com:office:office"
  xmlns:v="urn:schemas-microsoft-com:vml"
  xmlns:w10="urn:schemas-microsoft-com:office:word"
  xmlns:ns17="urn:schemas-microsoft-com:office:powerpoint"
  xmlns:odx="http://opendope.org/xpaths"
  xmlns:odc="http://opendope.org/conditions"
  xmlns:odq="http://opendope.org/questions"
  xmlns:odi="http://opendope.org/components"
  xmlns:odgm="http://opendope.org/SmartArt/DataHierarchy"
  xmlns:ns24="http://schemas.openxmlformats.org/officeDocument/2006/bibliography"
  xmlns:ns25="http://schemas.openxmlformats.org/drawingml/2006/compatibility"
  xmlns:ns26="http://schemas.openxmlformats.org/drawingml/2006/lockedCanvas">
  <w:body>
    <w:altChunk r:id="htmlChunk" />
    <w:sectPr>
      <w:pgSz w:w="%(doc_width)s" w:h="%(doc_height)s" w:orient="portrait" />
      <w:pgMar w:top="%(m_top)s"
               w:right="%(m_right)s"
               w:bottom="%(m_bottom)s"
               w:left="%(m_left)s"
               w:header="%(m_header)s"
               w:footer="%(m_footer)s"
               w:gutter="%(m_gutter)s"/>
    </w:sectPr>
  </w:body>
</w:document>"""

_AFCHUNK_MHT_TEMPLATE = """MIME-Version: 1.0
Content-Type: multipart/related;
    type="text/html";
    boundary="----=mhtDocumentPart"


------=mhtDocumentPart
Content-Type: text/html;
    charset="%(encoding)s"
Content-Transfer-Encoding: quoted-printable
Content-Location: file:///C:/fake/document.html

%(html)s

%(content_parts)s

------=mhtDocumentPart--"""

_CONTENT_PART_TEMPLATE = """------=mhtDocumentPart
Content-Type: %(content_type)s
Content-Transfer-Encoding: %(content_encoding)s
Content-Location: %(content_location)s

%(encoded_content)s"""