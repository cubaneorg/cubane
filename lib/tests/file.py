# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from django.utils import timezone
from cubane.tests.base import CubaneTestCase
from cubane.lib.file import get_file_hash
from cubane.lib.file import is_same_file
from cubane.lib.file import sizeof_fmt
from cubane.lib.file import file_get_mtime
from cubane.lib.file import file_set_mtime
from cubane.lib.file import ensure_dir
from cubane.lib.file import file_get_contents
from cubane.lib.file import file_put_contents
from cubane.lib.file import to_uniform_filename
from cubane.lib.file import is_text_file
from cubane.lib.file import get_caption_from_filename
from cubane.lib.file import folder_is_empty
from cubane.lib.file import folder_delete_content
from datetime import datetime
import tempfile
import os
import shutil
import codecs


class LibFileGetFileHashTestCase(CubaneTestCase):
    """
    cubane.lib.file.get_file_hash
    """
    EMPTY_FILE_HASH   = 'd41d8cd98f00b204e9800998ecf8427e'
    CONTENT_FILE_HASH = 'b10a8db164e0754105b7a99be72e3fe5'


    def test_should_generate_hash_for_empty_file(self):
        tmp = tempfile.gettempdir()
        filename = os.path.join(tmp, 'empty.txt')
        file_put_contents(filename, '')
        self.assertEqual(self.EMPTY_FILE_HASH, get_file_hash(filename))


    def test_should_generate_hash_for_file_with_content(self):
        tmp = tempfile.gettempdir()
        filename = os.path.join(tmp, 'content.txt')
        file_put_contents(filename, 'Hello World')
        self.assertEqual(self.CONTENT_FILE_HASH, get_file_hash(filename))


class LibFileIsSameFileTestCase(CubaneTestCase):
    """
    cubane.lib.file.is_same_file
    """
    def test_should_return_true_if_both_files_contain_the_same_content(self):
        tmp = tempfile.gettempdir()
        a = os.path.join(tmp, 'a.txt')
        file_put_contents(a, 'Hello World')

        tmp = tempfile.gettempdir()
        b = os.path.join(tmp, 'b.txt')
        file_put_contents(b, 'Hello World')

        self.assertTrue(is_same_file(a, b))


    def test_should_return_false_if_both_files_do_not_contain_the_same_content(self):
        tmp = tempfile.gettempdir()
        a = os.path.join(tmp, 'a.txt')
        file_put_contents(a, 'Hello Foo')

        tmp = tempfile.gettempdir()
        b = os.path.join(tmp, 'b.txt')
        file_put_contents(b, 'Hello Bar')

        self.assertFalse(is_same_file(a, b))


class LibFileSizeOfFMTTestCase(CubaneTestCase):
    """
    cubane.lib.file.sizeof_fmt()
    """
    KB = 1024
    MB = 1024 * KB
    GB = 1024 * MB
    TB = 1024 * GB


    def test_should_convert_to_bytes(self):
        self.assertEqual(sizeof_fmt(515), '515.0bytes')
        self.assertEqual(sizeof_fmt(-515), '-515.0bytes')


    def test_should_convert_to_KB(self):
        self.assertEqual(sizeof_fmt(self.KB), '1.0KB')
        self.assertEqual(sizeof_fmt(-self.KB), '-1.0KB')


    def test_should_convert_to_MB(self):
        self.assertEqual(sizeof_fmt(self.MB), '1.0MB')
        self.assertEqual(sizeof_fmt(-self.MB), '-1.0MB')


    def test_should_convert_to_GB(self):
        self.assertEqual(sizeof_fmt(self.GB), '1.0GB')
        self.assertEqual(sizeof_fmt(-self.GB), '-1.0GB')


    def test_should_convert_to_TB(self):
        self.assertEqual(sizeof_fmt(self.TB), '1.0TB')
        self.assertEqual(sizeof_fmt(-self.TB), '-1.0TB')


class LibFileFileGetSetMTimeTestCase(CubaneTestCase):
    """
    cubane.lib.file.file_set_mtime()
    cubane.lib.file.file_get_mtime()
    """
    def test_should_set_file_mod_time(self):
        tmp = tempfile.gettempdir()
        filename = os.path.join(tmp, 'mtime_test')
        file_put_contents(filename, 'test')
        ts = datetime(2016, 10, 8, 13, 40, 13)
        file_set_mtime(filename, ts)

        ts_read = file_get_mtime(filename)
        self.assertEqual(ts, ts_read)


class LibFileEnsureDirTestCase(CubaneTestCase):
    """
    cubane.lib.file.ensure_dir()
    """
    def test_should_create_path_if_not_exists(self):
        tmp = tempfile.gettempdir()
        filename = os.path.join(tmp, 'cubanetest', 'b', 'c', 'test.txt')
        path = ensure_dir(filename)
        self.assertEqual(path, os.path.dirname(filename))
        self.assertTrue(os.path.exists(path))
        shutil.rmtree(os.path.join(tmp, 'cubanetest'))


    def test_should_ignore_path_if_already_exists(self):
        tmp = tempfile.gettempdir()
        filename = os.path.join(tmp, 'cubanetest', 'b', 'c', 'test.txt')
        path = os.path.dirname(filename)

        self.assertFalse(os.path.exists(path))
        os.makedirs(path)
        self.assertTrue(os.path.exists(path))

        _path = ensure_dir(filename)
        self.assertEqual(path, _path)
        self.assertTrue(os.path.exists(path))

        shutil.rmtree(os.path.join(tmp, 'cubanetest'))


class LibFileGetContentsTestCase(CubaneTestCase):
    """
    cubane.lib.file.file_get_contents()
    """
    def test_should_receive_file_content_as_unicode(self):
        tmp = tempfile.gettempdir()
        filename = os.path.join(tmp, 'test.txt')
        content = unicode('Hello World')
        with codecs.open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        content_read = file_get_contents(filename)
        self.assertEqual(content_read, content)
        self.assertIsInstance(content_read, unicode)

        os.remove(filename)


class LibFilePutContentsTestCase(CubaneTestCase):
    """
    cubane.lib.file.file_put_contents()
    """
    def test_should_write_file_content_as_unicode(self):
        tmp = tempfile.gettempdir()
        filename = os.path.join(tmp, 'test.txt')
        content = unicode('Hello World')
        file_put_contents(filename, content)

        content_read = file_get_contents(filename)
        self.assertEqual(content_read, content)
        self.assertIsInstance(content_read, unicode)

        os.remove(filename)


class LibFileToUniformFilenameTestCase(CubaneTestCase):
    """
    cubane.lib.file.to_uniform_filename()
    """
    def test_should_replace_invalid_characters(self):
        self.assertEqual(to_uniform_filename('test/-*?+\\&^%$#@'), 'test')


    def test_should_strip_whitespace_and_invalid_characters(self):
        self.assertEqual(to_uniform_filename(' test@'), 'test')


    def test_should_replace_sequence_of_invalid_characters_only_once(self):
        self.assertEqual(to_uniform_filename('hello@@@@@@____world'), 'hello_world')


    def test_should_consider_extension(self):
        self.assertEqual(to_uniform_filename('hello', ext='.  world+++'), 'hello.world')


    def test_should_lower_case(self):
        self.assertEqual(to_uniform_filename('Test', ext='.TXT'), 'test.txt')


    def test_with_date(self):
        date = timezone.now().strftime(settings.STR_DATE_FORMAT)
        filename = to_uniform_filename('  test++.?txt-', with_timestamp=True)
        self.assertEqual(filename, 'test.txt_%s' % date)


class LibFileIsTextFileTestCase(CubaneTestCase):
    """
    cubane.lib.file.is_text_file()
    """
    def test_should_return_true_if_file_is_text_file(self):
        filename = os.path.join(settings.BASE_PATH, 'static', 'cubane', 'testapp', 'css', 'print.css')
        self.assertTrue(is_text_file(filename))


    def test_should_return_false_if_file_is_binary_file(self):
        filename = os.path.join(settings.BASE_PATH, 'static', 'cubane', 'testapp', 'img', 'test_images', 'test.jpg')
        self.assertFalse(is_text_file(filename))


class LibFileGetCaptionFromFilenameTestCase(CubaneTestCase):
    """
    cubane.lib.file.get_caption_from_filename()
    """
    def test_should_return_empty_string_for_none(self):
        self.assertEqual('', get_caption_from_filename(None))


    def test_should_unslugify_name_without_file_extension(self):
        self.assertEqual('Hello Foo', get_caption_from_filename('hello-foo.txt'))


    def test_should_replace_underline_with_spaces(self):
        self.assertEqual('Hello Foo', get_caption_from_filename('hello_foo.txt'))


    def test_should_replace_invalid_characters_with_space(self):
        self.assertEqual('Test 2', get_caption_from_filename('Test,=+*#£2.txt'))


    def test_should_substitute_multiple_spaces(self):
        self.assertEqual('Foo Bar', get_caption_from_filename('Foo     Bar.txt'))


    def test_should_ignore_missing_file_extension(self):
        self.assertEqual('Foo Bar', get_caption_from_filename('foo-bar'))


    def test_should_ignore_long_file_extension(self):
        self.assertEqual('Foo Bar', get_caption_from_filename('foo-bar.filextension'))


    def test_should_ignore_only_last_file_extensions(self):
        self.assertEqual('Foo Bar', get_caption_from_filename('foo.bar.txt'))


class LibFileFolderIsEmptyTestCase(CubaneTestCase):
    """
    cubane.lib.file.folder_is_empty()
    """
    def test_should_return_true_if_folder_is_empty(self):
        tmp = tempfile.gettempdir()
        folder = os.path.join(tmp, 'empty_folder')
        os.mkdir(folder)

        try:
            self.assertTrue(folder_is_empty(folder))
        finally:
            os.rmdir(folder)


    def test_should_return_false_if_folder_contains_files(self):
        tmp = tempfile.gettempdir()
        folder = os.path.join(tmp, 'not_empty_folder')
        filename = os.path.join(folder, 'test.txt')
        os.mkdir(folder)
        file_put_contents(filename, 'Foo')

        try:
            self.assertFalse(folder_is_empty(folder))
        finally:
            shutil.rmtree(folder)


    def test_should_return_false_if_folder_contains_sub_folders(self):
        tmp = tempfile.gettempdir()
        folder = os.path.join(tmp, 'not_empty_folder')
        sub_folder = os.path.join(folder, 'sub_folder')
        os.mkdir(folder)
        os.mkdir(sub_folder)

        try:
            self.assertFalse(folder_is_empty(folder))
        finally:
            shutil.rmtree(folder)


    def test_should_raise_error_if_folder_does_not_exist(self):
        tmp = tempfile.gettempdir()
        folder = os.path.join(tmp, 'does_not_exist')

        with self.assertRaisesRegexp(OSError, '\[Errno 2\] No such file or directory'):
            folder_is_empty(folder)


class LibFileFolderDeleteContentTestCase(CubaneTestCase):
    """
    cubane.lib.file.folder_delete_content()
    """
    def test_should_delete_files_and_folders_and_files_withing_sub_folders(self):
        # declare file paths
        tmp = tempfile.gettempdir()
        base = os.path.join(tmp, 'base_folder')
        filename = os.path.join(base, 'test.txt')
        subfolder = os.path.join(base, 'sub_folder')
        sub_file = os.path.join(subfolder, 'subtest.txt')

        # create file structure
        os.mkdir(base)
        os.mkdir(subfolder)
        file_put_contents(filename, 'Foo')
        file_put_contents(sub_file, 'Bar')

        try:
            # delete content of folder
            folder_delete_content(base)

            # folder should still exist
            self.assertTrue(os.path.isdir(base))

            # ...but folder should be empty
            self.assertTrue(folder_is_empty(base))
        finally:
            if os.path.isdir(base):
                shutil.rmtree(base)