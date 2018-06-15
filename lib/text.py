# coding=UTF-8
from __future__ import unicode_literals
from django.utils.html import strip_tags
from bs4 import BeautifulSoup, NavigableString
import re
import unicodedata
import htmlentitydefs


STOP_WORDS = [
    'a',
    'able',
    'about',
    'above',
    'abroad',
    'according',
    'accordingly',
    'across',
    'actually',
    'adj',
    'after',
    'afterwards',
    'again',
    'against',
    'ago',
    'ahead',
    'ain''t',
    'all',
    'allow',
    'allows',
    'almost',
    'alone',
    'along',
    'alongside',
    'already',
    'also',
    'although',
    'always',
    'am',
    'amid',
    'amidst',
    'among',
    'amongst',
    'an',
    'and',
    'another',
    'any',
    'anybody',
    'anyhow',
    'anyone',
    'anything',
    'anyway',
    'anyways',
    'anywhere',
    'apart',
    'appear',
    'appreciate',
    'appropriate',
    'are',
    'aren''t',
    'around',
    'as',
    'a''s',
    'aside',
    'ask',
    'asking',
    'associated',
    'at',
    'available',
    'away',
    'awfully',
    'b',
    'back',
    'backward',
    'backwards',
    'be',
    'became',
    'because',
    'become',
    'becomes',
    'becoming',
    'been',
    'before',
    'beforehand',
    'begin',
    'behind',
    'being',
    'believe',
    'below',
    'beside',
    'besides',
    'best',
    'better',
    'between',
    'beyond',
    'both',
    'brief',
    'but',
    'by',
    'c',
    'came',
    'can',
    'cannot',
    'cant',
    'can''t',
    'caption',
    'cause',
    'causes',
    'certain',
    'certainly',
    'changes',
    'clearly',
    'c''mon',
    'co',
    'co.',
    'com',
    'come',
    'comes',
    'concerning',
    'consequently',
    'consider',
    'considering',
    'contain',
    'containing',
    'contains',
    'corresponding',
    'could',
    'couldn''t',
    'course',
    'c''s',
    'currently',
    'd',
    'dare',
    'daren''t',
    'definitely',
    'described',
    'despite',
    'did',
    'didn''t',
    'different',
    'directly',
    'do',
    'does',
    'doesn''t',
    'doing',
    'done',
    'don''t',
    'down',
    'downwards',
    'during',
    'e',
    'each',
    'edu',
    'eg',
    'eight',
    'eighty',
    'either',
    'else',
    'elsewhere',
    'end',
    'ending',
    'enough',
    'entirely',
    'especially',
    'et',
    'etc',
    'even',
    'ever',
    'evermore',
    'every',
    'everybody',
    'everyone',
    'everything',
    'everywhere',
    'ex',
    'exactly',
    'example',
    'except',
    'f',
    'fairly',
    'far',
    'farther',
    'few',
    'fewer',
    'fifth',
    'first',
    'five',
    'followed',
    'following',
    'follows',
    'for',
    'forever',
    'former',
    'formerly',
    'forth',
    'forward',
    'found',
    'four',
    'from',
    'further',
    'furthermore',
    'g',
    'get',
    'gets',
    'getting',
    'given',
    'gives',
    'go',
    'goes',
    'going',
    'gone',
    'got',
    'gotten',
    'greetings',
    'h',
    'had',
    'hadn''t',
    'half',
    'happens',
    'hardly',
    'has',
    'hasn''t',
    'have',
    'haven''t',
    'having',
    'he',
    'he''d',
    'he''ll',
    'hello',
    'help',
    'hence',
    'her',
    'here',
    'hereafter',
    'hereby',
    'herein',
    'here''s',
    'hereupon',
    'hers',
    'herself',
    'he''s',
    'hi',
    'him',
    'himself',
    'his',
    'hither',
    'hopefully',
    'how',
    'howbeit',
    'however',
    'hundred',
    'i',
    'i''d',
    'ie',
    'if',
    'ignored',
    'i''ll',
    'i''m',
    'immediate',
    'in',
    'inasmuch',
    'inc',
    'inc.',
    'indeed',
    'indicate',
    'indicated',
    'indicates',
    'inner',
    'inside',
    'insofar',
    'instead',
    'into',
    'inward',
    'is',
    'isn''t',
    'it',
    'it''d',
    'it''ll',
    'its',
    'it''s',
    'itself',
    'i''ve',
    'j',
    'just',
    'k',
    'keep',
    'keeps',
    'kept',
    'know',
    'known',
    'knows',
    'l',
    'last',
    'lately',
    'later',
    'latter',
    'latterly',
    'least',
    'less',
    'lest',
    'let',
    'let''s',
    'like',
    'liked',
    'likely',
    'likewise',
    'little',
    'look',
    'looking',
    'looks',
    'low',
    'lower',
    'ltd',
    'm',
    'made',
    'mainly',
    'make',
    'makes',
    'many',
    'may',
    'maybe',
    'mayn''t',
    'me',
    'mean',
    'meantime',
    'meanwhile',
    'merely',
    'might',
    'mightn''t',
    'mine',
    'minus',
    'miss',
    'more',
    'moreover',
    'most',
    'mostly',
    'mr',
    'mrs',
    'much',
    'must',
    'mustn''t',
    'my',
    'myself',
    'n',
    'name',
    'namely',
    'nd',
    'near',
    'nearly',
    'necessary',
    'need',
    'needn''t',
    'needs',
    'neither',
    'never',
    'neverf',
    'neverless',
    'nevertheless',
    'new',
    'next',
    'nine',
    'ninety',
    'no',
    'nobody',
    'non',
    'none',
    'nonetheless',
    'noone',
    'no-one',
    'nor',
    'normally',
    'not',
    'nothing',
    'notwithstanding',
    'novel',
    'now',
    'nowhere',
    'o',
    'obviously',
    'of',
    'off',
    'often',
    'oh',
    'ok',
    'okay',
    'old',
    'on',
    'once',
    'one',
    'ones',
    'one''s',
    'only',
    'onto',
    'opposite',
    'or',
    'other',
    'others',
    'otherwise',
    'ought',
    'oughtn''t',
    'our',
    'ours',
    'ourselves',
    'out',
    'outside',
    'over',
    'overall',
    'own',
    'p',
    'particular',
    'particularly',
    'past',
    'per',
    'perhaps',
    'placed',
    'please',
    'plus',
    'possible',
    'presumably',
    'probably',
    'provided',
    'provides',
    'q',
    'que',
    'quite',
    'qv',
    'r',
    'rather',
    'rd',
    're',
    'really',
    'reasonably',
    'recent',
    'recently',
    'regarding',
    'regardless',
    'regards',
    'relatively',
    'respectively',
    'right',
    'round',
    's',
    'said',
    'same',
    'saw',
    'say',
    'saying',
    'says',
    'second',
    'secondly',
    'see',
    'seeing',
    'seem',
    'seemed',
    'seeming',
    'seems',
    'seen',
    'self',
    'selves',
    'sensible',
    'sent',
    'serious',
    'seriously',
    'seven',
    'several',
    'shall',
    'shan''t',
    'she',
    'she''d',
    'she''ll',
    'she''s',
    'should',
    'shouldn''t',
    'since',
    'six',
    'so',
    'some',
    'somebody',
    'someday',
    'somehow',
    'someone',
    'something',
    'sometime',
    'sometimes',
    'somewhat',
    'somewhere',
    'soon',
    'sorry',
    'specified',
    'specify',
    'specifying',
    'still',
    'sub',
    'such',
    'sup',
    'sure',
    't',
    'take',
    'taken',
    'taking',
    'tell',
    'tends',
    'th',
    'than',
    'thank',
    'thanks',
    'thanx',
    'that',
    'that''ll',
    'thats',
    'that''s',
    'that''ve',
    'the',
    'their',
    'theirs',
    'them',
    'themselves',
    'then',
    'thence',
    'there',
    'thereafter',
    'thereby',
    'there''d',
    'therefore',
    'therein',
    'there''ll',
    'there''re',
    'theres',
    'there''s',
    'thereupon',
    'there''ve',
    'these',
    'they',
    'they''d',
    'they''ll',
    'they''re',
    'they''ve',
    'thing',
    'things',
    'think',
    'third',
    'thirty',
    'this',
    'thorough',
    'thoroughly',
    'those',
    'though',
    'three',
    'through',
    'throughout',
    'thru',
    'thus',
    'till',
    'to',
    'together',
    'too',
    'took',
    'toward',
    'towards',
    'tried',
    'tries',
    'truly',
    'try',
    'trying',
    't''s',
    'twice',
    'two',
    'u',
    'un',
    'under',
    'underneath',
    'undoing',
    'unfortunately',
    'unless',
    'unlike',
    'unlikely',
    'until',
    'unto',
    'up',
    'upon',
    'upwards',
    'us',
    'use',
    'used',
    'useful',
    'uses',
    'using',
    'usually',
    'v',
    'value',
    'various',
    'versus',
    'very',
    'via',
    'viz',
    'vs',
    'w',
    'want',
    'wants',
    'was',
    'wasn''t',
    'way',
    'we',
    'we''d',
    'welcome',
    'well',
    'we''ll',
    'went',
    'were',
    'we''re',
    'weren''t',
    'we''ve',
    'what',
    'whatever',
    'what''ll',
    'what''s',
    'what''ve',
    'when',
    'whence',
    'whenever',
    'where',
    'whereafter',
    'whereas',
    'whereby',
    'wherein',
    'where''s',
    'whereupon',
    'wherever',
    'whether',
    'which',
    'whichever',
    'while',
    'whilst',
    'whither',
    'who',
    'who''d',
    'whoever',
    'whole',
    'who''ll',
    'whom',
    'whomever',
    'who''s',
    'whose',
    'why',
    'will',
    'willing',
    'wish',
    'with',
    'within',
    'without',
    'wonder',
    'won''t',
    'would',
    'wouldn''t',
    'x',
    'y',
    'yes',
    'yet',
    'you',
    'you''d',
    'you''ll',
    'your',
    'you''re',
    'yours',
    'yourself',
    'yourselves',
    'you''ve',
    'z',
    'zero',
]


def text_with_prefix(text, prefix):
    """
    Transform the given text, so that it always starts with the given prefix
    value (case in-sensitive).
    """
    if text and prefix:
        if not text.startswith(prefix):
            return prefix + text
    return text


def text_with_suffix(text, suffix):
    """
    Transform the given text, so that it always ends with the given suffix
    value (case in-sensitive).
    """
    if text and suffix:
        if not text.endswith(suffix):
            return text + suffix
    return text


def text_without_prefix(text, prefix):
    """
    Transform the given text, so that it does not start with the given prefix
    (case in-sensitive).
    """
    if text and prefix:
        text = unicode(text)
        n = len(prefix)
        if len(text) >= n and text[:n].lower() == prefix.lower():
            text = text[n:]
    return text


def text_without_suffix(text, suffix):
    """
    Transform the given text, so that it does not end with the given suffix
    (case in-sensitive).
    """
    if text and suffix:
        n = len(suffix)
        if len(text) >= n and text[-n:].lower() == suffix.lower():
            text = text[:-n]
    return text


def text_from_html(html, max_length=None):
    """
    Return the given html string as a plain text without any html tags.
    If the max_length argument is given, the resulting text will be cut off to
    the given max. length.
    """
    if not html:
        return ''

    s = re.sub(
        r'[\xa0\s]+',
        ' ',
        clean_unicode(
            unescape(
                strip_tags(
                    re.sub(r'<', ' <', html)
                )
            )
        )
    ).strip()

    return s[:max_length] if max_length else s


def formatted_text_from_html(html, max_length=None):
    """
    Return the given html string as a plain text without any html tags while
    maintaining basic formatting of the text by using newline and spaces.
    If the max_length argument is given, the resulting text will be cut off to
    the given max. length.
    """
    if not html:
        return ''

    def visit_tag(tag):
        text = ''
        if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
            text += tag.get_text() + '\n\n'
        elif tag.name is None:
            s = tag.string.strip()
            if s != '':
                text += tag.string + '\n\n'
        else:
            for child in tag.contents:
                text += visit_tag(child)

        return text

    soup = BeautifulSoup(html, 'html5lib')
    text = visit_tag(soup).strip().strip('\n')
    return text[:max_length] if max_length else text


def pluralize(n, terms, msg=None, tag=None):
    """
    Pluralize the given term based on the given number.
    """
    if isinstance(terms, basestring): terms = [terms, '%ss' % terms]
    if len(terms) == 1: terms.append('%ss' % terms[0])
    if msg != None: msg = ' ' + msg

    term = terms[0] if abs(n) == 1 else terms[1]
    return '%s%d%s %s%s' % (
        '<%s>' % tag if tag else '',
        n,
        '</%s>' % tag if tag else '',
        term,
        '%s' % msg if msg else ''
    )


def clean_unicode(string):
    """
    Return the given unicode string with unnamed characters removed
    (apart from tab and line feed).
    """
    new_string = ''
    for char in string:
        try:
            if char != '\n' and char != '\t':
                unicodedata.name(char)
            new_string += char
        except ValueError:
            pass
    return new_string


def unescape(text):
    """
    Unescape html entities into corresponding UTF-8 codes.
    Based on: http://effbot.org/zone/re-sub.htm#unescape-html
    """
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


def get_words(text, remove_duplicates=True, filter_stop_words=True, min_word_length=4, max_words=None, allow_digits=False):
    """
    Return a list of non-empty words that have been extracted from the given
    text that are NOT stop words, all words in lowercase without duplicates.
    """
    if text is None: return []

    # replace line breaks with empty spaces
    text = re.sub('\r?\n', ' ', text)

    # strip out non-relevant characters
    if allow_digits:
        text = re.sub(r'[^a-zA-Z0-9 ]', ' ', text)
    else:
        text = re.sub(r'[^a-zA-Z ]', ' ', text)

    # split into words
    words = [w.strip().lower() for w in re.split('\s', text)]

    # filter out empty words and stop words
    if filter_stop_words:
        words = filter(lambda w: w not in STOP_WORDS, words)
    else:
        words = filter(lambda w: w, words)

    # filter out short words
    if min_word_length:
        words = filter(lambda w: len(w) >= min_word_length, words)

    # max words
    if max_words:
        words = words[:max_words]

    # remove duplicates
    if remove_duplicates:
        words = list(set(words))

    return words


def get_keywords(s=None, word_count=20):
    """
    Generate a list of keywords based on the given text s containing a max.
    if word_count keywords or less.
    """
    # extract words from given text
    keywords = get_words(s, remove_duplicates=False)

    # determine keyword frequency
    unique_keywords = set(keywords)
    freq = list([(keyword, keywords.count(keyword)) for keyword in unique_keywords])
    freq = sorted(freq, key=lambda x: x[1], reverse=True)

    # extract keywords (most frequent first)
    keywords = list([k for k, _ in freq])

    # limit amount of keywords
    keywords = keywords[:word_count]

    # return list of keywords
    return keywords


def get_line_number_from_offset(message, offset):
    """
    Return the line number of the given offset within the given message text.
    """
    if not message or offset < 0:
        return 0

    # trim to given offset position
    s = message[:offset]

    # count line breaks within input string
    return 1 + len(re.findall(r'\n', s))


def join_not_blank(components, separator=' '):
    """
    Join given components together if they are not None or blank.
    """
    return separator.join(filter(lambda x: x, components))


def char_range(start, end, step=1):
    """
    Generates a range of given characters.
    """
    for char in range(ord(start), ord(end) + 1, step):
        yield chr(char)