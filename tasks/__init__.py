# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.utils.module_loading import import_module
from cubane.lib.file import file_get_contents, file_put_contents
from cubane.lib.mail import send_exception_email
from cubane.lib.libjson import to_json, decode_json
import os
import signal


class Task(object):
    STATUS_FILENAME = '.taskrunner.status'


    def __init__(self):
        """
        Create a new task.
        """


    def run(self):
        """
        Run task.
        """
        pass


    def report_start(self, total_records):
        """
        Report that this task has just been started.
        """
        self._total_records = total_records
        self._record_counter = 0
        self._message = None
        self._stopped = False
        self._report_status()


    def report_status(self, record_counter, message=None):
        """
        Report processing status
        """
        self._record_counter = record_counter
        self._message = message
        self._report_status()


    def report_stop(self):
        """
        Report that the task has been completed.
        """
        self._stopped = True
        self._message = None
        self._total_records = 0
        self._record_counter = 0
        self._report_status()


    def _report_status(self):
        """
        Write status to status file.
        """
        file_put_contents(
            os.path.join(settings.PUBLIC_HTML_ROOT, self.STATUS_FILENAME),
            to_json({
                'totalRecords': self._total_records,
                'recordCounter': self._record_counter,
                'message': self._message,
                'stopped': self._stopped
            })
        )


class TaskRunner(object):
    PID_FILENAME = '.taskrunner.pid'
    SIGNAL_FILENAME = '.taskrunner.signal'


    @classmethod
    def is_available(cls):
        """
        Return True, if the task runner is available.
        """
        return 'cubane.tasks' in settings.INSTALLED_APPS


    @classmethod
    def get_pid_filename(cls):
        """
        Return the full path of the pid file.
        """
        return os.path.join(settings.PUBLIC_HTML_ROOT, cls.PID_FILENAME)


    @classmethod
    def get_signal_filename(cls):
        """
        Return the full path to the signal file.
        """
        return os.path.join(settings.PUBLIC_HTML_ROOT, cls.SIGNAL_FILENAME)


    @classmethod
    def get_status_filename(cls):
        """
        Return the full path to the status file.
        """
        return os.path.join(settings.PUBLIC_HTML_ROOT, Task.STATUS_FILENAME)


    @classmethod
    def has_work(cls):
        """
        Return True, if there is a signal that work is available.
        """
        return os.path.isfile(cls.get_signal_filename())


    @classmethod
    def notify(cls):
        """
        Notify the task runner to be executed shortly.
        """
        file_put_contents(cls.get_signal_filename(), '1')


    @classmethod
    def get_status(cls):
        """
        Return task runner status information.
        """
        try:
            taskinfo = decode_json(file_get_contents(cls.get_status_filename()))

            # calc. percentage
            if taskinfo.get('stopped', False):
                percent = 0
            else:
                counter = taskinfo.get('recordCounter', 0)
                total = taskinfo.get('totalRecords', 0)
                if counter > total:
                    total = counter
                if total == 0:
                    total = 1
                percent = int(round(float(counter) / float(total) * 100.0))
            taskinfo['percent'] = percent

            return taskinfo
        except IOError:
            return {}


    @classmethod
    def get_pid(cls):
        """
        Return the process identifier (pid) that is stored in the pid file
        for the task runner. Returns None if no pid file exists or the pid
        cannot be parsed as an integer number.
        """
        try:
            return int(file_get_contents(cls.get_pid_filename()))
        except (ValueError, IOError):
            return None


    @classmethod
    def signal_running(cls):
        """
        Indicate that the task running is currently running by writing the
        current process identifier (pid) to the pid file.
        """
        file_put_contents(
            cls.get_pid_filename(),
            unicode(os.getpid())
        )


    @classmethod
    def signal_terminated(cls):
        """
        Signal that the task runner has been terminated by removing the pid file.
        """
        filename = cls.get_pid_filename()
        if os.path.isfile(filename):
            os.remove(filename)


    @classmethod
    def process_running_with_pid(cls, pid):
        """
        Return True, if a process with the given pid is actually running.
        """
        try:
            # will raise exception if process does not exist and will do
            # nothing otherwise...
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True


    @classmethod
    def is_running(cls):
        """
        Return True, if another process of the task runner is already running.
        The pid file contains the pid of the process for executing background
        work. We have to verify that the pid file exists, but also if there is
        actually a process running with the given pid.
        """
        pid = cls.get_pid()
        if pid:
            return cls.process_running_with_pid(pid)
        else:
            return False


    @classmethod
    def terminate(cls):
        """
        Terminate the task runner (if running).
        """
        pid = cls.get_pid()
        if pid:
            os.kill(pid, signal.SIGTERM)


    @classmethod
    def remove_status(cls):
        """
        Remove task runner status file.
        """
        filename = cls.get_status_filename()
        if os.path.isfile(filename):
            os.remove(filename)


    @classmethod
    def signal_no_work(cls):
        """
        Signal that there is no further work.
        """
        filename = cls.get_signal_filename()
        if os.path.isfile(filename):
            os.remove(filename)


    def __init__(self):
        """
        Create a new instance of the task runner.
        """
        self._tasks = []
        for app_name in settings.INSTALLED_APPS:
            try:
                app = import_module(app_name)
                if hasattr(app, 'install_tasks'):
                    app.install_tasks(self)
            except:
                send_exception_email()


    def register(self, task):
        """
        Register the given task runner.
        """
        self._tasks.append(task)


    def run(self):
        """
        Run background tasks.
        """
        for task in self._tasks:
            try:
                task.run()
                task.report_stop()
            except:
                send_exception_email()