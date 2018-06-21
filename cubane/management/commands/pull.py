# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from cubane.lib.verbose import out
import subprocess
import sys
import re
import base64
import os


class Options(object):
    """
    Represents configuration options controlling the behaviour of this command.
    """
    def __init__(self):
        self.host = self.get_arg('HOST', settings.DOMAIN_NAME)
        self.user = self.get_arg('USER', 'root')
        self.sudo = self.get_arg('SUDO', None)
        self.dbdump = self.get_arg('DBDUMP', 'pg_dump')
        self.dbname = self.get_arg('DATABASE', settings.DATABASE_NAME)
        self.shell = self.get_arg('SHELL', 'sh')
        self.sudo_defined = self.get_arg('SUDO_DEFINED', False)


    def get_arg(self, name, default_value=None):
        """
        Return the cleaned settings argument with the given name. If no such
        name exists, the default value is returned.
        """
        if isinstance(settings.CUBANE_PULL, dict):
            return self.clean_arg(settings.CUBANE_PULL.get(name, default_value))
        else:
            return self.clean_arg(default_value)


    def clean_arg(self, arg):
        """
        Remove invalid characters from the given argument.
        """
        if arg is not None:
            if isinstance(arg, basestring):
                arg = arg.strip()
                arg = re.sub(r'[^-\d\w\s_\.]', '', arg)

        return arg


class Command(BaseCommand):
    """
    Pull database and media assets from remote server.
    """
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'password'


    args = ''
    help = 'Pull application data from remote production server.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        options = Options()

        # create database dump
        try:
            self.create_db_dump(options, 'Creating database dump on server')
            self.secure_copy(options, 'Copying database dump file from server')
            self.remove_db_dump(options, 'Remove database dump file on server')
            self.install_empty('Re-installing new (empty) database')
            self.import_db_dump(options, 'Importing remote database dump file')
            self.dbmigrate('Migrating database')
            self.install_admin_account('Installing admin account')
            self.rsync_media(options, 'Synchronising media files...Please Wait...')

            # all done. Just tell the user what the admin account
            # credentials are
            print
            print '****************************'
            print '* Username: %-14s *' % self.ADMIN_USERNAME
            print '* Password: %-14s *' % self.ADMIN_PASSWORD
            print '****************************'
            print
            print 'Installation complete. Local development environment copied from production system.'
            print
        except ValueError as e:
            sys.stderr.write('ERROR: %s\n' % e)


    def get_username(self, options):
        """
        Return the username for the site.
        """
        return options.sudo if options.sudo_defined else options.user


    def create_db_dump(self, options, task):
        """
        Create database dump file.
        """
        self.verbose_task(task)
        remote_db_dump_cmd = self.get_remote_db_dump_cmd(options)
        self.run_remote_cmd(remote_db_dump_cmd, options)


    def secure_copy(self, options, task):
        """
        Copy file over ssh.
        """
        self.verbose_task(task)

        username = self.get_username(options)
        cmd = 'scp %(user)s@%(host)s:%(path)s ./' % {
            'user': options.user,
            'host': options.host,
            'path': os.path.join('/', 'home', username, 'tmp', '%s.sql' % options.dbname)
        }

        self.run_local_cmd(cmd)


    def remove_db_dump(self, options, task):
        """
        Remove database dump file from remote server.
        """
        self.verbose_task(task)
        cmd = 'rm ~/tmp/%s.sql' % options.dbname
        self.run_remote_cmd(cmd, options)


    def install_empty(self, task):
        """
        Re-install app with empty database.
        """
        self.verbose_task(task)
        call_command('install', interactive=False, empty=True)


    def import_db_dump(self, options, task):
        """
        Import database dump file into empty database.
        """
        self.verbose_task(task)

        # import database dump file
        cmd = 'python manage.py dbshell < %s.sql' % options.dbname
        self.run_local_cmd(cmd)

        # remove local file
        os.unlink('%s.sql' % options.dbname)


    def dbmigrate(self, task):
        """
        Run database migrations
        """
        self.verbose_task(task)
        call_command('dbmigrate', interactive=True)


    def install_admin_account(self, task):
        """
        Make sure that we have an admin account "admin" with the password
        "password". The database import script might have created the account
        already; however, we will reset the password to "password", since this
        is intended for local development.
        """
        self.verbose_task(task)

        try:
            u = User.objects.get(username=self.ADMIN_USERNAME)
        except User.DoesNotExist:
            u = User()
            u.username = self.ADMIN_USERNAME

        # enface development password
        u.is_staff = True
        u.is_superuser = True
        u.set_password(self.ADMIN_PASSWORD)
        u.save()


    def rsync_media(self, options, task):
        self.verbose_task(task)

        username = self.get_username(options)
        cmd = 'rsync -r --progress %(user)s@%(host)s:%(path)s ./' % {
            'user': options.user,
            'host': options.host,
            'path': os.path.join('/', 'home', username, 'public_html', 'media')
        }

        self.run_local_cmd(cmd)


    def verbose_task(self, task):
        """
        Print out the task we are currently executing.
        """
        print '- %s' % task


    def get_remote_db_dump_cmd(self, options):
        """
        Construct the command used to generate a database dump file on the
        remote server.
        """
        if options.dbdump == 'pg_dump':
            return 'pg_dump -c %(dbname)s > ~/tmp/%(dbname)s.sql' % {
                'dbname': options.dbname
            }

        return None


    def run_local_cmd(self, cmd):
        """
        Execute given local command.
        """
        try:
            retcode = subprocess.call(cmd, shell=True)

            if retcode >= 0:
                return True

            raise ValueError('Execution failed: %s. Command terminated by signal %s.' % (cmd, -retcode))
        except OSError as e:
            raise ValueError('Execution failed: %s. Error: %s.' % (cmd, e))


    def run_remote_cmd(self, cmd, options):
        """
        Execute the given command or script on a remote server and
        deal with errors.
        """
        # base64 encode the command to execute, so that we do not face any
        # issues with escaping etc.
        cmd_encoded = base64.b64encode(cmd)

        # build command to execute on remote server
        cmd = 'echo \\"%s\\" | base64 --decode | ' % cmd_encoded
        if options.sudo_defined:
            cmd += 'sudo su - %s' % options.sudo
        else:
            cmd += options.shell

        # build local ssh command
        ssh_cmd = 'ssh %s@%s "%s"' % (options.user, options.host, cmd)
        self.run_local_cmd(ssh_cmd)
