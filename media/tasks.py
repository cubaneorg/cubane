# coding=UTF-8
from __future__ import unicode_literals
from cubane.tasks import Task
from cubane.media.models import Media
from cubane.lib.mail import send_exception_email


class MediaTask(Task):
    def run(self):
        """
        Process blank media assets.
        """
        i = 1
        blank_media = self.get_blank_media()
        self.report_start(len(blank_media))
        for i, media in enumerate(blank_media, start=1):
            # report status
            filename = media.filename
            if not filename:
                filename = media.external_url
            self.report_status(i, 'Processing media file: <em>%s</em>' % filename)

            # download from external source if we do not have the
            # original image yet
            if not media.original_exists:
                media.download_from_external_source()

            # generate multiple versions
            try:
                media.generate_images()
                media.is_blank = False
                media.save()
            except:
                send_exception_email()


    def get_blank_media(self):
        """
        Return the next blank media asset.
        """
        return list(Media.objects.filter(is_blank=True).order_by('-created_on'))