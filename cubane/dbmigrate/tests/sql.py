# coding=UTF-8
from __future__ import unicode_literals
from django.db import connection
from django.db import models
from django.db.utils import DatabaseError
from cubane.tests.base import CubaneManualTransactionTestCase
from cubane.dbmigrate.sql import PostgresSql
from cubane.media.models import Media
from cubane.testapp.models import TestModel, TestTreeNode
from datetime import datetime


@CubaneManualTransactionTestCase.complex()
class DBMigrateSqlPostgresTestCase(CubaneManualTransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super(DBMigrateSqlPostgresTestCase, cls).setUpClass()
        cls.sql = PostgresSql(connection)
        cls.table = TestModel._meta.db_table
        cls.rel_table = Media._meta.db_table


class DBMigrateSqlPostgresQTestCase(DBMigrateSqlPostgresTestCase):
    @classmethod
    def setUpClass(cls):
        super(DBMigrateSqlPostgresQTestCase, cls).setUpClass()
        cls.sql = PostgresSql(connection)


    def test_none_should_become_null(self):
        self.assertEqual('NULL', self.sql.q(None))


    def test_bool_should_become_true_or_false(self):
        self.assertEqual('true', self.sql.q(True))
        self.assertEqual('false', self.sql.q(False))


    def test_int_should_become_number_as_string(self):
        self.assertEqual('12345', self.sql.q(12345))


    def test_float_should_become_float_as_string(self):
        self.assertEqual('1.250000', self.sql.q(1.25))


    def test_string_should_be_quoted(self):
        self.assertEqual('\'table\'', self.sql.q('table'))


class DBMigrateSqlPostgresGetDataTypeFromFieldTestCase(DBMigrateSqlPostgresTestCase):
    def test_charfield_or_slugfield_should_become_varchar(self):
        self.assertEqual('varchar(16)', self.sql.get_data_type_from_field(models.CharField(max_length=16)))


    def test_textfield_should_become_text(self):
        self.assertEqual('text', self.sql.get_data_type_from_field(models.TextField()))


    def test_textfield_with_max_length_should_become_text_without_length(self):
        self.assertEqual('text', self.sql.get_data_type_from_field(models.TextField(max_length=16)))


    def test_integer_field_should_become_integer(self):
        self.assertEqual('integer', self.sql.get_data_type_from_field(models.IntegerField()))


    def test_foreignkey_field_should_become_integer(self):
        # TODO: This is actually not always correct, a foreign key might not be
        # of type integer. However, the cirrect version of cubane makes that
        # assumtion and we will fix this at a later stage
        self.assertEqual('integer', self.sql.get_data_type_from_field(models.ForeignKey(TestModel)))


    def test_float_field_should_become_float(self):
        self.assertEqual('float', self.sql.get_data_type_from_field(models.FloatField()))


    def test_decimal_field_should_become_decimal(self):
        self.assertEqual('decimal(5, 2)', self.sql.get_data_type_from_field(models.DecimalField(max_digits=5, decimal_places=2)))


    def test_boolean_field_should_become_bool(self):
        self.assertEqual('bool', self.sql.get_data_type_from_field(models.BooleanField()))


    def test_datetime_field_should_become_datetime_with_timezone(self):
        self.assertEqual('timestamp with time zone', self.sql.get_data_type_from_field(models.DateTimeField()))


    def test_date_field_should_become_date(self):
        self.assertEqual('date', self.sql.get_data_type_from_field(models.DateField()))


    def test_time_field_should_become_time(self):
        self.assertEqual('time', self.sql.get_data_type_from_field(models.TimeField()))


    def test_unknown_field_type_should_raise_value_error(self):
        with self.assertRaisesRegexp(ValueError, 'Unknown field type'):
            self.sql.get_data_type_from_field('unknown field type')


class DBMigrateSqlPostgresGetTableNamesTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_list_of_table_names(self):
        # test for a few tables that should exists, not all because otherwise
        # this test will break every time we add some new models/tables to
        # the test app
        table_names = self.sql.get_table_names()
        for table_name in ['auth_group', 'auth_user']:
            self.assertIn(table_name, table_names)


class DBMigrateSqlPostgresGetColumnNamesTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_list_of_column_names(self):
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
            self.sql.get_column_names(self.table)
        )


class DBMigrateSqlPostgresGetFunctionNamesTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_list_of_all_functions(self):
        # test the existance of a few standard postgresql functions
        function_names = self.sql.get_function_names()
        for function_name in ['ts_rank', 'textcat', 'random']:
            self.assertIn(function_name, function_names)


class DBMigrateSqlPostgresGetIndicesTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_list_of_all_indices(self):
        existing_indices = self.sql.get_indices(self.table)
        expected_indices = [
            'created_by_id',
            'created_on',
            'deleted_by_id',
            'deleted_on',
            'image_id',
            'pkey',
            'seq',
            'title',
            'title_like',
            'updated_by_id',
            'updated_on'
        ]

        self.assertEqual(len(expected_indices), len(existing_indices))
        for expected_index in expected_indices:
            expected_index_name = self.sql.get_index_name(self.table, expected_index)
            self.assertTrue(expected_index_name in existing_indices, 'Column \'%s\' (\'%s\') expected to be present. Existing indices: %s' % (
                expected_index,
                expected_index_name,
                ', '.join(['\'%s\'' % name for name in existing_indices])
            ))


class DBMigrateSqlPostgresGetTriggersTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_list_of_all_triggers(self):
        self.sql.begin()
        try:
            trigger_name = 'cubane_test_trigger'
            self.sql.create_trigger(
                self.table,
                trigger_name,
                'before insert or update',
                'each row',
                'tsvector_update_trigger'
            )

            self.assertEqual([trigger_name], self.sql.get_triggers(self.table))
            self.sql.drop_trigger(self.table, trigger_name)
        except:
            self.sql.rollback()
            raise


class DBMigrateSqlPostgresTransactionsTestCase(DBMigrateSqlPostgresTestCase):
    def test_begin_should_start_new_transaction(self):
        # each test runs within a transaction already, so make sure we are
        # stepping out of it.
        self.sql.rollback()

        # now we should see new transactions being created for each statement
        self.assertNotEqual(self.get_tid(), self.get_tid())

        # starting another transaction should 'freeze' the transaction id
        self.sql.begin()
        self.assertEqual(self.get_tid(), self.get_tid())


    def test_rollback_should_rollback_transaction(self):
        new_table = self.table + '_test'

        self.sql.begin()
        self.sql.rename_table(self.table, new_table)

        # table has been renamed
        self.assertFalse(self.sql.table_exists(self.table))
        self.assertTrue(self.sql.table_exists(new_table))

        # rollback should undo any changes we made
        self.sql.rollback()
        self.assertTrue(self.sql.table_exists(self.table))
        self.assertFalse(self.sql.table_exists(new_table))


    def test_commit_should_apply_changes(self):
        new_table = self.table + '_test'

        self.sql.begin()
        self.sql.rename_table(self.table, new_table)
        self.sql.commit()

        # we should not be able to rollback from this
        self.sql.rollback()

        # rename actually happend
        self.assertFalse(self.sql.table_exists(self.table))
        self.assertTrue(self.sql.table_exists(new_table))

        # undo changes for next test case
        self.sql.rename_table(new_table, self.table)


    def get_tid(self):
        return self.sql.select_value('select txid_current();')


class DBMigrateSqlPostgresTableExistsTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_table_exists(self):
        self.assertTrue(self.sql.table_exists(self.table))


    def test_should_return_false_if_table_does_not_exist(self):
        self.assertFalse(self.sql.table_exists('does_not_exist'))


class DBMigrateSqlPostgresRenameTableTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_rename_table(self):
        new_table = self.table + '_test'
        self.assertTrue(self.sql.table_exists(self.table))
        self.assertFalse(self.sql.table_exists(new_table))

        self.sql.rename_table(self.table, new_table)

        self.assertFalse(self.sql.table_exists(self.table))
        self.assertTrue(self.sql.table_exists(new_table))
        self.sql.rename_table(new_table, self.table)


class DBMigrateSqlPostgresDropTableTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_raise_exception_if_table_does_not_exist(self):
        with self.assertRaisesRegexp(DatabaseError, 'does not exist'):
            self.sql.drop_table('does_not_exist')


    def test_should_drop_table(self):
        self.sql.begin()
        self.sql.drop_table('testapp_testmodel')
        self.assertFalse(self.sql.table_exists('testapp_testmodel'))
        self.sql.rollback()


class DBMigrateSqlPostgresColumnExistsTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_column_exists(self):
        self.assertTrue(self.sql.column_exists(self.table, 'title'))


    def test_should_return_false_if_column_does_not_exist(self):
        self.assertFalse(self.sql.column_exists(self.table, 'does_not_exist'))


class DBMigrateSqlPostgresIndexExistsTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_index_exists(self):
        self.assertTrue(self.sql.index_exists('testapp_testmodel_pkey'))


    def test_should_return_false_if_index_does_not_exist(self):
        self.assertFalse(self.sql.index_exists('does_not_exist'))


class DBMigrateSqlPostgresIsIndexUniqueTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_index_is_unqiue(self):
        self.sql.begin()
        try:
            index_name = self.sql.get_index_name(self.table, 'title')
            index_name_key = self.sql.get_index_name(self.table, 'title', unique=True)
            self.sql.drop_index(self.table, index_name)
            self.sql.create_column_index(self.table, 'title', unique=True)
            self.assertEqual(False, self.sql.is_index_unique(index_name))
            self.assertEqual(True, self.sql.is_index_unique(index_name_key))
        finally:
            self.sql.rollback()


    def test_should_return_false_if_index_is_not_unique(self):
        self.assertEqual(False, self.sql.is_index_unique('testapp_testmodel_title'))


    def test_should_return_false_if_index_does_not_exist(self):
        self.assertEqual(False, self.sql.is_index_unique('testapp_testmodel_does_not_exist'))


class DBMigrateSqlPostgresRenameIndexTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_rename_index(self):
        name = 'testapp_testmodel_pkey'
        new_name = name + '_test'
        self.assertTrue(self.sql.index_exists(name))
        self.assertFalse(self.sql.index_exists(new_name))

        self.sql.begin()
        try:
            self.sql.rename_index(self.table, name, new_name)
            self.assertFalse(self.sql.index_exists(name))
            self.assertTrue(self.sql.index_exists(new_name))
        finally:
            self.sql.rollback()


    def test_should_ignore_if_index_does_not_exist(self):
        name = 'does_not_exist'
        new_name = name + '_test'

        self.sql.begin()
        try:
            self.sql.rename_index(self.table, name, new_name)
            self.assertFalse(self.sql.index_exists(name))
            self.assertFalse(self.sql.index_exists(new_name))
        finally:
            self.sql.rollback()


    def test_should_ignore_if_target_index_already_exists(self):
        name = 'testapp_testmodel_pkey'
        new_name = self.sql.get_index_name(self.table, 'seq')

        self.sql.begin()
        try:
            self.sql.rename_index(self.table, name, new_name)
            self.assertTrue(self.sql.index_exists(name))
            self.assertTrue(self.sql.index_exists(new_name))
        finally:
            self.sql.rollback()


class DBMigrateSqlPostgresRenameColumnIndexTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_rename_column_index(self):
        column = 'seq'
        new_column = 'ord'

        seq_index_name = self.sql.get_index_name(self.table, 'seq')
        ord_index_name = self.sql.get_index_name(self.table, 'ord')

        self.assertTrue(self.sql.index_exists(seq_index_name))
        self.assertFalse(self.sql.index_exists(ord_index_name))
        self.sql.rename_column_index(self.table, column, new_column)
        self.assertFalse(self.sql.index_exists(seq_index_name))
        self.assertTrue(self.sql.index_exists(ord_index_name))
        self.sql.rename_column_index(self.table, new_column, column)


class DBMigrateSqlPostgresRenameLikeIndexTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_rename_like_index(self):
        column = 'title'
        new_column = 'headline'

        title_index_name = self.sql.get_like_index_name(self.table, 'title')
        headline_index_name = self.sql.get_like_index_name(self.table, 'headline')

        self.assertTrue(self.sql.index_exists(title_index_name))
        self.assertFalse(self.sql.index_exists(headline_index_name))

        self.sql.begin()
        try:
            self.sql.rename_like_index(self.table, column, new_column)
            self.assertFalse(self.sql.index_exists(title_index_name))
            self.assertTrue(self.sql.index_exists(headline_index_name))
        finally:
            self.sql.rollback()


class DBMigrateSqlPostgresCreateColumnIndexTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_create_index_for_column(self):
        self.sql.create_column_index(self.table, 'text', False)
        index_name = self.sql.get_index_name(self.table, 'text')
        self.assertTrue(self.sql.index_exists(index_name))
        self.sql.drop_index(self.table, index_name)


class DBMigrateSqlPostgresDropIndexTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_drop_index_for_column(self):
        self.sql.create_column_index(self.table, 'text', False)
        index_name = self.sql.get_index_name(self.table, 'text')
        self.assertTrue(self.sql.index_exists(index_name))
        self.sql.drop_index(self.table, index_name)
        self.assertFalse(self.sql.index_exists(index_name))


    def test_should_drop_unique_constraint_for_unique_column(self):
        self.sql.create_column_index(self.table, 'text', True)
        index_name = self.sql.get_index_name(self.table, 'text', unique=True)
        self.assertTrue(self.sql.constraint_exists(self.table, index_name))
        self.assertTrue(self.sql.is_index_unique(index_name))

        self.sql.drop_index(self.table, index_name)

        self.assertFalse(self.sql.index_exists(index_name))
        self.assertFalse(self.sql.constraint_exists(self.table, index_name))


    def test_drop_unique_index_without_constraint_should_remove_index_only(self):
        self.sql.sql('CREATE UNIQUE INDEX %s ON %s (%s);' % (
            'testapp_testmodel_text_key',
            'testapp_testmodel',
            'text'
        ))
        self.assertTrue(self.sql.is_index_unique('testapp_testmodel_text_key'))

        self.sql.drop_index(self.table, 'testapp_testmodel_text_key')

        self.assertFalse(self.sql.index_exists('testapp_testmodel_text_key'))
        self.assertFalse(self.sql.constraint_exists('testapp_testmodel', 'text_key'))


class DBMigrateSqlPostgresCreateLikeIndexTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_create_like_index(self):
        self.sql.drop_index(self.table, self.sql.get_index_name(self.table, 'title_like'))
        self.assertFalse(self.sql.index_exists(self.sql.get_index_name(self.table, 'title_like')))
        self.sql.create_like_index(self.table, 'title')
        self.assertTrue(self.sql.index_exists(self.sql.get_index_name(self.table, 'title_like')))


class DBMigrateSqlPostgresCreateFTSIndexTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_create_fts_index(self):
        column = 'title'
        index_name = 'cubane_fts_%s_%s' % (self.table, column)
        self.assertFalse(self.sql.index_exists(index_name))
        self.sql.create_fts_index(self.table, index_name, 'to_tsvector(\'english\', \'%s\')' % column)
        self.assertTrue(self.sql.index_exists(index_name))
        self.sql.drop_index(self.table, index_name)


class DBMigrateSqlPostgresConstraintExistsTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_constraint_exists(self):
        self.assertTrue(self.sql.constraint_exists(self.table, '%s_pkey' % self.table))


    def test_should_return_false_if_constraint_does_not_exist(self):
        self.assertFalse(self.sql.constraint_exists(self.table, 'does_not_exist'))


class DBMigrateSqlPostgresColumnIsNullableTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_column_is_nullable(self):
        self.sql.make_nullable(self.table, 'title')
        self.assertTrue(self.sql.column_is_nullable(self.table, 'title'))
        self.sql.make_not_nullable(self.table, 'title')


    def test_should_return_false_if_column_is_not_nullable(self):
        self.assertFalse(self.sql.column_is_nullable(self.table, 'title'))


    def test_should_return_false_if_column_does_not_exist(self):
        self.assertFalse(self.sql.column_is_nullable(self.table, 'does_not_exist'))


class DBMigrateSqlPostgresGetColumnDefaultTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_default_for_column(self):
        self.sql.set_column_default(self.table, 'title', 'default')
        self.assertEqual('default', self.sql.get_column_default(self.table, 'title'))
        self.sql.drop_column_default(self.table, 'title')


    def test_should_return_none_for_column_does_not_have_default(self):
        self.assertEqual(None, self.sql.get_column_default(self.table, 'title'))


    def test_should_return_none_for_column_does_not_exist(self):
        self.assertEqual(None, self.sql.get_column_default(self.table, 'does_not_exist'))


class DBMigrateSqlPostgresGetColumnDataTypeTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_datatype_for_varchar_column(self):
        dt, max_length = self.sql.get_column_datatype(self.table, 'title')
        self.assertEqual('varchar', dt)
        self.assertEqual(255, max_length)


    def test_should_return_datatype_for_integer_column(self):
        dt, max_length = self.sql.get_column_datatype(TestTreeNode._meta.db_table, 'seq')
        self.assertEqual('integer', dt)
        self.assertEqual(None, max_length)


    def test_should_return_none_for_column_does_not_exist(self):
        dt, max_length = self.sql.get_column_datatype(self.table, 'does_not_exist')
        self.assertEqual(None, dt)
        self.assertEqual(None, max_length)


class DBMigrateSqlPostgresHasNullValueTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_at_least_one_row_is_null(self):
        a = TestModel(title='a')
        b = TestModel(title='b', text='test')
        a.save()
        b.save()
        self.assertTrue(self.sql.has_null_value(self.table, 'text'))
        a.delete()
        b.delete()


    def test_should_return_false_if_there_is_no_row_that_is_null(self):
        a = TestModel(title='a', text='test a')
        b = TestModel(title='b', text='test b')
        a.save()
        b.save()
        self.assertFalse(self.sql.has_null_value(self.table, 'text'))
        a.delete()
        b.delete()


    def test_should_return_false_if_there_is_no_row_to_begin_with(self):
        self.assertFalse(self.sql.has_null_value(self.table, 'text'))


class DBMigrateSqlPostgresUpdateNullToDefaultTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_update_null_values_to_given_default_value(self):
        a = TestModel(title='a')
        b = TestModel(title='b', text='test')
        a.save()
        b.save()

        self.sql.update_null_to_default(self.table, 'text', 'default')
        self.assertFalse(self.sql.has_null_value(self.table, 'text'))

        a.delete()
        b.delete()


class DBMigrateSqlPostgresDropConstraintTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_drop_constraint(self):
        name = '%s_pkey' % self.table
        self.sql.begin()
        self.assertTrue(self.sql.constraint_exists(self.table, name))
        self.sql.drop_constraint(self.table, name)
        self.assertFalse(self.sql.constraint_exists(self.table, name))
        self.sql.rollback()


class DBMigrateSqlPostgresMakeNullableTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_make_column_nullable_or_not_nullable(self):
        self.assertFalse(self.sql.column_is_nullable(self.table, 'title'))
        self.sql.make_nullable(self.table, 'title')
        self.assertTrue(self.sql.column_is_nullable(self.table, 'title'))
        self.sql.make_not_nullable(self.table, 'title')
        self.assertFalse(self.sql.column_is_nullable(self.table, 'title'))


class DBMigrateSqlPostgresSetAndDropColumnDefaultTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_set_and_drop_column_default(self):
        self.assertEqual(None, self.sql.get_column_default(self.table, 'title'))
        self.sql.set_column_default(self.table, 'title', 'default')
        self.assertEqual('default', self.sql.get_column_default(self.table, 'title'))
        self.sql.drop_column_default(self.table, 'title')
        self.assertEqual(None, self.sql.get_column_default(self.table, 'title'))


class DBMigrateSqlPostgresForeignKeyConstraintExistsTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_foreign_key_constraint_exists(self):
        self.assertTrue(self.sql.foreign_key_constraint_exists(self.table, 'image_id', self.rel_table, 'id'))


    def test_should_return_false_if_foreign_key_constraint_does_not_exist(self):
        self.assertFalse(self.sql.foreign_key_constraint_exists(self.table, 'does_not_exist', self.rel_table, 'id'))


class DBMigrateSqlPostgresCreateAndDropForeignKeyConstraintTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_create_foreign_key_constraint(self):
        self.assertTrue(self.sql.foreign_key_constraint_exists(self.table, 'image_id', self.rel_table, 'id'))
        self.sql.drop_foreign_key_constraint(self.table, 'image_id', self.rel_table, 'id')
        self.assertFalse(self.sql.foreign_key_constraint_exists(self.table, 'image_id', self.rel_table, 'id'))
        self.sql.create_foreign_key_constraint(self.table, 'image_id', self.rel_table, 'id')
        self.assertTrue(self.sql.foreign_key_constraint_exists(self.table, 'image_id', self.rel_table, 'id'))


class DBMigrateSqlPostgresRenameForeignKeyConstraintTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_rename_existing_foreign_key_constraint_renaming_column(self):
        self.sql.begin()
        self.assertTrue(self.sql.foreign_key_constraint_exists(self.table, 'image_id', self.rel_table, 'id'))
        self.sql.rename_column(self.table, 'image_id', 'media_id')
        self.sql.rename_foreign_key_constraint(self.table, 'image_id', 'media_id', self.rel_table, 'id')
        self.assertFalse(self.sql.foreign_key_constraint_exists(self.table, 'image_id', self.rel_table, 'id'))
        self.assertTrue(self.sql.foreign_key_constraint_exists(self.table, 'media_id', self.rel_table, 'id'))
        self.sql.rollback()


    def test_should_rename_existing_foreign_key_constraint_renaming_table(self):
        self.sql.begin()
        self.assertTrue(self.sql.foreign_key_constraint_exists(self.table, 'image_id', self.rel_table, 'id'))
        self.sql.rename_table(self.table, 'test_table')
        self.sql.rename_foreign_key_constraint('test_table', 'image_id', 'image_id', self.rel_table, 'id', old_table=self.table)
        self.assertFalse(self.sql.foreign_key_constraint_exists(self.table, 'image_id', self.rel_table, 'id'))
        self.assertTrue(self.sql.foreign_key_constraint_exists('test_table', 'image_id', self.rel_table, 'id'))
        self.sql.rollback()


class DBMigrateSqlPostgresCreateColumnTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_create_new_column(self):
        column = 'test_column'
        self.sql.begin()
        self.sql.create_column(self.table, column, 'varchar', null=True, default='test')
        self.assertTrue(self.sql.column_exists(self.table, column))
        self.assertTrue(self.sql.column_is_nullable(self.table, column))
        self.assertEqual('test', self.sql.get_column_default(self.table, column))
        self.sql.rollback()


    def test_should_create_new_column_not_nullable_without_default_value(self):
        column = 'test_column'
        self.sql.begin()
        self.sql.create_column(self.table, column, 'varchar', null=False, default=None)
        self.assertTrue(self.sql.column_exists(self.table, column))
        self.assertFalse(self.sql.column_is_nullable(self.table, column))
        self.assertIsNone(self.sql.get_column_default(self.table, column))
        self.sql.rollback()


    def test_should_create_new_column_with_datetime_now_ignoring_default(self):
        column = 'test_column'
        self.sql.begin()
        self.sql.create_column(self.table, column, 'timestamp', null=False, default=datetime.now(), auto_now=True)
        self.assertTrue(self.sql.column_exists(self.table, column))
        self.assertFalse(self.sql.column_is_nullable(self.table, column))
        self.assertEqual('now()', self.sql.get_column_default(self.table, column))
        self.sql.rollback()


class DBMigrateSqlPostgresRenameColumnTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_rename_column(self):
        self.sql.begin()
        self.assertTrue(self.sql.column_exists(self.table, 'title'))
        self.sql.rename_column(self.table, 'title', 'new_title')
        self.assertFalse(self.sql.column_exists(self.table, 'title'))
        self.assertTrue(self.sql.column_exists(self.table, 'new_title'))
        self.sql.rollback()


class DBMigrateSqlPostgresUpdateVarcharLengthTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_crop_varchar_column_values(self):
        self.sql.begin()
        obj = TestModel.objects.create(title='1234567890')
        self.sql.update_varchar_length(self.table, 'title', 4)
        obj = TestModel.objects.get(pk=obj.pk)
        self.assertEqual('1234', obj.title)
        self.sql.rollback()


    def test_should_not_extend_varchar_column_values(self):
        self.sql.begin()
        obj = TestModel.objects.create(title='1234')
        self.sql.update_varchar_length(self.table, 'title', 8)
        obj = TestModel.objects.get(pk=obj.pk)
        self.assertEqual('1234', obj.title)
        self.sql.rollback()


class DBMigrateSqlPostgresChangeColumnDataTypeTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_decrease_varchar_column_length(self):
        self.sql.begin()
        self.sql.change_column_data_type(self.table, 'title', 'varchar(128)')
        dt, max_length = self.sql.get_column_datatype(self.table, 'title')
        self.assertEqual('varchar', dt)
        self.assertEqual(128, max_length)
        self.sql.rollback()


    def test_should_increase_varchar_column_length(self):
        self.sql.begin()
        self.sql.change_column_data_type(self.table, 'title', 'varchar(512)')
        dt, max_length = self.sql.get_column_datatype(self.table, 'title')
        self.assertEqual('varchar', dt)
        self.assertEqual(512, max_length)
        self.sql.rollback()


class DBMigrateSqlPostgresDropColumnTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_drop_column(self):
        self.sql.begin()
        self.assertTrue(self.sql.column_exists(self.table, 'title'))
        self.sql.drop_column(self.table, 'title')
        self.assertFalse(self.sql.column_exists(self.table, 'title'))
        self.sql.rollback()


class DBMigrateSqlPostgresFunctionExistsTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_function_exists(self):
        self.assertTrue(self.sql.function_exists('lower'))


    def test_should_return_false_if_function_does_not_exist(self):
        self.assertFalse(self.sql.function_exists('does_not_exist'))


class DBMigrateSqlPostgresCreateFunctionTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_create_function_withoput_arguments(self):
        self.sql.begin()
        self.sql.create_function('test_magic_number', None, 'int', 'begin\nreturn 42;\nend')
        self.assertTrue(self.sql.function_exists('test_magic_number'))
        self.assertEqual([{'test_magic_number': 42}], self.sql.select('select test_magic_number();'))
        self.sql.rollback()


    def test_should_create_function_with_arguments(self):
        self.sql.begin()
        self.sql.create_function('test_echo', [('name', 'varchar')], 'varchar', 'begin\nreturn $1;\nend')
        self.assertTrue(self.sql.function_exists('test_echo'))
        self.assertEqual([{'test_echo': 'hello world'}], self.sql.select('select test_echo(\'hello world\');'))
        self.sql.rollback()


class DBMigrateSqlPostgresDropFunctionTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_drop_function(self):
        self.sql.create_function('test_echo', [('name', 'varchar')], 'varchar', 'begin\nreturn $1;\nend')
        self.assertTrue(self.sql.function_exists('test_echo'))
        self.sql.drop_function('test_echo(varchar)')
        self.assertFalse(self.sql.function_exists('test_echo'))


class DBMigrateSqlPostgresTriggerExistsTestCase(DBMigrateSqlPostgresTestCase):
    def setUp(self):
        self.trigger_name = 'cubane_test_trigger'


    def test_should_return_true_if_trigger_exists(self):
        self.sql.create_trigger(
            self.table,
            self.trigger_name,
            'before insert or update',
            'each row',
            'tsvector_update_trigger'
        )
        self.assertTrue(self.sql.trigger_exists(self.table, self.trigger_name))
        self.sql.drop_trigger(self.table, self.trigger_name)


    def test_should_return_false_if_trigger_does_not_exist(self):
        self.assertFalse(self.sql.trigger_exists(self.table, self.trigger_name))


class DBMigrateSqlPostgresCreateTriggerTestCase(DBMigrateSqlPostgresTestCase):
    def setUp(self):
        self.trigger_name = 'cubane_test_trigger'


    def test_should_create_trigger_without_arguments(self):
        self.sql.begin()
        self.sql.create_trigger(
            self.table,
            self.trigger_name,
            'before insert or update',
            'each row',
            'tsvector_update_trigger'
        )
        self.assertTrue(self.sql.trigger_exists(self.table, self.trigger_name))
        self.sql.rollback()


    def test_should_create_trigger_with_arguments(self):
        self.sql.begin()
        self.sql.create_trigger(
            self.table,
            self.trigger_name,
            'before insert or update',
            'each row',
            'tsvector_update_trigger',
            arguments=['test']
        )
        self.assertTrue(self.sql.trigger_exists(self.table, self.trigger_name))
        self.sql.rollback()


class DBMigrateSqlPostgresDropTriggerTestCase(DBMigrateSqlPostgresTestCase):
    def setUp(self):
        self.trigger_name = 'cubane_test_trigger'


    def test_should_drop_trigger(self):
        self.sql.create_trigger(
            self.table,
            self.trigger_name,
            'before insert or update',
            'each row',
            'tsvector_update_trigger',
            arguments=['test']
        )
        self.assertTrue(self.sql.trigger_exists(self.table, self.trigger_name))
        self.sql.drop_trigger(self.table, self.trigger_name)
        self.assertFalse(self.sql.trigger_exists(self.table, self.trigger_name))


class DBMigrateSqlPostgresFTSIndexTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_update_column_value(self):
        self.sql.fts_index(self.table, ['title'])


class DBMigrateSqlPostgresHasOneRowTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_the_result_has_one_row(self):
        self.assertTrue(self.sql.has_one_row("select unnest(array['a']);"))


    def test_should_return_false_if_the_result_is_empty(self):
        self.assertFalse(self.sql.has_one_row("select * from %s" % self.table))


    def test_should_return_false_for_multiple_rows(self):
        self.assertFalse(self.sql.has_one_row("select unnest(array['a', 'b', 'c']);"))


class DBMigrateSqlPostgresHasOneOrMoreRowTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_true_if_the_result_has_one_row(self):
        self.assertTrue(self.sql.has_one_or_more_rows("select unnest(array['a']);"))


    def test_should_return_true_for_multiple_rows(self):
        self.assertTrue(self.sql.has_one_or_more_rows("select unnest(array['a', 'b', 'c']);"))


    def test_should_return_false_if_the_result_is_empty(self):
        self.assertFalse(self.sql.has_one_or_more_rows("select * from %s" % self.table))


class DBMigrateSqlPostgresSelectTestCase(DBMigrateSqlPostgresTestCase):
    def setUp(self):
        self.a = TestModel(title='a', text='A')
        self.b = TestModel(title='b', text='B')
        self.a.save()
        self.b.save()


    def tearDown(self):
        self.a.delete()
        self.b.delete()


    def test_should_return_list_of_columns(self):
        self.assertEqual(
            [('a', 'A'), ('b', 'B')],
            self.sql.select('select title, text from %s' % self.table, as_dict=False)
        )


    def test_should_return_list_of_dict(self):
        self.assertEqual(
            [{'text': 'A', 'title': 'a'}, {'text': 'B', 'title': 'b'}],
            self.sql.select('select title, text from %s' % self.table, as_dict=True)
        )


class DBMigrateSqlPostgresSelectValueTestCase(DBMigrateSqlPostgresTestCase):
    def test_should_return_first_column_value_of_first_row(self):
        self.assertEqual('a', self.sql.select_value("select unnest(array['a', 'b', 'c']);"))


    def test_should_return_none_for_empty_result(self):
        self.assertIsNone(self.sql.select_value("select * from %s" % self.table))