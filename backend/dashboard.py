# coding=UTF-8
from __future__ import unicode_literals
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse
from cubane.lib.ident import camel_to_ident
from cubane.lib.acl import Acl


def render_dashboard_widget_to_html(widget_context):
    """
    Render given widget context to HTML.
    """
    return render_to_string('cubane/backend/dashboard/widget.html', {
        'widget': widget_context
    })


def render_dashboard_widget(request, widget):
    """
    Render the given dashboard widget.
    """
    content = widget.render(request)
    if isinstance(content, dict):
        template = widget.get_template(request)
        content.update({
            'request': request,
            'widget': widget,
            'backend': request.backend
        })
        content = render_to_string(template, content)

    return {
        'identifier': widget.get_identifier(),
        'title': widget.get_title(),
        'size': widget.get_size(),
        'url': widget.get_url(),
        'options': widget.options,
        'sizes': DashboardWidget.SIZES,
        'message': widget.get_message(request),
        'content': content
    }


def render_dashboard_widgets(request, widgets):
    """
    Render the given list of dashboard widgets.
    """
    rendered_widgets = []
    for widget in widgets:
        rendered_widgets.append(render_dashboard_widget(request, widget))
    return rendered_widgets


class DashboardWidget(object):
    """
    Base class for a dashboard widget.
    """
    SIZE_1X1 = '1x1'
    SIZE_1X2 = '1x2'
    SIZE_1X3 = '1x3'
    SIZE_2X1 = '2x1'
    SIZE_2X2 = '2x2'
    SIZE_2X3 = '2x3'
    SIZE_3X1 = '3x1'
    SIZE_4X1 = '4x1'
    SIZE_DEFAULT = SIZE_1X1
    SIZES = [
        SIZE_1X1,
        SIZE_1X2,
        SIZE_1X3,
        SIZE_2X1,
        SIZE_2X2,
        SIZE_2X3,
        SIZE_3X1,
        SIZE_4X1
    ]


    title = None


    def __init__(self, options):
        """
        Create a new instance of a widget with the given options.
        """
        # widget options
        if options is None:
            options = {}
        self.options = options

        # acl
        if hasattr(self, 'model'):
            self.acl = Acl.of(self.model)
        else:
            self.acl = Acl.default(None)


    @classmethod
    def get_identifier(cls):
        """
        Return the unique identifier of this widget class.
        """
        return '%s.%s' % (
            cls.__module__,
            cls.__name__
        )


    @classmethod
    def get_title(cls):
        """
        Return the title of this widget.
        """
        return cls.title


    @classmethod
    def get_url(cls):
        """
        Return the URL to the section of the backend that is responsible for
        managing the type of information that is presented by this dashboard
        widget, if any.
        """
        if hasattr(cls, 'url'):
            return reverse(cls.url)
        else:
            return None


    def get_size(self):
        """
        Return the size of this widget.
        """
        try:
            size = self.options.get('size')
        except:
            size = None

        if size is None:
            if hasattr(self, 'size'):
                size = self.size
            else:
                size = self.SIZE_DEFAULT

        if size not in self.SIZES:
            size = self.SIZE_DEFAULT

        return size


    def get_template(self, request):
        """
        Return the name of the template that is used to render the content
        of this widget.
        """
        if hasattr(self, 'template'):
            return self.template
        else:
            return 'dashboard/%s' % camel_to_ident(self.__class__.__name__)


    def get_objects_base(self, request):
        """
        Virtual: Return base queryset.
        """
        if hasattr(self, 'model'):
            return self.model.objects.all()
        else:
            raise ValueError('Dashboard widget \'%s\' does not specify model.' % self.__class__.__name__)


    def get_objects(self, request):
        """
        Return the base queryset.
        """
        objects = self.get_objects_base(request)
        return self.acl.filter(request, objects)


    def render(self, request):
        """
        Virtual: Render dashboard widget content by returning HTML or
        a dict. which then becomes the template context.
        """
        return None


    def get_message(self, request):
        """
        Virtual: Render welcome message to user.
        """
        return None