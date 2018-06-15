# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase, CubaneManualTransactionTestCase
from django.test.utils import override_settings
from django.db import connection
from django.db import models
from django.db.utils import DatabaseError
from django.contrib.auth.models import User
from django.utils import timezone
from cubane.media.models import Media
from cubane.dbmigrate.schema import Schema
from cubane.dbmigrate.sql import PostgresSql
from cubane.testapp.models import TestModel
from cubane.testapp.models import TestModelWithManyToMany
from cubane.testapp.models import TestModelNotNullableWithoutDefault
from cubane.testapp.models import TestModelNotNullableWithDefault
from cubane.testapp.models import TestModelWithoutDefault
from cubane.testapp.models import TestFTSPart
from cubane.testapp.models import TestLikeIndexUniqueModel
from cubane.testapp.models import TestFieldWithoutIndexModel
from cubane.testapp.models import TestLikeIndexNotUniqueModel
from mock import patch, Mock, MagicMock
from datetime import datetime


@CubaneTestCase.complex()
class DBMigrateSchemaBaseTestCase(CubaneManualTransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super(DBMigrateSchemaBaseTestCase, cls).setUpClass()
        cls.schema = Schema(connection)


    def assertColumnExists(self, table, name, exists=True):
        self.assertEqual(exists, self.schema.sql.column_exists(table, name))


    def assertIndexExists(self, table, name, exists=True):
        self.assertEqual(
            exists,
            self.schema.sql.index_exists(
                self.schema.sql.get_index_name(table, name)
            )
        )


    def assertForeignKeyConstraintExists(self, table, column, rel_table, rel_column, exists=True):
        self.assertEqual(
            exists,
            self.schema.sql.foreign_key_constraint_exists(table, column, rel_table, rel_column)
        )


@CubaneTestCase.complex()
class DBMigrateSchemaVendorTestCase(CubaneManualTransactionTestCase):
    def test_should_create_postgresql_vendor_for_postgresql(self):
        self.assertIsInstance(Schema(connection).sql, PostgresSql)


    @patch('django.db.connection')
    def test_should_raise_not_implemented_error_for_other_than_postgresql(self, connection):
        connection.vendor = 'not-postgresql'
        with self.assertRaisesRegexp(NotImplementedError, 'is currently not supported'):
            Schema(connection)


class DBMigrateSchemaKeepIndiciesTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_prevent_dropping_index_added_to_keep(self):
        table = TestModel._meta.db_table
        index_name = self.schema.sql.get_index_name(table, 'title')
        self.schema.keep_indicies([index_name])
        self.schema.begin()
        try:
            # even though we are dropping the index, the index should not
            # actually be removed, since we instructed the system to
            # keep this index, despite what the model dictates...
            self.schema.drop_index(table, index_name)
            self.assertTrue(self.schema.sql.index_exists(index_name))
        finally:
            self.schema.rollback()


class DBMigrateSchemaGetColumnNamesTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_return_names_of_table_columns_for_given_model(self):
        self.assertEqual(
            [
                'created_by_id',
                'created_on',
                'deleted_by_id',
                'deleted_on',
                'id',
                'image_id',
                'seq',
                'text',
                'title',
                'updated_by_id',
                'updated_on'
            ],
            self.schema.get_column_names(TestModel)
        )


class DBMigrateSchemaTransactionsTestCase(DBMigrateSchemaBaseTestCase):
    def test_begin_should_start_new_transaction(self):
        # each test runs within a transaction already, so make sure we are
        # stepping out of it.
        self.schema.rollback()
        try:
            # now we should see new transactions being created for each statement
            self.assertNotEqual(self.get_tid(), self.get_tid())

            # starting another transaction should 'freeze' the transaction id
            self.schema.begin()
            self.assertEqual(self.get_tid(), self.get_tid())
        finally:
            self.schema.rollback()


    def test_rollback_should_rollback_transaction(self):
        self.schema.begin()
        try:
            self.schema.drop_field(TestModel, 'seq')

            # field has been dropped
            self.assertFalse(self.schema.sql.column_exists(TestModel._meta.db_table, 'seq'))

            # rollback should undo any changes we made
            self.schema.rollback()
            self.assertTrue(self.schema.sql.column_exists(TestModel._meta.db_table, 'seq'))
        finally:
            self.schema.rollback()


    def test_commit_should_apply_changes(self):
        self.schema.begin()
        try:
            self.schema.drop_field(TestModel, 'seq')
            self.schema.commit()

            # we should not be able to rollback from this. drop field
            # actually happend
            self.schema.rollback()
            self.assertFalse(self.schema.sql.column_exists(TestModel._meta.db_table, 'seq'))

            # undo changes for next test case
            field = TestModel._meta.get_field('seq')
            self.schema.create_field(TestModel, field)
        finally:
            self.schema.rollback()


    def get_tid(self):
        return self.schema.sql.select_value('select txid_current();')


class DBMigrateSchemaGetTableNamesTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_return_all_table_names(self):
        tables = self.schema.get_table_names()
        self.assertIn('auth_user', tables)
        self.assertIn('testapp_custompage', tables)
        self.assertIn('testapp_testmodel', tables)
        self.assertTrue(len(tables) >= 40)


class DBMigrateSchemaTableExistsTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_return_true_if_table_exists(self):
        self.assertTrue(self.schema.table_exists(TestModel))


    def test_should_return_false_if_table_does_not_exist(self):
        self.schema.begin()
        try:
            self.schema.sql.rename_table(TestModel._meta.db_table, 'renamed_testmodel')
            self.assertFalse(self.schema.table_exists(TestModel))
        finally:
            self.schema.rollback()


class DBMigrateSchemaGetModelFieldsTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_yield_model_fields(self):
        self.assertEqual(
            [
                (models.AutoField,     'id'),
                (models.DateTimeField, 'created_on'),
                (models.ForeignKey,    'created_by'),
                (models.DateTimeField, 'updated_on'),
                (models.ForeignKey,    'updated_by'),
                (models.DateTimeField, 'deleted_on'),
                (models.ForeignKey,    'deleted_by'),
                (models.IntegerField,  'seq'),
                (models.CharField,     'title'),
            ],
            [(f.__class__, f.name) for f in self.schema.get_model_fields(TestModelWithManyToMany)]
        )


    def test_should_ignore_field_does_not_exist(self):
        self.assertEqual(
            [
                (models.AutoField,                 'id'),
                (models.DateTimeField,             'created_on'),
                (models.ForeignKey,                'created_by'),
                (models.DateTimeField,             'updated_on'),
                (models.ForeignKey,                'updated_by'),
                (models.DateTimeField,             'deleted_on'),
                (models.ForeignKey,                'deleted_by'),
                (models.CharField,                 'uid'),
                (models.CharField,                 'hashid'),
                (models.ForeignKey,                'parent'),
                (models.BooleanField,              'share_enabled'),
                (models.CharField,                 'share_filename'),
                (models.CharField,                 'caption'),
                (models.CharField,                 'credits'),
                (models.CharField,                 'filename'),
                (models.IntegerField,              'width'),
                (models.IntegerField,              'height'),
                (models.BooleanField,              'is_image'),
                (models.BooleanField,              'has_preview'),
                (models.BooleanField,              'is_member_image'),
                (models.BooleanField,              'is_blank'),
                (models.IntegerField,              'member_id'),
                (models.CharField,                 'extra_image_title'),
                (models.BooleanField,              'is_svg'),
                (models.BooleanField,              'auto_fit'),
                (models.CharField,                 'external_url'),
                (models.IntegerField,              'version'),
                (models.PositiveSmallIntegerField, 'org_quality'),
                (models.PositiveSmallIntegerField, 'jpeg_quality'),
                (models.FloatField,                'focal_x'),
                (models.FloatField,                'focal_y')
            ],
            [(f.__class__, f.name) for f in self.schema.get_model_fields(Media)]
        )


class DBMigrateSchemaIsAutoNowFieldTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_return_true_if_auto_now_add_is_true_for_datetime_field(self):
        field = models.DateTimeField(auto_now_add=True)
        self.assertTrue(self.schema.is_auto_now_field(field))


    def test_should_return_true_if_default_is_datetime_now_property(self):
        field = models.DateTimeField(default=datetime.now)
        self.assertTrue(self.schema.is_auto_now_field(field))


    def test_should_return_true_if_default_is_timezone_now_property(self):
        field = models.DateTimeField(default=timezone.now)
        self.assertTrue(self.schema.is_auto_now_field(field))


    def test_should_return_false_if_auto_now_add_is_set_but_field_is_not_a_datetime_field(self):
        field = Mock()
        field.auto_now_add = True
        self.assertFalse(self.schema.is_auto_now_field(field))


class DBMigrateSchemaCreateTableTestCase(DBMigrateSchemaBaseTestCase):
    def test_create_table_shoukld_raise_exception_if_table_already_exists(self):
        self.schema.begin()
        try:
            with self.assertRaisesRegexp(DatabaseError, 'already exists'):
                self.schema.create_table(TestModel)
        finally:
            self.schema.rollback()


    def test_create_table_should_create_table_for_given_model(self):
        self.schema.begin()
        try:
            self.schema.sql.drop_table(TestModel._meta.db_table)
            self.assertFalse(self.schema.table_exists(TestModel))

            # re-create
            self.schema.create_table(TestModel)
            self.assertTrue(self.schema.table_exists(TestModel))
        finally:
            self.schema.rollback()


class DBMigrateSchemaRenameTableTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_raise_exception_if_table_does_not_exist(self):
        self.schema.begin()
        try:
            with self.assertRaisesRegexp(DatabaseError, 'does not exist'):
                self.schema.rename_table('does_not_exist', TestModel)
        finally:
            self.schema.rollback()

    def test_should_rename_existing_table(self):
        self.schema.begin()
        try:
            self.schema.sql.rename_table(TestModel._meta.db_table, 'previous_name')

            self.schema.rename_table('previous_name', TestModel)
            self.assertFalse(self.schema.sql.table_exists('previous_name'))
            self.assertTrue(self.schema.sql.table_exists(TestModel._meta.db_table))
        finally:
            self.schema.rollback()


class DBMigrateSchemaCreateFieldTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_raise_exception_if_field_already_exists(self):
        field = TestModel._meta.get_field('seq')
        with self.assertRaisesRegexp(DatabaseError, 'already exists'):
            self.schema.create_field(TestModel, field)


    def test_should_create_field_that_is_not_null_without_default_if_table_is_empty(self):
        table = TestModelWithoutDefault._meta.db_table
        field = TestModelWithoutDefault._meta.get_field('test')
        column = field.column
        self.schema.begin()
        try:
            self.schema.sql.drop_column(table, column)
            self.assertColumnExists(table, column, False)

            self.schema.create_field(TestModelWithoutDefault, field)
            self.assertColumnExists(table, column, True)
        finally:
            self.schema.rollback()


    def test_should_raise_exception_for_field_that_is_not_null_without_default_if_table_is_not_empty(self):
        table = TestModelWithoutDefault._meta.db_table
        field = TestModelWithoutDefault._meta.get_field('test')
        column = field.column
        self.schema.begin()
        try:
            TestModelWithoutDefault.objects.create(title='Foo', test='Bar')
            self.schema.sql.drop_column(table, column)

            with self.assertRaisesRegexp(ValueError, 'must be null or must have a default value'):
                self.schema.create_field(TestModelWithoutDefault, field)
        finally:
            self.schema.rollback()


    def test_should_create_field_with_index(self):
        self.assertCreateField(TestModel, TestModel._meta.get_field('seq'))


    def test_should_create_foreign_key_field(self):
        self.assertCreateField(TestModel, TestModel._meta.get_field('image'), Media, Media._meta.get_field('id'))


    def test_should_create_like_index_for_char_field(self):
        self.assertCreateField(TestModel, TestModel._meta.get_field('title'))


    def assertCreateField(self, model, field, rel_model=None, rel_field=None):
        table = model._meta.db_table
        column = field.column

        rel_table = rel_model._meta.db_table if rel_model else None
        rel_column = rel_field.column if rel_field else None

        self.schema.begin()
        try:
            self.schema.sql.drop_column(table, column)
            self.assertColumnExists(table, column, False)
            self.assertIndexExists(table, column, False)

            if isinstance(field, models.CharField):
                self.assertIndexExists(table, '%s_like' % column, False)

            if rel_table and rel_column:
                self.assertForeignKeyConstraintExists(table, column, rel_table, rel_column, False)

            self.schema.create_field(model, field)

            self.assertColumnExists(table, column)
            self.assertIndexExists(table, column)

            if isinstance(field, models.CharField):
                self.assertIndexExists(table, '%s_like' % column)

            if rel_table and rel_column:
                self.assertForeignKeyConstraintExists(table, column, rel_table, rel_column)
        finally:
            self.schema.rollback()


class DBMigrateSchemaRenameFieldTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_raise_exception_if_column_under_previous_name_does_not_exist(self):
        self.schema.begin()
        try:
            field = TestModel._meta.get_field('seq')
            with self.assertRaisesRegexp(DatabaseError, 'does not exist'):
                self.schema.rename_field(TestModel, 'does_not_exist', field)
        finally:
            self.schema.rollback()


    def test_should_rename_column_and_index(self):
        self.assertRenameField(TestModel, TestModel._meta.get_field('seq'))


    def test_should_rename_foreignkey_constraint(self):
        self.assertRenameField(TestModel, TestModel._meta.get_field('image'), Media, Media._meta.get_field('id'))


    def test_should_rename_like_index_for_char_field(self):
        self.assertRenameField(TestModel, TestModel._meta.get_field('title'))


    def assertRenameField(self, model, field, rel_model=None, rel_field=None):
        table = model._meta.db_table
        column = field.column
        old_column = '%s_old' % column

        rel_table = rel_model._meta.db_table if rel_model else None
        rel_column = rel_field.column if rel_field else None

        self.schema.begin()
        try:
            self.schema.sql.rename_column(table, column, old_column)
            self.schema.sql.rename_column_index(table, column, old_column)

            if isinstance(field, models.CharField):
                self.schema.sql.rename_like_index(table, column, old_column)

            if rel_table:
                self.schema.sql.rename_foreign_key_constraint(table, column, old_column, rel_table, rel_column)

            self.assertColumnExists(table, column, False)
            self.assertIndexExists(table, column, False)

            if isinstance(field, models.CharField):
                self.assertIndexExists(table, '%s_like' % column, False)

            if rel_table and rel_column:
                self.assertForeignKeyConstraintExists(table, column, rel_table, rel_column, False)

            self.schema.rename_field(model, old_column, field)

            self.assertColumnExists(table, column)
            self.assertIndexExists(table, column)

            if isinstance(field, models.CharField):
                self.assertIndexExists(table, '%s_like' % column)

            if rel_table:
                self.assertForeignKeyConstraintExists(table, column, rel_table, rel_column)
        finally:
            self.schema.rollback()


class DBMigrateSchemaDefaultAddedTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_return_true_if_default_value_was_added(self):
        field = TestModel._meta.get_field('title')
        self.assertTrue(self.schema.default_added(field, None))


    def test_should_return_false_if_default_value_is_present_in_model_and_database(self):
        field = TestModel._meta.get_field('title')
        self.assertFalse(self.schema.default_added(field, 'default value'))


    def test_should_return_false_if_no_default_value_is_present_in_model_nor_database(self):
        field = TestModel._meta.get_field('text')
        self.assertFalse(self.schema.default_added(field, None))


    def test_should_return_false_if_default_value_was_removed(self):
        field = TestModel._meta.get_field('text')
        self.assertFalse(self.schema.default_added(field, 'default value'))


class DBMigrateSchemaDefaultRemovedTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_return_true_if_default_value_was_removed(self):
        field = TestModel._meta.get_field('text')
        self.assertTrue(self.schema.default_removed(field, 'default value'))


    def test_should_return_false_if_default_value_is_present_in_model_and_database(self):
        field = TestModel._meta.get_field('title')
        self.assertFalse(self.schema.default_removed(field, 'default value'))


    def test_should_return_false_if_no_default_value_is_present_in_model_nor_database(self):
        field = TestModel._meta.get_field('text')
        self.assertFalse(self.schema.default_removed(field, None))


    def test_should_return_false_if_default_value_was_added(self):
        field = TestModel._meta.get_field('title')
        self.assertFalse(self.schema.default_removed(field, None))


class DBMigrateSchemaUpdateFieldTestCase(DBMigrateSchemaBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(DBMigrateSchemaUpdateFieldTestCase, cls).setUpClass()
        cls.schema = Schema(connection)
        cls.model = TestModel
        cls.table = cls.model._meta.db_table


    def test_should_add_default_if_not_present(self):
        field = self.model._meta.get_field('title')
        self.schema.begin()
        try:
            self.schema.sql.drop_column_default(self.table, field.column)
            self.schema.update_field(self.model, field)
            self.assertEqual(
                '',
                self.schema.sql.get_column_default(self.table, field.column)
            )
        finally:
            self.schema.rollback()


    def test_should_remove_default_if_present(self):
        field = self.model._meta.get_field('text')
        self.schema.begin()
        try:
            self.schema.sql.set_column_default(self.table, field.column, '')
            self.schema.update_field(self.model, field)
            self.assertIsNone(self.schema.sql.get_column_default(self.table, field.column))
        finally:
            self.schema.rollback()


    def test_should_add_null_constraint_if_not_present(self):
        field = self.model._meta.get_field('text')
        self.schema.begin()
        try:
            self.schema.sql.make_not_nullable(self.table, field.column)
            self.schema.update_field(self.model, field)
            self.assertTrue(self.schema.sql.column_is_nullable(self.table, field.column))
        finally:
            self.schema.rollback()


    def test_should_drop_null_constraint_if_present(self):
        field = self.model._meta.get_field('title')
        self.schema.begin()
        try:
            self.schema.sql.make_nullable(self.table, field.column)
            self.schema.update_field(self.model, field)
            self.assertFalse(self.schema.sql.column_is_nullable(self.table, field.column))
        finally:
            self.schema.rollback()


class DBMigrateSchemaUpdateFieldAddIndexTestCase(DBMigrateSchemaBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(DBMigrateSchemaUpdateFieldAddIndexTestCase, cls).setUpClass()
        cls.schema = Schema(connection)
        cls.model = TestLikeIndexUniqueModel
        cls.table = cls.model._meta.db_table


    def test_should_add_index_if_not_present(self):
        self._test_add_index('title', 'key', unique=True)


    def test_should_add_like_index_for_char_field_if_not_present(self):
        self._test_add_index('title', 'like', unique=False)


    def test_should_add_index_and_like_index_if_not_present(self):
        field = self.model._meta.get_field('title')
        index_name = self.schema.sql.get_index_name(self.table, field.column, unique=True)
        like_index_name = self.schema.sql.get_like_index_name(self.table, field.column)
        self.schema.begin()
        try:
            self.schema.sql.drop_index(self.table, index_name)
            self.schema.sql.drop_index(self.table, like_index_name)
            self.schema.update_field(self.model, field)
            self.assertTrue(self.schema.sql.index_exists(index_name))
            self.assertTrue(self.schema.sql.is_index_unique(index_name))
            self.assertTrue(self.schema.sql.index_exists(like_index_name))
        finally:
            self.schema.rollback()


    def test_should_make_index_unique_if_not_unique_yet(self):
        field = self.model._meta.get_field('title')
        index_name = self.schema.sql.get_index_name(self.table, field.column, unique=True)
        self.schema.begin()
        try:
            self.schema.sql.drop_index(self.table, index_name)
            self.schema.sql.create_column_index(self.table, 'title', unique=False)
            self.schema.update_field(self.model, field)
            self.assertTrue(self.schema.sql.index_exists(index_name))
            self.assertTrue(self.schema.sql.is_index_unique(index_name))
        finally:
            self.schema.rollback()


    def test_should_make_new_unique_index_if_existing_unique_index_has_incorrect_name(self):
        field = self.model._meta.get_field('title')
        index_name = self.schema.sql.get_index_name(self.table, field.column)
        unique_index_name = self.schema.sql.get_index_name(self.table, field.column, unique=True)
        self.schema.begin()
        try:
            self.schema.sql.drop_index(self.table, unique_index_name)
            self.schema.sql.sql('CREATE UNIQUE INDEX %s ON %s (%s);' % (
                index_name,
                self.table,
                field.column
            ))
            self.assertTrue(self.schema.sql.is_index_unique(index_name))

            self.schema.update_field(self.model, field)

            self.assertFalse(self.schema.sql.index_exists(index_name))
            self.assertTrue(self.schema.sql.index_exists(unique_index_name))
            self.assertTrue(self.schema.sql.is_index_unique(unique_index_name))
        finally:
            self.schema.rollback()


    def _test_add_index(self, fieldname, index_postfix, unique):
        field = self.model._meta.get_field(fieldname)
        if index_postfix == 'key':
            index_name = self.schema.sql.get_index_name(self.table, field.column, unique=True)
        elif index_postfix == 'like':
            index_name = self.schema.sql.get_like_index_name(self.table, field.column)

        self.schema.begin()
        try:
            self.schema.sql.drop_index(self.table, index_name)
            self.schema.update_field(self.model, field)
            self.assertTrue(self.schema.sql.index_exists(index_name))

            if unique:
                self.assertTrue(self.schema.sql.is_index_unique(index_name))
        finally:
            self.schema.rollback()


class DBMigrateSchemaUpdateFieldDropIndexTestCase(DBMigrateSchemaBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(DBMigrateSchemaUpdateFieldDropIndexTestCase, cls).setUpClass()
        cls.schema = Schema(connection)
        cls.model = TestFieldWithoutIndexModel
        cls.table = cls.model._meta.db_table


    def test_should_drop_index_if_present(self):
        self._test_drop_index('title', unique=False)


    def test_should_drop_index(self):
        self._test_drop_index('id', unique=False)


    def test_should_drop_unique_index_if_present(self):
        self._test_drop_index('title', unique=True)


    def test_should_drop_index_and_like_index_if_present(self):
        field = self.model._meta.get_field('title')
        index_name = self.schema.sql.get_index_name(self.table, field.column, unique=True)
        like_index_name = self.schema.sql.get_like_index_name(self.table, field.column)
        self.schema.begin()
        try:
            self.schema.sql.create_column_index(self.table, 'title', True)
            self.schema.sql.create_like_index(self.table, 'title')
            self.schema.update_field(self.model, field)
            self.assertFalse(self.schema.sql.index_exists(index_name))
            self.assertFalse(self.schema.sql.index_exists(index_name + '_key'))
            self.assertFalse(self.schema.sql.index_exists(index_name + '_like'))
        finally:
            self.schema.rollback()


    def _test_drop_index(self, fieldname, unique):
        field = self.model._meta.get_field(fieldname)
        index_name = self.schema.sql.get_index_name(self.table, field.column)
        unique_index_name = self.schema.sql.get_index_name(self.table, field.column, unique=True)
        self.schema.begin()
        try:
            self.schema.sql.create_column_index(self.table, 'title', unique)
            self.schema.update_field(self.model, field)
            self.assertFalse(self.schema.sql.index_exists(index_name))
            self.assertFalse(self.schema.sql.index_exists(unique_index_name))
        finally:
            self.schema.rollback()


class DBMigrateSchemaUpdateFieldDropUniqueConstraintTestCase(DBMigrateSchemaBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(DBMigrateSchemaUpdateFieldDropUniqueConstraintTestCase, cls).setUpClass()
        cls.schema = Schema(connection)
        cls.model = TestLikeIndexNotUniqueModel
        cls.table = cls.model._meta.db_table


    def test_should_drop_unique_constraint_if_unique(self):
        field = self.model._meta.get_field('title')
        index_name = self.schema.sql.get_index_name(self.table, field.column)
        self.schema.begin()
        try:
            self.schema.sql.create_column_index(self.table, 'title', True)
            self.schema.update_field(self.model, field)
            self.assertTrue(self.schema.sql.index_exists(index_name))
            self.assertFalse(self.schema.sql.index_exists(index_name + '_key'))
            self.assertFalse(self.schema.sql.is_index_unique(index_name))
        finally:
            self.schema.rollback()


class DBMigrateSchemaUpdateFieldNotNullableFieldWithoutDefaultTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_raise_exception_if_drop_null_constraint_conflicts_with_existing_data_being_null_without_having_a_default(self):
        model = TestModelNotNullableWithoutDefault
        table = model._meta.db_table
        field = model._meta.get_field('title')
        self.schema.begin()
        try:
            # make column nullable and insert some data with NULL values.
            self.schema.sql.make_nullable(table, field.column)
            self.schema.sql.sql('insert into %s (title) VALUES (NULL);' % table)

            # making the column NOT NULL-able again should raise an
            # exception, because we do have NULL values in the dataset and no
            # default value for the column
            with self.assertRaisesRegexp(ValueError, 'is suppose to be NOT NULL but contains NULL values'):
                self.schema.update_field(model, field)
        finally:
            self.schema.rollback()


    def test_should_update_null_values_to_default_if_drop_null_constraint_with_existing_data_being_null_but_having_a_default(self):
        model = TestModelNotNullableWithDefault
        table = model._meta.db_table
        field = model._meta.get_field('title')
        self.schema.begin()
        try:
            # make column nullable and insert some data with NULL values.
            self.schema.sql.make_nullable(table, field.column)
            self.schema.sql.sql('insert into %s (title) VALUES (NULL);' % table)

            # making the column NOT NULL-able again should automatically
            # update NULL values with the default value of the field
            # before making the field not nullable.
            self.schema.update_field(model, field)
            self.assertFalse(self.schema.sql.column_is_nullable(table, field.column))
        finally:
            self.schema.rollback()


class DBMigrateSchemaUpdateFieldChangeVarCharLengthTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_decrease_varchar_length(self):
        model = TestModel
        table = model._meta.db_table
        field = model._meta.get_field('title')
        self.schema.begin()
        try:
            # make column length bigger than it is defined right now
            self.schema.sql.change_column_data_type(table, field.column, 'varchar(512)')

            # updating field should bring it back to normal size
            self.schema.update_field(model, field)
            dt, max_length = self.schema.sql.get_column_datatype(table, field.column)
            self.assertEqual('varchar', dt)
            self.assertEqual(255, max_length)
        finally:
            self.schema.rollback()


    def test_should_increase_varchar_length(self):
        model = TestModel
        table = model._meta.db_table
        field = model._meta.get_field('title')
        self.schema.begin()
        try:
            # make column length smaller than it is defined right now
            self.schema.sql.change_column_data_type(table, field.column, 'varchar(128)')

            # updating field should bring it back to normal size
            self.schema.update_field(model, field)
            dt, max_length = self.schema.sql.get_column_datatype(table, field.column)
            self.assertEqual('varchar', dt)
            self.assertEqual(255, max_length)
        finally:
            self.schema.rollback()


class DBMigrateSchemaDropFieldTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_drop_field(self):
        self.schema.begin()
        try:
            self.schema.drop_field(TestModel, 'title')
            self.assertFalse(self.schema.sql.column_exists(TestModel._meta.db_table, 'title'))
        finally:
            self.schema.rollback()


    def test_should_raise_exception_if_column_does_not_exist(self):
        with self.assertRaisesRegexp(DatabaseError, 'does not exist'):
            self.schema.drop_field(TestModel, 'does_not_exist')


class DBMigrateSchemaGetFtsColumnsForModelTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_return_fts_columns_for_model(self):
        self.assertEqual(
            {'fts_index': ['partno', 'name']},
            self.schema.get_fts_columns_for_model(TestFTSPart)
        )


    def test_should_return_empty_fts_definition_if_fts_columns_do_not_exist(self):
        self.assertEqual(
            {},
            self.schema.get_fts_columns_for_model(TestModel)
        )


class DBMigrateSchemaFtsInstallForColumnTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_install_fts_indices(self):
        model = TestFTSPart
        table = model._meta.db_table
        column = 'fts_index'
        fields = ['partno', 'name']
        fieldnames = '_'.join(fields)
        index_name = 'cubane_fts_%s_%s' % (table, column)
        trigger_name = 'cubane_fts_%s_%s_%s' % (table, column, fieldnames)

        self.schema.begin()
        try:
            self.schema.fts_install_for_column(model, column, fields)
            self.assertTrue(self.schema.sql.column_exists(table, column))
            self.assertTrue(self.schema.sql.index_exists(index_name))
            self.assertTrue(self.schema.sql.trigger_exists(table, trigger_name))
        finally:
            self.schema.rollback()


    def test_should_raise_exception_if_column_does_not_start_with_fts(self):
        with self.assertRaisesRegexp(ValueError, 'must start with \'fts_\''):
            self.schema.fts_install_for_column(TestFTSPart, 'test', ['test'])


class DBMigrateSchemaFtsRemoveFieldsTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_remove_deprecated_indices_and_triggers(self):
        model = TestModel
        table = model._meta.db_table

        self.schema.begin()
        try:
            self.schema.fts_install_for_column(model, 'fts_index1', ['title'])
            self.schema.fts_install_for_column(model, 'fts_index2', ['text'])
            self.schema.fts_remove_fields(model, {'fts_index2': ['text']})

            self.assertFalse(self.schema.sql.column_exists(table, 'fts_index1'))
            self.assertTrue(self.schema.sql.column_exists(table, 'fts_index2'))

            self.assertFalse(self.schema.sql.index_exists('cubane_fts_%s_fts_index1' % table))
            self.assertTrue(self.schema.sql.index_exists('cubane_fts_%s_fts_index2' % table))

            self.assertFalse(self.schema.sql.trigger_exists(table, 'cubane_fts_%s_fts_index1_title' % table))
            self.assertTrue(self.schema.sql.trigger_exists(table, 'cubane_fts_%s_fts_index2_text' % table))
        finally:
            self.schema.rollback()


class DBMigrateSchemaFtsReindexModelTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_update_fts_columns(self):
        self.schema.sql.fts_index = MagicMock()
        self.schema.fts_reindex_model(TestFTSPart)
        self.schema.sql.fts_index.assert_called_with('testapp_testftspart', ['partno'])


class DBMigrateSchemaFtsReindexTestCase(DBMigrateSchemaBaseTestCase):
    def test_should_reindex_all_models(self):
        self.schema.sql.fts_index = MagicMock()
        self.schema.fts_reindex()
        self.schema.sql.fts_index.assert_called_with('testapp_product', ['title'])