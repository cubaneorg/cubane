#
# Original code based on drop-in extension of the CSV module by
# Ed Halley (ed@halley.cc) 18 August 2009
#
from __future__ import unicode_literals
from cubane.lib.utf8 import get_file_encoding, write_file_encoding
import csv ; from csv import *
import codecs
import cStringIO


__version__ = '1.0 Unicode'
__dropins__ = ['reader', 'writer']


class UTF8Recoder:
    """
    Iterator that reads a stream encoded in the given encoding.
    The output is re-encoded to UTF-8 for internal consistency.
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)


    def __iter__(self):
        return self


    def next(self):
        chunk = self.reader.next()
        chunk = chunk.encode('utf-8')
        return chunk


class reader:
    """
    A CSV reader which will iterate over lines in the CSV file 'f',
    from content in the optional encoding.
    """
    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        # try to read BOM if available
        bom, encoding = get_file_encoding(f, encoding)

        # open csv reader
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)


    def value(self, s):
        try:
            return int(s)
        except:
            pass

        try:
            return float(s)
        except:
            pass

        return unicode(s, 'utf-8')


    def next(self):
        row = self.reader.next()
        return [self.value(s) for s in row]


    def __iter__(self):
        return self


class writer:
    """
    A CSV writer which will write rows to CSV file 'f',
    employing the given encoding.
    """
    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.lookup(encoding)[-1](f, 'ignore')

        # write byte order mark for UTF encodings
        write_file_encoding(self.stream, encoding)


    def writerow(self, row):
        self.writer.writerow([(u'%s'%s).encode('utf-8') for s in row])

        # fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode('utf-8')

        # ... and reencode it into the target encoding
        self.encoder.write(data)

        # empty queue
        self.queue.truncate(0)


    def writerows(self, rows):
        for row in rows:
            self.writerow(row)