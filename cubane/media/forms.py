# coding=UTF-8
from __future__ import unicode_literals
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe
from cubane.forms import BaseForm, BaseModelForm, ExtFileField
from cubane.lib.tree import is_any_child_of
from cubane.backend.forms import BrowseField, BrowseThumbnailField, BrowseTreeField
from cubane.backend.forms import BrowseSelectThumbnail
from cubane.backend.forms import InfoField
from cubane.media.models import Media, MediaFolder


IMAGE_SIZE_CHOICES = (
    ('0-320', 'Small'),
    ('320-900', 'Medium'),
    ('900-9999', 'Large'),
)


class BrowseMediaFolderField(BrowseTreeField):
    """
    Simplified version of browse folder field for browsing media folders.
    """
    def __init__(self, *args, **kwargs):
        model = MediaFolder
        kwargs['model'] = model
        kwargs['browse'] = reverse_lazy('cubane.cms.%s.index' % slugify(model._meta.verbose_name_plural))
        kwargs['create'] = reverse_lazy('cubane.cms.%s.create' % slugify(model._meta.verbose_name_plural))
        super(BrowseMediaFolderField, self).__init__(*args, **kwargs)


class MediaFolderForm(BaseModelForm):
    """
    Form for editing media folders.
    """
    ERROR_ITSELF_AS_PARENT = 'Cannot have itself as parent.'
    ERROR_PARENT_AS_CHILD = 'Parent cannot be a child of this node.'


    class Meta:
        model = MediaFolder
        fields = '__all__'


    parent = BrowseMediaFolderField(
        label='Parent Folder',
        required=False,
        help_text='The parent folder of this folder.'
    )


    def clean_parent(self):
        parent = self.cleaned_data.get('parent')
        if parent:
            # tree node cannot have itself as a parent
            if parent.id and self._instance.id and parent.id == self._instance.id:
                raise forms.ValidationError(self.ERROR_ITSELF_AS_PARENT)

            # parent node cannot be a child of the node we are editing
            if is_any_child_of(parent, self._instance):
                raise forms.ValidationError(self.ERROR_PARENT_AS_CHILD)

        return parent


class MediaShareForm(BaseForm):
    """
    Form for sharing a media asset publicly.
    """
    share_enabled = forms.BooleanField(
        label='Share Enabled',
        required=False,
        help_text='Enable file sharing for this media asset.'
    )

    share_filename = forms.CharField(
        label='Public Filename',
        max_length=255,
        required=False,
        help_text='Public filename under which the system will make this document or image publicly available for download.'
    )


    def clean(self):
        d = super(MediaShareForm, self).clean()

        share_enabled = d.get('share_enabled')
        share_filename = d.get('share_filename')

        if share_enabled:
            # if share is enabled, filename is required
            if not share_filename:
                self.field_error('share_filename', 'This field is required if sharing is enabled.')
            else:
                # if share is enabled, filename must be unique
                assets = Media.objects.filter(share_enabled=True, share_filename=share_filename).exclude(pk=self._instance.pk)
                if assets.count() > 0:
                    self.field_error('share_filename', mark_safe('There is at least another media asset that is currently shared under the same name (<em>%s</em>). Please choose a different name.' % (
                        assets[0].caption
                    )))

        return d


class FileInputWidget(forms.ClearableFileInput):
    def __init__(self, *args, **kwargs):
        self._multiple = kwargs.pop('multiple', False)
        super(FileInputWidget, self).__init__(*args, **kwargs)


    def render(self, name, value, attrs=None, renderer=None):
        if self._multiple:
            attrs['multiple'] = 'multiple'

        html = super(FileInputWidget, self).render(name, value, attrs)

        return (
            '<div class="cubane-file-upload">' +
			'<svg class="cubane-file-upload-icon" xmlns="http://www.w3.org/2000/svg" width="50" height="43" viewBox="0 0 50 43"><path d="M48.4 26.5c-.9 0-1.7.7-1.7 1.7v11.6h-43.3v-11.6c0-.9-.7-1.7-1.7-1.7s-1.7.7-1.7 1.7v13.2c0 .9.7 1.7 1.7 1.7h46.7c.9 0 1.7-.7 1.7-1.7v-13.2c0-1-.7-1.7-1.7-1.7zm-24.5 6.1c.3.3.8.5 1.2.5.4 0 .9-.2 1.2-.5l10-11.6c.7-.7.7-1.7 0-2.4s-1.7-.7-2.4 0l-7.1 8.3v-25.3c0-.9-.7-1.7-1.7-1.7s-1.7.7-1.7 1.7v25.3l-7.1-8.3c-.7-.7-1.7-.7-2.4 0s-.7 1.7 0 2.4l10 11.6z"/></svg>' +
			html +
            '<div class="cubane-file-label"></div>' +
			'<label for="id_%s"><strong class="btn">Choose a file</strong> or drag it here.</label>' % name +
		    '</div>'
        )


    def get_multiple(self):
        return self._multiple


    def set_multiple(self, multiple):
        self._multiple = multiple


    multiple = property(get_multiple, set_multiple)


class MediaForm(BaseForm):
    """
    Form for editing media content, such as images or documents.
    """
    IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.svg']
    DOCUMENT_EXT = ['.pdf', '.xlsx', '.xls', '.doc', '.docx', '.odt', '.csv']


    media = ExtFileField(
        label='Upload File',
        widget=FileInputWidget(multiple=True)
    )

    caption = forms.CharField(
        label='Caption',
        required=False,
        max_length=255,
        help_text=
            'Leave empty to fill automatically; Briefly describe the content ' +
            'of the image or document. This information is associated with ' +
            'the image or document and may be analysed by search engines.'
    )

    credits = forms.CharField(
        label='Credits',
        required=False,
        max_length=255,
        help_text='If you wish to give credits for this image please put them here.'
    )

    extra_image_title = forms.CharField(
        label='Description',
        required=False,
        max_length=4000,
        help_text='If you wish to add an extra description to the image or document.',
        widget=forms.Textarea()
    )

    parent = BrowseTreeField(
        label='Folder',
        required=False,
        model=MediaFolder,
        help_text='Optional: The folder this media asset is stored in.'
    )

    auto_fit = forms.BooleanField(
        label='Auto Fit',
        required=False,
        help_text='Automatically fit the image onto the required aspect ratio that is required by the website (may result in white spaces around the edges).'
    )

    jpeg_quality = forms.IntegerField(
        label='JPEG Quality',
        required=False,
        max_value=100,
        min_value=1,
        help_text='Optional: JPEG Quality Level.'
    )

    _download = InfoField(
        label=''
    )

    focal_x = forms.FloatField(
        required=False,
        widget=forms.HiddenInput()
    )

    focal_y = forms.FloatField(
        required=False,
        widget=forms.HiddenInput()
    )


    def configure(self, request, instance, edit):
        super(MediaForm, self).configure(request, instance, edit)

        # caption
        self.fields['caption'].label = settings.IMAGE_CAPTION_LABEL
        self.fields['caption'].help_text = settings.IMAGE_CAPTION_HELP_TEXT

        # credits
        if not settings.IMAGE_CREDITS:
            self.remove_field('credits')

        # extra title
        if not settings.IMAGE_EXTRA_TITLE:
            self.remove_field('extra_image_title')
        else:
            self.fields['extra_image_title'].label = settings.IMAGE_EXTRA_TITLE_LABEL
            self.fields['extra_image_title'].help_text = settings.IMAGE_EXTRA_TITLE_HELP_TEXT

        # only allow one image to be uploaded when in edit mode
        # also caption is required
        if edit:
            self.fields['media'].widget.multiple = False
            self.fields['caption'].required = True

        # force image/document type
        if hasattr(request, 'is_image'):
            self.fields['media'].ext = \
                self.IMAGE_EXT if request.is_image else self.DOCUMENT_EXT

        # file field is not required when editing record
        if edit:
            self.fields['media'].required = False
            self.fields['media'].help_text = 'Select only if you want to replace the existing image.'

        # file field is not required when duplicating content
        if self.is_duplicate:
            self.fields['media'].required = False
            self.fields['media'].help_text = 'Optionally choose a different image.'

        # auto-fit
        if not settings.IMAGE_FITTING_ENABLED or not settings.IMAGE_FITTING_SHAPES:
            self.remove_field('auto_fit', if_exists=True)

        # jpeg quality
        from cubane.media.views import DocumentView
        if instance and instance.pk and edit:
            # auto fit
            if not instance.is_image:
                self.remove_field('auto_fit', if_exists=True)

            # quality
            if instance.is_jpeg_image:
                if instance.org_quality:
                    self.fields['jpeg_quality'].help_text = 'Optional: JPEG Quality Level. Original image quality is %d.' % instance.org_quality
            else:
                self.remove_field('jpeg_quality', if_exists=True)
        elif hasattr(request, 'view_instance') and isinstance(request.view_instance, DocumentView):
            # create document
            self.remove_field('auto_fit', if_exists=True)
            self.remove_field('jpeg_quality', if_exists=True)

        # download button
        if edit and hasattr(self, 'view'):
            download_url = '%s?pk=%s' % (self.view._get_url(request, 'download'), instance.pk)
            self.fields['_download'].html = '<a class="btn btn-primary" href="%s" download>Download</a>' % download_url
        else:
            self.remove_field('_download')

        # in case we deleted fields
        self.update_sections()


class MultiMediaForm(BaseForm):
    """
    Form for editing media content, such as images or documents.
    """
    media = ExtFileField(
        label='Upload File',
        widget=FileInputWidget(multiple=True)
    )

    parent = BrowseTreeField(
        required=False,
        model=MediaFolder,
        help_text='The folder this media asset is stored.'
    )

    auto_fit = forms.BooleanField(
        required=False,
        help_text='Automatically fit the image onto the required aspect ratio that is required by the website (may result in white spaces around the edges).'
    )

    jpeg_quality = forms.IntegerField(
        required=False,
        max_value=100,
        min_value=1,
        help_text='Optional: JPEG Quality Level.'
    )


    def configure(self, request):
        super(MultiMediaForm, self).configure(request)

        # force image/document type
        self.fields['media'].ext = \
            MediaForm.IMAGE_EXT if request.is_image else MediaForm.DOCUMENT_EXT


class MediaFilterForm(BaseForm):
    class Meta:
        model = Media


    image_size = forms.ChoiceField(
        label='Image Size',
        choices=IMAGE_SIZE_CHOICES
    )

    caption = forms.CharField(
        label='Caption',
        max_length=255
    )

    filename = forms.CharField(
        label='Filename',
        max_length=255
    )

    auto_fit = forms.BooleanField(
        label='Auto Fit'
    )

    share_enabled = forms.BooleanField(
        label='Shared'
    )

    share_filename = forms.CharField(
        label='Share Filename',
        max_length=255
    )


class BrowseMediaField(BrowseField):
    """
    Simplified version of browse select widget specialisied in
    browsing media assets.
    """
    def __init__(self, *args, **kwargs):
        images = kwargs.pop('images', True)
        if images:
            name = 'Images'
            browse_name = 'cubane.cms.images.index'
            create_name = 'cubane.cms.images.create'
        else:
            name = 'Documents'
            browse_name = 'cubane.cms.documents.index'
            create_name = 'cubane.cms.documents.create'

        kwargs['queryset'] = Media.objects.filter(is_image=images)
        kwargs['name'] = name
        kwargs['browse'] = reverse_lazy(browse_name)
        kwargs['create'] = reverse_lazy(create_name)

        super(BrowseMediaField, self).__init__(*args, **kwargs)


class BrowseSelectMediaThumbnail(BrowseSelectThumbnail):
    def __init__(self, *args, **kwargs):
        kwargs['model'] = Media
        kwargs['data_name'] = 'Images'
        kwargs['browse'] = reverse_lazy('cubane.cms.images.index')
        kwargs['create'] = reverse_lazy('cubane.cms.images.create')
        kwargs['edit'] = reverse_lazy('cubane.cms.images.edit')
        super(BrowseSelectMediaThumbnail, self).__init__(*args, **kwargs)


class BrowseMediaThumbnailField(BrowseThumbnailField):
    """
    Simplified version of browse select thumbnail widget specialisied in
    browsing media assets.
    """
    widget = BrowseSelectMediaThumbnail


    def __init__(self, *args, **kwargs):
        kwargs['queryset'] = Media.objects.filter(is_image=True)
        kwargs['data_name'] = 'Images'
        kwargs['browse'] = reverse_lazy('cubane.cms.images.index')
        kwargs['create'] = reverse_lazy('cubane.cms.images.create')
        kwargs['edit'] = reverse_lazy('cubane.cms.images.edit')
        super(BrowseMediaThumbnailField, self).__init__(*args, **kwargs)


class BrowseImagesField(BrowseMediaThumbnailField):
    """
    Used to be based on 'BrowseMediaField' using a drop down select field.
    However, this field is now using the thumbnail image version instead of
    the drop down field.
    """
    pass


class BrowseImagesSelectField(BrowseMediaField):
    """
    Simplified version of the browse select widget specialised in
    selecting all images. This used to be called 'BrowseImagesField' and is based
    on a dropdown field. However, the original 'BrowseImagesField' has now been
    replaced with 'BrowseMediaThumbnailField'.
    """
    def __init__(self, *args, **kwargs):
        kwargs['images'] = True
        super(BrowseImagesSelectField, self).__init__(*args, **kwargs)


class BrowseDocumentsField(BrowseMediaField):
    """
    Simplified version of the browse select widget specialised in
    selecting all documents.
    """
    def __init__(self, *args, **kwargs):
        kwargs['images'] = False
        super(BrowseDocumentsField, self).__init__(*args, **kwargs)
