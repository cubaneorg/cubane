# coding=UTF-8
from __future__ import unicode_literals
from django.db.models import Max
from django.contrib.contenttypes.models import ContentType
from cubane.lib.file import get_caption_from_filename
from cubane.media.models import Media, MediaFolder
from cubane.cms.models import MediaGallery
from cubane.tasks import TaskRunner
import os.path
import requests
import urlparse


class MediaScriptingMixin(object):
    def delete_content(self):
        """
        Override: Delete all media content as well.
        """
        super(MediaScriptingMixin, self).delete_content()
        self.delete_media_content()


    def delete_media_content(self):
        """
        Delete media content.
        """
        for m in Media.objects.all():
            m.delete()


    def create_media_from_file(self, local_filepath, caption, filename=None, folder=None, generate_images=True):
        """
        Create a new media item within the media library by downloading content
        from the given url.
        """
        # read media from local disk
        f = open(local_filepath, 'rb')
        content = f.read()
        f.close()

        # if no filename is given, determine filename from input path
        if not filename:
            filename = os.path.basename(local_filepath)

        # create media with given content
        return self.create_media(content, caption, filename, folder, generate_images=generate_images)


    def create_media_from_url(self, url, caption=None, filename=None, folder=None, generate_images=True):
        """
        Create a new media item within the media library by downloading content
        from the given url.
        """
        # download content from url
        content = requests.get(url, timeout=1000)
        if content == None: return None
        if content.status_code != 200: return None

        # generate filename based on given url
        if filename == None:
            url_parts = urlparse.urlparse(url)
            path = url_parts.path
            filename = os.path.basename(path)

        # create media with given content
        return self.create_media(content.content, caption, filename, folder, generate_images=generate_images)


    def create_media_folder(self, title, parent=None, if_not_exists=True):
        """
        Create a new media folder with given name.
        """
        folder = None
        if if_not_exists:
            try:
                folder = MediaFolder.objects.get(title=title, parent=parent)
            except MediaFolder.DoesNotExist:
                pass

        if not folder:
            folder = MediaFolder()
            folder.title = title
            folder.parent = parent
            folder.save()

        return folder


    def create_media(self, content, caption, filename, folder=None, generate_images=True):
        """
        Create a new media item within the media library based on the given
        content data.
        """
        media = self.create_media_object(caption, filename, folder)

        if media:
            media.upload_from_content(content, filename, generate_images=generate_images)

        return media


    def create_media_object(self, caption, filename, folder=None):
        """
        Create a new media item object within the media library based on the
        given meta data. This will simply create the meta data but will not
        upload or store any actual image/document data and it is assumed that
        this happens outside of the image media object creation.
        """
        # generate caption based on filename if provided
        if not caption and filename:
            caption = get_caption_from_filename(filename)

        media = Media()
        media.caption = caption
        media.filename = filename

        if folder:
            media.parent = folder

        media.save()

        return media


    def create_blank_external_media(self, url, filename=None, caption=None, folder=None):
        """
        Create a new (blank) media item with the given external url and
        optionally the given parent folder.
        """
        media = Media()
        media.is_blank = True
        media.external_url = url

        # generate filename based on given url
        url_parts = urlparse.urlparse(url)
        path = url_parts.path

        # filename
        if filename:
            media.filename = filename
        else:
            media.filename = os.path.basename(path)

        # generate caption from filename
        if caption:
            media.caption = caption
        else:
            media.caption = get_caption_from_filename(media.filename)

        # folder
        if folder:
            media.folder = folder

        media.save()

        # notify task runner that there is something to do
        TaskRunner.notify()

        return media


    def add_media_to_gallery(self, page, images):
        """
        Add list of images to the gallery of the given cms page.
        """
        if not isinstance(images, list):
            images = [images]

        # get content type of page object
        content_type = ContentType.objects.get_for_model(page.__class__)

        # get last seq.
        r = page.gallery_images.aggregate(Max('seq'))
        seq = r.get('seq__max')
        if seq == None: seq = 0
        for i, image in enumerate(images, start=seq + 1):
            mg = MediaGallery()
            mg.media = image
            mg.content_type = content_type
            mg.target_id = page.pk
            mg.seq = i
            mg.save()


    def clear_media_gallery(self, page):
        """
        Remove all media from the gallery for the given page.
        """
        [m.delete() for m in page.gallery_images.all()]