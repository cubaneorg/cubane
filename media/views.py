# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import (
    HttpResponse,
    Http404,
    FileResponse,
    HttpResponseNotModified
)
from django.views.static import was_modified_since
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.utils.http import http_date
from django.core.files.temp import NamedTemporaryFile
from django.template.defaultfilters import slugify
from django.contrib import messages
from django.core.cache import cache
from cubane.media.models import Media, MediaFolder
from cubane.media.forms import MediaForm, MediaFolderForm, MultiMediaForm
from cubane.media.forms import MediaShareForm
from cubane.media.templatetags.media_tags import render_image
from cubane.cms.models import MediaGallery
from cubane.views import ModelView, view_url
from cubane.backend.views import BackendSection, Progress
from cubane.lib.request import request_int
from cubane.lib.image import get_colorized_svg_image
from cubane.lib.url import make_absolute_url
from cubane.lib.libjson import to_json_response
from cubane.lib.args import get_pks
from cubane.tasks import TaskRunner
import os
import re
import mimetypes
import stat
import zipfile
import datetime
import copy


def load_media_gallery(gallery_images):
    """
    Load list of gallery images as form initial.
    """
    return [
        x.media for x in gallery_images.select_related('media').order_by('seq')
    ]


def save_media_gallery(request, instance, media):
    """
    Save the given list of media items (media) to the given instance.
    """
    if media is None:
        return

    content_type = ContentType.objects.get_for_model(instance.__class__)

    # delete all existing assignments
    assignments = MediaGallery.objects.filter(
        content_type=content_type,
        target_id=instance.pk
    ).all()
    for assignment in assignments:
        if request:
            request.changelog.delete(assignment)
        assignment.delete()

    if media:
        # create new assignments
        for i, m in enumerate(media, start=1):
            mg = MediaGallery()
            mg.media = m
            mg.content_type = content_type
            mg.target_id = instance.pk
            mg.seq = i
            mg.save()

            if request:
                request.changelog.create(mg)


def get_img_tags(content):
    """
    Return a list of media identifiers that are references within the given
    content.
    """
    if content is None:
        return []

    def get_img_tags_by_prefix(prefix, content):
        return re.findall(r'<img.*?data-%s-media-id="(\d+)".*?>' % prefix, content)

    return (
        get_img_tags_by_prefix('cubane', content) +
        get_img_tags_by_prefix('ikit', content)
    )


def load_images_for_content(content, images=None):
    """
    Returns a list of images that are used within the given content. Image data
    is loading from the given list of image data or, if not already present add
    to the list of existing images.
    """
    # determine image ids used within given content
    ids = get_img_tags(content)

    # determine image ids that we don't have meta data for yet
    unknown_ids = []
    for _id in ids:
        if images is None or _id not in images:
            unknown_ids.append(_id)

    # load additional meta data from database
    if len(unknown_ids) > 0:
        additional_images = Media.objects.filter(is_image=True).in_bulk(unknown_ids)
        if images is None:
            images = {}
        images.update(additional_images)

    return images


class FolderView(ModelView):
    """
    View for editing media folders.
    """
    template_path = 'cubane/media/'
    namespace = 'cubane.cms.media-folders'
    model = MediaFolder
    folder_model = MediaFolder
    form = MediaFolderForm


    def _get_objects(self, request):
        return self.model.objects.all()


    def _get_folders(self, request, parent):
        folders = self.folder_model.objects.all()

        if parent:
            folders = folders.filter(parent=parent)

        return folders


class MediaView(ModelView):
    """
    Base class for editing media assets.
    """
    template_path = 'cubane/media/'
    model = Media
    folder_model = MediaFolder
    form = MediaForm


    PATTERNS = [
        view_url(r'download/', 'download', name='download')
    ]

    LISTING_ACTIONS = [
        ('Download', 'download', 'multiple')
    ]

    SHORTCUT_ACTIONS = [
        'download'
    ]


    def __init__(self, *args, **kwargs):
        self.patterns = copy.copy(self.PATTERNS)
        self.listing_actions = copy.copy(self.LISTING_ACTIONS)
        self.shortcut_actions = copy.copy(self.SHORTCUT_ACTIONS)

        # auto fit
        self.exclude_columns = []
        if not settings.IMAGE_FITTING_ENABLED or not settings.IMAGE_FITTING_SHAPES:
            self.exclude_columns.append('auto_fit')

        # provide media sharing if CMS is used
        if 'cubane.cms' in settings.INSTALLED_APPS:
            self.patterns.append(
                view_url(r'share/', 'share', name='share')
            )
            self.listing_actions.append(
                ('[/Share]', 'share', 'single')
            )
            self.shortcut_actions.append('share')
        else:
            self.exclude_columns.append('share_enabled')

        super(MediaView, self).__init__(*args, **kwargs)


    def before_save(self, request, cleaned_data, instance, edit):
        """
        Detect changes of media instance regarding image-relevant properties,
        such as auto-fit or compression quality.
        """
        auto_fit_changed = settings.IMAGE_FITTING_ENABLED and settings.IMAGE_FITTING_SHAPES and instance.auto_fit != cleaned_data.get('auto_fit')
        quality_changed = instance.jpeg_quality != cleaned_data.get('jpeg_quality')
        focal_point_changed = instance.focal_x != cleaned_data.get('focal_x') or instance.focal_y != cleaned_data.get('focal_y')

        if auto_fit_changed or quality_changed or focal_point_changed:
            instance._image_config_changed = True
        else:
            instance._image_config_changed = False


    def after_save(self, request, cleaned_data, instance, edit):
        changed = False
        if 'media' in request.FILES:
            instance.upload_from_stream(request.FILES['media'], request=request)
            changed = True
        elif instance._image_config_changed:
            # edit -> if we changed image-relevant configuration then we need
            # to re-generate image shapes...
            instance.upload(request=request)
            changed = True

        # image edited -> increase version number
        if edit and changed:
            instance.increase_version()


    def before_bulk_save(self, request, cleaned_data, instance, edit):
        """
        Called before the given model instance is saved as part of bulk editing.
        """
        self.before_save(request, cleaned_data, instance, edit)


    def after_bulk_save(self, request, cleaned_data, instance, edit):
        """
        Called after the given model instance is saved as part of bulk editing.
        """
        self.after_save(request, cleaned_data, instance, edit)


    def _get_folders(self, request, parent):
        folders = self.folder_model.objects.all()

        if parent:
            folders = folders.filter(parent=parent)

        return folders


    def _folder_filter(self, request, objects, folder_pks):
        if folder_pks:
            q = Q()
            for pk in folder_pks:
                q |= Q(parent_id=pk) | \
                     Q(parent__parent_id=pk) | \
                     Q(parent__parent__parent_id=pk) | \
                     Q(parent__parent__parent__parent_id=pk) | \
                     Q(parent__parent__parent__parent__parent_id=pk) | \
                     Q(parent__parent__parent__parent__parent__parent_id=pk)
            objects = objects.filter(q)
        return objects


    def after(self, request, handler, response):
        if isinstance(response, dict):
            response['multi_url'] = self.namespace + '.create_multi'
        return super(MediaView, self).after(request, handler, response)


    @property
    def listing_with_image(self):
        return True


    def _create_edit(self, request, pk=None, edit=False, duplicate=False):
        if not edit and len(request.FILES.getlist('media')) > 1:
            # cancel?
            if request.POST.get('cubane_form_cancel', '0') == '1':
                return self._redirect(request, 'index')

            kwargs = {}

            # create form
            if request.method == 'POST':
                form = MultiMediaForm(request.POST, request.FILES, **kwargs)
            else:
                form = MultiMediaForm(**kwargs)

            form.configure(request)

            # validate form
            if request.method == 'POST' and form.is_valid():
                # update properties in model instance
                d = form.cleaned_data

                if 'media' in request.FILES:
                    file_list = request.FILES.getlist('media')
                    n = 0
                    Progress.start(request, len(file_list))
                    first_instance = None
                    for f in file_list:
                        instance = self.model()
                        instance.parent = d.get('parent')

                        if first_instance is None:
                            first_instance = instance

                        # auto fit
                        if settings.IMAGE_FITTING_ENABLED and settings.IMAGE_FITTING_SHAPES:
                            instance.auto_fit = d.get('auto_fit')

                        # jpeg quality
                        instance.jpeg_quality = d.get('jpeg_quality')

                        # save
                        instance.save()
                        instance.upload_save_from_stream(f, request=request)
                        n += 1

                        request.changelog.create(instance)

                        # notify task runner to do the job
                        if instance.is_blank:
                            TaskRunner.notify()

                        # report progress made
                        Progress.set_progress(request, n)

                    # commit changes
                    message = '<em>%d</em> %s created.' % (n, self.model._meta.verbose_name_plural)
                    change = request.changelog.commit(
                        message,
                        model=self.model
                    )

                    Progress.stop(request)

                    # ajax operation, simply return success and message
                    # information
                    if request.is_ajax():
                        return to_json_response({
                            'success': True,
                            'message': message,
                            'change': change,
                            'next': self._get_url(request, 'index', namespace=True),
                            'instance_id': first_instance.pk,
                            'instance_title': unicode(first_instance),
                        })

                # dialog or screen?
                if request.GET.get('create', 'false') == 'true':
                    return {
                        'dialog_created_id': instance.pk,
                        'dialog_created_title': unicode(instance)
                    }
                else:
                    return self._redirect(request, 'index')
            elif request.is_ajax():
                return to_json_response({
                    'success': False,
                    'errors': form.errors
                })

            context = {
                'form': form,
                'permissions': {
                    'create': self.user_has_permission(request.user, 'add'),
                    'view': self.user_has_permission(request.user, 'view'),
                    'edit': self.user_has_permission(request.user, 'edit')
                },
                'verbose_name': 'Multiple Media'
            }
        else:
            if request.method == 'POST':
                Progress.start(request, 1)

            context = super(MediaView, self)._create_edit(request, pk, edit, duplicate)

        if isinstance(context, dict):
            context['is_images'] = isinstance(self, ImageView)

        return context


    def download(self, request):
        """
        Download individual or multiple media assets. Multiple media assets are
        zipped.
        """
        # get pks
        pks = get_pks(request.GET)

        # get list of media
        media = Media.objects.filter(pk__in=pks).order_by('caption')
        n_media = media.count()

        # no media?
        if n_media == 0:
            raise Http404('Unable to export media assets for empty list of media objects.')

        # single media item?
        if n_media == 1:
            item = media.first()
            response = FileResponse(open(item.original_path, 'rb'))
            response['Content-Disposition'] = 'attachment; filename="%s"' % item.filename
            return response

        # multiple assets -> create zip file
        f = NamedTemporaryFile()
        zf = zipfile.ZipFile(f, 'w')

        # attach original files to zip, handle duplicated filenames
        filenames = {}
        for item in media:
            # determine unique filename
            filename = item.filename
            if filename not in filenames:
                filenames[filename] = 1
            else:
                fn = filename
                base, ext = os.path.splitext(filename)
                while fn in filenames:
                    filenames[fn] += 1
                    fn = '%s-%d%s' % (base, filenames[fn], ext)
                filename = fn
                filenames[filename] = 1

            # attach file to zip...
            zf.write(item.original_path, filename)
        zf.close()
        f.seek(0)

        # determine site name from settings (CMS)
        if 'cubane.cms' in settings.INSTALLED_APPS:
            from cubane.cms.views import get_cms_settings
            site_name = get_cms_settings().name
            if site_name is None: site_name = ''
            site_name = slugify(site_name)
            if site_name != '': site_name += '_'
        else:
            site_name = ''

        # generate download filename for zip file
        today = datetime.date.today()
        filename = '{0}media_{1:02d}_{2:02d}_{3:04d}.zip'.format(
            site_name,
            today.day,
            today.month,
            today.year
        )

        # serve file
        response = FileResponse(f)
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


    def share(self, request):
        # get media asset
        pk = request.GET.get('pk')
        media = get_object_or_404(Media, pk=pk)

        # create form
        if request.method == 'POST':
            form = MediaShareForm(request.POST)
        else:
            share_filename = media.share_filename
            if not share_filename:
                share_filename = media.filename

            form = MediaShareForm(initial={
                'share_enabled': media.share_enabled,
                'share_filename': share_filename
            })

        # configure form
        form.configure(request, instance=media, edit=True)

        # validate form
        if request.method == 'POST' and form.is_valid():
            d = form.cleaned_data

            if media.share_enabled != d.get('share_enabled') or media.share_filename != d.get('share_filename'):
                previous_instance = request.changelog.get_changes(media)

                media.share_enabled = d.get('share_enabled')
                media.share_filename = d.get('share_filename')
                media.save()

                request.changelog.edit(media, previous_instance)
                request.changelog.commit(
                    'File sharing %s: <em>%s</em>.' % (
                        'enabled' if media.share_enabled else 'disabled',
                        media.caption
                    ),
                    media,
                    flash=True
                )

            return self._redirect(request, 'index')

        return {
            'form': form,
            'media': media,
            'base_url': make_absolute_url(settings.MEDIA_DOWNLOAD_URL)
        }


class ImageView(MediaView):
    """
    Edit CMS images.
    """
    namespace = 'cubane.cms.images'
    context = { 'is_image': True }


    def before(self, request, handler):
        request.is_image = True


    def _get_objects(self, request):
        return Media.objects.select_related('parent').filter(is_image=True)


class DocumentView(MediaView):
    """
    Edit CMS documents.
    """
    namespace = 'cubane.cms.documents'
    context = { 'is_image': False }
    exclude_columns = ['size', 'image_size']


    PATTERNS = [
        view_url(r'download/', 'download', name='download'),
        view_url(r'preview/', 'preview', name='preview')
    ]


    def before(self, request, handler):
        request.is_image = False


    def _get_objects(self, request):
        return self.model.objects.select_related('parent').filter(is_image=False)


    def preview(self, request):
        return {
            'url': request.GET.get('url')
        }


class ProcessingMediaView(MediaView):
    """
    Base class for editing media assets.
    """
    template_path = 'cubane/media/'
    namespace = 'cubane.cms.processing_media'
    model = Media
    view_identifier = 'processing-media'
    listing_with_image = True
    grid_view = False
    can_add = False
    can_edit = False


    def _get_objects(self, request):
        return self.model.objects.filter(is_blank=True)


class ImageBackendSection(BackendSection):
    """
    Backend section for editing image content.
    """
    title = 'Images'
    slug = 'images'
    view = ImageView()


class DocumentBackendSection(BackendSection):
    """
    Backend section for editing document content.
    """
    title = 'Documents'
    slug = 'documents'
    view = DocumentView()


class FolderBackendSection(BackendSection):
    """
    Backend section for editing folders.
    """
    title = 'Folders'
    slug = 'media-folders'
    view = FolderView()


class ProcessingMediaSection(BackendSection):
    """
    Backend section for viewing media assets that are being processed right now.
    """
    title = 'Processing'
    slug = 'processing'
    view = ProcessingMediaView()


class MediaBackendSection(BackendSection):
    """
    Backend section for editing general media content such as images and
    documents.
    """
    title = 'Media'
    sections = [
        ImageBackendSection(),
        DocumentBackendSection(),
        FolderBackendSection()
    ] + (
        [ProcessingMediaSection()] if TaskRunner.is_available() else []
    )


def serve_media_api(request, media, shape=None):
    """
    Serve the given media asset with given shape (or original shape).
    """
    # get reference to underlying media file
    if media.is_blank or shape is None or size is None:
        filepath = media.original_path
    else:
        filepath = media.get_image_path(size, shape)

    # 404 if file does not exist
    if not os.path.isfile(filepath):
        raise Http404('Media file \'%s\' does not exist.' % filepath)

    # respect the If-Modified-Since header.
    statobj = os.stat(filepath)
    if not was_modified_since(
        request.META.get('HTTP_IF_MODIFIED_SINCE'),
        statobj.st_mtime,
        statobj.st_size
    ):
        # not modified
        return HttpResponseNotModified()

    # determine content type
    content_type, encoding = mimetypes.guess_type(filepath)
    content_type = content_type or 'application/octet-stream'

    if media.is_svg:
        # determine colorise information and colorise image, if SVG
        layers = dict(request.GET.iterlists())
        svg = get_colorized_svg_image(filepath, layers)
        response = HttpResponse(svg, content_type=content_type)
    else:
        # regular file response
        response = FileResponse(open(filepath, 'rb'), content_type=content_type)
        if stat.S_ISREG(statobj.st_mode):
            response['Content-Length'] = statobj.st_size

        if encoding:
            response['Content-Encoding'] = encoding

    # last mod. timestamp
    response['Last-Modified'] = http_date(statobj.st_mtime)

    return response


def media_api(request, shape, size, bucket, pk, filename):
    """
    Serve a media asset for the given shape and size and apply custom
    overwrites on demand.
    """
    # load media based on arguments
    media = get_object_or_404(Media, pk=pk, filename=filename)

    # bucket must match
    try:
        bucket = int(bucket)
    except ValueError:
        bucket = -1
    if media.bucket_id != bucket:
        raise Http404('Bucket does not match.')

    return serve_media_api(request, media, shape)


def media_api_original(request, bucket, pk, filename):
    """
    Serve a media asset for the original version of the given media asset and
    apply custom overwrites on demand.
    """
    return media_api(request, None, None, bucket, pk, filename)


def media_api_pk(request, pk):
    """
    Serve a media asset for the original version of the given media asset and
    apply custom overwrites on demand. The media asset is only accessed via its
    unique primary key.
    """
    # load media based on pk argument
    return serve_media_api(request, get_object_or_404(Media, pk=pk))