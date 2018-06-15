# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from cubane.tests.base import CubaneTestCase
from cubane.lib.file import file_get_contents
from cubane.lib.resources import load_resource_version_identifier
from cubane.svgicons import get_svgicons_filename
import os
import shutil

class CreateSvgIconsManagementCommandTestCase(CubaneTestCase):
    def test_create_svgicons_management_command_should_generate_svgicon_file(self):
        from cubane.svgicons.management.commands.create_svgicons import Command
        self.call_command(Command())

        # - email and location are stripped (style)
        # - phone style has been retained (see resource declaration in testapp)
        self.assertEqual(
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" style="display: none;"><symbol id="svgicon-email" viewBox="0 0 64 64"><g id="email-sc8O5C.tif"> <g> <path d="M6.4,13.7c17.1,0,34.1,0,51.2,0c0.1,0.1,0.2,0.1,0.4,0.2c1.3,0.8,1.4,2,0.4,3c-5.5,5.5-11,11-16.4,16.5 c-2.7,2.7-5.4,5.5-8.1,8.2c-1,1-2.6,1.1-3.5,0.1c-2-2-3.9-3.9-5.9-5.9c-3.5-3.5-6.9-7-10.4-10.5c-2.9-3-5.9-5.9-8.8-8.9 c-0.3-0.3-0.4-0.6-0.3-1C5.1,14.6,5.6,14,6.4,13.7z"/> <path d="M32,52.3c-8.1,0-16.2,0-24.4,0c-1,0-1.8-0.2-2.4-1.1c-0.5-0.9-0.5-1.4,0.3-2.1c4.5-4.6,9.1-9.1,13.6-13.7 c0.5-0.5,0.5-0.5,1,0c2.8,2.8,5.5,5.5,8.3,8.3c2,2,5.2,2,7.2,0c2.8-2.8,5.5-5.6,8.3-8.3c0.5-0.5,0.5-0.5,1,0 c2.9,2.9,5.7,5.8,8.6,8.6c1.7,1.7,3.4,3.5,5.2,5.2c0.4,0.4,0.5,0.9,0.4,1.4c-0.2,1-1.1,1.6-2.1,1.7c-0.2,0-0.4,0-0.6,0 C48.2,52.3,40.1,52.3,32,52.3z"/> <path d="M4.9,32.9c0-4,0-8,0-12.1c0-0.2-0.1-0.5,0.1-0.6c0.2-0.1,0.3,0.2,0.5,0.4c3.9,4,7.9,7.9,11.8,11.9c0.4,0.4,0.3,0.6,0,0.9 c-4,4-7.9,8-11.9,12c-0.1,0.1-0.2,0.3-0.4,0.2c-0.2-0.1-0.1-0.3-0.1-0.5C4.9,41,4.9,37,4.9,32.9z"/> <path d="M59.1,32.9c0,3.9,0,7.9,0,11.8c0,0.1,0,0.3,0,0.4c0,0.1,0.1,0.3-0.1,0.4c-0.2,0.1-0.3-0.1-0.4-0.2 c-0.7-0.7-1.4-1.4-2.1-2.1c-1.8-1.8-3.6-3.6-5.4-5.4c-1.5-1.5-3-3-4.5-4.5c-0.3-0.3-0.3-0.5,0-0.9c4-4,7.9-8,11.9-11.9 c0.1-0.1,0.2-0.2,0.3-0.2c0.1-0.1,0.3-0.1,0.3,0.1c0,0.2,0,0.3,0,0.5C59.1,24.9,59.1,28.9,59.1,32.9z"/> </g> </g></symbol><symbol id="svgicon-location" viewBox="0 0 64 64"><g id="location-xNv91c.tif"> <g> <path d="M28.4,0c1.8,0,3.5,0,5.3,0c0.1,0,0.2,0.1,0.4,0.1c8.7,1.3,15.1,5.8,18.9,13.7c2.1,4.2,2.9,8.8,1.9,13.5 c-0.7,3.4-2.2,6.5-3.9,9.6c-4.2,7.7-9.4,14.7-15,21.5c-1.5,1.9-3.1,3.7-4.7,5.6c-0.1,0-0.2,0-0.3,0C24.8,57,19,49.7,14,41.7 c-3.1-4.9-5.9-10-7-15.8c0-1.5,0-3,0-4.5c0-0.2,0.1-0.4,0.1-0.6c1.5-9.1,6.4-15.4,14.8-19.1C24,0.8,26.2,0.4,28.4,0z"/> </g> </g></symbol><symbol id="svgicon-phone" viewBox="0 0 60 60"><path d="M9.8,6.2c-0.9,0.6-7.2,5.2-8.1,10.4S0.5,27.1,6.2,36.2c5.9,9.3,17.4,20.7,27.4,21.3c8.9,0.5,15.2-5.7,15.9-8.1 c0.7-2.3-2.7-5.8-3.6-6.5c-0.8-0.6-5.6-4.9-8.4-4.3c-4.6,0.9-4.3,4.9-8.4,5.3c-2.4,0.2-5.3-1.5-9.6-6.8c-9.4-11.7-4.8-12.2-3.1-13.7 c1.7-1.5,4.7-3.2,4.1-5.6s-3-8.5-5.5-10.6c-1.8-1.7-2.1-1.6-2.8-1.7S10.7,5.6,9.8,6.2z" style="fill:#FFFFFF;"/></symbol></svg>',
            file_get_contents(self._get_path())
        )


    def test_create_svgicons_management_command_should_create_static_folder_if_not_exist_yet(self):
        if os.path.isdir(settings.STATIC_ROOT):
            shutil.rmtree(settings.STATIC_ROOT)

        from cubane.svgicons.management.commands.create_svgicons import Command
        self.call_command(Command())

        self.assertTrue(os.path.isfile(self._get_path()))


    def _get_path(self):
        identifier = load_resource_version_identifier()
        filename = get_svgicons_filename('frontend', identifier)
        return os.path.join(settings.STATIC_ROOT, filename)
