# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.utils import timezone
import os
import codecs
import datetime
import re
import hashlib
import time
import shutil
import errno


def get_file_hash(filename):
    """
    Return the hash of the content of the given file. It is not specified which
    hash (or combination of hash) is used.
    """
    return hashlib.md5(open(filename, 'rb').read()).hexdigest()


def is_same_file(filename_a, filename_b):
    """
    Return True, if both files contain the same content based on comparing MD5
    hashes for both files.
    """
    return get_file_hash(filename_a) == get_file_hash(filename_b)


def sizeof_fmt(num):
    """
    Returns a human-readable representation of the given filesize, which is
    given in bytes.
    """
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0 and num > -1024.0:
            return '%3.1f%s' % (num, x)
        num /= 1024.0
    return '%3.1f%s' % (num, 'TB')


def file_set_mtime(filename, mtime):
    """
    Set the last access and modification timestamp of the file with the given
    filename to the given timestamp (datetime).
    """
    t = int(time.mktime(mtime.timetuple()))
    os.utime(filename, (t, t))


def file_get_st_mtime(filename):
    """
    Return the last modification timestamp of the file with the given filename
    as st_mtime.
    """
    stat = os.stat(filename)
    return stat.st_mtime


def file_get_mtime(filename):
    """
    Return the last modification timestamp of the file with the given filename
    as datetime.
    """
    return datetime.datetime.fromtimestamp(file_get_st_mtime(filename))


def ensure_dir(f):
    """
    Ensure that the full path and all components of the path to the given
    file f exist. If a directory component does not exist yet, it is created
    automatically.
    """
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)
    return d


def file_get_contents(filename):
    """
    Return the content of the given file.
    """
    with codecs.open(filename, encoding='utf-8') as f:
        return f.read()


def file_put_contents(filename, content):
    """
    Write the given content to the given file.
    """
    with codecs.open(filename, 'w', encoding='utf-8') as f:
        return f.write(content)


def file_move(src, dst):
    """
    Try to rename the source file to the dest. file via os.rename, which might
    fails due to "Invalid cross-device link", in which case we fall back to
    shutil.move(), but we need to deal with
    """
    # target directory must exist in order for shutil.move() to be compatible
    # with os.rename()...
    path = os.path.dirname(dst)
    if not os.path.isdir(path):
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT))

    # try os.rename(), otherwise use shutil.move()...
    try:
        os.rename(src, dst)
    except os.error, e:
        if e.errno == errno.EXDEV:
            shutil.move(src, dst)
        else:
            raise


def to_uniform_filename(filename, ext='', with_timestamp=False):
    """
    Return a uniform filename based on the given filename, where the filename
    is lower case and all spaces and not-allowed characters have been replaced
    by underline characters.
    Optionally the filename contains time information of the current date.
    """
    if with_timestamp:
        filename = '%s_%s%s' % (
            filename,
            timezone.now().strftime(settings.STR_DATE_FORMAT),
            ext
        )
    else:
        filename = '%s%s' % (filename, ext)

    plain_filename = re.sub(r'([-\s\/\?\*\+\\&^%$#@_]+)', '_', filename).lower().strip('_')
    plain_filename = re.sub(r'\._', '.', plain_filename)
    plain_filename = re.sub(r'_\.', '.', plain_filename)

    return plain_filename


def is_text_file(filename):
    """
    Return True, if the given file is assumed to be a text file.
    See: http://stackoverflow.com/questions/898669/how-can-i-detect-if-a-file-is-binary-non-text-in-python
    Further information:
    http://stackoverflow.com/questions/32184809/python-file1-why-are-the-numbers-7-8-9-10-12-13-27-and-range0x20-0x100
    """
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    is_binary = lambda bytes: bool(bytes.translate(None, textchars))
    return not is_binary(open(filename, 'rb').read(1024))


def get_caption_from_filename(filename):
    """
    Extract human-readable caption text from given filename.
    """
    if filename is None:
        return ''

    fname, _ = os.path.splitext(filename)
    caption = re.sub(r'([^\w\d\s]|[_])', ' ', fname).strip()
    caption = re.sub(r'\s{2,}', ' ', caption)
    caption = caption.title()
    return caption


def folder_is_empty(path):
    """
    Return True, if the given folder is empty; so does not contain any files or
    sub-folders.
    """
    return not os.listdir(path)


def folder_delete_content(path):
    """
    Deletes the content of the given folder including all files and sub-folders
    without removing the root folder itself.
    """
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except:
            pass