# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.tests.base import CubaneTestCase
from cubane.lib.file import file_get_contents, file_put_contents
from cubane.lib.deploy import get_deploy_timestamp_filename
from cubane.lib.deploy import save_deploy_timestamp
from cubane.lib.deploy import load_deploy_timestamp
from cubane.lib.deploy import delete_deploy_timestamp
from freezegun import freeze_time
from datetime import datetime
import os


class LibDeployGetDeployTimestampFilenameTestCase(CubaneTestCase):
    def test_should_return_correct_path_to_timestamp_file(self):
        self.assertEqual(
            os.path.join(settings.STATIC_ROOT, 'deployts'),
            get_deploy_timestamp_filename()
        )


@freeze_time('2016-06-20')
class LibDeploySaveDeployTimestampTestCase(CubaneTestCase):
    def test_should_save_timestamp_in_iso_format(self):
        ts = save_deploy_timestamp()

        timestamp = datetime.strptime(
            file_get_contents(get_deploy_timestamp_filename()),
            '%Y-%m-%dT%H:%M:%S'
        )
        self.assertEqual(datetime.now(), timestamp)
        self.assertEqual(datetime.now(), ts)


    def test_should_overwrite_existing_file(self):
        file_put_contents(get_deploy_timestamp_filename(), 'hello world')
        save_deploy_timestamp()

        timestamp = datetime.strptime(
            file_get_contents(get_deploy_timestamp_filename()),
            '%Y-%m-%dT%H:%M:%S'
        )
        self.assertEqual(datetime.now(), timestamp)


@freeze_time('2016-06-20')
class LibDeployLoadDeployTimestampTestCase(CubaneTestCase):
    def test_should_return_none_if_file_does_not_exist(self):
        delete_deploy_timestamp()
        self.assertFalse(os.path.exists(get_deploy_timestamp_filename()))
        self.assertIsNone(load_deploy_timestamp())


    def test_should_return_none_if_incorrect_timestamp_format(self):
        file_put_contents(get_deploy_timestamp_filename(), 'not an ISO formatted timestamp')
        self.assertIsNone(load_deploy_timestamp())


    def test_should_load_timestamp_from_iso_format(self):
        save_deploy_timestamp()
        ts = load_deploy_timestamp()
        self.assertIsNotNone(ts)
        self.assertEqual(datetime.now(), ts)