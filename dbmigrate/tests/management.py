# coding=UTF-8
from __future__ import unicode_literals
from django.db import connection
from cubane.tests.base import CubaneTestCase, CubaneManualTransactionTestCase
from cubane.dbmigrate import commit_changes
from cubane.dbmigrate.schema import Schema
from cubane.dbmigrate.management.commands.dbmigrate import Command
from mock import patch


@CubaneTestCase.complex()
class DBMigrateManagementCommandTestCase(CubaneManualTransactionTestCase):
    @patch('cubane.dbmigrate.commit_changes')
    def test_db_migrate_should_auto_migrate(self, commit_changes):
        # commit_changes is mocked and will never happen, so we can simply
        # rollback the entire migration and not affecting other tests...
        schema = Schema(connection)
        schema.begin()
        try:
            self.call_command(Command(), options={
                'interactive': False,
                'skip_fixtures': True
            })

            self.assertTrue(schema.sql.index_exists(schema.sql.get_index_name('django_content_type', 'app_label')))
            self.assertEqual('GB', schema.sql.get_column_default('testapp_settings', 'country_id'))
        finally:
            schema.rollback()