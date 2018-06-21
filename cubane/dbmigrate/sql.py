# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django.db import models
from django.db.backends.utils import truncate_name
from django.db.models.fields import NOT_PROVIDED
from django.utils.encoding import force_bytes
from cubane.lib import verbose
from cubane.lib.app import get_models
import re
import hashlib


class ModelMock(object):
    class _meta:
        db_table = None


class Sql(object):
    """
    Interfaces with specific database via raw sql for manipulating
    database schema.
    """
    def __init__(self, connection, _verbose=True):
        self.connection = connection
        self._verbose = _verbose


class PostgresSql(Sql):
    """
    Provides access to the database schema for a postgres database.
    """
    SQL_BEGIN_TRANSACTION = 'begin transaction;'
    SQL_COMMIT = 'commit;'
    SQL_ROLLBACK = 'rollback;'

    SQL_LOCK_TABLE = 'lock %(table)s in ACCESS EXCLUSIVE mode;'

    SQL_SELECT_TABLE_NAMES = 'select table_name from information_schema.tables where table_type = \'BASE TABLE\' and table_schema = \'public\' order by table_name;'
    SQL_SELECT_COLUMN_NAMES = 'select column_name from information_schema.columns WHERE table_name = \'%(table)s\' order by column_name;'
    SQL_SELECT_FUNCTIONS = 'select routines.routine_name from information_schema.routines ORDER BY routines.routine_name;'
    SQL_SELECT_INDICES = 'SELECT i.relname FROM pg_class t JOIN pg_index ix ON t.oid = ix.indrelid JOIN pg_class i ON i.oid = ix.indexrelid JOIN pg_attribute a ON a.attrelid = t.oid WHERE a.attnum = ANY(ix.indkey) AND t.relkind = \'r\' AND t.relname = \'%(table)s\' ORDER BY t.relname, i.relname;'
    SQL_SELECT_TRIGGERS = 'select distinct triggers.trigger_name from information_schema.triggers where triggers.event_object_table = \'%(table)s\' ORDER BY triggers.trigger_name;'
    SQL_COLUMN_IS_NULLABLE = 'select is_nullable from INFORMATION_SCHEMA.COLUMNS where table_name=\'%(table)s\' and column_name=\'%(column)s\';';
    SQL_GET_COLUMN_DEFAULT = 'select column_default from INFORMATION_SCHEMA.COLUMNS where table_name=\'%(table)s\' and column_name=\'%(column)s\';';
    SQL_GET_COLUMN_NULL_VALUE_COUNT = 'select count(*) from "%(table)s" where "%(column)s" is null;'
    SQL_GET_COLUMN_TYPE = 'select data_type, character_maximum_length from INFORMATION_SCHEMA.COLUMNS where table_name=\'%(table)s\' and column_name=\'%(column)s\';';
    SQL_GET_ROW_COUNT = 'select count(*) from "%(table)s";'

    SQL_TABLE_EXISTS = 'select 1 from information_schema.tables where table_type = \'BASE TABLE\' and table_schema = \'public\' and table_name=\'%(table)s\';'
    SQL_CONSTRAINT_EXISTS = 'select constraint_name from information_schema.constraint_column_usage where table_name = \'%(rel_table)s\' and constraint_name = \'%(name)s\''
    SQL_INDEX_EXISTS = 'select 1 FROM pg_class c join pg_namespace n ON n.oid = c.relnamespace where c.relname = \'%(name)s\' and c.relkind = \'i\';'
    SQL_GET_INDICES = 'SELECT * FROM pg_indexes WHERE tablename = \'%(table)s\';'
    SQL_IS_INDEX_UNIQUE = 'select idx.indisunique FROM pg_class c join pg_namespace n ON n.oid = c.relnamespace join pg_index idx on idx.indexrelid = c.oid where c.relname = \'%(name)s\' and c.relkind = \'i\';'
    SQL_COLUMN_EXISTS = 'select 1 from information_schema.columns WHERE table_name = \'%(table)s\' and column_name = \'%(column_name)s\';'

    SQL_RENAME_TABLE = 'alter table "%(name)s" rename to "%(new_name)s";'
    SQL_RENAME_INDEX = 'alter index "%(name)s" RENAME TO "%(new_name)s";'

    SQL_DROP_TABLE = 'drop table "%(name)s" cascade;'

    SQL_ALTER_TABLE_ADD_COLUMN = 'alter table "%(table)s" add column "%(column)s" %(datatype)s %(null)s%(default)s;'
    SQL_ALTER_TABLE_DROP_COLUMN = 'alter table "%(table)s" drop column "%(column)s";'
    SQL_ALTER_TABLE_DROP_CONSTRAINT = 'alter table "%(table)s" drop constraint "%(constraint_name)s";'
    SQL_ALTER_TABLE_DROP_CONSTRAINT_CASCADE = 'alter table "%(table)s" drop constraint "%(constraint_name)s" cascade;'
    SQL_ALTER_TABLE_ADD_FOREIGN_KEY_CONSTRAINT = 'alter table "%(table)s" add constraint "%(name)s" foreign key ("%(column)s") references "%(rel_table)s" ("%(rel_column)s") DEFERRABLE INITIALLY DEFERRED;'
    SQL_ALTER_TABLE_ADD_UNIQUE_CONSTRAINT = 'alter table "%(table)s" add constraint "%(index_name)s" unique (%(column_list)s);'
    SQL_ALTER_TABLE_RENAME_COLUMN = 'alter table "%(table)s" rename "%(column)s" to "%(new_column)s";'
    SQL_UPDATE_VARCHAR_VALUE_LENGTH = 'update "%(table)s" set "%(column)s" = substring(%(column)s from 1 for %(max_length)s) where char_length(%(column)s) > %(max_length)s;'
    SQL_ALTER_TABLE_COLUMN_TYPE = 'alter table "%(table)s" alter column "%(column)s" TYPE %(data_type)s;'

    SQL_DROP_NOT_NULL_CONTRAINT = 'alter table "%(table)s" alter column "%(column)s" drop not null;'
    SQL_SET_NOT_NULL_CONTRAINT = 'alter table "%(table)s" alter column "%(column)s" set not null;'

    SQL_SET_DEFAULT = 'alter table "%(table)s" alter column "%(column)s" set default %(default)s;'
    SQL_DROP_DEFAULT = 'alter table "%(table)s" alter column "%(column)s" drop default;'

    SQL_UPDATE_NULL_TO_DEFAULT = 'update "%(table)s" set "%(column)s" = \'%(default)s\' where "%(column)s" is null;'
    SQL_UPDATE_NULL_TO_NULL = 'update "%(table)s" set "%(column)s" = null where "%(column)s" is null;'

    SQL_CREATE_INDEX = 'create index "%(index_name)s" on "%(table)s" (%(column_list)s);'
    SQL_DROP_INDEX = 'drop index %(index_name)s;'
    SQL_DROP_INDEX_CASCADE = 'drop index %(index_name)s cascade;'
    SQL_CREATE_LIKE_INDEX = 'create index "%(index_name)s" on "%(table)s" using %(index_type)s ("%(column)s" %(pattern_ops)s);'
    SQL_CREATE_FTS_INDEX = 'create index %(index_name)s on %(table)s using gin(%(column_list)s);'

    SQL_FUNCTION_EXISTS = 'select 1 from information_schema.routines where routines.routine_name = \'%(name)s\';'
    SQL_CREATE_FUNCTION = 'create function %(name)s%(arguments)s returns %(return_type)s as $$\n%(body)s\n$$ language plpgsql;'
    SQL_DROP_FUNCTION = 'drop function %(function_name)s;'

    SQL_TRIGGER_EXISTS = 'select 1 from information_schema.triggers where triggers.event_object_table = \'%(table)s\' and triggers.trigger_name = \'%(trigger_name)s\';'
    SQL_CREATE_TRIGGER = 'create trigger %(trigger_name)s %(event)s on %(table)s for %(foreach)s execute procedure %(function_name)s%(arguments)s;'
    SQL_DROP_TRIGGER = 'drop trigger %(trigger_name)s on %(table)s';

    SQL_FTS_INDEX = 'update %(table)s set %(updates)s;'


    def q(self, v):
        """
        Quote given value depending on its type in the database-specific
        pattern.
        """
        if v == None:
            return 'NULL'
        elif isinstance(v, bool):
            return 'true' if v else 'false'
        elif isinstance(v, int):
            return '%d' % v
        elif isinstance(v, float):
            return '%f' % v
        else:
            return "'%s'" % v


    def q_name(self, name):
        """
        Quote database name.
        """
        return '"%s"' % name


    def get_data_type_from_field(self, field):
        """
        Returns the corresponding postgresql datatype for the given field, for
        example varchar(n) for models.CharField().
        """
        if isinstance(field, (models.CharField, models.SlugField)):
            return 'varchar(%d)' % field.max_length
        elif isinstance(field, models.TextField):
            return 'text'
        elif isinstance(field, (models.IntegerField, models.ForeignKey)):
            return 'integer'
        elif isinstance(field, models.FloatField):
            return 'float'
        elif isinstance(field, models.DecimalField):
            return 'decimal(%d, %d)' % (field.max_digits, field.decimal_places)
        elif isinstance(field, models.BooleanField) or isinstance(field, models.NullBooleanField):
            return 'bool'
        elif isinstance(field, models.DateTimeField):
            return 'timestamp with time zone'
        elif isinstance(field, models.DateField):
            return 'date'
        elif isinstance(field, models.TimeField):
            return 'time'
        else:
            raise ValueError(
                ("Unknown field type '%s'. Do not know the corresponding " + \
                "data type for database schema.") % field.__class__.__name__
            )


    def _digest(cls, *args):
        """
        Generates a 32-bit digest of a set of arguments that can be used to
        shorten identifying names.
        """
        h = hashlib.md5()
        for arg in args:
            h.update(force_bytes(arg))
        return h.hexdigest()[:8]


    def _get_model_by_table_name(self, table):
        """
        Return the model based on the given table name.
        """
        if not hasattr(self, '_model_table_cache'):
            self._model_table_cache = {}
            for model in get_models():
                self._model_table_cache[model._meta.db_table] = model

        return self._model_table_cache.get(table)


    def _create_index_name(self, table, column_names, suffix=''):
        """
        Generates a unique name for an index/unique constraint.
        """
        # Call into django's base to construct index names
        schema_editor = self.connection.schema_editor()
        model = self._get_model_by_table_name(table)
        if not model:
            model = ModelMock()
            model._meta.db_table = table
        return schema_editor._create_index_name(model, column_names, suffix)


    def get_index_name(self, table, column_names, suffix='', unique=False):
        """
        Return a unique name for an index/unique constraint.
        """
        if not isinstance(column_names, list):
            column_names = [column_names]

        if unique and len(column_names) == 1:
            # since this index is usually auto-generated by postgresql, it
            # follows the naming convention that postgresql usually applies...
            return '%s_%s_key' % (table, column_names[0])

        if len(column_names) == 1 and column_names[0] == 'pkey':
            return '%s_%s' % (table, column_names[0])
        elif len(column_names) == 1 and column_names[0].endswith('_like'):
            return self._create_index_name(table, [column_names[0][:-5]], suffix='_like')
        else:
            return self._create_index_name(table, column_names, suffix)


    def get_fk_name(self, table, column, rel_table, rel_column):
        """
        Return the name of the foreign key constraint for the given model and
        model field referring to the given rel. table and column.
        """
        suffix = '_fk_%(rel_table)s_%(rel_column)s' % {
            'rel_table': rel_table,
            'rel_column': rel_column
        }
        return self.get_index_name(table, column, suffix=suffix)


    def get_like_index_name(self, table, column):
        """
        Return the index name of the like-index for the given table and column.
        """
        return self.get_index_name(table, column, suffix='_like')


    def get_table_names(self):
        """
        Return a list of all table names that are available.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_SELECT_TABLE_NAMES)
        return [row[0] for row in c.fetchall()]


    def get_column_names(self, table):
        """
        Return a list of names for all columns of the given table.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_SELECT_COLUMN_NAMES % {
            'table': table
        })
        return [row[0] for row in c.fetchall()]


    def get_function_names(self):
        """
        Return a list of all functions.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_SELECT_FUNCTIONS);
        return [row[0] for row in c.fetchall()]


    def get_indices(self, table):
        """
        Return a list of all indices for the given table.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_SELECT_INDICES % {
            'table': table
        });
        return [row[0] for row in c.fetchall()]


    def get_triggers(self, table):
        """
        Return a list of all triggers.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_SELECT_TRIGGERS % {
            'table': table
        });
        return [row[0] for row in c.fetchall()]


    def begin(self):
        """
        Begin a new database-level transaction.
        """
        self.sql(self.SQL_BEGIN_TRANSACTION)


    def lock_table(self, table):
        """
        Lock given table.
        """
        self.sql(self.SQL_LOCK_TABLE % {
            'table': table
        })


    def commit(self):
        """
        Commit previous transaction.
        """
        self.sql(self.SQL_COMMIT)


    def rollback(self):
        """
        Roll back previous transaction.
        """
        self.sql(self.SQL_ROLLBACK)


    def table_exists(self, table):
        """
        Return True, if the table with the given name exists.
        """
        return self.has_one_row(self.SQL_TABLE_EXISTS % {
            'table': table
        })


    def rename_table(self, name, new_name):
        """
        Renames the table with the given name to the new table name.
        """
        self.sql(self.SQL_RENAME_TABLE % {
            'name': name,
            'new_name': new_name
        })


    def drop_table(self, name):
        """
        Drop the given table.
        """
        self.sql(self.SQL_DROP_TABLE % {
            'name': name
        })


    def column_exists(self, table, column_name):
        """
        Return True, if the given column name on the given table exists.
        """
        return self.has_one_row(self.SQL_COLUMN_EXISTS % {
            'table': table,
            'column_name': column_name
        })


    def index_exists(self, name):
        """
        Return True, if the given index exists; otherwise False.
        """
        return self.has_one_row(self.SQL_INDEX_EXISTS % {
            'name': name
        })


    def get_table_indices(self, table):
        """
        Return a list of all index names for the given table.
        """
        rows = self.select(self.SQL_GET_INDICES % {
            'table': table
        })
        return [row.get('indexname') for row in rows]


    def is_index_unique(self, name):
        """
        Assuming the given index exists, return True if the index if unique;
        False otherwise.
        """
        return self.select_value(self.SQL_IS_INDEX_UNIQUE % {
            'name': name
        }, False)


    def rename_index(self, table, name, new_name):
        """
        Rename index for given column and table.
        """
        if self.index_exists(name) and not \
           self.index_exists(new_name):
            self.sql(self.SQL_RENAME_INDEX % {
                'table': table,
                'name': name,
                'new_name': new_name
            })


    def rename_column_index(self, table, column, new_column):
        """
        Rename index for given column and table.
        """
        self.rename_index(
            table,
            self.get_index_name(table, column),
            self.get_index_name(table, new_column)
        )


    def rename_like_index(self, table, column, new_column):
        """
        Rename like index for given column and table.
        """
        self.rename_index(
            table,
            self.get_like_index_name(table, column),
            self.get_like_index_name(table, new_column)
        )


    def create_column_index(self, table, column_name, unique, column_list=None):
        """
        Create index for given column and table. If the index is unique, we
        actually just adding the unique constraint (which will then generate
        the corresponding index automatically).
        """
        column_list = column_list or self.q_name(column_name)
        index_name = self.get_index_name(table, column_name, unique=unique)

        if unique:
            self.sql(self.SQL_ALTER_TABLE_ADD_UNIQUE_CONSTRAINT % {
                'table': table,
                'column_name': column_name,
                'column_list': column_list,
                'index_name': index_name
            })
        else:
            self.sql(self.SQL_CREATE_INDEX % {
                'table': table,
                'column_name': column_name,
                'column_list': column_list,
                'index_name': index_name
            })


    def drop_index(self, table, index_name, cascade=False):
        """
        Remove the index with the given name. If the index is unique, we will
        drop the unique constraint instead, which will drop the index as well.
        """
        if self.constraint_exists(table, index_name):
            return self.drop_constraint(table, index_name, cascade)

        sql = self.SQL_DROP_INDEX_CASCADE if cascade else self.SQL_DROP_INDEX
        self.sql(sql % {
            'index_name': index_name
        })


    def create_like_index(self, table, column, index_type='btree', pattern_ops='varchar_pattern_ops'):
        """
        Create like index for given column and table.
        """
        self.sql(self.SQL_CREATE_LIKE_INDEX % {
            'table': table,
            'column': column,
            'index_name': self.get_index_name(table, '%s_like' % column),
            'index_type': index_type,
            'pattern_ops': pattern_ops
        })


    def create_fts_index(self, table, index_name, column_list=None):
        column_list = column_list or '"' + index_name + '"'
        self.sql(self.SQL_CREATE_FTS_INDEX % {
            'table': table,
            'index_name': index_name,
            'column_list': column_list
        })


    def constraint_exists(self, rel_table, name):
        """
        Return True, if a constraint with the given name of the given table
        exists. Constraints are stored for the referenced table, so the first
        argument is the table to which a constraint is referenced.
        """
        return self.has_one_or_more_rows(self.SQL_CONSTRAINT_EXISTS % {
            'rel_table': rel_table,
            'name': name
        })


    def column_is_nullable(self, table, column):
        """
        Return True, if the given column of given table is nullable; otherwise
        return False.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_COLUMN_IS_NULLABLE % {
            'table': table,
            'column': column
        })
        rows = c.fetchall()
        if len(rows) >= 1:
            return rows[0][0] == 'YES'
        else:
            return False


    def get_column_default(self, table, column):
        """
        Return the default for the given column of the given table.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_GET_COLUMN_DEFAULT % {
            'table': table,
            'column': column
        })
        rows = c.fetchall()
        default = None
        if len(rows) >= 1:
            default = rows[0][0]

            # convert "'12345'::character varying" to '12345'
            if default:
                m = re.match(r'^\'(.*?)\'\:\:(.*?)$', default)
                if m:
                    default = m.group(1)

        return default


    def get_column_datatype(self, table, column):
        """
        Return the data type and max. length for the given column of given table.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_GET_COLUMN_TYPE % {
            'table': table,
            'column': column
        })
        rows = c.fetchall()
        data_type = None
        max_length = None
        if len(rows) >= 1:
            data_type = rows[0][0]
            max_length = rows[0][1]

            # convert character varying to varchar
            if data_type == 'character varying':
                data_type = 'varchar'

        return data_type, max_length


    def has_null_value(self, table, column):
        """
        Return True, if there is at least one row with NULL value for the
        given column of the given table.
        """
        c = self.connection.cursor()
        c.execute(self.SQL_GET_COLUMN_NULL_VALUE_COUNT % {
            'table': table,
            'column': column
        })
        rows = c.fetchall()
        return rows[0][0] > 0


    def is_empty_table(self, table):
        """
        Return True, if the given table is empty.
        """
        return self.select_value(self.SQL_GET_ROW_COUNT % {
            'table': table
        }) == 0


    def update_null_to_default(self, table, column, default):
        """
        Update given table and the the column to the given default value
        whereever the current column value is NULL.
        """
        if default is None:
            self.sql(self.SQL_UPDATE_NULL_TO_NULL % {
                'table': table,
                'column': column
            })
        else:
            self.sql(self.SQL_UPDATE_NULL_TO_DEFAULT % {
                'table': table,
                'column': column,
                'default': default
            })


    def drop_constraint(self, table, constraint_name, cascade=False):
        """
        Delete (drop) given constraint for the given table.
        """
        sql = self.SQL_ALTER_TABLE_DROP_CONSTRAINT_CASCADE if cascade else self.SQL_ALTER_TABLE_DROP_CONSTRAINT
        self.sql(sql % {
            'table': table,
            'constraint_name': constraint_name
        })


    def make_nullable(self, table, column):
        """
        Drop the NOT NULL contraint on the given column of the given table.
        """
        self.sql(self.SQL_DROP_NOT_NULL_CONTRAINT % {
            'table': table,
            'column': column,
        })


    def make_not_nullable(self, table, column):
        """
        Set the NOT NULL contraint on the given column of the given table.
        """
        self.sql(self.SQL_SET_NOT_NULL_CONTRAINT % {
            'table': table,
            'column': column,
        })


    def set_column_default(self, table, column, default, auto_now=False):
        """
        Set the given default to the given column of the given table.
        """
        # default
        if auto_now:
            default = 'now()'
        else:
            default = self.q(default)

        self.sql(self.SQL_SET_DEFAULT % {
            'table': table,
            'column': column,
            'default': default
        })


    def drop_column_default(self, table, column):
        """
        Drop the default of the given column of the given table.
        """
        self.sql(self.SQL_DROP_DEFAULT % {
            'table': table,
            'column': column
        })


    def foreign_key_constraint_exists(self, table, column, rel_table, rel_column):
        """
        Return True, if the foreign key constraint for the given table and
        column exists.
        """
        return self.constraint_exists(
            rel_table,
            self.get_fk_name(table, column, rel_table, rel_column)
        )


    def create_foreign_key_constraint(self, table, column, rel_table, rel_column):
        """
        Creates a foreign key constraint from given table and column to given
        target table rel_table and column rel_column.
        """
        name = self.get_fk_name(table, column, rel_table, rel_column)
        self.sql(self.SQL_ALTER_TABLE_ADD_FOREIGN_KEY_CONSTRAINT % {
            'table': table,
            'name': name,
            'column': column,
            'rel_table': rel_table,
            'rel_column': rel_column
        })


    def rename_foreign_key_constraint(self, table, column, new_column, rel_table, rel_column, old_table=None):
        """
        Rename given foreign key constraint if exists. In postgresql this is
        only possible by dropping constraint and re-creating it under the new
        name.
        """
        if old_table:
            fk_name = self.get_fk_name(old_table, column, rel_table, rel_column)
            if self.constraint_exists(rel_table, fk_name):
                # drop and re-create...
                self.drop_constraint(table, fk_name)
                self.create_foreign_key_constraint(table, new_column, rel_table, rel_column)
        else:
            if self.foreign_key_constraint_exists(table, column, rel_table, rel_column) and not \
               self.foreign_key_constraint_exists(table, new_column, rel_table, rel_column):
                # drop and re-create...
                self.drop_foreign_key_constraint(table, column, rel_table, rel_column)
                self.create_foreign_key_constraint(table, new_column, rel_table, rel_column)


    def drop_foreign_key_constraint(self, table, column, rel_table, rel_column):
        """
        Delete (drop) foreign key constraint for the given column on the given
        table.
        """
        name = self.get_fk_name(table, column, rel_table, rel_column)
        self.drop_constraint(table, name)


    def create_column(self, table, column, datatype, null=True, default=None, auto_now=False):
        """
        Perform sql for adding the given column to the given table.
        """
        # default
        if auto_now:
            default = ' default now()'
        else:
            default = ' default %s' % self.q(default) if default != NOT_PROVIDED else ''

        # create field
        self.sql(self.SQL_ALTER_TABLE_ADD_COLUMN % {
            'table': table,
            'column': column,
            'datatype': datatype,
            'null': 'null' if null else 'not null',
            'default': default
        })


    def rename_column(self, table, column, new_column):
        """
        Rename given column of given table to the new given column name.
        """
        self.sql(self.SQL_ALTER_TABLE_RENAME_COLUMN % {
            'table': table,
            'column': column,
            'new_column': new_column
        })


    def update_varchar_length(self, table, column, max_length):
        """
        Update and shrink any varchar values of the given table/column to the
        given max_length.
        """
        self.sql(self.SQL_UPDATE_VARCHAR_VALUE_LENGTH % {
            'table': table,
            'column': column,
            'max_length': max_length
        })


    def change_column_data_type(self, table, column, data_type):
        """
        Change the data type of the given table/column.
        """
        self.sql(self.SQL_ALTER_TABLE_COLUMN_TYPE % {
            'table': table,
            'column': column,
            'data_type': data_type
        })


    def drop_column(self, table, column):
        """
        Perform sql for dropping the given column from the given table.
        """
        # drop column (should implicitly drop index etc)...
        self.sql(self.SQL_ALTER_TABLE_DROP_COLUMN % {
            'table': table,
            'column': column
        })


    def function_exists(self, name):
        """
        Return True, if a function with the given name exists.
        """
        # multiple entries may exist for the same function name
        return self.has_one_or_more_rows(self.SQL_FUNCTION_EXISTS % {
            'name': name
        })


    def create_function(self, name, arguments, return_type, body):
        """
        Perform sql for creating a function.
        """
        if arguments == None or len(arguments) == 0:
            arguments = '()'
        else:
            arguments = '(' + ', '.join(['%s %s' % (argname, argtype) for argname, argtype in arguments]) + ')'

        self.sql(self.SQL_CREATE_FUNCTION % {
            'name': name,
            'arguments': arguments,
            'return_type': return_type,
            'body': body
        })


    def drop_function(self, function_name):
        """
        Perform sql for dropping the function with the given function name and
        arguments. Since multiple function may exist with the same name, the list
        of function arguments must be supplied, for example add(int, int).
        """
        self.sql(self.SQL_DROP_FUNCTION % {
            'function_name': function_name
        })


    def trigger_exists(self, table, trigger_name):
        """
        Return True, if a trigger with the given name exists for the given table.
        """
        return self.has_one_or_more_rows(self.SQL_TRIGGER_EXISTS % {
            'table': table,
            'trigger_name': trigger_name
        })


    def create_trigger(self, table, trigger_name, event, foreach, function_name, arguments=None):
        """
        Perform sql for creating a trigger to execute the given functon with given arguments
        in certain events.
        """
        if arguments == None or len(arguments) == 0:
            arguments = '()'
        else:
            arguments = '(' + ', '.join(arguments) + ')'

        self.sql(self.SQL_CREATE_TRIGGER % {
            'table': table,
            'trigger_name': trigger_name,
            'event': event,
            'foreach': foreach,
            'function_name': function_name,
            'arguments': arguments
        })


    def drop_trigger(self, table, trigger_name):
        """
        Perform sql for dropping the given trigger from the given table.
        """
        self.sql(self.SQL_DROP_TRIGGER % {
            'table': table,
            'trigger_name': trigger_name
        })


    def fts_index(self, table, columns):
        """
        Perform sql update on the given table by updating the given column
        to trigger the update trigger for re-indexing the table.
        """
        self.sql(self.SQL_FTS_INDEX % {
            'table': table,
            'updates': ', '.join(['%s = %s' % (c, c) for c in columns])
        })


    def has_one_row(self, query):
        """
        Execute given query and return True, if the result has exactly one row.
        """
        c = self.connection.cursor()
        c.execute(query)
        return len(c.fetchall()) == 1


    def has_one_or_more_rows(self, query):
        """
        Execute given query and return True, if the result has exactly one row.
        """
        c = self.connection.cursor()
        c.execute(query)
        return len(c.fetchall()) >= 1


    def sql(self, sql):
        """
        Perform given sql statement.
        """
        verbose.out('> ' + sql, verbose=self._verbose)
        c = self.connection.cursor()
        c.execute(sql)


    def select(self, sql, as_dict=True):
        """
        Perform given select statement and return the result.
        """
        c = self.connection.cursor()
        c.execute(sql);
        columns = [column[0] for column in c.description]

        if as_dict:
            results = []
            for row in c.fetchall():
                results.append(dict(zip(columns, row)))
        else:
            results = c.fetchall()

        return results


    def select_value(self, sql, default=None):
        """
        Perform given select statement and return the value of the first column
        of the first row.
        """
        r = self.select(sql, as_dict=False)
        if len(r) > 0:
            if len(r[0]) > 0:
                return r[0][0]
        return default