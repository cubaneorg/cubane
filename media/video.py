# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.utils.text import slugify
import re


class VideoTypeBase(object):
    name = ''


    def get_id_from_url(self, url):
        """
        Return the id to the video.
        """
        return ''


    def get_url_from_id(self, video_id):
        """
        Return the full URL to the video.
        """
        return ''


    def get_embed_html(self, video_id):
        """
        Return the embed html to the video.
        """
        return ''


    def get_thumbnail_url(self, video_id):
        """
        Return the full URL to the video thumbnail.
        """
        return ''


class Youtube(VideoTypeBase):
    name = 'YouTube'


    def get_id_from_url(self, url):
        """
        Return the id to the youtube video.
        """
        if url:
            # share link
            m = re.match(r'^(http://|https://|//|)youtu\.be/([-a-zA-z0-9]+)', url)
            if m:
                return m.group(2)

            # youtube page link
            m = re.match(r'^(http://|https://|//|)(www\.|)youtube\.com/watch\?v=([-a-zA-z0-9]+)', url)
            if m:
                return m.group(3)

            # embed video
            m = re.match(r'^(http://|https://|//|)(www\.|)youtube\.com/embed/([-a-zA-z0-9]+)', url)
            if m:
                return m.group(3)

        return url


    def get_url_from_id(self, video_id):
        """
        Return the full URL to the youtube video.
        """
        if video_id:
            return 'https://www.youtube.com/watch?v=%s' % video_id
        return ''


    def get_embed_html(self, video_id, width=640, height=480):
        """
        Return the embed html to the youtube video.
        """
        if video_id:
            return '<iframe width="%s" height="%s" src="https://www.youtube.com/embed/%s?rel=0" frameborder="0" gesture="media" allowfullscreen></iframe>' % (width, height, video_id)
        return ''


    def get_thumbnail_url(self, video_id):
        """
        Return the full URL to the primary youtube video thumbnail or None.
        """
        if video_id:
            return 'https://img.youtube.com/vi/%s/0.jpg' % video_id
        return ''


_CUBANE_VIDEO_TYPES = [
    Youtube(),
]


def get_default_video_type():
    """
    Return the default video type.
    """
    return slugify(_CUBANE_VIDEO_TYPES[0].name)


def get_video_type_choices():
    """
    Get video type choices filter by settings
    """
    choices = []
    for typ in _CUBANE_VIDEO_TYPES:
        slug = slugify(typ.name)
        if slug in settings.CUBANE_VIDEO_TYPES:
            choices.append((slug, typ.name))
    return choices


def get_video_type(identifier):
    for video_type in _CUBANE_VIDEO_TYPES:
        if slugify(video_type.name) == identifier:
            return video_type
    return VideoTypeBase()
