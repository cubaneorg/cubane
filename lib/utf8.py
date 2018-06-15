# coding=UTF-8
from __future__ import unicode_literals
from cubane.lib.file import file_put_contents
from StringIO import StringIO
import chardet


DEFAULT_ENCOPDING = 'utf_8'
DETECT_ENCODING   = 'detect'
ENCODING_CHOICES  = (
    ('utf_8',          'UTF-8 (All Languages)'),
    ('cp1252',         'Windows-1252 Western Europe'),

    ('cp1250',         'Windows-1250 Central and Eastern Europe'),
    ('cp1251',         'Windows-1251 Bulgarian, Byelorussian, Macedonian, Russian, Serbian'),
    ('cp1253',         'Windows-1253 Greek'),
    ('cp1254',         'Windows-1254 Turkish'),
    ('cp1255',         'Windows-1255 Hebrew'),
    ('cp1256',         'Windows-1256 Arabic'),
    ('cp1257',         'Windows-1257 Baltic languages'),
    ('cp1258',         'Windows-1258 Vietnamese'),

    ('utf_32',         'UTF-32 (All Languages)'),
    ('utf_32_be',      'UTF-32 BE (All Languages)'),
    ('utf_32_le',      'UTF-32 LE (All Languages)'),
    ('utf_16',         'UTF-16 (All Languages)'),
    ('utf_16_be',      'UTF-16 BE (All Languages) (BMP only)'),
    ('utf_16_le',      'UTF-16 LE (All Languages) (BMP only)'),
    ('utf_7',          'UTF-7 (All Languages)'),
    ('utf_8_sig',      'UTF-8 SIG (All Languages)'),

    (DETECT_ENCODING,  'Automatically Detect (Ambiguous)'),

    ('ascii',          '646, us-ascii English'),
    ('big5',           'big5-tw, csbig5	Traditional Chinese'),
    ('big5hkscs',      'big5-hkscs, hkscs Traditional Chinese'),
    ('cp037',          'IBM037, IBM039 English'),
    ('cp424',          'EBCDIC-CP-HE, IBM424 Hebrew'),
    ('cp437',          '437, IBM437	English'),
    ('cp500',          'EBCDIC-CP-BE, EBCDIC-CP-CH, IBM500 Western Europe'),
    ('cp720',          'Arabic'),
    ('cp737',          'Greek'),
    ('cp775',          'IBM775 Baltic languages'),
    ('cp850',          '850, IBM850	Western Europe'),
    ('cp852',          '852, IBM852	Central and Eastern Europe'),
    ('cp855',          '855, IBM855	Bulgarian, Byelorussian, Macedonian, Russian, Serbian'),
    ('cp856',          'Hebrew'),
    ('cp857',          '857, IBM857	Turkish'),
    ('cp858',          '858, IBM858	Western Europe'),
    ('cp860',          '860, IBM860	Portuguese'),
    ('cp861',          '861, CP-IS, IBM861	Icelandic'),
    ('cp862',          '862, IBM862	Hebrew'),
    ('cp863',          '863, IBM863	Canadian'),
    ('cp864',          'IBM864 Arabic'),
    ('cp865',          '865, IBM865	Danish, Norwegian'),
    ('cp866',          '866, IBM866	Russian'),
    ('cp869',          '869, CP-GR, IBM869 Greek'),
    ('cp874',          'Thai'),
    ('cp875',          'Greek'),
    ('cp932',          '932, ms932, mskanji, ms-kanji Japanese'),
    ('cp949',          '949, ms949, uhc	Korean'),
    ('cp950',          '950, ms950 Traditional Chinese'),
    ('cp1006',         'Urdu'),
    ('cp1026',         'ibm1026	Turkish'),
    ('cp1140',         'ibm1140	Western Europe'),
    ('euc_jp',         'eucjp, ujis, u-jis Japanese'),
    ('euc_jis_2004',   'jisx0213, eucjis2004 Japanese'),
    ('euc_jisx0213',   'eucjisx0213	Japanese'),
    ('euc_kr',         'euckr, korean, ksc5601, ks_c-5601, ks_c-5601-1987, ksx1001, ks_x-1001 Korean'),
    ('gb2312',         'chinese, csiso58gb231280, euc- cn, euccn, eucgb2312-cn, gb2312-1980, gb2312-80, iso- ir-58 Simplified Chinese'),
    ('gbk',            '936, cp936, ms936 Unified Chinese'),
    ('gb18030',        'gb18030-2000 Unified Chinese'),
    ('hz',             'hzgb, hz-gb, hz-gb-2312	Simplified Chinese'),
    ('iso2022_jp',     'csiso2022jp, iso2022jp, iso-2022-jp	Japanese'),
    ('iso2022_jp_1',   'iso2022jp-1, iso-2022-jp-1 Japanese'),
    ('iso2022_jp_2',   'iso2022jp-2, iso-2022-jp-2 Japanese, Korean, Simplified Chinese, Western Europe, Greek'),
    ('iso2022_jp_2004','iso2022jp-2004, iso-2022-jp-2004 Japanese'),
    ('iso2022_jp_3',   'iso2022jp-3, iso-2022-jp-3 Japanese'),
    ('iso2022_jp_ext', 'iso2022jp-ext, iso-2022-jp-ext Japanese'),
    ('iso2022_kr',     'csiso2022kr, iso2022kr, iso-2022-kr	Korean'),
    ('latin_1',        'iso-8859-1, iso8859-1, 8859, cp819, latin, latin1, L1 West Europe'),
    ('iso8859_2',      'iso-8859-2, latin2, L2 Central and Eastern Europe'),
    ('iso8859_3',      'iso-8859-3, latin3, L3 Esperanto, Maltese'),
    ('iso8859_4',      'iso-8859-4, latin4, L4 Baltic languages'),
    ('iso8859_5',      'iso-8859-5, cyrillic Bulgarian, Byelorussian, Macedonian, Russian, Serbian'),
    ('iso8859_6',      'iso-8859-6, arabic Arabic'),
    ('iso8859_7',      'iso-8859-7, greek, greek8 Greek'),
    ('iso8859_8',      'iso-8859-8, hebrew Hebrew'),
    ('iso8859_9',      'iso-8859-9, latin5, L5 Turkish'),
    ('iso8859_10',     'iso-8859-10, latin6, L6	Nordic languages'),
    ('iso8859_11',     'iso-8859-11, thai Thai languages'),
    ('iso8859_13',     'iso-8859-13, latin7, L7	Baltic languages'),
    ('iso8859_14',     'iso-8859-14, latin8, L8	Celtic languages'),
    ('iso8859_15',     'iso-8859-15, latin9, L9	Western Europe'),
    ('iso8859_16',     'iso-8859-16, latin10, L10 South-Eastern Europe'),
    ('johab',          'cp1361, ms1361 Korean'),
    ('koi8_r',         'Russian'),
    ('koi8_u',         'Ukrainian'),
    ('mac_cyrillic',   'maccyrillic	Bulgarian, Byelorussian, Macedonian, Russian, Serbian'),
    ('mac_greek',      'macgreek Greek'),
    ('mac_iceland',    'maciceland Icelandic'),
    ('mac_latin2',     'maclatin2, maccentraleurope	Central and Eastern Europe'),
    ('mac_roman',      'macroman Western Europe'),
    ('mac_turkish',    'macturkish Turkish'),
    ('ptcp154',        'csptcp154, pt154, cp154, cyrillic-asian	Kazakh'),
    ('shift_jis',      'csshiftjis, shiftjis, sjis, s_jis Japanese'),
    ('shift_jis_2004', 'shiftjis2004, sjis_2004, sjis2004 Japanese'),
    ('shift_jisx0213', 'shiftjisx0213, sjisx0213, s_jisx0213 Japanese')
)


#
# Byte Order Markers
#
BYTE_ORDER_MARKER_MIN_LENGTH = 2
BYTE_ORDER_MARKER_MAX_LENGTH = 5
BYTE_ORDER_MARKERS = [
    ([0xEF, 0xBB, 0xBF],             'utf_8'),
    ([0xFE, 0xFF],                   'utf_16_be'),
    ([0xFF, 0xFE],                   'utf_16_le'),
    ([0x00, 0x00, 0xFE, 0xFF],       'utf_32_be'),
    ([0xFF, 0xFE, 0x00, 0x00],       'utf_32_le'),
    ([0x2B, 0x2F, 0x76, 0x38],       'utf_7'),
    ([0x2B, 0x2F, 0x76, 0x39],       'utf_7'),
    ([0x2B, 0x2F, 0x76, 0x2B],       'utf_7'),
    ([0x2B, 0x2F, 0x76, 0x2F],       'utf_7'),
    ([0x2B, 0x2F, 0x76, 0x38, 0x2D], 'utf_7'),
]


def get_file_encoding(f, default_encoding=DEFAULT_ENCOPDING):
    """
    Attempt to read BOM marker at the beginning of the given file stream
    and return the expected encoding.
    """
    def _array_equal(ass, bss):
        if len(ass) != len(bss):
            return False

        for i, a in enumerate(ass):
            if a != bss[i]:
                return False

        return True

    bom = [ord(c) for c in f.read(BYTE_ORDER_MARKER_MAX_LENGTH)]
    for i in range(BYTE_ORDER_MARKER_MIN_LENGTH, BYTE_ORDER_MARKER_MAX_LENGTH + 1):
        _bom = bom[:i]
        for marker, encoding in BYTE_ORDER_MARKERS:
            if _array_equal(_bom, marker):
                f.seek(i)
                return _bom, encoding

    # encoding not found
    f.seek(0)
    return None, default_encoding


def write_file_encoding(f, encoding):
    """
    Write BOM marker at the beginning of the given file stream,
    if the file encoding matches.
    """
    if not encoding:
        return

    encoding = encoding.strip().lower().replace('-', '_')
    for marker, _encoding in BYTE_ORDER_MARKERS:
        if _encoding == encoding:
            for byte in marker:
                f.write(chr(byte))


def to_utf8(rawdata, encoding=None):
    """
    Takes the given raw data that might be encoded in something that is not
    UTF-8 and convert the data into UTF-8. If the encoding is DETECT_ENCODING,
    the current encoding is detected by using statistical analysis, which might
    not be 100 percent correct.
    """
    if encoding is None:
        encoding = DETECT_ENCODING

    if encoding == DETECT_ENCODING:
        # attempt to detect encoding
        result = chardet.detect(rawdata)
        if result:
            encoding = result.get('encoding')

    # if we found an encoding, attempt to decode the raw data string
    # according to the encoding that is assumed. This is obviously a best guess
    # here, but will probably work out of the box as long as the data is
    # large enought...
    return rawdata.decode(encoding)


def utf8_stream(stream, encoding=None):
    """
    Returns a new UTF8-encoded stream of the given stream by decoding the data
    using the given encoding and then re-encoding the data as UTF-8.
    """
    # read stream data and convert into utf8
    rawdata = stream.read()
    utf8_data = to_utf8(rawdata, encoding)

    # pack utf-8 string back into a binary stream (utf-8 encoded)
    result = StringIO()
    result.write(utf8_data.encode('utf-8'))
    result.seek(0)
    return result