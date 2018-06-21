# coding=UTF-8
from __future__ import unicode_literals
from django.db import connection
from cubane.tests.base import CubaneTestCase, CubaneManualTransactionTestCase
from cubane.dbmigrate.schema import Schema
from cubane.dbmigrate.indexing import get_class_name_with_modules, check_custom_indexing
from cubane.testapp.models import TestModel
from cubane.testapp.models import TestLikeIndexUniqueModel


@CubaneTestCase.complex()
class DBMigrateIndexingTestCase(CubaneManualTransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super(DBMigrateIndexingTestCase, cls).setUpClass()
        cls.schema = Schema(connection)


    def test_should_ignore_unknoqn_model_fields(self):
        self._test_custom_index(
            TestModel,
            [
                'does_not_exist',
                ['title', 'does_not_exist']
            ],
            ['does_not_exist']
        )


    def test_should_add_custom_indicies(self):
        self._test_custom_index(
            TestModel,
            [
                'text',
                ['title', 'text']
            ],
            [],
            ['text', ['text', 'title']]
        )


    def test_should_create_like_index_together_with_unique_index(self):
        self._test_custom_index(
            TestLikeIndexUniqueModel,
            [
                'title'
            ],
            [],
            ['title_key', 'title_like']
        )


    def _get_index_name(self, table, column):
        if not isinstance(column, list):
            if column.endswith('_key'):
                return self.schema.sql.get_index_name(table, column[:-4], unique=True)
            elif column.endswith('_like'):
                return self.schema.sql.get_like_index_name(table, column[:-5])

        return self.schema.sql.get_index_name(table, column)


    def _test_custom_index(self, model, index, index_false=[], index_true=[]):
        custom_index = {
            get_class_name_with_modules(model): index
        }
        table = model._meta.db_table
        self.schema.begin()
        try:
            check_custom_indexing(self.schema, model, custom_index)

            for index in index_false:
                index_name = self._get_index_name(table, index)
                self.assertFalse(self.schema.sql.index_exists(index_name))

            for index in index_true:
                index_name = self._get_index_name(table, index)
                self.assertTrue(self.schema.sql.index_exists(index_name))
        finally:
            self.schema.rollback()