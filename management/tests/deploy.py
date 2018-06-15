# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.test.utils import override_settings
from cubane.management.tests.base import ManagementTestCaseBase
from cubane.lib.resources import load_resource_version_identifier
from cubane.lib.deploy import load_deploy_timestamp
from cubane.lib.minify import minify
from freezegun import freeze_time
from datetime import datetime
import cubane


_minify = cubane.lib.minify.minify


class CubaneManagementDeployCommandTestCase(ManagementTestCaseBase):
    @classmethod
    def setUpClass(cls):
        super(CubaneManagementDeployCommandTestCase, cls).setUpClass()

        # patch minify to not actually minify under test
        def minify_mock(content, filetype='js'):
            return content
        cubane.lib.minify.minify = minify_mock


    @classmethod
    def tearDownClass(cls):
        cubane.lib.minify.minify = _minify
        super(CubaneManagementDeployCommandTestCase, cls).tearDownClass()


    @freeze_time('2016-06-20')
    def test_deploy_should_deploy_website(self):
        call_command('deploy')
        identifier = load_resource_version_identifier()

        # version identifier correct?
        self._assertStaticFile('revision', identifier)

        # deploy timestamp?
        self.assertEqual(datetime.now(), load_deploy_timestamp())

        # static (compiled) assets present
        for bucket in ['backend', 'backend-inline', 'frontend', 'inline']:
            self._assertStaticFile('cubane.%s.screen.%s.min.css' % (bucket, identifier))
            self._assertStaticFile('cubane.%s.%s.min.js' % (bucket, identifier))

        # static (compiled) css for testing bucket
        self._assertStaticFile('cubane.testing.screen.%s.min.css' % identifier)
        self._assertStaticFile('cubane.testing.print.%s.min.css' % identifier)

        # static (compiled) empty files for css and js
        self._assertStaticFile('cubane.empty.screen.%s.min.css' % identifier)
        self._assertStaticFile('cubane.empty.print.%s.min.css' % identifier)
        self._assertStaticFile('cubane.empty.%s.min.js' % identifier)

        # compiled svg icons?
        self._assertStaticFile('cubane.svgicons.frontend.%s.svg' % identifier)
        self._assertStaticFile('cubane.svgicons.testing.%s.svg' % identifier)

        # fonts
        self._assertStaticFile(
            'cubane.frontend.screen.%s.min.css' % identifier,
            contains_content='@font-face {\n    font-family: \'Open Sans\';'
        )


    @override_settings()
    def test_deploy_should_deploy_website_without_fonts_installed(self):
        settings.INSTALLED_APPS.remove('cubane.fonts')
        call_command('deploy')