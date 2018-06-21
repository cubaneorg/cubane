# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
import cStringIO
import cubane.lib.ucsv as csv


class LibUCSVTestCaseBase(CubaneTestCase):
    """
    Help methods for constructing CSV content
    """
    def create_content_from_string(self, s):
        """
        Create sample CSV content from the given string.
        """
        content = cStringIO.StringIO()
        content.write(s)
        content.seek(0)
        return content


    def create_content(self, lines=[]):
        """
        Create sample CSV content based on given array of lines.
        """
        return self.create_content_from_string('\n'.join(lines))


    def create_reader(self, content, encoding='utf-8'):
        """
        Construct default CSV reader with standard options for given content.
        """
        return csv.reader(
            content,
            delimiter=b',',
            quotechar=b'"',
            quoting=csv.QUOTE_ALL,
            encoding=encoding
        )


    def create_writer(self, stream):
        """
        Create CSV writer with default options to write its content to the
        given stream.
        """
        return csv.writer(
            stream,
            delimiter=b',',
            quotechar=b'"',
            quoting=csv.QUOTE_ALL
        )


class LibUCSVReaderTestCase(LibUCSVTestCaseBase):
    """
    Reading CSV content
    """
    def test_reader(self):
        reader = self.create_reader(
            self.create_content([
                'ID,Name',
                '1,Foo',
                '2,Bar'
            ])
        )
        self.assertEqual(list(reader), [[u'ID', u'Name'], [1, u'Foo'], [2, u'Bar']])


    def test_reader_latin_1(self):
        reader = self.create_reader(
            self.create_content_from_string(u'ééé'.encode('latin1')),
            encoding='latin-1'
        )
        self.assertEqual(list(reader), [[u'\xe9\xe9\xe9']])


    def test_read_int_and_floats(self):
        reader = self.create_reader(
            self.create_content([
                'Int,44',
                'Float,0.25'
            ])
        )
        self.assertEqual(list(reader), [[u'Int', 44], ['Float', 0.25]])


class LibUCSVWriterTestCase(LibUCSVTestCaseBase):
    """
    Writing CSV content
    """
    def test_writer_row(self):
        content = self.create_content()
        writer = self.create_writer(content)
        writer.writerow(['ID', 'NAME'])
        writer.writerow(['1', 'Foo'])
        writer.writerow(['2', 'Bar'])

        content = content.getvalue().decode('utf-8')
        self.assertTrue(content.startswith('\ufeff'))
        self.assertEqual(content[1:], '"ID","NAME"\r\n"1","Foo"\r\n"2","Bar"\r\n')


    def test_write_rows(self):
        content = self.create_content()
        writer = self.create_writer(content)
        writer.writerows([
            ['ID', 'NAME'],
            ['1', 'Foo'],
            ['2', 'Bar']
        ])

        content = content.getvalue().decode('utf-8')
        self.assertTrue(content.startswith('\ufeff'))
        self.assertEqual(content[1:], '"ID","NAME"\r\n"1","Foo"\r\n"2","Bar"\r\n')