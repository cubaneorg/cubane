# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from cubane.lib.resources import *
from cubane.lib.deploy import save_deploy_timestamp
from cubane.lib.minify import minify_files
from cubane.lib.verbose import out
from cubane.tasks import TaskRunner
import os
import sys
import traceback
import tempfile
import requests


class Command(BaseCommand):
    """
    Deploy cubane application by performing several tasks, such as compiling
    and compressing all css and javascript resources.
    """
    args = ''
    help = 'Deploy application'

    # silent django logs about copying,skiping etc.
    verbosity = 0


    def handle(self, *args, **options):
        """
        Run command.
        """
        # epilogue
        self.print_info()
        self.collect_static()

        # generate a new version identifier (without saving it yet)
        identifier = self.generate_identifier()

        # generate assets
        self.update_fontcache()
        self.create_favicons()
        self.create_svgicons(identifier)
        self.minify_resources(identifier)

        # switch to the new version
        save_resource_version_identifier(identifier)

        # epilogue and cleanup
        self.invalidate()
        self.remove_deprecated_resources()
        self.terminate_task_runner()
        self.generate_timestamp()


    def print_info(self):
        """
        Print some verbose information about the application and where stuff
        is written to...
        """
        out('CODE:   %s' % settings.BASE_PATH)
        out('STATIC: %s' % settings.STATIC_ROOT)
        out('MEDIA:  %s' % settings.MEDIA_ROOT)


    def generate_identifier(self):
        """
        Generate new version identifier.
        """
        if settings.TRACK_REVISION:
            identifier = generate_resource_version_identifier()
            out('Version: %s.' % identifier)
        else:
            identifier = None

        return identifier


    def generate_timestamp(self):
        """
        Generate deployment timestamp file.
        """
        save_deploy_timestamp()


    def update_fontcache(self):
        """
        Run manage.py loadfonts in order to update the font cache.
        """
        if 'cubane.fonts' in settings.INSTALLED_APPS:
            call_command('loadfonts', interactive=False)


    def create_favicons(self):
        """
        Run manage.py create_favicons in order to create various sizes of the
        favicon provided.
        """
        call_command('create_favicons', interactive=False)


    def create_svgicons(self, identifier):
        """
        Run manage.py create_svgicons in order to generate svg icon sheet files
        at deployment time.
        """
        if 'cubane.svgicons' in settings.INSTALLED_APPS:
            call_command('create_svgicons', identifier=identifier, interactive=False)


    def collect_static(self):
        """
        Run manage.py collectstatic in order to copy all static assets
        across.
        """
        settings.INSTALLED_APPS += (
            'django.contrib.staticfiles',
        )
        import django.contrib.staticfiles
        stdout = open(os.devnull, 'w') if settings.TEST else sys.stdout
        call_command('collectstatic', interactive=False, verbosity=self.verbosity, stdout=stdout)


    def minify_resources(self, identifier):
        """
        Compile and minify all resources.
        """
        # compress resources
        out('Compressing resources...Please Wait...')
        for target in get_resource_targets():
            out('[%s]' % target)
            for ext in ['css', 'js']:
                if ext == 'js':
                    self.minify_resources_for(target, ext, None, identifier)
                else:
                    for css_media in settings.CSS_MEDIA:
                        self.minify_resources_for(target, ext, css_media, identifier)

        out('Complete.')


    def download_external_resource(self, url):
        """
        Download the given external url and store the resource in a temporary
        file. Return the full path to such file. Raise exception if the external
        resource could not be downloaded.
        """
        # download
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError('Unable to download external resource: %s. Status Code: %s' % (
                url,
                response.status_code
            ))

        # save to local temp file
        f, path = tempfile.mkstemp()
        os.write(f, response.content)
        os.close(f)
        return path


    def minify_resources_for(self, target, ext, css_media, identifier):
        """
        Compile and minify all resources for the given target, file extension
        and css media (for css resources only).
        """
        # build resources
        resources = []
        downloaded_files = []
        for r in get_resources(target, ext, css_media):
            if r.startswith('/media/'):
                # media resource
                path = os.path.join(settings.MEDIA_ROOT, r[7:])
            elif is_external_resource(r):
                # download external resource
                url = get_downloadable_resource_url(r)
                out('\tDownloading: %s...' % url)
                path = self.download_external_resource(url)
                downloaded_files.append(path)
            else:
                # local resource
                if r.startswith('/'): r = r[1:]
                path = os.path.join(settings.STATIC_ROOT, r)

            resources.append(path)

        if resources:
            filename = get_minified_filename(
                target,
                ext,
                css_media,
                identifier
            )

            out('\tCompressing: %s...' % filename)

            path = os.path.join(settings.STATIC_ROOT, filename)
            minify_files(resources, settings.STATIC_ROOT, path, ext, identifier)

        if downloaded_files:
            out('\tDeleting downloaded files...')
            for path in downloaded_files:
                try:
                    os.remove(path)
                except:
                    pass


    def invalidate(self):
        """
        Invalidate cms cache.
        """
        if 'cubane.cms' in settings.INSTALLED_APPS:
            call_command('invalidate', interactive=False)


    def remove_deprecated_resources(self):
        """
        Delete all resource files that do not belong to the current version.
        """
        # remove deprecated resource assets from previous version(s)...
        if settings.TRACK_REVISION:
            identifier = load_resource_version_identifier()
            for filename in get_resource_files_not_matching_identifier(identifier):
                os.remove(filename)


    def terminate_task_runner(self):
        """
        Terminate task runner if running.
        """
        if TaskRunner.is_available():
            TaskRunner.terminate()
