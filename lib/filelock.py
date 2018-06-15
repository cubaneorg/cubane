# coding=UTF-8
from __future__ import unicode_literals
import os
import fcntl
import hashlib
import tempfile


class FileLock:
    """
    File-based lock based on:
    http://blog.vmfarms.com/2011/03/cross-process-locking-and.html.

    Usage:

    lock = FileLock('/tmp/filename')
    try:
        lock.acquire()
        # Do important stuff that needs to be synchronised
        .
        .
        .
    finally:
        lock.release()
    """
    def __init__(self, filename):
        """
        Create a new file-based lock based on the given filename. Multiple
        instances of this class with the same filename will protect the same
        resource; only one process may acquire the lock at any given time and
        must release the lock after done acquiring in.
        """
        self.filename = filename
        self.handle = open(filename, 'w') # create if not there yet


    @classmethod
    def temp(self, *args):
        """
        Create a new file lock based on a temporary file that has a unique name
        based on the given list of arguments. A unique hash is constructed based
        on the given list of arguments.
        """
        # generate unique filename
        m = hashlib.md5()
        m.update('-'.join([unicode(arg) for arg in args]))
        filename = os.path.join(tempfile.gettempdir(), m.hexdigest())
        return FileLock(filename)


    def acquire(self, wait=True):
        """
        Acquire access to the locked resource. If wait is True, we will
        block the calling process until the resource is available.
        """
        flag = fcntl.LOCK_EX
        if not wait:
            flag |= fcntl.LOCK_NB # non-blocking

        try:
            fcntl.flock(self.handle, flag)
            return True
        except IOError:
            return False


    def release(self):
        """
        Release the lock and allow other processes to acquire it.
        """
        fcntl.flock(self.handle, fcntl.LOCK_UN)


    def __del__(self):
        """
        Close file handle when done.
        """
        self.handle.close()