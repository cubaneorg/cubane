# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.utils.http import http_date
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.views import serve
from django.core.management import call_command
from django.core.management.commands.runserver import \
    Command as RunserverCommand
from cubane.lib.serve import serve_static_with_context
import re


class StaticFilesTemplateHandler(StaticFilesHandler):
    """
    WSGI middleware that intercepts calls to the static files directory, as
    defined by the STATIC_URL setting, and serves those files. In addition,
    files ending with template.xxx are processed via the template system before
    being served.
    """
    def serve(self, request):
        """
        Actually serves the request path.
        """
        # serve static content as usually
        response = serve(request, self.file_path(request.path), insecure=True)

        # resource is using the template system?
        if isinstance(response, FileResponse) and re.match(r'.{1,}\.(template|templating)\..{1,}$', request.path):
            # load content from file response and run it through the template
            # system. The result is then packed into a new http response with
            # the last-modified timestamp based on the current date and time
            # and content type of the original response.
            content = ''.join([chunk for chunk in response.streaming_content])
            rendered_response = HttpResponse(
                serve_static_with_context(content),
                content_type=response['Content-Type']
            )
            rendered_response['Content-Length'] = len(rendered_response.content)
            rendered_response['Last-Modified'] = http_date()
            response = rendered_response

        return response


class Command(RunserverCommand):
    """
    Override command to serve static files.
    """
    help = "Starts a lightweight Web server for development and also serves static files."


    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--nostatic', action="store_false", dest='use_static_handler', default=True,
            help='Tells Django to NOT automatically serve static files at STATIC_URL.',
        )
        parser.add_argument(
            '--insecure', action="store_true", dest='insecure_serving', default=False,
            help='Allows serving static files even if DEBUG is False.',
        )


    def run(self, **options):
        """
        Runs the server, using the autoreloader if needed
        """
        if settings.DEBUG:
            # install if database does not exist yet
            from django.db import connection
            try:
                connection.cursor()
            except:
                # database does not exist yet, install...
                call_command('install')

            # fonts
            if 'cubane.fonts' in settings.INSTALLED_APPS:
                call_command('loadfonts')

        super(Command, self).run(**options)


    def get_handler(self, *args, **options):
        """
        Returns the static files serving handler wrapping the default handler,
        if static files should be served. Otherwise just returns the default
        handler.
        """
        # serve static content
        print 'Serving static content.'

        handler = super(Command, self).get_handler(*args, **options)
        use_static_handler = options['use_static_handler']
        insecure_serving = options['insecure_serving']
        staticfiles_installed = 'django.contrib.staticfiles' in settings.INSTALLED_APPS
        if use_static_handler and (settings.DEBUG or insecure_serving) and staticfiles_installed:
            return StaticFilesTemplateHandler(handler)
        return handler