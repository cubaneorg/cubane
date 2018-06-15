# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.app import require_app
from django.conf import settings
from cubane.lib.app import require_app


RESOURCES = [
    # cubane core
    '/cubane/js/cubane.polyfill.js',
    '/cubane/js/cubane.js',
    '/cubane/js/cubane.string.js',
    '/cubane/js/cubane.html.js',
    '/cubane/js/cubane.urls.js',
    '/cubane/js/cubane.utils.js',
    '/cubane/js/cubane.dialog.js',
    '/cubane/js/cubane.pulse.js',
    '/cubane/js/cubane.csrf.js',

    # jquery
    'jquery/jquery-2.0.3.min.js',
    'jquery/selectors.js',
    'jquery/csrf.js',

    # bootstrap
    'bootstrap/css/bootstrap.css',
    'bootstrap/css/bootstrap-responsive.css',
    'bootstrap/css/bootstrap-fixes.css',
    'bootstrap/js/bootstrap.min.js',

    # font awaesome
    'fontawesome/css/font-awesome.css',

    # select2
    'select2/css/select2.min.css',
    'select2/js/select2.min.js',

    # interact
    'interact/interact.js',

    # tiny-mce
    'tinymce/js/tinymce/tinymce.min.js',
    'tinymce/js/tinymce/plugins/emoticons/plugin.min.js',
    'tinymce/js/tinymce/plugins/advlist/plugin.min.js',
    'tinymce/js/tinymce/plugins/autolink/plugin.min.js',
    'tinymce/js/tinymce/plugins/charmap/plugin.min.js',
    'tinymce/js/tinymce/plugins/print/plugin.min.js',
    'tinymce/js/tinymce/plugins/searchreplace/plugin.min.js',
    'tinymce/js/tinymce/plugins/visualblocks/plugin.min.js',
    'tinymce/js/tinymce/plugins/code/plugin.min.js',
    'tinymce/js/tinymce/plugins/fullscreen/plugin.min.js',
    'tinymce/js/tinymce/plugins/insertdatetime/plugin.min.js',
    'tinymce/js/tinymce/plugins/table/plugin.min.js',
    'tinymce/js/tinymce/plugins/paste/plugin.min.js',
    'tinymce/js/tinymce/plugins/nonbreaking/plugin.min.js',
    'tinymce/js/tinymce/plugins/textcolor/plugin.min.js',
    'tinymce/js/tinymce/plugins/emoticons/plugin.min.js',
    'tinymce/js/tinymce/plugins/lists/plugin.min.js',
    'tinymce/js/tinymce/plugins/youtube/plugin.min.js',
    'tinymce/js/plugins/cubanefillresize.js',
    'tinymce/js/plugins/cubanepreview.js',
    'tinymce/js/plugins/cubaneimage.js',
    'tinymce/js/plugins/cubanelink.js',
    'tinymce/js/plugins/cubaneyoutube.js',
    'tinymce/css/tinymce.css',

    # font
    'fonts/montserrat/montserrat.css',

    # style
    'css/login.css',
    'css/auth.css',
    'css/plain.css',
    'css/theme.css',
    'css/form.css',
    'css/form_embedded.css',
    'css/table.css',
    'css/tree.css',
    'css/listing.css',
    'css/related_listing.css',
    'css/dnd.css',
    'css/sortable.css',
    'css/collection-items.css',
    'css/dialog.css',
    'css/responsive.css',
    'css/gmap.css',
    'css/taskinfo.css',
    'css/changes.css',
    'css/postcode.css',
    'css/dashboard.css',
    'print|css/print.css',

    # date picker
    'css/bootstrap-datepicker.min.css',
    'js/bootstrap-datepicker.min.js',

    # time picker
    'css/bootstrap-timepicker.css',
    'js/bootstrap-timepicker.js',

    # color picker
    'css/minicolors.css',
    'js/minicolors.js',

    # javascript
    'js/cubane.backend.js',
    'js/cubane.backend.heartbeat.js',
    'js/cubane.backend.dblclick.js',
    'js/cubane.backend.browse.js',
    'js/cubane.backend.collection-items.js',
    'js/cubane.backend.sortable.js',
    'js/cubane.backend.listing.js',
    'js/cubane.backend.lightbox.js',
    'js/cubane.backend.dnd.js',
    'js/cubane.backend.tree.js',
    'js/cubane.backend.gmap.js',
    'js/cubane.backend.sidepanel.js',
    'js/cubane.backend.embedform.js',
    'js/cubane.backend.dashboard.js'
]


RESOURCE_TARGETS = {
    'backend': [
        'cubane.backend',

    ],
    'backend-inline': [
        'cubane.custom_event',
        'cubane.medialoader'
    ]
}


def install_backend(backend):
    from cubane.backend.api import BackendApiView
    backend.register_api(BackendApiView())

    from cubane.backend.views import ChangeLogBackendSection
    backend.register_section(ChangeLogBackendSection())
