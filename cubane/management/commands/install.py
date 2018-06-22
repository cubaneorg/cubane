#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from cubane.backend.models import UserProfile
from cubane.lib.module import module_exists
from cubane.lib.app import get_models
import os
import pwd


UNWANTED_PERMISSIONS = [
    'add_proxyuser',
    'change_proxyuser',
    'delete_proxyuser',

    'add_proxygroup',
    'change_proxygroup',
    'delete_proxygroup',

    'add_proxypermission',
    'change_proxypermission',
    'delete_proxypermission',

    'add_country',
    'change_country',
    'delete_country',

    'add_contenttype',
    'change_contenttype',
    'delete_contenttype',

    'add_session',
    'change_session',
    'delete_session',
]


class Command(BaseCommand):
    USAGE = 'Usage: install [testdata]'

    args = ''
    help = 'Installs cubane application.'


    def syncdb(self):
        os.system("python manage.py migrate --noinput --no-color --run-syncdb")


    def drop_tables(self):
        print 'Dropping tables...'
        psql = settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql_psycopg2'
        sqlite = settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'

        c = connection.cursor()
        if psql:
            c.execute('''
                SELECT \'DROP TABLE \' || n.nspname || \'.\' || c.relname || \' CASCADE;\' FROM pg_catalog.pg_class AS c
                LEFT JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
                WHERE relkind = \'r\' AND n.nspname NOT IN (\'pg_catalog\', \'pg_toast\') AND pg_catalog.pg_table_is_visible(c.oid)
            ''')

            rows = c.fetchall()
            for r in rows:
                c.execute(r[0])
            connection._commit()
        elif sqlite:
            c.execute('SELECT \'DROP TABLE \' || name || \';\' FROM sqlite_master WHERE type = \'table\'')

            rows = c.fetchall()
            for r in rows:
                c.execute(r[0])

        connection.close()


    def database_exists(self):
        """
        Return True, if the given database already exists (postgres only).
        """
        try:
            connection.cursor()
            return True
        except:
            return False


    def create_database(self):
        """
        Attempts to create a postgresql database if we are using postgres.
        """
        # get database settings
        db = settings.DATABASES.get('default', None)
        if not db: return

        # only for postgres...
        engine = db.get('ENGINE')
        if engine != 'django.db.backends.postgresql_psycopg2':
            return

        # database already there?
        if self.database_exists():
            return

        # do we have a postgres user? if so, we have to sudo...
        try:
            pwd.getpwnam('postgres')
            sudo = True
        except KeyError:
            sudo = False

        # build command for creating UTF-8 postgresql database
        dbname = db.get('NAME')
        cmd = 'psql -c "CREATE DATABASE %s WITH ENCODING \'UNICODE\';"' % \
            dbname
        if sudo:
            cmd = 'sudo -u postgres %s' % cmd

        # execute command
        print 'Creating database...'
        os.system(cmd)


    def dbmigrate(self):
        """
        Run database migrations if available.
        """
        if 'cubane.dbmigrate' not in settings.INSTALLED_APPS:
            return

        print 'Migrating database...'
        call_command('dbmigrate', interactive=False, verbose=False)


    def create_users(self, users, password):
        """
        Create default admin user.
        """
        for person in users:
            # create admin user account
            user = User()
            user.username = person
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()

            # create backend profile (force user to reset password after login)
            profile = UserProfile()
            profile.user = user
            profile.reset = True
            profile.save()

            # print out the username/password
            print('')
            print('    ****************************')
            print('    * Username: %-14s *' % user.username)
            print('    * Password: %-14s *' % password)
            print('    ****************************')
            print('')


    def add_arguments(self, parser):
        """
        Arguments
        """
        parser.add_argument(
            '--empty', action='store_true', dest='empty',
            help='Installs a cubane app with an empty database.',
        )


    def handle(self, *args, **kwargs):
        """
        Main
        """
        print 'Installing cubane app...Please Wait...'

        # get options
        empty = kwargs.get('empty')

        # create a new database and schema from scratch, removing any existing
        # database that may exist...
        self.create_database()
        self.drop_tables()

        if not empty:
            self.syncdb()

        # delete unwanted permissions
        if not empty:
            for p in UNWANTED_PERMISSIONS:
                try:
                    permission = Permission.objects.get(codename=p)
                    permission.delete()
                except Permission.DoesNotExist:
                    pass

        # create additional view permissions for user, group and permission
        # itself
        if not empty:
            Permission.objects.create(codename='view_user', name='Can view user', content_type=ContentType.objects.get(model='user', app_label='auth'))
            Permission.objects.create(codename='view_group', name='Can view group', content_type=ContentType.objects.get(model='group', app_label='auth'))
            Permission.objects.create(codename='view_permission', name='Can view permission', content_type=ContentType.objects.get(model='permission', app_label='auth'))

        # run dbmigrate if available, unless we have an empty database
        if not empty:
            self.dbmigrate()

        # create admin users
        if not empty:
            self.create_users([
                'admin'
            ], 'password')

        print 'cubane application %s installed successfully.' % settings.DOMAIN_NAME
        print '=> python manage.py runserver <= to get started.'
        print '-' * 59
        print