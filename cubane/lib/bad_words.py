# coding=UTF-8
from __future__ import unicode_literals
import unicodedata
import re


SPECIAL_CHARACTER_SUBS = {
    '!': 'i',
    '1': 'i',
    '!': 'i',
    '0': 'o',
    '3': 'e',
    '4': 'a',
    '5': 's',
    '7': 't',
    '%': 'u'
}


SHORT_STOP_WORDS = [
    'a',
    'to',
    'i',
    'im',
    'me',
    'my',
    'so'
]


BAD_WORDS = [
    'anal',
    'anus',
    'arrse',
    'arse',
    'ass',
    'asses',
    'assfucker',
    'assfukka',
    'asshole',
    'assholes',
    'asswhole',
    'ballbag',
    'balls',
    'ballsack',
    'bastard',
    'beastial',
    'beastiality',
    'bellend',
    'bestial',
    'bestiality',
    'biatch',
    'bich',
    'bitch',
    'bitcher',
    'bitchers',
    'bitches',
    'bitchin',
    'bitching',
    'bloody',
    'blow job',
    'blowjob',
    'blowjobs',
    'boiolas',
    'bollock',
    'bollok',
    'boner',
    'boob',
    'boobs',
    'booobs',
    'boooobs',
    'booooobs',
    'booooooobs',
    'breasts',
    'buceta',
    'bugger',
    'bukkake',
    'bum',
    'bunny fucker',
    'butt',
    'butthole',
    'buttmuch',
    'buttmunch',
    'buttplug',
    'carpet muncher',
    'cawk',
    'chink',
    'cipa',
    'clit',
    'clitoris',
    'clits',
    'cnut',
    'cock',
    'cck',
    'cockface',
    'cockhead',
    'cockmunch',
    'cockmuncher',
    'cocks',
    'cocksuck',
    'cocksucked',
    'cocksucker',
    'cocksucking',
    'cocksucks',
    'cocksuka',
    'cocksukka',
    'cok',
    'cokmuncher',
    'coksucka',
    'coon',
    'cox',
    'crap',
    'cum',
    'cummer',
    'cumming',
    'cums',
    'cumshot',
    'cunilingus',
    'cunillingus',
    'cunnilingus',
    'cunt',
    'cuntlick',
    'cuntlicker',
    'cuntlicking',
    'cunts',
    'cyalis',
    'cyberfuc',
    'cyberfuck',
    'cyberfucked',
    'cyberfucker',
    'cyberfuckers',
    'cyberfucking',
    'damn',
    'dick',
    'dck',
    'dickhead',
    'dildo',
    'dildos',
    'dink',
    'dinks',
    'dirsa',
    'dlck',
    'dogfucker',
    'doggin',
    'dogging',
    'donkeypunch',
    'donkeyribber',
    'doosh',
    'duche',
    'dyke',
    'ejaculat',
    'ejaculate',
    'ejaculated',
    'ejaculates',
    'ejaculating',
    'ejaculatings',
    'ejaculation',
    'ejakulate',
    'fag',
    'fagging',
    'faggitt',
    'faggot',
    'faggs',
    'fagot',
    'fagots',
    'fags',
    'fanny',
    'fannyflaps',
    'fannyfucker',
    'fanyy',
    'fatass',
    'fcuk',
    'fcuker',
    'fcuking',
    'feck',
    'fecker',
    'felch',
    'felching',
    'fellate',
    'fellatio',
    'fingerfuck',
    'fingerfucked',
    'fingerfucker',
    'fingerfuckers',
    'fingerfucking',
    'fingerfucks',
    'fistfuck',
    'fistfucked',
    'fistfucker',
    'fistfuckers',
    'fistfucking',
    'fistfuckings',
    'fistfucks',
    'flange',
    'fleshflute',
    'fook',
    'fooker',
    'fuck',
    'fck',
    'fucka',
    'fucked',
    'fucker',
    'fuckers',
    'fuckhead',
    'fuckheads',
    'fuckin',
    'fucking',
    'fuckings',
    'fuckingshitmotherfucker',
    'fuckme',
    'fucks',
    'fuckwhit',
    'fuckwit',
    'fudge packer',
    'fudgepacker',
    'fuk',
    'fuker',
    'fukker',
    'fukkin',
    'fuks',
    'fukwhit',
    'fukwit',
    'fux',
    'fuxor',
    'gangbang',
    'gangbanged',
    'gangbangs',
    'gaylord',
    'gaysex',
    'getlaid',
    'get laid',
    'girls',
    'goatse',
    'god',
    'goddam',
    'goddamn',
    'goddamned',
    'hardcoresex',
    'hell',
    'heshe',
    'hoar',
    'hoare',
    'hoer',
    'homo',
    'hore',
    'horniest',
    'horny',
    'hotsex',
    'jackoff',
    'jap',
    'jerkoff',
    'jism',
    'jiz',
    'jizm',
    'jizz',
    'kawk',
    'kike',
    'knob',
    'knobead',
    'knobed',
    'knobend',
    'knobhead',
    'knobjocky',
    'knobjokey',
    'kock',
    'kondum',
    'kondums',
    'kum',
    'kummer',
    'kumming',
    'kums',
    'kunilingus',
    'l3ich',
    'l3itch',
    'labia',
    'lmfao',
    'lust',
    'lusting',
    'masochist',
    'masterb8',
    'masterbat',
    'masterbat3',
    'masterbate',
    'masterbation',
    'masterbations',
    'masturbate',
    'mofo',
    'mothafuck',
    'mothafucka',
    'mothafuckas',
    'mothafuckaz',
    'mothafucked',
    'mothafucker',
    'mothafuckers',
    'mothafuckin',
    'mothafucking',
    'mothafuckings',
    'mothafucks',
    'mother fucker',
    'motherfuck',
    'motherfucked',
    'motherfucker',
    'motherfuckers',
    'motherfuckin',
    'motherfucking',
    'motherfuckings',
    'motherfuckka',
    'motherfucks',
    'muff',
    'mutha',
    'muthafecker',
    'muthafuckker',
    'muther',
    'mutherfucker',
    'nazi',
    'nigg3r',
    'nigga',
    'niggah',
    'niggas',
    'niggaz',
    'nigger',
    'niggers',
    'nob',
    'nob jokey',
    'nobhead',
    'nobjocky',
    'nobjokey',
    'numbnuts',
    'nutsack',
    'orgasim',
    'orgasims',
    'orgasm',
    'orgasms',
    'pawn',
    'pecker',
    'penis',
    'penisfucker',
    'phonesex',
    'phonesxx',
    'phuck',
    'phuk',
    'phuked',
    'phuking',
    'phukked',
    'phukking',
    'phuks',
    'phuq',
    'pigfucker',
    'pimpis',
    'piss',
    'pissed',
    'pisser',
    'pissers',
    'pisses',
    'pissflaps',
    'pissin',
    'pissing',
    'pissoff',
    'poop',
    'porn',
    'porno',
    'pornography',
    'pornos',
    'prick',
    'pricks',
    'pron',
    'pube',
    'pusse',
    'pussi',
    'pussies',
    'pussy',
    'pussys',
    'rectum',
    'retard',
    'rimjaw',
    'rimming',
    'russia',
    'sadist',
    'schlong',
    'screwing',
    'scroat',
    'scrote',
    'scrotum',
    'semen',
    'sex',
    'sxx',
    'shag',
    'shagger',
    'shaggin',
    'shagging',
    'shemale',
    'singles',
    'shit',
    'shitdick',
    'shite',
    'shited',
    'shitey',
    'shitfuck',
    'shitfull',
    'shithead',
    'shiting',
    'shitings',
    'shits',
    'shitted',
    'shitter',
    'shitters',
    'shitting',
    'shittings',
    'shitty',
    'skank',
    'slut',
    'sluts',
    'smegma',
    'smut',
    'snatch',
    'sob',
    'sonofabitch',
    'spac',
    'spic',
    'spunk',
    'teets',
    'teez',
    'testical',
    'testicle',
    'tit',
    'titfuck',
    'tits',
    'titt',
    'tittiefucker',
    'titties',
    'tittyfuck',
    'tittywank',
    'titwank',
    'tosser',
    'turd',
    'twat',
    'twathead',
    'twatty',
    'twunt',
    'twunter',
    'vagina',
    'viagra',
    'vigra',
    'vulva',
    'wang',
    'wank',
    'wanker',
    'wanky',
    'whoar',
    'whore',
    'willies',
    'willy',
    'woose',
    'xrated',
    'xxx'
]


PATTERN_SPECIAL_CHARACTER_SUBS = re.compile('|'.join(SPECIAL_CHARACTER_SUBS.keys()))
PATTERN_STARTS_WITH_BAD_WORD = re.compile(r'\b(%s)' % '|'.join(BAD_WORDS))
PATTERN_ENDS_WITH_BAD_WORD = re.compile(r'(%s)\b' % '|'.join(BAD_WORDS))
PATTERN_MATCHES_BAD_WORD = re.compile(r'\b(%s)\b' % '|'.join(BAD_WORDS))


def normalise_text(text, substitude_numbers=True, remove_numbers=True, remove_underscore=False):
    """
    Normalise given input text for matching bad words. This normalisation
    process is critical to find bad words even if those are specially encoded,
    for example like *fuck*, or f u c k.
    """
    if text:
        # only work with lowercase text
        text = text.lower()

        # substitude _ for spaces or remove
        if remove_underscore:
            text = re.sub('_', '', text)
        else:
            text = re.sub('_', ' ', text)

        # remove ! at the end of words otherwise we end up
        # substituting it with i.
        def match_exclamation_marks(m):
            return m.group(1) + ' '
        text = re.sub(r'(\w)!{1,}(\W|$)', match_exclamation_marks, text)

        # remove individual ! characters that are not part of a word
        text = re.sub(r'\W!{1,}(\W|$)', '', text)

        # remove multi-digit numbers, so that we do not substitute those
        if remove_numbers:
            text = re.sub(r'\d{2,}', '', text)

        # substitue certain special characters to corresponding letters
        if substitude_numbers:
            text = PATTERN_SPECIAL_CHARACTER_SUBS.sub(lambda x: SPECIAL_CHARACTER_SUBS[x.group()], text)

        # remove characters that are not letters or spaces
        text = re.sub(r'[^a-z\s]', '', text)

        # remove spaces between single or two-letter words
        words = text.split()
        normalised_words = []
        for word, next_word in zip(words, words[1:] + [' ']):
            normalised_words.append(word)
            after_long_word = len(word) > 2 or word in SHORT_STOP_WORDS
            before_long_word = len(next_word) > 2 or next_word in SHORT_STOP_WORDS
            if after_long_word or before_long_word:
                normalised_words.append(' ')
        text = ''.join(normalised_words)

        # remove double-spaces
        text = re.sub(r'\s{1,}', ' ', text)

        return text.strip()
    else:
        return ''


def _contains_bad_word(text, custom_words=None, substitude_numbers=True, remove_numbers=True, remove_underscore=False):
    """
    Return True, if the given text contains a bad word, where the given text is normalised
    by using the given options.
    """
    text = normalise_text(text, substitude_numbers, remove_numbers, remove_underscore)

    # standard cases (fast)
    if re.search(PATTERN_MATCHES_BAD_WORD, text):
        return True

    # custom cases (slow)
    if custom_words:
        pattern_matches = re.compile(r'\b(%s)\b' % '|'.join(custom_words))
        if re.search(pattern_matches, text):
            return True

    # unlikly to contain a bad word
    return False


def _get_bad_words(text, custom_words=None, substitude_numbers=True, remove_numbers=True, remove_underscore=False):
    """
    Return a list of bad words that are contained within the given text, where the given text
    is normalised by using the given options.
    """
    if custom_words is None:
        custom_words = []

    text = normalise_text(text, substitude_numbers, remove_numbers, remove_underscore)
    words = text.split()
    bad_words = set()

    for word in words:
        if word in BAD_WORDS or word in custom_words:
            bad_words.add(word)

    return bad_words


def contains_bad_word(text, custom_words=None):
    """
    Return True, if the given text contains a bad word.
    """
    for substitude_numbers in [True, False]:
        for remove_numbers in [True, False]:
            for remove_underscore in [True, False]:
                if _contains_bad_word(text, custom_words, substitude_numbers, remove_numbers, remove_underscore):
                    return True

    return False


def get_bad_words(text, custom_words=None):
    """
    Return a list of bad words that are contained within the given text.
    """
    bad_words = set()
    for substitude_numbers in [True, False]:
        for remove_numbers in [True, False]:
            for remove_underscore in [True, False]:
                bad_words.update(_get_bad_words(text, custom_words, substitude_numbers, remove_numbers, remove_underscore))
    return bad_words


def is_suspicious_username(username):
    """
    Return True, if the given username is suspicious.
    """
    return len(re.findall(r'[@_\.]', username)) > 1


_latin_letters = {}
def is_latin_ch(uchr):
    """
    Return True, if the given unicode character is a latin charactcer based on
    the unicode name of the given character.
    Based on: http://stackoverflow.com/questions/3094498/how-can-i-check-if-a-python-unicode-string-contains-non-western-letters
    """
    try:
        return _latin_letters[uchr]
    except KeyError:
         return _latin_letters.setdefault(uchr, 'LATIN' in unicodedata.name(uchr))


def is_latin(text):
    """
    Return True, if the given text is latin text and does not contain foreign
    languages characters, such as arabic or chinese.
    """
    if text:
        return all(is_latin_ch(uchr) for uchr in text if uchr.isalpha())
    else:
        return True