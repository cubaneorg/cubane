# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand
from cubane.tasks import TaskRunner
import time
import os
import signal
import sys
import random


class Command(BaseCommand):
    """
    Executes background tasks.
    """
    WAIT_FOR_WORK_SLEEP_SEC = 1
    MAX_WAIT_FOR_WORK_SEC = 8 * 60


    args = ''
    help = 'Executes background tasks.'


    def handle(self, *args, **options):
        """
        Run command.
        """
        # sleep for a random amount of time in case we are trying to
        # start the task runner multiple times.
        time.sleep(random.uniform(0.0, 3.0))

        # immediatly exit if another instance of the task runner is
        # already running...
        if TaskRunner.is_running():
            return

        # mark ourselves as running
        TaskRunner.signal_running()

        # setup cleanup handler that is executed whenever we terminate
        signal.signal(signal.SIGTERM, self.kill_handler)

        # whenever we have a fresh re-start, notify yourself, so that we might
        # pick up any work that is left to do for us, we might have missed
        # a previous notification...
        TaskRunner.notify()

        # continiously execute background work unless we do not have any more
        # work
        while True:
            if TaskRunner.has_work():
                # indicate that there is no more work, since we are about to run
                TaskRunner.signal_no_work()

                # execute background tasks
                runner = self.create_task_runner()
                runner.run()

            # wait for further work to appear...
            if not self.wait_for_work():
                break

        # terminate
        self.cleanup()


    def wait_for_work(self):
        """
        Periodically check if there is more work. After having waited for more
        work to appear for a while, stop waiting.
        """
        start_time = time.time()
        while not TaskRunner.has_work():
            # sleep and stop waiting if we get interrupted by user
            try:
                time.sleep(self.WAIT_FOR_WORK_SLEEP_SEC)
            except KeyboardInterrupt:
                return False

            # determine total waiting time so far and stop waiting once
            # we waited long enought...
            time_ellapsed_sec = time.time() - start_time
            if time_ellapsed_sec > self.MAX_WAIT_FOR_WORK_SEC:
                return False
        return True


    def create_task_runner(self):
        """
        Create a new instance of the task runner.
        """
        return TaskRunner()


    def cleanup(self):
        """
        Cleanup whenever the task runner is terminated. Clear status file and
        remove pid file.
        """
        TaskRunner.remove_status()
        TaskRunner.signal_terminated()


    def kill_handler(self, signal, frame):
        self.cleanup()
        sys.exit(0)