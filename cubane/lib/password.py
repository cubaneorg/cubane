# coding=UTF-8
# Adaption of:
# http://stackoverflow.com/questions/5501477/
# any-python-password-generators-that-are-readable-and-pronounceable
# originally written by Greg Haskins
from __future__ import unicode_literals
import string
import itertools
import random


INITIAL_CONSONANTS = (
    set(string.ascii_lowercase) - set('aeiou')

    # remove those easily confused with others
    - set('qxc')

    # add some crunchy clusters
    | set([
        'bl', 'br', 'cl', 'cr', 'dr', 'fl',
        'fr', 'gl', 'gr', 'pl', 'pr', 'sk',
        'sl', 'sm', 'sn', 'sp', 'st', 'str',
        'sw', 'tr'
    ])
)

FINAL_CONSONANTS = (
    set(string.ascii_lowercase) - set('aeiou')

    # confusable
    - set('qxcsj')

    # crunchy clusters
    | set([
        'ct', 'ft', 'mp', 'nd', 'ng', 'nk',
        'nt', 'pt', 'sk', 'sp', 'ss', 'st'
    ])
)

VOWELS = 'aeiou'

# each syllable is consonant-vowel-consonant "pronounceable"
SYLLABLES = map(
    ''.join,
    itertools.product(
        INITIAL_CONSONANTS,
        VOWELS,
        FINAL_CONSONANTS
    )
)


def gibberish(wordcount, wordlist=SYLLABLES):
    """
    Return a list of random pronounceable words.
    """
    return random.sample(wordlist, wordcount)


def get_pronounceable_password(wordcount=2, digitcount=2):
    """
    Return a new random pronounceable password.
    """
    numbermax = 10 ** digitcount
    password = ''.join(gibberish(wordcount))

    if digitcount >= 1:
        password += unicode(int(random.random() * numbermax))

    return password