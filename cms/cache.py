# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from cubane.lib.file import sizeof_fmt
from cubane.lib.file import file_put_contents
from cubane.lib.file import file_get_contents
from cubane.lib.file import file_set_mtime
from cubane.lib.file import file_get_mtime
from cubane.lib.file import file_move
from cubane.lib import verbose as cubane_verbose
from cubane.lib.libjson import decode_json, to_json
from htmlmin.minify import html_minify
import os
import codecs
import time
import datetime
import hashlib


class CacheContext(object):
    """
    Encapsulates internal data that is cached during the rendering process
    of all content when rendering for the cache system.
    """
    def __init__(self):
        """
        Create a new (empty) instance of the cache context.
        """
        self._cache = {}


    def cached(self, key, func):
        """
        Return the cached entry for the given key. If there is no cached
        entry yet, a new cached entry is created by executing the given
        callable.
        """
        if key not in self._cache:
            self._cache[key] = func()

        return self._cache.get(key)


class Cache(object):
    """
    CMS content cache system. Files are generated to disk when publishing
    content in order to increase request throughput.
    """
    INDEX_FILENAME     = '.cache'
    RESERVED_FILENAMES = [
        INDEX_FILENAME
    ]


    def __init__(self):
        self.filenames = []
        self._size = 0


    @property
    def context(self):
        """
        Return the cache context associated with this cache instance.
        """
        if not hasattr(self, '_context'):
            self._context = CacheContext()
        return self._context


    @property
    def index_filename(self):
        """
        Return the full path to the cache index file.
        """
        return os.path.join(settings.CACHE_ROOT, self.INDEX_FILENAME)


    @property
    def size(self):
        """
        Return the size of the cache content in bytes.
        """
        return self._size


    @property
    def items(self):
        """
        Return the count of items in the cache.
        """
        return len(self.filenames)


    def set_index(self, filenames):
        """
        Generate cache index file which contains a list of all cached content
        files that were generated the last time content was published.
        The ftime of this file determines when the content was published.
        """
        # sort filenames (longest first) so that we can remove all
        # intermediate folders in the correct orders without runnig into the
        # situation that we are attempting to remove a non-empty folder
        filenames = sorted(filenames, key=lambda x: len(x), reverse=True)

        # write cache index file containing all file names
        # (directories are derived from files).
        try:
            with codecs.open(self.index_filename, 'w', 'utf-8') as f:
                for filename in filenames:
                    line = '%s\n' % filename
                    f.write(line.decode('utf-8'))
        except:
            pass


    def get_index(self):
        """
        Read cache index file (if exists) and return a list of cached content
        filenames. If no cache index file exists, return the empty list.
        """
        try:
            with codecs.open(self.index_filename, 'r', 'utf-8') as f:
                return filter(None, [s.strip() for s in f.readlines()])
        except:
            return []


    def clear_index(self):
        """
        Delete cache index file. Having no cache index file means that the
        CMS system has no content published.
        """
        self._remove_file(self.index_filename)


    def get_mtime(self, filename):
        """
        Return the last mod. timestamp of the given file. The given file may
        not exist because the cache has been invalidated. In this case the file
        may have been renamed to .filename.
        """
        fullpath = os.path.join(settings.CACHE_ROOT, filename)

        if os.path.isfile(fullpath):
            return file_get_mtime(fullpath)
        else:
            invalidated_filename = self._get_invalidated_cache_filename(fullpath)
            if os.path.isfile(invalidated_filename):
                return file_get_mtime(invalidated_filename)


    def publish_required(self):
        """
        Return True, if a publish is required that is when no cache index file
        is present.
        """
        return not os.path.isfile(self.index_filename)


    def invalidate(self, verbose=False):
        # get list of files published previously
        cache = self.get_index()

        # invalidate all files, so that we keep the generated content
        # but such pages are no longer cached as such.
        n = 0
        for filename in cache:
            path = os.path.join(settings.CACHE_ROOT, filename)
            if os.path.isfile(path):
                new_path = self._get_invalidated_cache_filename(path)

                file_move(path, new_path)
                cubane_verbose.out('%-70s' % path, verbose=verbose)

                n += 1

        # delete cache index
        self.clear_index()

        return n


    def clear(self, verbose=False):
        """
        Clear cache entirely and remove all cached content files.
        """
        # delete all files and folders
        n = self._cleanup()

        # delete meta data
        self.clear_index()

        return n


    def add(self, filename, mtime, changed, content, minify_html=True):
        """
        Add given content to the cache and store the content as the given
        filename. If the last mod. timestamp did not change, no content is
        actually written to the cache system; however the meta data is generated
        as usual. If the content did not change we might still have to restore
        the corresponding cache file which might have been renamed during
        cache invalidation.
        """
        # if no timestamp is given, assume current time
        if mtime is None:
            mtime = datetime.datetime.now()

        # content changed? We may already know whether content changed or not.
        # if changed is None however, we have to figure this out by ourselves...
        fullpath = os.path.join(settings.CACHE_ROOT, filename)
        invalidated_path = self._get_invalidated_cache_filename(fullpath)
        current_mtime = self.get_mtime(filename)
        if changed is None:
            changed = mtime != current_mtime

        if changed:
            # generate new content
            self._add(fullpath, mtime, content, minify_html)

            # remove invalidated cache file version
            self._remove_file(invalidated_path)
        else:
            # move cached content file back into place
            if os.path.isfile(invalidated_path) and not os.path.isfile(fullpath):
                file_move(invalidated_path, fullpath)

        # add filename to index
        self.filenames.append(filename)

        # contribute to total size
        size = os.path.getsize(fullpath)
        self._size += size
        return size, changed


    def _add(self, fullpath, mtime, content, minify_html=True):
        """
        Add given content to the cache and store the content as the given
        full path.
        """
        # create intermediate folders if required
        path = os.path.dirname(fullpath)
        if not os.path.exists(path):
            os.makedirs(path)

        # minify content
        if minify_html:
            try:
                content = html_minify(content)

                # Fix for Source Element
                # W3 Spec: "The source element is a void element. A source element must have a start tag but must not have an end tag."
                # https://github.com/cobrateam/django-htmlmin/issues/37
                content = content.replace('</source>', '')
            except:
                pass

        # write content
        with codecs.open(fullpath, 'w', 'utf-8') as f:
            f.write(content)

        # update file's modification time to the given one
        file_set_mtime(fullpath, mtime)


    def write(self):
        """
        Write cache index file for all files that have been added to the cache.
        """
        self.set_index(self.filenames)


    def cleanup(self):
        """
        Scan the cache folder and delete any files and empty folders that are
        not suppose to be in the cache according to the cache index.
        """
        return self._cleanup(self.filenames)


    def _cleanup(self, exclude=[]):
        """
        Scan the cache folder and delete any files and empty folders unless
        a file is present within the given list of excluded files.
        """
        # remove deprecated files not in the index
        n = 0
        for root, _, filenames in os.walk(settings.CACHE_ROOT):
            for filename in filenames:
                if filename in self.RESERVED_FILENAMES:
                    continue

                fullpath = os.path.join(root, filename)
                relpath = fullpath.replace(settings.CACHE_ROOT, '')
                if relpath.startswith('/'):
                    relpath = relpath[1:]
                if relpath not in exclude:
                    os.remove(fullpath)
                    n += 1

        # remove any empty folders
        empty_folder_found = True
        while empty_folder_found:
            empty_folder_found = False
            for root, folders, _ in os.walk(settings.CACHE_ROOT):
                for folder in folders:
                    path = os.path.join(root, folder)
                    if len(os.listdir(path)) == 0:
                        os.rmdir(path)
                        empty_folder_found = True

        return n


    def _remove_file(self, filename):
        """
        Remove given file and return True if the file was removed successfully.
        """
        if os.path.isfile(filename):
            os.remove(filename)
            return True
        else:
            return False


    def _get_invalidated_cache_filename(self, filename):
        """
        Return the invalidated version of the given cache filename.
        """
        head, tail = os.path.split(filename)
        return os.path.join(head, '.' + tail)